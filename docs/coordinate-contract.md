# Coordinate contract 1

Coordinates refer to pixel centres: `(0, 0)` is the top-left sample, x increases
rightwards, and y increases downwards. Distances and extents use pixels. Domains
are rectangles with inclusive left/top bounds and exclusive right/bottom bounds.
A raster of width W and height H has sample centres through `(W-1, H-1)`.

## Spaces and supported mappings

| Space | Definition | Current mapping |
| --- | --- | --- |
| `raw_sensor` | Full unrotated decoder sensor array, including margins | Offset into active area |
| `active_sensor` | Unrotated visible sensor samples | Identity into detection array |
| `decoded_detection` | Camera-native CFA sample array, without postprocessing | Same dimensions as active area |
| `preview` | Oriented, scaled display evidence | EXIF orientations 1–8 and declared preview scaling |
| `darktable_input` | Coordinates at the selected repair module's input | Unsupported pending capability spike |
| `final_export` | Coordinates in the final rendered export | Unsupported pending capability spike |

Every mapping records source/target domains, implementation and contract
versions, matrix, inverse availability, numerical error bound, rounding and
mask resampling. Each decode report stores the resolved chain and links to the
inventory's geometry and source hashes. The source domain of raw-to-active
includes the full sensor; margin points return outside-output.

Homographies represent affine and perspective transformations. Singular,
ill-conditioned and projective-horizon mappings are rejected. Nonlinear lens
mappings must be represented as unsupported until a calibrated backend is
implemented. A named space alone does not imply a supported mapping.

## Domain and inverse rules

`map_point` returns `None` for a valid source point outside the target domain.
An invalid source point raises `MappingError`. An inverse is usable only when
declared available and validated over its domain. Unsupported geometry or a
numerical error bound above the caller's tolerance raises `MappingError`.

Outside-output is an export exclusion, separate from the repair planner's
`not-visible` state. No out-of-bounds coordinate is clamped to a border.
Geometric failures block any application or review that needs the failed path.
Native inventory and decoding can still generate evidence in supported spaces.

A new downstream nonlinear backend must provide its own validated domain,
forward/inverse algorithm, resolved parameters and error calibration. A caller
must not replace an unsupported transform with identity or an affine estimate.

## Masks and extents

`map_support` maps polygon vertices through a supported homography. A circle
must first be represented by an appropriate polygon or raster mask. The result
need not remain circular. Bounding-box intersection conservatively rejects
partially clipped or ambiguous support. Wholly excluded polygons return `None`.

`map_mask` maps Boolean raster sample support using inverse nearest-neighbour
sampling with half-up rounding (`floor(value + 0.5)`). Raster domains must have
integer dimensions and zero origin. Unsupported inverses and partially clipped
foreground samples raise `MappingError`; wholly excluded support returns
`None`. Empty masks produce an empty target mask.

The numerical transform tolerance excludes nearest-neighbour resampling error.
Raster support describes sample centres, not continuous pixel coverage; a
future repair backend must validate full feathered target/source support and
any interpolation footprint before application. No repair backend is currently
enabled.

## Calibration evidence

`decode-check` writes undemosaiced sensor arrays and CFA channel-index arrays as
NumPy `.npy` files, with dtype, shape and SHA-256 recorded in the report. Load
arrays with `allow_pickle=False`. Black and white levels remain metadata; the
sample array is unchanged by those levels.

The PNG overlay marks numbered corners and a centre point after orientation
and display scaling. Its greyscale background divides camera-native samples by
the recorded white level solely for display. The report records point round-trip
error separately from this preview. Unit/property fixtures cover all EXIF
orientations, odd dimensions, crops, perspective, mask rotation, excluded points,
partial support, unavailable inverses and unsupported lens correction.

A human must review actual camera/orientation evidence and full-resolution
darktable comparisons before approving the coordinate contract. The current
report explicitly records `darktable_export_calibration: unverified`.

Scoped human decisions can be imported through the
[approval-recording interface](approval-recording.md). The current coordinate
checkpoint exposes this unverified export calibration as a blocker and refuses
approval; native preview evidence alone cannot satisfy the release gate.
