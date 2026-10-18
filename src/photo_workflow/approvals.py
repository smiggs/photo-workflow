"""Prepare review evidence and record explicit, immutable human decisions."""

from pathlib import Path

from .io import atomic_write, canonical_bytes, digest, file_digest, safe_child, validate_run_location
from .models import DecodeReport, Inventory, ReviewDecision, ReviewPacket, ReviewScope, RunManifest
from .storage import inspect_run, run_lock
from .tools import discover_tools

CHECKPOINTS = ('cohort-rules', 'coordinate-contract')


def record_bytes(record):
    return canonical_bytes(record.model_dump(mode='json'))


def verify_environment(manifest):
    if discover_tools(30) != manifest.tools:
        raise ValueError('implementation or tool fingerprints changed; use a new run directory')


def build_packet(run, manifest, checkpoint):
    inventory = Inventory.model_validate_json(safe_child(run, 'inventory.json').read_bytes())
    hashes = {'run': manifest.run_id, 'configuration': manifest.configuration_sha256,
              'tools': digest(canonical_bytes([tool.model_dump(mode='json') for tool in manifest.tools])),
              'inventory': file_digest(safe_child(run, 'inventory.json'))}
    for stage, result in sorted(manifest.stages.items()):
        hashes[f'stage:{stage}'] = result.fingerprint_sha256
        hashes.update({f'artefact:{name}': value for name, value in result.artefacts.items()})
    blockers = []
    spaces = ['raw_sensor', 'active_sensor', 'decoded_detection', 'preview']
    if not inventory.cohorts:
        blockers.append('no_reviewable_cohorts')
    if any(issue.severity == 'error' for issue in inventory.issues):
        blockers.append('inventory_errors_require_resolution')
    if checkpoint == 'coordinate-contract':
        # This version cannot qualify darktable geometry, regardless of a decision file.
        blockers.append('darktable_export_calibration_unverified')
        if 'decode-check' not in manifest.stages:
            blockers.append('decode_evidence_missing')
    if 'decode-check' in manifest.stages:
        report = DecodeReport.model_validate_json(safe_child(run, 'decode-check.json').read_bytes())
        hashes['transforms'] = digest(canonical_bytes({
            frame.frame_id: [transform.model_dump(mode='json') for transform in frame.coordinate_transforms]
            for frame in report.frames}))
        if checkpoint == 'coordinate-contract':
            covered = {frame.frame_id for frame in report.frames}
            expected = {(frame.cohort_id, frame.metadata.orientation) for frame in inventory.frames
                        if frame.cohort_id is not None}
            actual = {(frame.cohort_id, frame.metadata.orientation) for frame in inventory.frames
                      if frame.frame_id in covered}
            if not expected or expected != actual or any(i.severity == 'error' for i in report.issues):
                blockers.append('decode_coverage_incomplete')
    coverage = [{'frame_id': frame.frame_id, 'cohort_id': frame.cohort_id,
                 'make': frame.metadata.make, 'model': frame.metadata.model,
                 'body_serial': frame.metadata.body_serial, 'orientation': frame.metadata.orientation,
                 'readout_mode': frame.metadata.readout_mode,
                 'exclusion_reasons': frame.exclusion_reasons}
                for frame in inventory.frames]
    return ReviewPacket(run_id=manifest.run_id, checkpoint=checkpoint,
        scope=ReviewScope(cohort_ids=sorted(cohort.cohort_id for cohort in inventory.cohorts),
                          coordinate_spaces=spaces if checkpoint == 'coordinate-contract' else []),
        input_hashes=hashes, evidence_paths=sorted({name for result in manifest.stages.values()
                                                 for name in result.artefacts}),
        camera_coverage=coverage, blockers=blockers,
        limitations=['Camera coverage describes recorded metadata; a human must establish intended real-camera coverage.',
                     'Native preview markers do not validate full-resolution darktable repair support.',
                     'Darktable input, final export and nonlinear lens mappings remain unsupported.',
                     'Cohort approval does not approve coordinates or release Package 01.'])


def packet_path(packet_hash):
    return f'reviews/{packet_hash}.json'


def decision_path(decision_hash):
    return f'approvals/{decision_hash}.json'


def validate_records(run: Path, manifest: RunManifest):
    """Check published records; uncommitted files never contribute a decision."""
    latest = {}
    for decision in manifest.approvals:
        if not isinstance(decision, ReviewDecision):
            continue  # Legacy records lack packet/scope binding and cannot open these gates.
        decision_hash = digest(record_bytes(decision))
        if safe_child(run, decision_path(decision_hash)).read_bytes() != record_bytes(decision):
            raise ValueError('approval record hash mismatch')
        data = safe_child(run, packet_path(decision.packet_sha256)).read_bytes()
        if digest(data) != decision.packet_sha256:
            raise ValueError('review packet hash mismatch')
        packet = ReviewPacket.model_validate_json(data)
        if (decision.run_id != manifest.run_id or decision.run_id != packet.run_id
                or decision.checkpoint != packet.checkpoint or decision.scope != packet.scope
                or decision.input_hashes != packet.input_hashes):
            raise ValueError('approval does not match its review packet')
        if decision.decision == 'approved' and packet.blockers:
            raise ValueError('approval attempts to bypass a blocked checkpoint')
        previous = latest.get(decision.checkpoint)
        expected = digest(record_bytes(previous)) if previous else None
        if decision.supersedes_sha256 != expected:
            raise ValueError('approval supersession must name the latest decision for this checkpoint')
        if previous and decision.timestamp_utc < previous.timestamp_utc:
            raise ValueError('superseding decision predates the previous decision')
        latest[decision.checkpoint] = decision
    return latest


def review_status(run, manifest):
    latest = validate_records(run, manifest)
    environment_matches = True
    if latest:
        environment_matches = discover_tools(30) == manifest.tools
    statuses = {}
    for checkpoint in CHECKPOINTS:
        packet = build_packet(run, manifest, checkpoint)
        decision = latest.get(checkpoint)
        state = 'awaiting_approval'
        if decision:
            state = decision.decision if (environment_matches and
                decision.packet_sha256 == digest(record_bytes(packet))) else 'stale'
        statuses[checkpoint] = {'state': state, 'blockers': packet.blockers,
            'cohorts': {cohort: state for cohort in packet.scope.cohort_ids}}
    return statuses


def review_packet(run: Path, checkpoint: str, *, dry_run=False):
    manifest = inspect_run(run)
    run = validate_run_location(Path(manifest.source_root), run)
    with run_lock(run):
        manifest = inspect_run(run)
        verify_environment(manifest)
        packet = build_packet(run, manifest, checkpoint)
        data = record_bytes(packet)
        packet_hash = digest(data)
        name = packet_path(packet_hash)
        if not dry_run:
            target = safe_child(run, name)
            if target.exists():
                if target.read_bytes() != data:
                    raise ValueError('existing review packet is inconsistent')
            else:
                atomic_write(target, data)
        latest = validate_records(run, manifest).get(checkpoint)
        template = {'schema_version': 1, 'run_id': manifest.run_id, 'checkpoint': checkpoint,
                    'packet_sha256': packet_hash, 'scope': packet.scope.model_dump(mode='json'),
                    'input_hashes': packet.input_hashes, 'reviewer': None, 'decision': None,
                    'timestamp_utc': None, 'reason': None,
                    'supersedes_sha256': digest(record_bytes(latest)) if latest else None}
        return {'packet': packet.model_dump(mode='json'), 'packet_sha256': packet_hash,
                'packet_path': name, 'decision_template': template, 'dry_run': dry_run}


def approve(run: Path, checkpoint: str, decision_file: Path, *, dry_run=False):
    try:
        decision = ReviewDecision.model_validate_json(decision_file.read_bytes())
    except OSError as error:
        raise ValueError('human decision file is missing or unreadable') from error
    manifest = inspect_run(run)
    run = validate_run_location(Path(manifest.source_root), run)
    with run_lock(run):
        manifest = inspect_run(run)
        verify_environment(manifest)
        packet = build_packet(run, manifest, checkpoint)
        if (decision.checkpoint != checkpoint or decision.run_id != manifest.run_id
                or decision.packet_sha256 != digest(record_bytes(packet))
                or decision.scope != packet.scope or decision.input_hashes != packet.input_hashes):
            raise ValueError('decision does not match the current checkpoint packet and fingerprints')
        stored_packet = safe_child(run, packet_path(decision.packet_sha256))
        if not stored_packet.is_file() or stored_packet.read_bytes() != record_bytes(packet):
            raise ValueError('review packet is missing or changed; prepare and review it first')
        if decision.decision == 'approved' and packet.blockers:
            raise ValueError('checkpoint is blocked: ' + ', '.join(packet.blockers))
        data = record_bytes(decision)
        decision_hash = digest(data)
        name = decision_path(decision_hash)
        target = safe_child(run, name)
        if target.exists():
            raise ValueError('decision artefact already exists; inspect it before recovery')
        updated = RunManifest.model_validate(manifest.model_dump(mode='json') | {
            'approvals': [item.model_dump(mode='json') for item in manifest.approvals] +
                         [decision.model_dump(mode='json')]})
        # Validate the chain before writing anything, then publish the manifest last.
        latest = validate_records(run, manifest).get(checkpoint)
        expected = digest(record_bytes(latest)) if latest else None
        if decision.supersedes_sha256 != expected:
            raise ValueError('supersedes_sha256 must name the latest decision for this checkpoint')
        if latest and decision.timestamp_utc < latest.timestamp_utc:
            raise ValueError('superseding decision predates the previous decision')
        if not dry_run:
            atomic_write(target, data)
            atomic_write(safe_child(run, 'run-manifest.json'), record_bytes(updated))
        return {'decision_sha256': decision_hash, 'decision_path': name, 'dry_run': dry_run,
                'review_status': review_status(run, updated if not dry_run else manifest)}
