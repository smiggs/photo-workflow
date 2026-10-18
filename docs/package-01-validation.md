# Package 01 validation: 18 October 2026

Package 01 remains unreleased. Native inventory and decode checks have now run
on authorised copies from a Sony α6000 ILCE-6000 in landscape and portrait.
The minimal human-decision recording path is implemented. Full-resolution
coordinate calibration and human approval remain outstanding.

## Engineering checks

The initial 46-test baseline passed before changes. The expanded suite has 70
passing tests, including packet binding, explicit decisions, rejection,
supersession, changed source/transform/tool evidence, stale status, interrupted
publication, record tampering and dry runs. Project metadata validation and
wheel/source builds pass. The wheel contains all 22 generated schemas; an
isolated installed-wheel smoke check passed inventory, decode, inspection and
packet generation outside the checkout.

Python is 3.12.14. Temporary local tools provide uv 0.13.1 and ExifTool 12.40.
These temporary tool paths are not durable installation instructions. Use the
[README setup](../README.md) in a new environment.

## Camera evidence

The user authorised the dated source folder for this camera and specified
landscape and portrait coverage. A read-only metadata scan found 48 ARW files:
42 with EXIF orientation 1 and six with orientation 6. Two representatives were
copied for experiments. Private raws, image exports, source metadata, body
identity, original-file hashes and review packets are kept under the ignored
`work/package-01-validation-2026-10-18/` directory, outside ordinary Git history.

Both representatives inventory into one cohort using the same recorded Sony
internal body identifier. Both decode successfully using rawpy/LibRaw. The
recorded geometry is:

| Evidence | Landscape | Portrait |
| --- | --- | --- |
| EXIF orientation | 1 | 6 |
| Raw sensor array, width × height | 6048 × 4024 | 6048 × 4024 |
| LibRaw active array, width × height | 6024 × 4024 | 6024 × 4024 |
| CFA channel indices | `[[0,1],[3,2]]`, RGBG | `[[0,1],[3,2]]`, RGBG |
| darktable control export, width × height | 6020 × 4024 | 4024 × 6020 |

All 96 original files in the authorised folder were hashed before and after
experiments and remained byte-for-byte unchanged. Both copied raws also match
the original hashes. Native rerun reuse preserves the committed evidence.

The selected files lack capture-time UTC offsets and generic crop/readout tags.
The capture times remain local and ambiguous. Sony's `FullImageSize` metadata
on the inspected landscape copy reports 6000 × 4000; this does not establish the
missing mapping or certify every camera mode. Scope is limited to the observed
geometry and orientations. Other readout/crop modes remain unqualified.

The four-column difference between LibRaw's active width and darktable's
landscape export width prevents assuming an identity mapping. No offset,
centred crop, scale or nonlinear mapping has been inferred from dimensions.

## Early darktable spike

The installed executable is darktable 3.8.1, with Lua API 8.0.0, OpenMP and
OpenCL compiled in. OpenCL was disabled during sequential probe exports, with
two OpenMP threads. The disposable library reports schema version 34 and the
configuration records a scene-referred workflow.

The default version invocation fails when the user's default configuration and
cache directories are absent. Setting both `XDG_CONFIG_HOME` and
`XDG_CACHE_HOME` to disposable directories allows version/help discovery. Actual
exports also used explicit `--configdir`, `--cachedir` and `--library` paths.
The production adapter still treats an unusable default invocation as a
capability warning; executable presence alone does not qualify a backend.

A generated 64 × 48 DNG exported twice to full-resolution, three-channel,
8-bit TIFF. The decoded pixels were identical with maximum channel difference
zero; TIFF file bytes differed because `DocumentName` records the output
filename. Both real-camera representatives also exported
at full resolution with embedded ICC profiles. These are control renders,
without retouch operations or an approved production export configuration. A
repeated landscape export also had identical decoded pixels and different TIFF
bytes for the same filename-metadata reason. Native orientation round trips measured zero error in both examples;
that measurement excludes export geometry and resampling coverage.

The private `darktable-capabilities.json` records hashes, render comparisons
and resolved history/parameter hashes. The disposable database and configuration
are preserved beside it. Current history includes raw preparation, demosaicing,
input/output colour, white balance, highlights, sharpening, filmic RGB, exposure
and orientation. History presence does not prove coordinate correctness.

## Outstanding gates

1. Establish a disposable retouch fixture with distinguishable target masks and
   healing source points. Transfer and inspect the shapes and exported pixels.
2. Measure native-to-module-to-export mappings, including the observed width
   difference, crop, perspective and enabled lens correction. Record operation
   order, resolved parameters, domains, inverses and error tolerances.
3. Validate full feathered target/source support and interpolation footprints,
   borders, partial clipping and wholly excluded support against full-resolution
   exports. Native preview markers alone cannot close this gate.
4. Complete transfer, existing-edit preservation, repeat-application and style
   composition experiments, then obtain the human architecture decision for an
   exact darktable/backend signature.
5. Resolve intended readout/crop coverage and have the human review the concrete
   inventory and calibrated evidence before recording decisions. No actual
   camera approval has been recorded.

The cohort packet is available for eventual human review. The coordinate
packet explicitly blocks approval with
`darktable_export_calibration_unverified`. No production repair or export
backend has been enabled. See [approval recording](approval-recording.md).
