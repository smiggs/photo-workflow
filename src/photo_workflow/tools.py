"""Bounded subprocesses and capability discovery without shell interpolation."""

import importlib.metadata
import shutil
import subprocess
import sys
from pathlib import Path

from .models import ToolVersion


class ToolFailure(RuntimeError):
    pass


def run_command(arguments: list[str], timeout: float) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(arguments, shell=False, timeout=timeout, capture_output=True,
                                text=True, encoding='utf-8', errors='replace')
    except subprocess.TimeoutExpired as error:
        raise ToolFailure('external tool timeout') from error
    except OSError as error:
        raise ToolFailure('external tool could not start') from error
    if result.returncode:
        raise ToolFailure(f'external tool exited with status {result.returncode}')
    return result


def discover_tools(timeout: float) -> list[ToolVersion]:
    tools = [ToolVersion(name='python', available=True, executable_path=sys.executable,
                         version=sys.version.split()[0])]
    for package in ['photo-workflow', 'pydantic', 'numpy', 'rawpy', 'opencv-python', 'scikit-image']:
        try:
            version = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            tools.append(ToolVersion(name=package, available=False))
            continue
        native = {}
        if package == 'rawpy':
            import rawpy
            native = {'libraw': '.'.join(map(str, rawpy.libraw_version)),
                      **{f'libraw_feature_{name}': str(value) for name, value in rawpy.flags.items()}}
        if package == 'photo-workflow':
            from .io import canonical_bytes, digest, file_digest
            directory = Path(__file__).parent
            native = {'implementation_sha256': digest(canonical_bytes({
                path.relative_to(directory).as_posix(): file_digest(path)
                for path in sorted(directory.rglob('*.py'))}))}
        if package == 'numpy':
            import numpy as np
            from .io import canonical_bytes, digest
            native = {'build_configuration_sha256': digest(canonical_bytes(np.show_config(mode='dicts')))}
        if package == 'opencv-python':
            import cv2
            from .io import digest
            native = {'opencv': cv2.__version__, 'build_information_sha256': digest(cv2.getBuildInformation().encode())}
        tools.append(ToolVersion(name=package, available=True, version=version, native_versions=native))
    for name, command, flag in [('exiftool', 'exiftool', '-ver'), ('darktable', 'darktable-cli', '--version')]:
        executable = shutil.which(command)
        version = None
        if executable:
            try:
                version = run_command([executable, flag], timeout).stdout.strip()
            except ToolFailure:
                pass
        tools.append(ToolVersion(name=name, available=bool(version), executable_path=executable, version=version))
    return tools
