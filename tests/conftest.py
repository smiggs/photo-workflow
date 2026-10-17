import json
from pathlib import Path

import numpy as np
import pytest
import tifffile


def write_dng(path, *, value=1000):
    pixels = np.full((48, 64), value, dtype=np.uint16)
    pixels[10:14, 20:24] = value // 2
    tags = [
        (271, 's', 0, 'Photo workflow', False),
        (272, 's', 0, 'Synthetic camera', False),
        (274, 'H', 1, 1, False),
        (50735, 's', 0, 'SYNTHETIC-BODY-1', False),
        (36867, 's', 0, '2026:01:02 03:04:05', False),
        (36881, 's', 0, '+00:00', False),
        (50706, 'B', 4, (1, 4, 0, 0), False),
        (50707, 'B', 4, (1, 1, 0, 0), False),
        (50708, 's', 0, 'Photo workflow synthetic camera', False),
        (33421, 'H', 2, (2, 2), False),
        (33422, 'B', 4, (0, 1, 1, 2), False),
        (50710, 'B', 3, (0, 1, 2), False),
        (50711, 'H', 1, 1, False),
        (50714, 'H', 1, 0, False),
        (50717, 'H', 1, 4095, False),
        (50721, '2i', 9, (1, 1, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 1), False),
        (50728, '2I', 3, (1, 1, 1, 1, 1, 1), False),
        (50778, 'H', 1, 21, False),
    ]
    tifffile.imwrite(path, pixels, photometric=32803, metadata=None, extratags=tags)
    return pixels


@pytest.fixture
def raw_batch(tmp_path):
    root = tmp_path / 'raw photographs'
    root.mkdir()
    pixels = write_dng(root / 'landscape ü.dng')
    return root, pixels


@pytest.fixture
def metadata_tool(tmp_path, monkeypatch):
    directory = tmp_path / 'tools'
    directory.mkdir()
    script = directory / 'exiftool'
    script.write_text('''#!/usr/bin/env python3
import json
import sys
from pathlib import Path
if sys.argv[1:] == ['-ver']:
    print('test-fixture-1')
else:
    path = Path(sys.argv[-1])
    metadata = dict(Make='Synthetic', Model='Fixture', SerialNumber='BODY-1',
        DateTimeOriginal='2026:01:02 03:04:05', OffsetTimeOriginal='+00:00',
        Orientation=1, LensModel='Fixture lens', FNumber=8, FocalLength=50,
        FocusDistance=2, CropMode='full')
    if 'portrait' in path.name:
        metadata['Orientation'] = 6
    if 'unknown' in path.name:
        metadata.pop('SerialNumber')
    print(json.dumps([dict(SourceFile=str(path), **metadata)]))
''')
    script.chmod(0o755)
    import os
    monkeypatch.setenv('PATH', str(directory) + os.pathsep + os.environ['PATH'])
    return script
