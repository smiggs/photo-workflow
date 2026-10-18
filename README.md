# Photo workflow

Tools and plans for fixed sensor-defect removal and a reusable darktable house
style. The initial implementation provides raw inventory and decode/calibration
checks. It does not detect dust, apply repairs, export through darktable or
qualify a camera's coordinate contract. Explicit human decisions can be recorded
against review packets; unverified coordinate routes remain blocked.

## Set up

Use Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/).
The package contains Python code and depends on pinned native-library wheels.
`uv.lock` records the complete dependency resolution. Development and test tools
use dependency groups; there are no CLI dependencies beyond the runtime package.

```bash
uv sync --locked --all-groups
```

Install ExifTool separately and put `exiftool` on `PATH`. The program records its
resolved executable and version. Missing ExifTool blocks inventory; missing or
unusable darktable produces a capability warning and does not block inventory
or native sample decoding.

## Inventory and decode

Keep run directories outside the raw source tree. Commands accept a raw file
or a directory of raws. Common options follow the subcommand.

```bash
uv run photo-pipeline inventory INPUT --run-dir RUN --dry-run
uv run photo-pipeline inventory INPUT --run-dir RUN --json
uv run photo-pipeline decode-check INPUT --run-dir RUN --json
uv run photo-pipeline inspect-run RUN --json
```

Replace `INPUT` with your copied raw batch and `RUN` with a separate output
directory. Dry runs list inputs without decoding, calling external tools or
creating a run. `decode-check` creates an inventory if needed, then checks the
configured number of representatives for each cohort/orientation combination.
`inspect-run` verifies recorded artefact and current source hashes; it does not
approve a run. When scoped decisions exist, it also checks current tool and
implementation compatibility to derive their review status.

Source raws and existing sidecars remain read-only. Content-identical files
share a content-derived frame ID and retain all their source paths. Cohorts
include body serial, raw/active geometry, CFA layout, readout/crop evidence and
decoder compatibility. Missing body identity, orientation or camera model
excludes a frame rather than guessing compatibility. A missing UTC offset
preserves local capture time and records ambiguous order.

Outputs include:

- `inventory.json`, `frames.jsonl` and `cohorts.json`;
- `run-manifest.json`, committed after its stage artefacts;
- `decode-check.json` and per-frame `samples.npy`, `cfa.npy` and
  `calibration.png` files; and
- versioned JSON Lines stage logs under `logs/`, with UTC timestamps and no
  command arguments, source filenames or external-tool output.

Manifests link all stage artefacts by SHA-256 and record package/native tool
versions, resolved configuration hashes and a Python implementation hash.
Inventory data is deterministic; stage log timestamps are the declared timing
exception. Changed sources, configuration, implementation or tools require a
new run directory. Existing matching runs are checked and reused without
rewriting their artefacts.

The run lock prevents concurrent writers. After interruption, inspect the
workspace and process before removing a stale lock. Uncommitted artefacts are
never treated as a completed stage or overwritten: use a new run directory.
Automatic interrupted-stage recovery belongs to Package 06.

## Configuration and exit codes

`--config SETTINGS.json` loads a versioned JSON object. Unknown keys and schema
versions are rejected. Importable APIs can apply explicit overrides after file
values; CLI arguments do not silently override configuration fields.

```json
{
  "schema_version": 1,
  "tool_timeout_seconds": 30,
  "representatives_per_cohort": 1
}
```

The other supported setting is `raw_extensions`, an array of filename suffixes.
Defaults are declared in `src/photo_workflow/config.py`. All commands
support `--config`, `--dry-run`, `--log-level` and `--json`. For `inspect-run`,
`--dry-run` remains a read-only verification; an explicit configuration must
match the recorded configuration.

| Exit code | Meaning |
| --- | --- |
| 0 | Evidence generated/reused or inspection passed; human approval is separate |
| 2 | Invalid input, configuration, schema, unsafe path or stale/conflicting run |
| 3 | Missing or unusable required external tool |
| 4 | Partial result with excluded or unreadable inputs |
| 5 | Internal or output-write failure |
| 6 | All raw inputs are corrupt/unsupported, or no representative could decode |

## Coordinate scope and release gates

See [the coordinate contract](docs/coordinate-contract.md). Native detection
arrays contain unrotated, undemosaiced, camera-native sensor samples. No
postprocessing, gamma, automatic brightness, white balance or black subtraction
is applied. These samples and their black/white levels are evidence for later
normalisation, not a calibrated colour image or proof of every camera's linear
response. PNG overlays use a separate declared display mapping.

The implementation supports affine/projective mappings and EXIF orientation.
Nonlinear lens mappings and mappings to darktable input/final export remain
unsupported and fail closed. The capability spike must establish those routes;
synthetic coordinate tests cannot release them. Cohort evidence remains
immutable and initially unreviewed.
The [approval-recording interface](docs/approval-recording.md) prepares packets,
imports explicit human decisions and derives reviewed state from matching
records. Coordinate approval remains blocked by unverified darktable export
calibration. Full orchestration belongs to Package 06.

## Develop and verify

```bash
uv run --group test pytest
uv run python scripts/generate-schemas.py
uv run validate-pyproject pyproject.toml
uv build
```

The tests use generated, distributable synthetic DNGs decoded by the real
rawpy/LibRaw adapter. ExifTool subprocess fixtures make metadata, timeout and
failure tests independent of installed tools. No private photographs are
included. Schema tests compare committed JSON Schemas with Pydantic models.
No numerical coverage gate or lint/type checker has been configured.

The first implementation was verified on Python 3.12.14/Linux, including a
separate smoke check with ExifTool 12.40 and a synthetic DNG. Subsequent
validation used authorised Sony α6000 ILCE-6000 copies in landscape and portrait. Native decode and isolated darktable control exports succeeded,
but their active/export widths differ. Full-resolution coordinate calibration,
backend qualification and the human checkpoint remain outstanding; see the
[validation record](docs/package-01-validation.md).

## Workflow specifications

- [Raw dust-removal workflow](raw-dust-removal-pipeline.md)
- [Implementation plan](dust-pipeline-implementation-plan.md)
- [Darktable house style](darktable-house-style-workflow.md)
- [Package 01](plans/scripts/01-foundation-and-inventory.md)
- [Human checkpoints](plans/human-ai-checkpoints.md)
