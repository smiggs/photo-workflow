"""Read source metadata and raw geometry without editing source files."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import rawpy
from pydantic import ValidationError

from .io import canonical_bytes, digest, file_digest, reject_symlinks
from .models import CaptureMetadata, Cohort, ImageGeometry, Inventory, Issue, LensState, RawFrame, Rectangle
from .tools import ToolFailure, run_command

METADATA_TAGS = (
    'Make', 'Model', 'SerialNumber', 'BodySerialNumber', 'CameraSerialNumber',
    'InternalSerialNumber', 'DateTimeOriginal',
    'SubSecDateTimeOriginal', 'OffsetTimeOriginal', 'Orientation', 'LensModel',
    'FocalLength', 'FNumber', 'FocusDistance', 'CropMode', 'DefaultCropOrigin',
    'DefaultCropSize', 'ActiveArea',
)


def enumerate_raws(source: Path, extensions: tuple[str, ...]):
    source = reject_symlinks(source).resolve(strict=True)
    issues = []
    if source.is_file():
        if source.suffix.lower() not in extensions:
            raise ValueError('input file has an unsupported raw extension')
        return source.parent, [source], issues
    if not source.is_dir():
        raise ValueError('input must be a file or directory')
    files = []
    def walk_error(error):
        raise ValueError('cannot enumerate source directory') from error
    for directory, directories, names in os.walk(source, followlinks=False, onerror=walk_error):
        for name in list(directories):
            path = Path(directory) / name
            if path.is_symlink():
                directories.remove(name)
                issues.append(Issue(code='symlink_skipped', message='Directory symlink was not followed',
                                    relative_path=path.relative_to(source).as_posix()))
        for name in names:
            path = Path(directory) / name
            if path.suffix.lower() not in extensions:
                continue
            if path.is_symlink():
                issues.append(Issue(code='symlink_skipped', message='File symlink was not followed',
                                    relative_path=path.relative_to(source).as_posix()))
            elif path.is_file():
                files.append(path)
    return source, sorted(files), sorted(issues, key=lambda issue: issue.relative_path)


def read_metadata(path: Path, executable: str, timeout: float) -> CaptureMetadata:
    result = run_command([executable, '-json', '-n', *[f'-{tag}' for tag in METADATA_TAGS],
                          '--', str(path)], timeout)
    records = json.loads(result.stdout)
    if not isinstance(records, list) or len(records) != 1 or not isinstance(records[0], dict):
        raise ValueError('metadata tool must return exactly one object')
    record = records[0]
    if 'Error' in record:
        raise ValueError('metadata tool reported an error')
    fields = {key: record[key] for key in METADATA_TAGS if key in record}
    local = fields.get('SubSecDateTimeOriginal') or fields.get('DateTimeOriginal')
    captured = None
    if local:
        iso = str(local)[:10].replace(':', '-') + str(local)[10:].replace(' ', 'T', 1)
        if fields.get('OffsetTimeOriginal') and not ('+' in iso[10:] or '-' in iso[10:] or iso.endswith('Z')):
            iso += str(fields['OffsetTimeOriginal'])
        parsed = datetime.fromisoformat(iso)
        if parsed.tzinfo:
            captured = parsed.astimezone(timezone.utc)
    return CaptureMetadata(make=fields.get('Make'), model=fields.get('Model'),
        body_serial=str(fields.get('BodySerialNumber') or fields.get('CameraSerialNumber')
                        or fields.get('SerialNumber') or fields.get('InternalSerialNumber') or '') or None,
        captured_at_local=str(local) if local else None, captured_at_utc=captured,
        orientation=fields.get('Orientation'), readout_mode=str(fields['CropMode']) if 'CropMode' in fields else None,
        lens=LensState(lens=fields.get('LensModel'), focal_length_mm=fields.get('FocalLength'),
                       aperture_f_number=fields.get('FNumber'), focus_distance_m=fields.get('FocusDistance')),
        source_fields=fields)


def raw_geometry(raw) -> ImageGeometry:
    sizes = raw.sizes
    if raw.raw_image_visible.ndim != 2 or raw.raw_pattern is None:
        raise ValueError('only flat CFA raw images are supported by coordinate contract 1')
    if raw.raw_image_visible.shape != (sizes.height, sizes.width):
        raise ValueError('decoder geometry differs from visible sample dimensions')
    return ImageGeometry(raw_width_px=sizes.raw_width, raw_height_px=sizes.raw_height,
        active_area=Rectangle(x_px=sizes.left_margin, y_px=sizes.top_margin,
                              width_px=sizes.width, height_px=sizes.height),
        cfa_pattern=raw.raw_pattern.tolist(),
        colour_description=raw.color_desc.decode('ascii'), decoder_flip=sizes.flip)


def build_inventory(source: Path, config, tools) -> Inventory:
    root, paths, issues = enumerate_raws(source, config.raw_extensions)
    if not paths:
        raise ValueError('no supported regular raw files found')
    metadata_tool = next(tool for tool in tools if tool.name == 'exiftool')
    if not metadata_tool.available:
        raise ToolFailure('ExifTool is required for inventory; install exiftool')
    if not next(tool for tool in tools if tool.name == 'rawpy').available:
        raise ToolFailure('rawpy is required for inventory')
    if not next(tool for tool in tools if tool.name == 'darktable').available:
        issues.append(Issue(code='darktable_unavailable', message='Darktable is unavailable; inventory and native decoding remain supported'))
    contents = {}
    for path in paths:
        try:
            reject_symlinks(path)
            fingerprint = file_digest(path)
            contents.setdefault(fingerprint, []).append(path)
        except OSError:
            issues.append(Issue(severity='error', code='unreadable_source', message='Source file cannot be read',
                                relative_path=path.relative_to(root).as_posix()))
    frames = []
    groups = {}
    for fingerprint, duplicates in sorted(contents.items()):
        path = duplicates[0]
        relative_paths = [item.relative_to(root).as_posix() for item in duplicates]
        metadata = CaptureMetadata()
        geometry = None
        reasons = []
        try:
            metadata = read_metadata(path, metadata_tool.executable_path, config.tool_timeout_seconds)
        except (ToolFailure, ValueError, ValidationError):
            reasons.append('invalid_metadata')
        try:
            with rawpy.imread(str(path), shot_select=0) as raw:
                geometry = raw_geometry(raw)
        except (rawpy.LibRawError, ValueError):
            reasons.append('corrupt_or_unsupported_raw')
        if not metadata.body_serial and 'invalid_metadata' not in reasons:
            reasons.append('missing_body_identity')
        if metadata.orientation is None and 'invalid_metadata' not in reasons:
            reasons.append('missing_orientation')
        if not metadata.make or not metadata.model:
            reasons.append('missing_camera_model')
        if metadata.captured_at_utc is None:
            issues.append(Issue(code='ambiguous_capture_time', message='Capture order has no verified UTC time',
                                relative_path=relative_paths[0]))
        if len(duplicates) > 1:
            issues.append(Issue(code='duplicate_content', message='Identical raw content shares one frame ID',
                                relative_path=relative_paths[0]))
        cohort_id = None
        if not reasons:
            facts = dict(body_serial=metadata.body_serial, make=metadata.make, model=metadata.model,
                         geometry=geometry.model_dump(mode='json', exclude={'decoder_flip'}),
                         readout_mode=metadata.readout_mode,
                         crop_metadata={key: metadata.source_fields[key] for key in
                                        ['DefaultCropOrigin', 'DefaultCropSize', 'ActiveArea']
                                        if key in metadata.source_fields},
                         decoder=next(tool.model_dump(mode='json') for tool in tools if tool.name == 'rawpy'),
                         coordinate_contract_version='1')
            cohort_id = digest(canonical_bytes(facts))
            group = groups.setdefault(cohort_id, {'facts': facts, 'frame_ids': []})
            group['frame_ids'].append(fingerprint)
        frames.append(RawFrame(frame_id=fingerprint, content_sha256=fingerprint,
            relative_paths=relative_paths, size_bytes=path.stat().st_size, metadata=metadata,
            geometry=geometry, cohort_id=cohort_id, status='excluded' if reasons else 'unreviewed',
            exclusion_reasons=reasons))
        if file_digest(path) != fingerprint:
            raise ValueError('source changed while inventory was being built')
    for fingerprint, duplicates in contents.items():
        if any(file_digest(path) != fingerprint for path in duplicates):
            raise ValueError('a duplicate source changed during inventory')
    if len({frame.metadata.body_serial for frame in frames if frame.metadata.body_serial}) > 1:
        issues.append(Issue(code='mixed_camera_bodies', message='Multiple physical bodies require separate cohorts'))
    timestamps = [frame.metadata.captured_at_utc for frame in frames if frame.metadata.captured_at_utc]
    if len(timestamps) != len(set(timestamps)):
        issues.append(Issue(code='ambiguous_capture_order', message='Distinct frames share a capture timestamp'))
    return Inventory(source_root=str(root),
        input_sha256=digest(canonical_bytes([{'sha256': frame.content_sha256, 'paths': frame.relative_paths}
                                           for frame in frames])),
        configuration_sha256=digest(canonical_bytes(config.model_dump(mode='json'))),
        tools=tools, frames=frames,
        cohorts=[Cohort(cohort_id=key, frame_ids=value['frame_ids'], compatibility_facts=value['facts'])
                 for key, value in sorted(groups.items())], issues=issues)
