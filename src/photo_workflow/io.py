"""Hashing, atomic writes and source/run path boundaries."""

import hashlib
import json
import os
import tempfile
from pathlib import Path


def canonical_bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def reject_symlinks(path: Path):
    absolute = Path(os.path.abspath(path))
    if any(part.is_symlink() for part in (absolute, *absolute.parents)):
        raise ValueError('symlink path components are not allowed')
    return absolute


def validate_run_location(source: Path, run: Path) -> Path:
    try:
        source = reject_symlinks(source).resolve(strict=True)
    except OSError as error:
        raise ValueError('source path is missing or unreadable') from error
    source = source if source.is_dir() else source.parent
    run = reject_symlinks(run).resolve()
    if run.is_relative_to(source) or source.is_relative_to(run):
        raise ValueError('run directory must be separate from the raw source tree')
    return run


def safe_child(root: Path, name: str) -> Path:
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('artefact name must be a relative path without traversal')
    root = reject_symlinks(root).resolve()
    target = reject_symlinks(root / relative)
    if not target.resolve().is_relative_to(root):
        raise ValueError('artefact escapes the run directory')
    return target


def atomic_write(path: Path, data: bytes):
    path = reject_symlinks(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f'.{path.name}.', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
