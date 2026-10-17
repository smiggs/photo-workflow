import json

import numpy as np

from photo_workflow.cli import main
from photo_workflow.models import RunManifest


def test_decode_outputs_sensor_samples_and_requires_human_calibration(raw_batch, metadata_tool, tmp_path):
    source, expected = raw_batch
    run = tmp_path / 'run'
    assert main(['decode-check', str(source), '--run-dir', str(run)]) == 0
    report = json.loads((run / 'decode-check.json').read_text())
    assert report['darktable_export_calibration'] == 'unverified'
    assert report['state'] == 'awaiting_approval'
    item = report['frames'][0]
    actual = np.load(run / item['samples_path'], allow_pickle=False)
    assert np.array_equal(actual, expected)
    assert item['decode_options']['postprocess'] is False
    assert item['coordinate_transforms'][0]['source_space'] == 'raw_sensor'
    assert item['coordinate_transforms'][1]['target_space'] == 'decoded_detection'
    assert item['round_trip_max_error_px'] < 1e-6
    assert (run / item['overlay_path']).is_file()
    assert main(['inspect-run', str(run)]) == 0
    before = (run / 'run-manifest.json').read_bytes()
    assert main(['decode-check', str(source), '--run-dir', str(run)]) == 0
    assert before == (run / 'run-manifest.json').read_bytes()
    assert RunManifest.model_validate_json(before).approvals == []


def test_decode_dry_run_does_not_require_tools_or_create_run(raw_batch, tmp_path):
    source, _ = raw_batch
    run = tmp_path / 'run'
    assert main(['decode-check', str(source), '--run-dir', str(run), '--dry-run']) == 0
    assert not run.exists()


def test_changed_source_cannot_reuse_an_earlier_decode(raw_batch, metadata_tool, tmp_path):
    source, _ = raw_batch
    run = tmp_path / 'run'
    assert main(['decode-check', str(source), '--run-dir', str(run)]) == 0
    path = source / 'landscape ü.dng'
    path.write_bytes(path.read_bytes() + b'changed')
    assert main(['decode-check', str(source), '--run-dir', str(run)]) == 2
