import json
import os
import sys
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from photo_workflow.config import load_config
from photo_workflow.io import atomic_write, canonical_bytes, digest, safe_child, validate_run_location
from photo_workflow.models import ApprovalRecord, RunManifest
from photo_workflow.tools import ToolFailure, run_command


def test_configuration_precedence_and_unknown_keys(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text('{"tool_timeout_seconds": 7}')
    assert load_config(path, {'tool_timeout_seconds': 3}).tool_timeout_seconds == 3
    path.write_text('{"typo": 7}')
    with pytest.raises(ValidationError):
        load_config(path)


def test_manifest_rejects_future_versions_and_unknown_fields():
    valid = dict(run_id='a' * 64, source_root='/raw', configuration_sha256='b' * 64, tools=[])
    assert RunManifest.model_validate(valid).schema_version == 1
    with pytest.raises(ValidationError, match='schema_version'):
        RunManifest.model_validate(valid | {'schema_version': 2})
    with pytest.raises(ValidationError):
        load_config(overrides={'unknown': True})


def test_approval_rejects_naive_timestamp_and_missing_hashes():
    valid = dict(checkpoint='coordinates', reviewer='human', decision='approved',
                 timestamp_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
                 input_hashes={'inventory': 'a' * 64}, reason='Reviewed calibration evidence')
    assert ApprovalRecord(**valid).decision == 'approved'
    with pytest.raises(ValidationError, match='timestamp_utc'):
        ApprovalRecord(**(valid | {'timestamp_utc': datetime(2026, 1, 1)}))
    with pytest.raises(ValidationError, match='input_hashes'):
        ApprovalRecord(**(valid | {'input_hashes': {}}))


def test_canonical_hash_is_independent_of_key_order():
    assert digest(canonical_bytes({'a': 1, 'b': 2})) == digest(canonical_bytes({'b': 2, 'a': 1}))
    with pytest.raises(ValueError):
        canonical_bytes({'x': float('nan')})


@pytest.mark.parametrize('name', ['../escape', '/tmp/escape', 'a/../../escape'])
def test_safe_child_rejects_traversal(tmp_path, name):
    with pytest.raises(ValueError):
        safe_child(tmp_path, name)


def test_run_location_rejects_source_and_symlink_alias(tmp_path):
    source = tmp_path / 'raw'
    source.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(source, target_is_directory=True)
    for destination in [source, source / 'work', alias / 'work', tmp_path]:
        with pytest.raises(ValueError):
            validate_run_location(source, destination)


def test_atomic_write_preserves_previous_file_on_interruption(tmp_path, monkeypatch):
    target = tmp_path / 'result.json'
    atomic_write(target, b'{"complete": true}')
    def interrupt(*args):
        raise OSError('interrupted rename')
    monkeypatch.setattr(os, 'replace', interrupt)
    with pytest.raises(OSError):
        atomic_write(target, b'{"complete": false}')
    assert json.loads(target.read_text()) == {'complete': True}
    assert list(tmp_path.iterdir()) == [target]


def test_subprocess_treats_filenames_as_arguments_and_has_timeout():
    value = 'a ; $(touch should-not-exist) ü.nef'
    assert run_command([sys.executable, '-c', 'import sys; print(sys.argv[1])', value], 2).stdout.strip() == value
    with pytest.raises(ToolFailure, match='timeout'):
        run_command([sys.executable, '-c', 'import time; time.sleep(10)'], .05)


def test_missing_config_file_is_validation_failure(tmp_path):
    with pytest.raises(ValueError, match='configuration file'):
        load_config(tmp_path / 'missing.json')
