# Building a reusable house style in darktable

This document describes how to derive, test and maintain a reusable look from a
set of finished photographs. The style covers deliberate, repeatable choices in
tone, colour and contrast. Per-image technical corrections remain outside it.

Pin the darktable version used to create and release a style. Module behaviour,
parameter versions and default workflows can change between releases.

## Scope

The workflow separates three layers:

1. **Technical base:** image-specific raw development and geometry.
2. **House look:** reusable creative choices.
3. **Output:** destination profile, size, sharpening and metadata policy.

This separation is an operating rule rather than a claim that every darktable
module belongs permanently to one layer. Some modules contain both adaptive and
creative controls; split their responsibilities explicitly.

Sensor-defect removal is defined in `raw-dust-removal-pipeline.md`.

## Prerequisites

- A calibrated and profiled display in controlled viewing conditions.
- One pinned darktable version and an isolated, versioned production
  configuration.
- An explicit scene-referred pixel workflow.
- A chosen display transform: AgX, sigmoid or filmic RGB for current darktable
  releases. Exactly one may be active.
- Fifteen to twenty finished reference images spanning the lighting, dynamic
  range and subjects the style is expected to handle.
- The corresponding raws and their final per-image base edits.
- A held-out validation set that is not used to construct the style.

## Stage 1: define the style contract

Write a short specification before extracting settings. Describe:

- intended mood and use;
- shadow depth and highlight roll-off;
- mid-tone contrast;
- overall chroma and hue-specific preferences;
- skin rendering where relevant;
- conditions the style supports; and
- conditions that require a different variant.

Also state what the style must not change: exposure placement, illuminant,
crop, perspective, lens metadata, denoising and defect-removal decisions unless
an exception is explicitly justified.

## Stage 2: separate base, look and output

### Technical base

These settings are normally determined per image or from image metadata:

- `exposure`, adjusted for the subject and mid-tones;
- technical white balance, normally using the required `white balance` stage
  together with illuminant handling in `color calibration`;
- lens correction, rotation, perspective and crop;
- highlight reconstruction;
- `denoise (profiled)` and other noise-dependent correction; and
- input colour profile and camera-specific calibration.

Automatic presets may configure some of these modules, but their resolved
per-image state is still part of the base rather than the house look.

### House look

Candidates include stable creative controls from:

- `color balance rgb`;
- `color equalizer` or another intentional hue treatment;
- a scene-referred contrast module whose behaviour has proved reusable;
- one display transform, with its reusable creative controls separated from
  any image-specific input-range tuning;
- `local contrast`, if held-out testing shows it behaves consistently; and
- grain, bloom or other deliberate effects.

AgX and filmic RGB input-range controls may need per-image tuning. Sigmoid can
be more amenable to a fixed configuration, but it still requires held-out
testing. Do not force image-dependent parameters into the style merely because
they live inside the same module as a creative control.

### Output layer

Output colour profile, rendering intent, dimensions, format, quality and
output-specific sharpening belong to a named export preset or output style.
They should not be confused with the camera-independent house look.

## Stage 3: prepare the reference histories

Edit each reference to publication quality. Then produce two controlled
versions of every reference:

- **Base version:** all accepted per-image technical edits, with the candidate
  look modules disabled or removed.
- **Finished version:** the exact same base plus the final creative look.

The pair must have identical crop, dimensions, orientation, output profile,
rendering intent and export precision. This preserves pixel correspondence and
ensures that measurements isolate the look rather than exposure, white balance
or geometry differences.

Export both members of each pair as full-resolution 16-bit TIFFs in a declared
colour space. Retain the XMP histories and export settings as provenance.

## Stage 4: measure what the references share

Use registered base/finished pairs to measure:

- the pixelwise luminance mapping, including uncertainty by input range;
- percentile movement in addition to, not instead of, pixel correspondence;
- chroma and hue changes by input hue and luminance;
- shadow and highlight colour movement;
- skin luminance and hue where present; and
- local-contrast changes at declared spatial scales.

Measurements describe the target behaviour; they do not uniquely identify a
set of darktable module parameters. Several processing histories can create a
similar rendered mapping.

Report dispersion across references. A consistent disagreement associated with
a real capture condition may justify a variant. A disagreement caused by an
incorrect base edit should be fixed in the base instead.

## Stage 5: build the candidate style

1. Choose a representative frame near the middle of the supported range.
2. Apply and lock its correct technical base.
3. Select exactly one display transform.
4. Build the candidate look against the written contract and measured target
   behaviour.
5. Use stable, explicitly named module instances.
6. Keep image-dependent display-transform range settings outside the reusable
   style where necessary.
7. Compare the candidate with the hand-finished reference at full resolution
   and under colour-assessment viewing conditions.
8. Inspect saturated colours, gradients, skin, deep shadows and highlight
   transitions for clipping or hue artefacts.

The measurements constrain the work; visual judgement decides the look.

## Stage 6: export and identify the style

Create a style from the candidate history and select only the intended look
items. Do not include technical base or output modules accidentally.

Use an immutable identifier containing a semantic version, for example:

```text
house-natural-v1.2.0
```

Export the `.dtstyle` file and record:

- file hash;
- darktable version;
- parent/core style dependency, if any;
- included module instances and their intended order;
- compatible default pixel workflow;
- display-transform ownership; and
- the reference-set and measurement-report versions.

A `.dtstyle` file is XML, but its encoded parameter blobs are not meaningfully
reviewable as a textual diff. Validation must include rendered comparisons.

## Stage 7: test on held-out frames

Apply the candidate to the untouched held-out set after preparing each frame's
technical base.

For every frame, inspect:

- exposure and mid-tone placement;
- clipping and highlight roll-off;
- shadow colour and noise;
- hue stability and saturation;
- skin rendering where present;
- local-contrast or sharpening artefacts; and
- whether any candidate look parameter behaves as though it were
  image-dependent.

Classify follow-up adjustments:

- If most frames need the same correction, revise the style.
- If opposing corrections correlate with a real capture condition, consider a
  variant.
- If the correction is unique to one image, keep it in that image's base or
  finishing history.
- If a display transform needs different input-range settings, keep those
  settings per image while sharing only its stable creative controls.

Release only after the style passes explicit acceptance examples from every
supported condition.

### Optional ChatGPT review assistance

A separately evaluated multimodal prompt may compare held-out previews with the
written style contract and group recurring relative deviations by capture
condition. It must not make absolute calibrated-colour claims, change style
parameters automatically or approve a release.

Human reviewers judge the original renders on a calibrated display. Model notes
serve only as review triage and are evaluated against those human notes. The
experiment and its exit test are defined in
[`plans/chatgpt-assisted-review-development.md`](plans/chatgpt-assisted-review-development.md).

## Stage 8: compose styles safely

Darktable style categories provide organisation, not inheritance. A change to a
nominal parent does not automatically update its siblings.

Choose one explicit model:

- **Complete generated variants:** generate each released variant from a shared
  source specification and test the resulting `.dtstyle` files; or
- **Core plus overlay:** apply a versioned core style followed by a small
  variant overlay, with the order and compatible versions recorded.

Do not manually duplicate a large common base across variants without a test
that detects drift.

Before combining any style with an existing XMP history, inventory module
instances. Darktable's export-time append mode creates additional instances;
it must not introduce a second active display transform or unintentionally
double another effect. Overwrite mode must not be used when per-image history
needs to survive.

The preferred batch route is to compose and validate a complete history in a
controlled duplicate or export-only sidecar before export. Export-time style
append is acceptable only when the history contract proves that the appended
module instances are absent or intentionally additive.

## Stage 9: apply at scale

For interactive work, apply the style to selected images or assign it a
shortcut. For automated work, use the application route proven by the dust
pipeline's darktable spike.

Every run must pin and record:

- darktable and style versions;
- configuration and relevant preset hashes;
- per-image XMP or complete history hash;
- output profile, intent, format, dimensions and quality;
- active display transform and duplicate-module check; and
- output hash and path.

Use a dry run to list the resolved history and reject incompatible inputs before
rendering the batch.

## Stage 10: optional LUT approximation

A `.cube` LUT may be useful outside darktable, but it can represent only a
fixed, pointwise colour transformation under a fixed colour-management
pipeline.

It cannot reproduce:

- local contrast or sharpening;
- denoising, healing or other neighbourhood-dependent operations;
- masks, gradients or spatial edits;
- adaptive or image-dependent controls; or
- the complete behaviour of raw-domain processing.

To create one, process a suitable identity Hald CLUT through only the compatible
pointwise colour modules, with input and output colour spaces declared. Test the
result against colour patches and representative images. Name it as an
approximation rather than another copy of the darktable style.

## Stage 11: maintain the style

- Never overwrite a released style.
- Update the written contract and compatibility metadata with every release.
- Re-run the held-out suite and rendered comparisons after any module,
  darktable or configuration change.
- Retain prior darktable versions or containerised environments where exact old
  exports matter.
- Add newly discovered failure cases to the validation set.
- Revisit the creative brief periodically; publish a new major version when the
  intent changes rather than silently drifting the old one.

## Where Claude Code helps

Claude Code can:

- verify that reference pairs differ only in look modules;
- calculate and visualise the paired measurements;
- generate style compatibility metadata and run manifests;
- inspect XMP histories for duplicate modules and multiple display transforms;
- run held-out comparisons and assemble contact sheets; and
- generate and validate a colour-only Hald CLUT approximation.

The final creative decisions remain human judgements. Automated measurements
should expose disagreement and regressions, not invent an aesthetic target.

The required human/AI hand-offs for reference selection, style construction,
held-out review and release are listed in
[`plans/human-ai-checkpoints.md`](plans/human-ai-checkpoints.md).

## References

- [darktable processing defaults](https://docs.darktable.org/usermanual/development/en/preferences-settings/processing/)
- [darktable styles](https://docs.darktable.org/usermanual/development/en/module-reference/utility-modules/lighttable/styles/)
- [darktable export style composition](https://docs.darktable.org/usermanual/development/en/module-reference/utility-modules/shared/export/)
- [darktable AgX](https://docs.darktable.org/usermanual/5.6/en/module-reference/processing-modules/agx/)
- [darktable sigmoid](https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/sigmoid/)
- [darktable filmic RGB](https://docs.darktable.org/usermanual/development/en/module-reference/processing-modules/filmic-rgb/)
