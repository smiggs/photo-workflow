# Implementation plan: batch removal of fixed sensor defects

This plan implements `raw-dust-removal-pipeline.md` against local raw files and
a pinned darktable installation. It front-loads the integration and coordinate
risks that can invalidate the design. Each phase has an exit test based on
observable files or pixels.

## Phase 0: spike the darktable boundary

The first deliverable is a short decision record choosing an application route.
Run every experiment against copies in an isolated darktable configuration and
library.

### 0.1 Record the environment

Record the darktable version, operating system, configuration directory,
sidecar settings and default pixel workflow. Preserve the disposable fixtures
and all generated XMP and `.dtstyle` files.

### 0.2 Test complete XMP transfer

1. Edit one fixture frame in darktable and add two or three retouch heals.
2. Use distinguishable source offsets so their transfer can be verified.
3. Save the complete XMP through darktable.
4. Apply that history to a second file from the same camera geometry.
5. Export both through `darktable-cli`.
6. Confirm at pixel level that the target masks and source points were applied.
7. Repeat with orientation, crop and lens correction enabled.

Seeing a retouch entry in the history is not a pass; the exported pixels and
editable shapes must be correct.

### 0.3 Test a retouch style separately

Create and export a style containing only retouch, apply it to another fixture,
and inspect the result. Do not assume that a style contains the separately
stored mask geometry. If the masks or source points are absent, reject the
style route.

### 0.4 Test composition with an existing history

Create a target image whose XMP already contains base edits and one display
transform. Apply the proposed house style through the CLI in append mode and
inspect the resulting module instances and pixels. Also test overwrite mode on
the disposable copy so its destructive semantics are documented.

The production design must not depend on append mode if it creates a second
active instance of an existing look module or display transform.

### 0.5 Test external XMP and database precedence

Import a fixture, modify its XMP outside darktable, then reopen and export it.
Document when darktable reads the file and when its library database overwrites
it. This determines whether the production route uses explicit export-only XMP
files or darktable-managed duplicates.

### Phase 0 exit test

The decision record must name one route and demonstrate that it:

- transfers target and source geometry;
- preserves unrelated edits and metadata;
- is idempotent in both history and pixels;
- behaves correctly through geometric modules;
- works without a GUI step during a batch run; and
- keeps source raws and production sidecars untouched.

If no darktable route passes, document an external pixel-repair route,
including the intermediate format, colour space, bit depth, processing order
and coordinate transforms. Do not begin production sidecar generation before
this decision is made.

## Phase 1: repository, dependencies and schemas

1. Add the repository layout from the workflow document.
2. Put the safety invariants in `CLAUDE.md` and link to the workflow.
3. Pin Python and package versions for `rawpy`, `numpy`, `opencv-python` and
   `scikit-image`.
4. Install ExifTool as a separate executable dependency; if a Python wrapper is
   used, pin it independently and still check the executable version.
5. Define versioned JSON Schemas for:
   - inventory records;
   - immutable defect profiles;
   - per-frame repair plans; and
   - run manifests.
6. Add schema validation to every command that reads or writes these files.
7. Keep large or private raw fixtures outside ordinary Git history. Track them
   with Git LFS or a content-addressed fixture manifest as appropriate.

The profile schema must include body identity, active-area geometry, epoch
timestamps, exact source hashes, tool/configuration versions, defect evidence,
confidence and review state.

### Phase 1 exit test

A command can inventory one fixture raw, write valid empty profile and repair
plan files, and reject an intentionally incompatible schema version.

## Phase 2: coordinate and decoding contract

Implement this before detection so every later stage shares one coordinate
system.

1. Read raw dimensions, visible active-area rectangle, orientation and body
   metadata.
2. Define `(0, 0)` and axis directions for the unrotated visible-raw image.
3. Decode a linear detection image with automatic brightness, gamma and
   content-dependent settings disabled.
4. Record every crop, scale, rotation or geometric transform used for previews.
5. Write conversions between raw coordinates, detection images, displayed
   previews and final exports.
6. Test portrait and landscape metadata, camera crop modes and at least one
   frame with lens correction and crop.

### Phase 2 exit test

Known synthetic marks round-trip between every supported coordinate system
within the declared tolerance and land on the same pixels in a darktable
full-resolution export.

## Phase 3: detector

Begin with a confirmed single epoch.

1. Support dedicated flat-field inputs as the preferred detector source.
2. For ordinary photographs, sample across capture time and reject unsuitable
   frames such as clipped or nearly uniform failures.
3. Correct broad illumination gradients and normalise in linear light.
4. Estimate a smooth background per frame and retain signed residuals.
5. Aggregate spatially persistent negative residuals with a robust statistic.
6. Detect blobs over configured scale and contrast ranges.
7. Estimate coordinate uncertainty, radius, contrast, aperture response and
   persistence for every candidate.
8. Render the stack, residual evidence, full-frame overlay and candidate crops.
9. Keep every threshold and random seed in configuration.

Build a labelled fixture set containing true dust, repeated scene edges and
clean regions. Report precision, recall and coordinate error by aperture range.

### Phase 3 exit test

The detector meets explicit, pre-agreed precision and recall thresholds on the
labelled fixtures and gives stable coordinates on a held-out set. No exit test
may require an unsupported claim of perfect detection.

## Phase 4: epoch segmentation and profile comparison

1. Build candidate profiles from overlapping windows that satisfy the
   detector's minimum sample size.
2. Match candidate defects one-to-one using coordinate, radius, contrast and
   confidence tolerances.
3. Score candidate evidence on every individual frame.
4. Run a change-point algorithm over capture order, supporting multiple changes
   and repeated states.
5. Enforce minimum evidence and minimum stable-window sizes.
6. Render evidence before and after each proposed boundary.
7. Require manual confirmation before releasing epoch profiles.
8. Compare each released profile with previous compatible profiles and record
   `equivalent_to` or `supersedes` relationships without overwriting anything.

Create fixtures for one change near the middle, one near an edge, two changes,
A -> B -> A, and no change.

### Phase 4 exit test

The segmenter finds all supported boundaries within the agreed tolerance on the
fixture sequences, produces no boundary for the stable sequence, and reports
insufficient evidence rather than guessing when a stable window is too short.

## Phase 5: per-frame classification and repair planning

1. Project each profile target into a full-resolution frame crop without losing
   the raw-coordinate reference.
2. Estimate whether the defect is visible at the frame's aperture and local
   signal level.
3. Measure edges, texture and local contrast outside the defect itself.
4. Add semantic exclusion for faces if a validated detector is available.
   Otherwise mark possible people or ambiguous regions `manual`.
5. Select and validate an image-specific source region if the repair algorithm
   requires one.
6. Assign `auto`, `manual`, `uncertain` or `not-visible` with reason codes and
   confidence.
7. Support immutable global overrides in the profile and per-frame overrides in
   a separate reviewed file.

Label fixture crops for smooth sky, gradients, edges, foliage, fabric, faces and
low-signal regions. Evaluate unsafe-auto rate separately from overall accuracy.

### Phase 5 exit test

No labelled face, strong edge or high-texture fixture is classified `auto`.
Smooth fixtures reach the agreed automatic-coverage target, and every uncertain
case fails closed.

## Phase 5A: ChatGPT-assisted semantic and visual review

Develop the optional model layer according to
[`plans/chatgpt-assisted-review-development.md`](plans/chatgpt-assisted-review-development.md).
This work includes the human-labelled evaluation set, deterministic input
renderer, Structured Output schema, privacy decision, model/prompt evaluation,
fail-closed semantic veto, repair-QA triage and shadow rollout.

Enforce the state transition in code: the model may downgrade a deterministic
`auto` candidate but may never promote `manual`, `uncertain` or `not-visible`.
The deterministic pipeline must continue to work when this phase is disabled.

### Phase 5A exit test

A human approves the data policy, held-out results, exact model and prompt
bundle, operating thresholds and shadow-run evidence. Property and fault-
injection tests prove that malformed output, timeouts and API failures cannot
authorise a repair. Until then, the feature remains disabled.

## Phase 6: application engine

Implement only the route approved by phase 0.

1. Read a validated profile and per-frame repair plan.
2. Generate or apply only `auto` repairs.
3. Keep generated XMP files in a staging area unless the pipeline owns their
   entire lifecycle.
4. Preserve existing history, masks and metadata according to the chosen
   ownership model.
5. Give every generated repair a stable identity so reruns replace rather than
   append pipeline-owned state.
6. Add dry-run, resume and force-new-run modes.
7. Refuse unsupported darktable, schema or coordinate-contract versions.

### Phase 6 exit test

Two runs over unchanged inputs produce equivalent repair plans, histories and
full-resolution pixels. Existing non-pipeline edits remain unchanged, and a
forced failure leaves no partial production sidecar.

## Phase 7: house-style composition and export

1. Implement the integration contract from
   `darktable-house-style-workflow.md`.
2. Verify exactly one of AgX, sigmoid, filmic RGB or another chosen display
   transform is active.
3. Detect duplicate active module instances before export.
4. Use an isolated, pinned darktable configuration and explicit input XMP where
   the selected route requires it.
5. Fix output profile, intent, dimensions, bit depth, quality and metadata
   policy.
6. Treat chunking and parallel execution separately: test database locking and
   configuration safety before enabling parallel workers.
7. Write a manifest entry atomically after each successful output.

Each manifest entry should contain input and output hashes, relevant XMP and
repair-plan hashes, profile/style IDs, software versions, configuration hash,
export settings, command status, warnings and output path.

### Phase 7 exit test

An unchanged rerun creates byte-identical outputs when the pinned tools support
that guarantee, or pixel-equivalent outputs plus explicitly documented metadata
differences. No frame contains duplicate active display transforms.

## Phase 8: review and miss detection

1. Generate labelled before/after and difference crops for every automatic
   repair.
2. Generate a work sheet for `manual` and `uncertain` cases.
3. Generate full-frame overlays or flat-field checks that can reveal missed
   defects.
4. Include a sample of clean control regions.
5. Record accept/reject decisions as data linked to frame and defect IDs.
6. Feed confirmed false positives, misses and bad repairs back into the fixture
   set.

### Phase 8 exit test

A reviewer can trace every displayed crop to its raw, profile, repair decision
and output. Acceptance covers both repair quality and estimated miss rate;
ambiguous cases can be opened at full resolution.

## Phase 9: pilot on real work

Run one expendable copy of a real batch end to end before enabling production
output.

Compare against untouched exports at full resolution, including:

- every repaired spot in a representative sample;
- known difficult texture and face cases;
- frames at the widest and smallest apertures;
- frames around every proposed epoch boundary; and
- areas where the miss detector predicts no defect.

Release the workflow only after the profile, manifest and review artefacts can
reproduce and explain the pilot result.

## Sequencing

- Phase 0 blocks production application and export work.
- Phase 2 blocks detection, segmentation and repair application.
- Phase 3 blocks epoch segmentation.
- Phase 5 may begin with hand-authored profiles once phase 2 is stable.
- Phase 5A may begin once phase 5 can render stable frame/spot crops. It is
  optional and does not block the deterministic pipeline, but it must pass its
  own release gate before influencing repair decisions or review queues.
- Review tooling should begin with phase 3 and grow alongside every later
  phase.
- The house style can be developed separately, but its CLI composition must
  pass phase 7 before the full pipeline is accepted.

## Working with Claude Code

Give Claude Code one phase and one exit test at a time. Require it to preserve
the safety invariants and to show generated images, manifests and validation
results rather than relying on terminal success alone.

Keep algorithms deterministic, thresholds in versioned configuration, schemas
validated at boundaries, and intermediate artefacts addressable from the run
manifest. Any experiment that touches darktable configuration or XMP should use
the isolated fixture environment until explicitly promoted.

Human approvals and AI-prepared evidence for every phase are indexed in
[`plans/human-ai-checkpoints.md`](plans/human-ai-checkpoints.md).

## Script implementation plans

The executable work is divided into six bounded packages under
[`plans/scripts/`](plans/scripts/README.md): foundation and inventory, detection
and epochs, repair planning with optional ChatGPT review, darktable application
and export, visual review and style analysis, and end-to-end orchestration.

Implement those packages in order except for the darktable capability spike,
which should start early because its result determines the supported application
backend. Each package has its own commands, artefacts, tests, human checkpoint
and exit criteria.
