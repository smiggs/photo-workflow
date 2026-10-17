"""Preserve camera-native samples and generate coordinate calibration evidence."""

import io
from pathlib import Path

import cv2
import numpy as np
import rawpy

from .coordinates import map_point, orientation_transform
from .inventory import raw_geometry
from .io import canonical_bytes, digest, file_digest, safe_child, validate_run_location
from .models import CoordinateTransform, DecodeOptions, DecodeReport, DecodedFrame, Inventory, Issue, Rectangle, StageResult, StageState
from .stages import inventory_stage, summary
from .storage import commit_stage, inspect_run, run_lock


def array_bytes(array):
    stream = io.BytesIO()
    np.save(stream, array, allow_pickle=False)
    return stream.getvalue()


def calibration(samples, geometry, orientation, white_level):
    height, width = samples.shape
    mapping = orientation_transform(width, height, orientation)
    points = [(0, 0), (width - 1, 0), (width - 1, height - 1), (0, height - 1),
              ((width - 1) / 2, (height - 1) / 2)]
    displayed = [map_point(mapping, point) for point in points]
    error = max(float(np.linalg.norm(np.subtract(map_point(mapping, projected, inverse=True), point)))
                for point, projected in zip(points, displayed))
    target_width = int(mapping.target_domain.width_px)
    target_height = int(mapping.target_domain.height_px)
    scale = min(1, 1024 / max(target_width, target_height))
    preview_width, preview_height = max(1, int(target_width * scale)), max(1, int(target_height * scale))
    scale_x = (preview_width - 1) / (target_width - 1) if target_width > 1 else 1
    scale_y = (preview_height - 1) / (target_height - 1) if target_height > 1 else 1
    preview_matrix = np.diag([scale_x, scale_y, 1]) @ np.asarray(mapping.matrix)
    grey = (np.clip(samples.astype(float) / white_level, 0, 1) * 255).astype(np.uint8)
    preview = cv2.warpPerspective(grey, preview_matrix, (preview_width, preview_height), flags=cv2.INTER_NEAREST)
    overlay = cv2.cvtColor(preview, cv2.COLOR_GRAY2BGR)
    for index, (x, y) in enumerate(displayed):
        location = (int(np.floor(x * scale_x + .5)), int(np.floor(y * scale_y + .5)))
        cv2.drawMarker(overlay, location, (0, 255, 255), cv2.MARKER_CROSS, 11, 1)
        cv2.putText(overlay, str(index + 1), location, cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 255, 255), 1)
    encoded, image = cv2.imencode('.png', overlay)
    if not encoded:
        raise ValueError('calibration image encoding failed')
    area = geometry.active_area
    raw_to_active = CoordinateTransform(source_space='raw_sensor', target_space='active_sensor',
        source_domain=Rectangle(width_px=geometry.raw_width_px, height_px=geometry.raw_height_px),
        target_domain=mapping.source_domain,
        matrix=((1, 0, -area.x_px), (0, 1, -area.y_px), (0, 0, 1)))
    active_to_detection = CoordinateTransform(source_space='active_sensor', target_space='decoded_detection',
        source_domain=mapping.source_domain, target_domain=mapping.source_domain,
        matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    preview_transform = mapping.model_copy(update={
        'matrix': tuple(tuple(float(value) for value in row) for row in preview_matrix),
        'target_domain': Rectangle(width_px=preview_width, height_px=preview_height)})
    return image.tobytes(), [raw_to_active, active_to_detection, preview_transform], error


def decode_stage(source: Path, run: Path, config, *, dry_run=False):
    run = validate_run_location(source, run)
    proposed = inventory_stage(source, run, config, dry_run=dry_run)
    if dry_run:
        return proposed | {'stage': 'decode-check', 'darktable_export_calibration': 'unverified'}
    with run_lock(run):
        manifest = inspect_run(run)
        inventory = Inventory.model_validate_json(safe_child(run, 'inventory.json').read_bytes())
        fingerprint = digest(canonical_bytes({'inventory': manifest.stages['inventory'].fingerprint_sha256,
                                             'decode_options': DecodeOptions().model_dump(mode='json')}))
        previous = manifest.stages.get('decode-check')
        if previous:
            if previous.fingerprint_sha256 != fingerprint:
                raise ValueError('decode configuration changed; use a new run directory')
            return summary(previous, reused=True)
        selected = []
        for cohort in inventory.cohorts:
            frames = [frame for frame in inventory.frames if frame.cohort_id == cohort.cohort_id]
            for orientation in sorted({frame.metadata.orientation for frame in frames}):
                ordered = sorted([frame for frame in frames if frame.metadata.orientation == orientation],
                                 key=lambda frame: (frame.metadata.captured_at_utc.isoformat()
                                     if frame.metadata.captured_at_utc else '', frame.frame_id))
                selected.extend(ordered[:config.representatives_per_cohort])
        artefacts, decoded = {}, []
        issues = [Issue(code='darktable_export_unverified', message='Darktable input/export mapping requires the capability spike and human calibration')]
        for frame in selected:
            path = safe_child(Path(inventory.source_root), frame.relative_paths[0])
            if file_digest(path) != frame.content_sha256:
                raise ValueError('source content no longer matches inventory')
            try:
                with rawpy.imread(str(path), shot_select=0) as raw:
                    geometry = raw_geometry(raw)
                    if geometry != frame.geometry:
                        raise ValueError('decoded geometry changed after inventory')
                    samples = raw.raw_image_visible.copy()
                    colours = raw.raw_colors_visible.copy().astype(np.uint8)
                    if samples.dtype != np.uint16:
                        raise ValueError('decoder returned an unsupported sample dtype')
                    black_levels = list(raw.black_level_per_channel)
                    white_level = raw.white_level
                overlay, transforms, error = calibration(samples, geometry, frame.metadata.orientation, white_level)
            except (rawpy.LibRawError, ValueError) as failure:
                issues.append(Issue(severity='error', code='decode_failed', message=str(failure),
                                    relative_path=frame.relative_paths[0]))
                continue
            if file_digest(path) != frame.content_sha256:
                raise ValueError('source changed during decoding')
            base = f'decode/{frame.frame_id}'
            samples_path, colours_path, overlay_path = f'{base}/samples.npy', f'{base}/cfa.npy', f'{base}/calibration.png'
            sample_data, colour_data = array_bytes(samples), array_bytes(colours)
            artefacts.update({samples_path: sample_data, colours_path: colour_data, overlay_path: overlay})
            decoded.append(DecodedFrame(frame_id=frame.frame_id, samples_path=samples_path,
                samples_sha256=digest(sample_data), samples_shape=samples.shape,
                cfa_path=colours_path, cfa_sha256=digest(colour_data), overlay_path=overlay_path,
                geometry=geometry, black_level_per_channel=black_levels, white_level=white_level,
                coordinate_transforms=transforms, round_trip_max_error_px=error))
        state = StageState.AWAITING_APPROVAL
        if not decoded:
            state = StageState.FAILED
        elif len(decoded) != len(selected) or any(frame.status == 'excluded' for frame in inventory.frames):
            state = StageState.PARTIAL
        report = DecodeReport(state=state, inventory_sha256=manifest.stages['inventory'].fingerprint_sha256,
                              frames=decoded, issues=issues)
        artefacts['decode-check.json'] = canonical_bytes(report.model_dump(mode='json'))
        result = StageResult(stage='decode-check', fingerprint_sha256=fingerprint, state=state,
            artefacts={name: digest(value) for name, value in artefacts.items()}, issues=issues,
            upstream_ids=[manifest.stages['inventory'].fingerprint_sha256],
            counts={'selected': len(selected), 'decoded': len(decoded)})
        updated = commit_stage(run, manifest, result, artefacts)
        return summary(updated.stages['decode-check'])
