"""Synthetic human decisions exercise storage, never approve camera evidence."""

import json

import pytest

from photo_workflow.cli import main
from photo_workflow.io import canonical_bytes, digest


def packet_for(run, checkpoint, capsys):
    assert main(['review-packet', str(run), checkpoint, '--json']) == 0
    return json.loads(capsys.readouterr().out)


def decision_for(packet, *, decision='approved', supersedes=None):
    return packet['decision_template'] | {
        'reviewer': 'Synthetic test reviewer', 'decision': decision,
        'timestamp_utc': '2026-10-18T12:00:00Z',
        'reason': 'Synthetic fixture decision; no real camera approval.',
        'supersedes_sha256': supersedes,
    }


@pytest.fixture
def inventoried_run(raw_batch, metadata_tool, tmp_path, capsys):
    source, _ = raw_batch
    run = tmp_path / 'run'
    assert main(['inventory', str(source), '--run-dir', str(run), '--json']) == 0
    capsys.readouterr()
    return source, run


def submit(run, decision, tmp_path, capsys):
    path = tmp_path / 'decision.json'
    path.write_bytes(canonical_bytes(decision))
    code = main(['approve', str(run), decision['checkpoint'], str(path), '--json'])
    return code, json.loads(capsys.readouterr().out)


def test_packet_requires_explicit_decision_and_derives_cohort_review(inventoried_run, tmp_path, capsys):
    source, run = inventoried_run
    original = (run / 'inventory.json').read_bytes()
    packet = packet_for(run, 'cohort-rules', capsys)
    assert packet['decision_template']['decision'] is None
    assert packet['packet']['scope']['cohort_ids']
    assert packet['packet']['scope']['coordinate_contract_version'] == '1'
    assert packet['packet']['input_hashes']['inventory'] == digest(original)
    assert main(['inspect-run', str(run), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['review_status']['cohort-rules']['state'] == 'awaiting_approval'
    code, result = submit(run, packet['decision_template'], tmp_path, capsys)
    assert code == 2
    code, result = submit(run, decision_for(packet), tmp_path, capsys)
    assert code == 0
    assert result['review_status']['cohort-rules']['state'] == 'approved'
    assert (run / 'inventory.json').read_bytes() == original
    assert main(['inspect-run', str(run), '--json']) == 0
    status = json.loads(capsys.readouterr().out)
    assert status['review_status']['cohort-rules']['cohorts'] == {
        cohort: 'approved' for cohort in packet['packet']['scope']['cohort_ids']}
    assert status['review_status']['coordinate-contract']['state'] == 'awaiting_approval'


def test_rejection_and_explicit_supersession_preserve_previous_record(inventoried_run, tmp_path, capsys):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    code, rejected = submit(run, decision_for(packet, decision='rejected'), tmp_path, capsys)
    assert code == 0
    assert rejected['review_status']['cohort-rules']['state'] == 'rejected'
    old_path = run / rejected['decision_path']
    old_data = old_path.read_bytes()
    assert submit(run, decision_for(packet), tmp_path, capsys)[0] == 2
    approved = decision_for(packet, supersedes=rejected['decision_sha256'])
    code, result = submit(run, approved, tmp_path, capsys)
    assert code == 0
    assert old_path.read_bytes() == old_data
    assert result['review_status']['cohort-rules']['state'] == 'approved'
    assert len(json.loads((run / 'run-manifest.json').read_text())['approvals']) == 2
    assert submit(run, approved, tmp_path, capsys)[0] == 2


@pytest.mark.parametrize('field', ['packet_sha256', 'input_hashes', 'scope', 'run_id'])
def test_stale_or_altered_decision_is_rejected(inventoried_run, tmp_path, capsys, field):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    decision = decision_for(packet)
    if field == 'input_hashes':
        decision[field] = decision[field] | {'inventory': '0' * 64}
    elif field == 'scope':
        decision[field] = decision[field] | {'cohort_ids': []}
    else:
        decision[field] = '0' * 64
    assert submit(run, decision, tmp_path, capsys)[0] == 2
    assert json.loads((run / 'run-manifest.json').read_text())['approvals'] == []


@pytest.mark.parametrize('changed', ['source', 'transform', 'packet', 'tools'])
def test_changed_evidence_cannot_receive_approval(inventoried_run, tmp_path, capsys, monkeypatch, changed):
    source, run = inventoried_run
    assert main(['decode-check', str(source), '--run-dir', str(run), '--json']) == 0
    capsys.readouterr()
    packet = packet_for(run, 'cohort-rules', capsys)
    if changed == 'source':
        raw = next(source.glob('*.dng'))
        raw.write_bytes(raw.read_bytes() + b'changed')
    elif changed == 'transform':
        report = json.loads((run / 'decode-check.json').read_text())
        report['frames'][0]['coordinate_transforms'][0]['max_error_px'] = 0.1
        (run / 'decode-check.json').write_bytes(canonical_bytes(report))
    elif changed == 'packet':
        (run / packet['packet_path']).write_bytes(b'{}')
    else:
        from photo_workflow import approvals
        monkeypatch.setattr(approvals, 'discover_tools', lambda timeout: [])
    assert submit(run, decision_for(packet), tmp_path, capsys)[0] == 2


def test_new_decode_evidence_invalidates_old_packet(inventoried_run, tmp_path, capsys):
    source, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    assert main(['decode-check', str(source), '--run-dir', str(run), '--json']) == 0
    capsys.readouterr()
    assert submit(run, decision_for(packet), tmp_path, capsys)[0] == 2


def test_unverified_export_blocks_coordinate_approval_but_allows_rejection(inventoried_run, tmp_path, capsys):
    source, run = inventoried_run
    assert main(['decode-check', str(source), '--run-dir', str(run), '--json']) == 0
    capsys.readouterr()
    packet = packet_for(run, 'coordinate-contract', capsys)
    assert 'darktable_export_calibration_unverified' in packet['packet']['blockers']
    assert 'transforms' in packet['packet']['input_hashes']
    assert submit(run, decision_for(packet), tmp_path, capsys)[0] == 2
    assert submit(run, decision_for(packet, decision='rejected'), tmp_path, capsys)[0] == 0


def test_approval_record_tampering_and_uncommitted_records_fail_closed(inventoried_run, tmp_path, capsys, monkeypatch):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    from photo_workflow import approvals
    write = approvals.atomic_write
    def interrupt(path, data):
        if path.name == 'run-manifest.json':
            raise OSError('simulated interruption')
        return write(path, data)
    with monkeypatch.context() as patch:
        patch.setattr(approvals, 'atomic_write', interrupt)
        assert submit(run, decision_for(packet), tmp_path, capsys)[0] == 5
    assert main(['inspect-run', str(run), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['review_status']['cohort-rules']['state'] == 'awaiting_approval'
    assert submit(run, decision_for(packet), tmp_path, capsys)[0] == 2


def test_dry_run_creates_no_review_files(inventoried_run, tmp_path, capsys):
    _, run = inventoried_run
    assert main(['review-packet', str(run), 'cohort-rules', '--dry-run', '--json']) == 0
    packet = json.loads(capsys.readouterr().out)
    assert not (run / 'reviews').exists()
    assert submit(run, decision_for(packet), tmp_path, capsys)[0] == 2


def test_committed_decision_tampering_blocks_inspection(inventoried_run, tmp_path, capsys):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    code, result = submit(run, decision_for(packet), tmp_path, capsys)
    assert code == 0
    (run / result['decision_path']).write_bytes(b'{}')
    assert main(['inspect-run', str(run), '--json']) == 2


def test_new_evidence_marks_approval_stale_until_explicit_supersession(inventoried_run, tmp_path, capsys):
    source, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    code, result = submit(run, decision_for(packet), tmp_path, capsys)
    assert code == 0
    assert main(['decode-check', str(source), '--run-dir', str(run), '--json']) == 0
    capsys.readouterr()
    assert main(['inspect-run', str(run), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['review_status']['cohort-rules']['state'] == 'stale'
    new_packet = packet_for(run, 'cohort-rules', capsys)
    assert new_packet['decision_template']['supersedes_sha256'] == result['decision_sha256']
    decision = decision_for(new_packet, supersedes=result['decision_sha256'])
    assert submit(run, decision, tmp_path, capsys)[0] == 0


@pytest.mark.parametrize('field,value', [('reviewer', '  '), ('reason', '\t'),
                                        ('timestamp_utc', '2026-10-18T12:00:00'),
                                        ('timestamp_utc', '2026-10-18T12:00:00+01:00')])
def test_invalid_human_fields_are_rejected(inventoried_run, tmp_path, capsys, field, value):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    assert submit(run, decision_for(packet) | {field: value}, tmp_path, capsys)[0] == 2


def test_approve_dry_run_never_publishes_a_decision(inventoried_run, tmp_path, capsys):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    decision = tmp_path / 'decision.json'
    decision.write_bytes(canonical_bytes(decision_for(packet)))
    assert main(['approve', str(run), 'cohort-rules', str(decision), '--dry-run', '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['review_status']['cohort-rules']['state'] == 'awaiting_approval'
    assert not (run / 'approvals').exists()


def test_changed_environment_marks_existing_decision_stale(inventoried_run, tmp_path, capsys, monkeypatch):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    assert submit(run, decision_for(packet), tmp_path, capsys)[0] == 0
    from photo_workflow import approvals
    monkeypatch.setattr(approvals, 'discover_tools', lambda timeout: [])
    assert main(['inspect-run', str(run), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['review_status']['cohort-rules']['state'] == 'stale'


def test_packet_from_another_checkpoint_cannot_be_imported(inventoried_run, tmp_path, capsys):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    path = tmp_path / 'decision.json'
    path.write_bytes(canonical_bytes(decision_for(packet)))
    assert main(['approve', str(run), 'coordinate-contract', str(path), '--json']) == 2


def test_supersession_cannot_predate_latest_decision(inventoried_run, tmp_path, capsys):
    _, run = inventoried_run
    packet = packet_for(run, 'cohort-rules', capsys)
    code, result = submit(run, decision_for(packet, decision='rejected'), tmp_path, capsys)
    assert code == 0
    earlier = decision_for(packet, supersedes=result['decision_sha256']) | {
        'timestamp_utc': '2026-10-17T12:00:00Z'}
    assert submit(run, earlier, tmp_path, capsys)[0] == 2
