# Package 01: foundation, inventory and coordinates

## Outcome

Create the safe, testable base used by every later command. At completion, the
tool can inventory a copied raw batch, validate its environment and express all
sensor/display coordinate conversions without changing a photograph.

## Commands delivered

- `photo-pipeline inventory INPUT --run-dir RUN`
- `photo-pipeline decode-check INPUT --run-dir RUN`
- `photo-pipeline inspect-run RUN`

All commands support `--config`, `--dry-run`, `--log-level` and `--json`.

## Modules and responsibilities

### Package and command shell

- Select and pin one tested Python minor in `.python-version` (use Python 3.12
  initially unless native-dependency validation requires another supported
  minor).
- Pin `rawpy`, `numpy`, `opencv-python` and `scikit-image`; use Pydantic v2 as
  the model and JSON Schema source, and keep CLI/test dependencies in declared
  optional groups. Record native library versions at runtime as well as Python
  package versions.
- Define the console entry point and development/test extras in `pyproject.toml`.
- Add `CLAUDE.md` containing the safety invariants and links to the root
  workflow and these package plans.
- Use a single configuration loader with strict unknown-key rejection.
- Return stable exit codes for validation, missing tools, corrupt input,
  partial completion and internal error.
- Emit human-readable progress to the terminal and structured JSON Lines to
  the run log.

### Schemas

Define and test versioned models for:

- `RunManifest`, `ToolVersion` and `ApprovalRecord`;
- `RawFrame`, `LensState`, `CaptureMetadata` and `Cohort`;
- `CoordinateTransform` and `ImageGeometry`; and
- generic `StageResult`, warning and error records.

Serialised data must use explicit units, UTC timestamps and enums. Reject
unknown schema versions rather than guessing.
Generate committed JSON Schema documents from the models and test that they do
not drift from the implementation.

### Artefact storage

- Create a run directory only after validating its proposed location.
- Write to a temporary sibling file, flush, then rename into place.
- Hash source and generated artefacts with a recorded algorithm.
- Prevent path traversal and accidental writes inside raw source directories.
- Allocate stable frame IDs independently of filenames.
- Treat an existing completed artefact as reusable only when its input,
  configuration and tool-version fingerprints match.

### External-tool adapter

- Discover and record `exiftool`, the raw decoder and darktable, without
  assuming they are present.
- Wrap subprocesses with argument arrays, timeouts, captured output and redacted
  logs; never invoke a shell with interpolated filenames.
- Record exact executable path and version output.

### Inventory

- Enumerate supported raw files without following unexpected symlinks.
- Extract capture time, make/model, lens, focal length, aperture, orientation,
  raw dimensions, active area and crop metadata.
- Detect duplicate content, unreadable files, ambiguous capture order and mixed
  cameras.
- Group frames into compatible cohorts, but preserve the facts used for the
  grouping so a reviewer can override it.
- Write `inventory.json`, `frames.jsonl` and `cohorts.json`.

### Decode and coordinate contract

- Decode representative frames as linear, minimally processed data and record
  every decoder option.
- Define named spaces at minimum: raw sensor, active sensor, decoded detection,
  darktable input and final export.
- Store orientation, crop, scale and offset as an invertible transform chain.
- Implement point, radius and mask transformations with declared rounding.
- Produce a calibration overlay showing known synthetic points after a full
  round trip.

## Tests

- Unit tests for configuration precedence, schema rejection, hashes, atomic
  writes, safe paths and subprocess timeouts.
- Property tests for coordinate round trips, including rotations, crops and
  odd dimensions.
- Integration tests over a tiny fixture set with spaces and Unicode in names,
  duplicated content, missing metadata and one intentionally corrupt file.
- A failure-injection test proving interruption cannot leave a valid-looking
  partial manifest.

## Human checkpoint

A human reviews the inventory and calibration overlay for at least one file
from each intended camera/orientation combination. They approve the cohort
rules and coordinate contract version. The tool records the approval against
the inventory and transform hashes.

## Exit criteria

- Repeated inventory runs are deterministic apart from declared timing fields.
- The original raw tree is byte-for-byte unchanged.
- Every frame belongs to exactly one reviewed cohort or is explicitly excluded.
- Synthetic markers return to within the documented tolerance in every tested
  coordinate path.
- Missing darktable is reported as a capability limitation, not as a failure of
  inventory or decode checks.
