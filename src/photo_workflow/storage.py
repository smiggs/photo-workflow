"""Commit stage artefacts before publishing a validated run manifest."""

import os
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

from .io import atomic_write, canonical_bytes, digest, file_digest, reject_symlinks, safe_child
from .models import CohortCollection, DecodeReport, Inventory, LogEvent, RawFrame, RunManifest, StageResult


@contextmanager
def run_lock(run: Path):
    reject_symlinks(run)
    owner = safe_child(run, '.photo-workflow-run')
    if not run.exists():
        run.mkdir(parents=True)
        atomic_write(owner, b'photo-workflow run format 1\n')
    elif not owner.is_file() or owner.read_bytes() != b'photo-workflow run format 1\n':
        raise ValueError('existing run directory is not owned by photo-workflow')
    lock = safe_child(run, '.run-lock')
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ValueError('run is locked; inspect the process and lock before recovery') from error
    try:
        os.write(descriptor, str(os.getpid()).encode())
        yield
    finally:
        os.close(descriptor)
        lock.unlink()


def inspect_run(run: Path) -> RunManifest:
    reject_symlinks(run)
    try:
        manifest = RunManifest.model_validate_json(safe_child(run, 'run-manifest.json').read_bytes())
        for result in manifest.stages.values():
            for name, expected in result.artefacts.items():
                if file_digest(safe_child(run, name)) != expected:
                    raise ValueError(f'artefact hash mismatch: {name}')
        if 'inventory' in manifest.stages:
            inventory = Inventory.model_validate_json(safe_child(run, 'inventory.json').read_bytes())
            frames = [RawFrame.model_validate_json(line) for line in
                      safe_child(run, 'frames.jsonl').read_bytes().splitlines()]
            cohorts = CohortCollection.model_validate_json(safe_child(run, 'cohorts.json').read_bytes())
            if frames != inventory.frames or cohorts.cohorts != inventory.cohorts:
                raise ValueError('inventory records disagree across artefacts')
            if inventory.source_root != manifest.source_root:
                raise ValueError('inventory and manifest source roots disagree')
            for frame in frames:
                for name in frame.relative_paths:
                    if file_digest(safe_child(Path(manifest.source_root), name)) != frame.content_sha256:
                        raise ValueError('source content no longer matches inventory')
            if inventory.configuration_sha256 != manifest.configuration_sha256:
                raise ValueError('inventory and manifest configuration disagree')
        if 'decode-check' in manifest.stages:
            DecodeReport.model_validate_json(safe_child(run, 'decode-check.json').read_bytes())
        return manifest
    except OSError as error:
        raise ValueError('run manifest or an artefact is missing/unreadable; do not reuse an interrupted run') from error


def commit_stage(run: Path, manifest: RunManifest, result: StageResult, artefacts: dict[str, bytes]):
    log_name = f'logs/{result.stage}.jsonl'
    log = LogEvent(timestamp_utc=datetime.now(timezone.utc), stage=result.stage,
                   state=result.state, fingerprint_sha256=result.fingerprint_sha256)
    log_data = canonical_bytes(log.model_dump(mode='json'))
    artefacts = artefacts | {log_name: log_data}
    result = StageResult.model_validate(result.model_dump(mode='json') | {
        'artefacts': result.artefacts | {log_name: digest(log_data)}})
    for name, data in artefacts.items():
        target = safe_child(run, name)
        if target.exists():
            raise ValueError(f'artefact already exists; use a new run directory: {name}')
        if digest(data) != result.artefacts[name]:
            raise ValueError('stage artefact does not match its declared hash')
    for name, data in artefacts.items():
        atomic_write(safe_child(run, name), data)
    updated = manifest.model_copy(update={'stages': manifest.stages | {result.stage: result}})
    # Revalidation prevents model_copy from bypassing the serialised contract.
    updated = RunManifest.model_validate(updated.model_dump(mode='json'))
    atomic_write(safe_child(run, 'run-manifest.json'), canonical_bytes(updated.model_dump(mode='json')))
    return updated
