# Test fixtures

`tests/conftest.py` generates a 64 × 48, uncompressed CFA DNG containing a
uniform field and one darker square. The data and synthetic camera metadata
are created by this repository; no photographs or third-party image data are
included. Tests create duplicate, corrupt, renamed and read-only variants in
temporary directories. No fixture is an approved hardware-camera calibration.

The ExifTool stand-in is an executable subprocess fixture. It returns controlled
metadata for missing-body and portrait cases. Real rawpy/LibRaw decodes every
valid DNG; metadata tests do not replace the decoder with a mock.
