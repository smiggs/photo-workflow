import json
import shutil

from photo_workflow.cli import main
from photo_workflow.io import file_digest
from photo_workflow.models import RunManifest


def test_inventory_groups_duplicates_and_preserves_raws(raw_batch, metadata_tool, tmp_path, capsys):
    source, _ = raw_batch
    shutil.copyfile(source / 'landscape ü.dng', source / 'same content.dng')
    (source / 'broken.nef').write_bytes(b'not a raw')
    (source / 'unexpected.dng').symlink_to(source / 'landscape ü.dng')
    before = {p.name: file_digest(p) for p in source.iterdir() if not p.is_symlink()}
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run), '--json']) == 4
    result = json.loads(capsys.readouterr().out)
    assert result['state'] == 'partial'
    inventory = json.loads((run / 'inventory.json').read_text())
    assert len(inventory['frames']) == 2
    good = next(f for f in inventory['frames'] if f['status'] == 'unreviewed')
    assert len(good['relative_paths']) == 2
    assert good['metadata']['body_serial'] == 'BODY-1'
    assert good['metadata']['lens']['focal_length_mm'] == 50
    assert inventory['cohorts'][0]['review_status'] == 'unreviewed'
    assert RunManifest.model_validate_json((run / 'run-manifest.json').read_bytes()).approvals == []
    saved = (run / 'inventory.json').read_bytes()
    assert main(['inventory', str(source), '--run-dir', str(run), '--json']) == 4
    assert (run / 'inventory.json').read_bytes() == saved
    assert main(['inspect-run', str(run), '--json']) == 0
    assert before == {p.name: file_digest(p) for p in source.iterdir() if not p.is_symlink()}


def test_missing_serial_is_excluded_rather_than_merged(raw_batch, metadata_tool, tmp_path):
    source, _ = raw_batch
    (source / 'landscape ü.dng').rename(source / 'unknown body.dng')
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 4
    data = json.loads((run / 'inventory.json').read_text())
    assert data['cohorts'] == []
    assert data['frames'][0]['exclusion_reasons'] == ['missing_body_identity']


def test_dry_run_and_unsafe_destination_make_no_writes(raw_batch, tmp_path):
    source, _ = raw_batch
    run = tmp_path / 'not created'
    assert main(['inventory', str(source), '--run-dir', str(run), '--dry-run']) == 0
    assert not run.exists()
    assert main(['decode-check', str(source), '--run-dir', str(source / 'unsafe')]) == 2
    assert not (source / 'unsafe').exists()


def test_inspection_rejects_tampering_and_rerun_rejects_changed_inputs(raw_batch, metadata_tool, tmp_path):
    source, _ = raw_batch
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 0
    original = (run / 'run-manifest.json').read_bytes()
    (run / 'frames.jsonl').write_text('corrupt')
    assert main(['inspect-run', str(run)]) == 2
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 2
    assert (run / 'run-manifest.json').read_bytes() == original


def test_existing_unowned_run_directory_is_rejected(raw_batch, metadata_tool, tmp_path):
    source, _ = raw_batch
    run = tmp_path / 'run'
    run.mkdir()
    (run / 'inventory.json').write_text('valuable unrelated file')
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 2
    assert (run / 'inventory.json').read_text() == 'valuable unrelated file'


def test_failure_before_manifest_commit_cannot_look_complete(raw_batch, metadata_tool, tmp_path, monkeypatch):
    from photo_workflow import storage
    source, _ = raw_batch
    run = tmp_path / 'run'
    write = storage.atomic_write
    def interrupt(path, data):
        if path.name == 'run-manifest.json':
            raise OSError('simulated interruption')
        return write(path, data)
    monkeypatch.setattr(storage, 'atomic_write', interrupt)
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 5
    assert not (run / 'run-manifest.json').exists()
    assert main(['inspect-run', str(run)]) == 2


def test_changed_configuration_is_not_reused(raw_batch, metadata_tool, tmp_path):
    source, _ = raw_batch
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 0
    settings = tmp_path / 'config.json'
    settings.write_text('{"tool_timeout_seconds": 12}')
    assert main(['inventory', str(source), '--run-dir', str(run), '--config', str(settings)]) == 2
    assert main(['inspect-run', str(run), '--config', str(settings)]) == 2


def test_missing_exiftool_is_reported_without_a_run(raw_batch, tmp_path, monkeypatch):
    from photo_workflow import tools
    source, _ = raw_batch
    lookup = tools.shutil.which
    monkeypatch.setattr(tools.shutil, 'which', lambda command: None if command == 'exiftool' else lookup(command))
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 3
    assert not run.exists()


def test_missing_darktable_is_only_a_capability_warning(raw_batch, metadata_tool, tmp_path, monkeypatch):
    from photo_workflow import tools
    source, _ = raw_batch
    lookup = tools.shutil.which
    monkeypatch.setattr(tools.shutil, 'which', lambda command: None if command == 'darktable-cli' else lookup(command))
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 0
    data = json.loads((run / 'inventory.json').read_text())
    assert any(issue['code'] == 'darktable_unavailable' for issue in data['issues'])
    assert main(['decode-check', str(source), '--run-dir', str(run)]) == 0


def test_structured_stage_logs_do_not_include_source_paths(raw_batch, metadata_tool, tmp_path):
    source, _ = raw_batch
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 0
    entries = [json.loads(line) for line in (run / 'logs/inventory.jsonl').read_text().splitlines()]
    assert entries[-1]['event'] == 'stage_committed'
    from datetime import datetime
    assert datetime.fromisoformat(entries[-1]['timestamp_utc']).utcoffset().total_seconds() == 0
    assert str(source) not in (run / 'logs/inventory.jsonl').read_text()


def test_all_corrupt_inputs_have_a_distinct_exit_code(tmp_path, metadata_tool):
    source = tmp_path / 'raw'
    source.mkdir()
    (source / 'broken.nef').write_bytes(b'not raw')
    assert main(['inventory', str(source), '--run-dir', str(tmp_path / 'run')]) == 6


def test_inspection_checks_current_source_hashes(raw_batch, metadata_tool, tmp_path):
    source, _ = raw_batch
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 0
    path = source / 'landscape ü.dng'
    path.write_bytes(path.read_bytes() + b'changed')
    assert main(['inspect-run', str(run)]) == 2


def test_unreadable_sources_are_reported_as_partial(raw_batch, metadata_tool, tmp_path, monkeypatch):
    from photo_workflow import inventory
    source, _ = raw_batch
    path = source / 'unreadable.nef'
    path.write_bytes(b'denied')
    original = inventory.file_digest
    def unreadable(candidate):
        if candidate == path:
            raise PermissionError('denied')
        return original(candidate)
    monkeypatch.setattr(inventory, 'file_digest', unreadable)
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run)]) == 4
    data = json.loads((run / 'inventory.json').read_text())
    assert any(issue['code'] == 'unreadable_source' and issue['relative_path'] == 'unreadable.nef'
               for issue in data['issues'])


def test_missing_metadata_offset_is_preserved_without_guessing(tmp_path):
    from photo_workflow.inventory import read_metadata
    import sys
    script = tmp_path / 'metadata'
    script.write_text('#!' + sys.executable + '\nimport json\nprint(json.dumps([dict(Make="Fixture", Model="Body", SerialNumber="1", Orientation=1, DateTimeOriginal="2026:01:02 03:04:05")]))\n')
    script.chmod(0o755)
    data = read_metadata(tmp_path / 'raw.nef', str(script), 2)
    assert data.captured_at_local == '2026:01:02 03:04:05'
    assert data.captured_at_utc is None


def test_dng_camera_serial_tag_identifies_the_body(tmp_path):
    from photo_workflow.inventory import read_metadata
    import sys
    script = tmp_path / 'metadata'
    script.write_text('#!' + sys.executable + '\nimport json\nprint(json.dumps([dict(Make="Fixture", Model="Body", CameraSerialNumber="DNG-BODY", Orientation=1)]))\n')
    script.chmod(0o755)
    assert read_metadata(tmp_path / 'raw.dng', str(script), 2).body_serial == 'DNG-BODY'


def test_missing_source_is_validation_error_without_a_run(tmp_path):
    run = tmp_path / 'run'
    assert main(['inventory', str(tmp_path / 'missing'), '--run-dir', str(run)]) == 2
    assert not run.exists()


def test_read_only_raw_and_existing_sidecar_are_unchanged(raw_batch, metadata_tool, tmp_path):
    source, _ = raw_batch
    raw = source / 'landscape ü.dng'
    sidecar = source / 'landscape ü.dng.xmp'
    sidecar.write_text('existing unrelated edit')
    raw.chmod(0o444)
    sidecar.chmod(0o444)
    before = {path.name: file_digest(path) for path in source.iterdir()}
    assert main(['decode-check', str(source), '--run-dir', str(tmp_path / 'run')]) == 0
    assert {path.name: file_digest(path) for path in source.iterdir()} == before
