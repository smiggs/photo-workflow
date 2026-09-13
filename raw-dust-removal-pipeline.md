# Batch removal of fixed sensor defects from raw photos

This document defines a pipeline for detecting fixed sensor defects and
repairing them across a batch of raw photographs. Detection is shared within a
verified dust epoch; the decision to repair is made separately for every spot
on every frame.

The pipeline may be driven from Claude Code, but all file formats, commands and
safety rules belong to the repository and must remain deterministic without an
agent present.

## Scope

The first implementation covers defects that remain at the same coordinates in
the camera's visible raw sensor area, principally sensor dust. It applies only
to files from the same physical camera body and compatible sensor readout mode.

It does not initially cover:

- Dust or marks associated with a lens. Their position and appearance may
  depend on the lens, aperture and focus, so they require a separate,
  lens-keyed validation.
- Hot pixels, which darktable already handles with its `hot pixels` module.
- Defects that move between frames.
- Film dust or scanned material.

The house style, exposure and white-balance workflow is downstream and is
defined in `darktable-house-style-workflow.md`.

## Safety invariants

- Never modify or rename a source raw file.
- Never overwrite an existing defect profile or released style.
- Never replace an existing XMP sidecar unless the pipeline created and owns
  the complete file.
- Never repair a frame/spot pair classified as `manual` or `uncertain`.
- Never enable more than one display transform during export.
- Always support a dry run and write a manifest.
- Never report a batch as clean solely because all detected spots were
  repaired; missed spots must also be tested for.

## Core concepts

### Compatible cohort

Before detecting anything, group files by:

- stable body identifier, preferably camera serial number;
- raw dimensions and visible active-area rectangle;
- sensor readout or crop mode; and
- raw decoder compatibility.

Files in different cohorts cannot share coordinates without an explicitly
tested transform.

### Dust epoch

A dust epoch is a time span during which the fixed-defect state is unchanged.
A cleaning, contamination event or physical disturbance may start a new epoch.
A shoot or directory is not assumed to be an epoch.

Epoch boundaries are inferred from per-frame evidence and confirmed visually.
The algorithm must be able to represent more than one change in a batch,
including a temporary state such as A -> B -> A.

### Defect profile

An immutable profile describes defect geometry and evidence for one epoch. It
does not decide whether a defect is safe to repair on every photograph.

Each defect should include at least:

- stable identifier;
- target coordinate in the unrotated, uncropped visible-raw coordinate system;
- estimated radius or shape;
- contrast and confidence, including aperture dependence where measured;
- detection evidence; and
- an optional global prohibition on automatic repair.

### Per-frame repair plan

For each raw file, a generated repair plan records every candidate defect as
`auto`, `manual`, `uncertain` or `not-visible`. It may also record an
image-specific source region and repair parameters if the chosen repair engine
requires them.

This distinction is essential: a fixed sensor coordinate can fall on sky in
one photograph, foliage in another and a face in a third.

## Repository layout

```text
photo-workflow/
  CLAUDE.md
  docs/
  plans/
  scripts/
  config/
  profiles/
  styles/
  manifests/
  work/
  tests/
```

`profiles/` contains immutable JSON profiles. Use a collision-resistant name,
for example:

```text
BODYID-RAWGEOMETRY-EPOCHSTART-PROFILEID.json
```

The profile ID should be a UUID or content-derived identifier. A separate index
may point to the current profile; it must not replace old profiles.

`work/` holds reproducible intermediate images and may be cleaned. Manifests
and released profiles are retained.

## Stage 0: qualify the darktable application route

Do not generate or modify production sidecars until the darktable interface has
passed the spike in `dust-pipeline-implementation-plan.md`.

The approved route must prove all of the following on disposable copies:

- target masks and any healing source points survive transfer to another image;
- the repaired pixels, not merely the history entry, appear in a CLI export;
- existing edits and metadata remain intact;
- repeated application neither duplicates history entries nor changes output;
- coordinate behaviour remains correct with orientation, crop and lens
  correction; and
- the route works with the pinned darktable version and an isolated
  configuration directory.

If darktable cannot accept generated retouch geometry safely, use a documented
external pixel-repair route. The raw originals must still remain immutable, and
the manifest must record the intermediate format, colour space and coordinate
transform.

## Stage 1: inventory and decode

1. Inventory the raw files and create compatible cohorts.
2. Read capture time, body identifier, lens, aperture, focus distance where
   available, raw dimensions, active-area rectangle and orientation.
3. Decode detection images with fixed, explicit settings. Disable automatic
   brightness and any content-dependent processing.
4. Keep defect coordinates in the visible-raw coordinate system. Store any
   transform used to make previews or exports.
5. Reject or quarantine files whose metadata or geometry is incompatible.

The inventory, decoder version and decoder settings become part of the run
manifest.

## Stage 2: detect candidate defects

Dedicated flat-field frames are preferred: evenly illuminated, defocused
frames made at small apertures without clipping. If they are unavailable, use
a temporally stratified selection of varied photographs rather than one
convenient section of the batch.

1. Correct each detection image for broad illumination gradients and normalise
   it in linear light.
2. Estimate a smooth local background and form a residual image per frame.
3. Aggregate residual evidence robustly so a feature must recur at the same raw
   coordinate across many frames.
4. Detect dark blobs over an explicit range of scales.
5. Measure persistence, location uncertainty, radius, contrast and aperture
   dependence.
6. Render a full-resolution overlay and a contact sheet of source evidence.
7. Confirm the candidate list by eye before releasing a profile.

Repeated scene content must not be assumed to disappear in a median. The
detector should be evaluated against labelled fixtures using precision, recall
and coordinate error rather than a subjective claim of perfection.

## Stage 3: find and confirm epoch boundaries

Use sufficiently large time windows to propose defect states, then score those
candidate defects on each individual frame. Run change-point detection over the
per-frame evidence series.

For every proposed boundary:

1. Build independent profiles from stable windows before and after it.
2. Require minimum support on both sides.
3. Compare defect sets one-to-one using coordinate, radius, contrast and
   confidence tolerances.
4. Render evidence around the boundary frames.
5. Confirm or reject the boundary manually.

Do not recursively stack ever-smaller halves: the detector has a minimum sample
size and cannot infer a one-frame boundary from a one-frame stack.

## Stage 4: compare with previous profiles

Compare the new profile with the most recent compatible profile using a
bijective match. Equality requires no unexplained additions or removals and no
material change in geometry or measured appearance.

If equivalent, reference the existing profile from the run manifest. If
different, retain the new immutable profile and record the relationship between
the two. Never silently replace the earlier file.

## Stage 5: create per-frame repair plans

For every candidate defect on every frame:

1. Estimate whether the defect is visible at that aperture and signal level.
2. Inspect a region larger than the proposed repair for edges and texture.
3. Reject semantic high-risk regions such as faces. Low variance alone is not
   evidence that a region is safe.
4. If the repair method needs a source region, choose and validate it on that
   frame; do not assume that one fixed offset is safe across the batch.
5. Assign `auto`, `manual`, `uncertain` or `not-visible`, with reason codes and
   confidence.

Only high-confidence, smooth, non-semantic regions qualify for unattended
repair. Default to `manual` when a required check is unavailable.

### Optional ChatGPT semantic veto

A validated multimodal model may review deterministic `auto` candidates for
semantic risks that simple texture measures miss. It receives locally rendered
target, context and proposed-source crops plus explicit identifiers and
metadata. It does not locate the defect.

The model may retain `auto` or downgrade it to `uncertain`; it can never promote
another state to `auto`. Invalid output, low confidence or service failure must
fail closed. Development and release criteria are defined in
[`plans/chatgpt-assisted-review-development.md`](plans/chatgpt-assisted-review-development.md).

## Stage 6: apply repairs

Apply only `auto` entries using the route approved in stage 0.

Sidecar handling must follow one of two explicit ownership models:

- **Pipeline-owned export sidecars:** generate complete XMP files in a staging
  area and pass them explicitly to the exporter; or
- **Darktable-managed duplicates:** import or duplicate images in an isolated
  library, apply the repair through darktable, and let darktable write the
  complete history.

Do not patch a sidecar beside a production raw file unless a tested merge can
preserve every unknown XMP property, history item and mask. A rerun must replace
only the pipeline-owned repair state and produce equivalent history and pixels.

## Stage 7: compose the house style and export

Use a pinned darktable version and a dedicated configuration directory. Compose
per-image base edits, dust repairs and the house style according to the
contract in `darktable-house-style-workflow.md`.

Before export, verify:

- exactly one display transform is enabled;
- applying the style will not create duplicate active module instances;
- the intended XMP is the source of truth rather than a stale library record;
- output profile, intent, dimensions, quality and metadata settings are fixed;
  and
- parallelism is safe for the selected darktable configuration and database.

For every frame, record input and output hashes, XMP or repair-plan hash,
profile ID, style ID, darktable version, configuration hash, command settings,
output path and final status.

## Stage 8: review

Review both false repairs and missed defects.

Produce:

- paired before/after crops for every automatic repair;
- a difference crop where it helps expose smearing;
- a labelled work sheet for `manual` and `uncertain` entries;
- full-frame defect overlays or flat-field validation for false negatives; and
- a small set of nominally clean control crops.

A batch passes only when repair quality is acceptable, no high-confidence
candidate was skipped without explanation, and the miss-rate check passes.
Open individual frames whenever a sheet is ambiguous.

A validated ChatGPT review prompt may triage repaired crops into human queues,
but it cannot accept the batch. Human review must include every flagged result
and a random sample of unflagged results so model misses remain measurable. See
[`plans/human-ai-checkpoints.md`](plans/human-ai-checkpoints.md).

## Minimum profile provenance

Every released profile should record:

- schema version and immutable profile ID;
- body identifier and compatible raw geometry;
- epoch start and end, with boundary confidence;
- exact source-file hashes and relevant capture metadata;
- decoder, detector and configuration versions;
- defects, evidence and global overrides;
- review status, reviewer and review timestamp; and
- parent or equivalent profile IDs where applicable.

## Open decisions

- Which darktable application route passes the stage 0 spike.
- Whether the user's existing photographs provide enough varied evidence, or
  dedicated flat-field captures are required.
- Which semantic detector, if any, is trustworthy enough to permit automatic
  repair around people.
- How aperture changes defect visibility and repair radius for the user's
  camera.
- Whether any lens-associated marks are stable enough to justify a separate
  lens-keyed pipeline.

## References

- [darktable sidecar files](https://docs.darktable.org/usermanual/development/en/overview/sidecar-files/sidecar/)
- [darktable-cli](https://docs.darktable.org/usermanual/development/en/special-topics/program-invocation/darktable-cli/)
- [darktable retouch module](https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/retouch/)
- [darktable drawn masks](https://docs.darktable.org/usermanual/development/en/darkroom/masking-and-blending/masks/drawn/)
