# Handoff: complete Package 01

Continue work in `/home/andrew/projects/photo-workflow` on
[Package 01: foundation, inventory and coordinates](../plans/scripts/01-foundation-and-inventory.md).
Finish its remaining engineering and human-review gates without treating the
initial implementation as a released pipeline. Start with real-camera validation
and the early darktable capability spike; build the approval-recording path
alongside them where fixture or tool access is unavailable.

## Read first

- [Repository instructions](../AGENTS.md) and [safety contract](../CLAUDE.md).
- [Setup and working commands](../README.md).
- [Coordinate contract 1](../docs/coordinate-contract.md).
- [Root raw workflow](../raw-dust-removal-pipeline.md) and
  [master implementation plan](../dust-pipeline-implementation-plan.md).
- [Human checkpoints](../plans/human-ai-checkpoints.md).
- [Package 04](../plans/scripts/04-darktable-application-and-export.md), especially
  the capability spike, and
  [Package 06](../plans/scripts/06-end-to-end-orchestrator.md) for approval design.

Root workflows and recorded darktable spike results take precedence over
package plans. Use British English and the applicable skills. Write failing
behaviour tests before implementation changes.

## Starting state

Commit `d02bd77`, `Implement initial inventory and decode foundation`, was pushed
to `origin/main`. The working tree was clean before this handoff was added.
Inspect the current branch and changes before editing; do not assume the next
session starts at that commit or discard subsequent work.

The implementation already provides:

- Python 3.12 packaging, pinned dependencies and `uv.lock`;
- `photo-pipeline inventory`, `decode-check` and `inspect-run`;
- strict configuration, Pydantic models and 19 generated JSON Schemas;
- separate run directories, atomic writes, run locks, hashes, provenance,
  immutable stage artefacts and JSON Lines stage logs;
- ExifTool metadata extraction, including the DNG `CameraSerialNumber` tag;
- duplicate-aware frame IDs, unreviewed cohorts and explicit exclusions;
- native rawpy/LibRaw sample decoding, CFA arrays and calibration overlays; and
- affine/projective mappings, all eight EXIF orientations, crop exclusions,
  mask transformations and fail-closed handling of unsupported geometry.

Previous validation: 46 tests passed, metadata validation passed, wheel and
source distribution built, all 19 schemas were verified inside the wheel, and
an isolated installed-wheel CLI smoke check passed. A separate real ExifTool
12.40/rawpy smoke check succeeded on a generated DNG. These results are baseline
evidence, not a substitute for checking the next session's environment.

Tests generate synthetic DNGs and use an ExifTool subprocess stand-in for
controlled metadata cases. They do not establish hardware-camera calibration.
There are no private photographs or approved real-camera fixtures in Git.

## Resume and verify the environment

```bash
uv sync --locked --all-groups
uv run --group test pytest
uv run validate-pyproject pyproject.toml
```

Check Python, ExifTool and darktable executable paths, versions and actual
usability. The preceding session used Python 3.12.14/Linux. `uv` and ExifTool
were bootstrapped under `/tmp`; those temporary tools and smoke artefacts may
not survive. Do not depend on them. The existing `.venv`, if still valid, also
supports `.venv/bin/python -m pytest` and `.venv/bin/photo-pipeline --help`.

Missing ExifTool blocks inventory. Missing or unusable darktable must remain a
capability warning for inventory/native decode, while blocking work that needs
its geometry. No production darktable backend has been qualified.

For available copied fixtures, use the existing commands:

```bash
uv run photo-pipeline inventory INPUT --run-dir RUN --dry-run
uv run photo-pipeline inventory INPUT --run-dir RUN --json
uv run photo-pipeline decode-check INPUT --run-dir RUN --json
uv run photo-pipeline inspect-run RUN --json
```

Replace `INPUT` with a copied raw file or batch and `RUN` with a separate output
directory outside the raw tree. Changed input/configuration/code/tool
fingerprints require a new run directory. Do not delete stale locks or overwrite
interrupted artefacts without inspecting their state.

## Remaining steps

### 1. Validate actual camera files and cohort rules

Identify locally available, explicitly authorised fixture locations. If none
are available, ask the user for a local path and the intended camera/mode
coverage. Continue independent synthetic tests and approval work meanwhile;
do not search unrelated personal directories or invent camera metadata.

Build a local fixture manifest covering each intended physical camera body,
orientation and readout/crop mode. Preserve exact source hashes and capture
metadata. Keep private raws and sensitive evidence out of ordinary Git history;
use small distributable fixtures or local references as appropriate.

Run inventory and decode checks. Verify body identity, raw/active geometry, CFA
layout, crop/readout evidence, orientation and capture-time ambiguity. Confirm
that mixed bodies/modes separate correctly, duplicates retain their paths, and
every frame has an explicit cohort or exclusion. Confirm rerun determinism and
byte-for-byte preservation of raws and existing sidecars.

Fix discrepancies with regression tests. Missing identity or geometry must
remain an explicit exclusion or unresolved capability, never a guessed match.

### 2. Qualify the darktable coordinate route

Start the capability spike from Package 04 and master-plan phase 0 early, using
copied fixtures, an isolated configuration/library and no production catalogue.
Record the exact darktable version, environment and resolved processing history.
Do not assume CLI presence proves a usable or approved installation.

Establish how visible-raw coordinates map into the selected repair module's
input and final exports. Exercise orientation, crop, perspective and enabled
lens correction. Record operation order, resolved per-frame parameters,
source/target domains, inverse availability and measured error bounds.

Current `darktable_input`, `final_export` and nonlinear lens mappings are
explicitly unsupported. Implement only routes supported by spike evidence.
Never replace an unsupported mapping with identity or an affine approximation.
If a route cannot be validated, keep it blocked and document the limitation.
Do not expand into production repair/export implementation just to close this
package's coordinate gate.

### 3. Verify points, masks and full repair support in exports

Extend calibration evidence beyond the current corner/centre preview markers.
Use known points, masks and source/target extents in disposable calibration
fixtures and compare them against full-resolution darktable exports.

Cover portrait/landscape, odd dimensions, borders, crops, perspective and each
supported nonlinear operation. Validate full feathered support and any
interpolation footprint needed by the selected backend, rather than just the
centre or a scalar radius. Current raster mapping describes sample centres;
nearest-neighbour resampling is not proof of continuous repair coverage.

Record declared tolerances and measured errors. Test round trips only within
shared valid domains. Wholly cropped-out support is an output exclusion,
separate from `not-visible`; partial/ambiguous support, unavailable required
inverses and excessive error must fail closed. Add regression/property fixtures
and human-readable overlays/difference evidence.

### 4. Add the minimal human-approval recording path

`ApprovalRecord` and manifest approval fields exist, but no command currently
records approvals. Cohorts are fixed to `unreviewed`, and decode reports state
`darktable_export_calibration: unverified`.

The current status text defers approval recording to Package 06. Resolve that
dependency: Package 01 needs a small, usable approval path before its own exit
criteria can pass. Implement the smallest interface consistent with Package 06's
future `approve` contract, without building the full orchestrator. Update the
plans, README, models and generated schemas together where necessary.

The tool must present a review packet and accept an explicit human decision,
reviewer, UTC timestamp, reason and exact inventory/transform/evidence hashes.
Record cohort-rule and coordinate-contract scope explicitly. Keep decision
records immutable, with corrections superseding earlier records. Derive reviewed
state from valid decisions rather than mutating historical evidence or treating
file presence as approval.

Write tests for approval, rejection, stale packet/transform/input hashes,
missing decisions and supersession. Changed upstream fingerprints must prevent
approval reuse. No model or automated test may supply the human decision.

### 5. Complete the human checkpoint and release assessment

Prepare an evidence packet for at least one actual file from every intended
camera/orientation combination, including cohort decisions, calibration
placement, tolerances, exclusions and unsupported paths.

The human must review the inventory and full-resolution calibration evidence,
then approve or reject the cohort rules and coordinate contract version through
the new recording path. Do not request sign-off until the concrete evidence is
ready. If fixture access, darktable capability or a decision is missing, report
that precise outstanding gate and keep the package unreleased.

Reconcile every Package 01 exit criterion with recorded evidence. Do not claim
complete sensor/display conversion support while required paths remain
unverified. Record the approved supported scope and any explicit exclusions;
update the implementation status and README accordingly.

## Safety decisions that must remain intact

- Source raws and original sidecars stay read-only; all generated work goes to
  separate run directories.
- Unsupported coordinates block dependent application and review; never clamp
  out-of-bounds locations into an image.
- Every newly reviewed epoch gets its own immutable profile/evidence/approval;
  recurring states may link through `equivalent_to`, without inheriting approval.
- An enabled AI veto fails closed to `uncertain`; an outage never disables it.
  Deterministic-only mode is an explicit human-approved policy choice.
- A successful command or test suite is evidence, not human approval.

## Verification and session handback

Run focused tests during implementation and the full suite after changes.
Regenerate schemas when models change:

```bash
uv run python scripts/generate-schemas.py
uv run --group test pytest
uv run validate-pyproject pyproject.toml
uv build
git diff --check
git diff --stat
```

Verify the built wheel contains the current schemas and that its installed CLI
works independently of the source checkout. Check relative Markdown links and
report the real-camera/darktable experiments separately from synthetic tests.

Hand back the changes, validation results, supported camera/geometry scope,
approval artefact locations and any remaining gate. This handoff does not ask
for a new chat, commit or push; follow the user's instructions in the next
session for those actions.
