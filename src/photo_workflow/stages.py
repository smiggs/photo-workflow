"""Importable command operations and stage fingerprints."""

from pathlib import Path

from .inventory import build_inventory, enumerate_raws
from .io import canonical_bytes, digest, validate_run_location
from .models import CohortCollection, RunManifest, StageResult, StageState
from .storage import commit_stage, inspect_run, run_lock
from .tools import discover_tools


def inventory_stage(source: Path, run: Path, config, *, dry_run=False):
    run = validate_run_location(source, run)
    if dry_run:
        root, files, issues = enumerate_raws(source, config.raw_extensions)
        if not files:
            raise ValueError('no supported regular raw files found')
        return {'stage': 'inventory', 'dry_run': True, 'source_root': str(root),
                'files': [path.relative_to(root).as_posix() for path in files],
                'run_directory': str(run), 'issues': [issue.model_dump(mode='json') for issue in issues]}
    tools = discover_tools(config.tool_timeout_seconds)
    inventory = build_inventory(source, config, tools)
    data = canonical_bytes(inventory.model_dump(mode='json'))
    fingerprint = digest(data)
    with run_lock(run):
        if (run / 'run-manifest.json').exists():
            manifest = inspect_run(run)
            previous = manifest.stages.get('inventory')
            if previous is None or previous.fingerprint_sha256 != fingerprint:
                raise ValueError('inventory inputs/configuration/tools changed; use a new run directory')
            return summary(previous, reused=True)
        if any(child.name not in {'.photo-workflow-run', '.run-lock'} for child in run.iterdir()):
            raise ValueError('interrupted run has uncommitted artefacts; inspect it and use a new run directory')
        artefacts = {'inventory.json': data,
                     'frames.jsonl': b''.join(canonical_bytes(frame.model_dump(mode='json')) for frame in inventory.frames),
                     'cohorts.json': canonical_bytes(CohortCollection(cohorts=inventory.cohorts).model_dump(mode='json'))}
        state = StageState.PARTIAL if (any(frame.status == 'excluded' for frame in inventory.frames)
            or any(issue.severity == 'error' for issue in inventory.issues)) else StageState.AWAITING_APPROVAL
        if inventory.frames and all('corrupt_or_unsupported_raw' in frame.exclusion_reasons for frame in inventory.frames):
            state = StageState.FAILED
        result = StageResult(stage='inventory', fingerprint_sha256=fingerprint, state=state,
                             artefacts={name: digest(value) for name, value in artefacts.items()}, issues=inventory.issues,
                             counts={'frames': len(inventory.frames), 'cohorts': len(inventory.cohorts),
                                     'excluded': sum(frame.status == 'excluded' for frame in inventory.frames)})
        manifest = RunManifest(run_id=digest(canonical_bytes({'root': inventory.source_root, 'inventory': fingerprint})),
                               source_root=inventory.source_root,
                               configuration_sha256=inventory.configuration_sha256, tools=tools)
        updated = commit_stage(run, manifest, result, artefacts)
        return summary(updated.stages['inventory'])


def summary(result: StageResult, *, reused=False):
    return {'stage': result.stage, 'state': result.state.value, 'reused': reused,
            'fingerprint_sha256': result.fingerprint_sha256, 'artefacts': result.artefacts,
            'issues': [issue.model_dump(mode='json') for issue in result.issues],
            'counts': result.counts, 'human_approval_required': True}
