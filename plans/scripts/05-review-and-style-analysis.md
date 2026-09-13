# Package 05: visual review and house-style analysis

## Outcome

Provide reviewers with compact, traceable evidence for repairs and misses, and
provide measurable checks that a darktable house style behaves consistently
without pretending that a LUT represents spatial or scene-dependent modules.

## Commands delivered

- `photo-pipeline review RUN [--queue NAME]`
- `photo-pipeline record-review RUN DECISIONS`
- `photo-pipeline style-measure REFERENCES --run-dir RUN`
- `photo-pipeline style-audit-references REFERENCES --run-dir RUN`
- `photo-pipeline style-validate STYLE TEST_SET --run-dir RUN`
- `photo-pipeline inspect-style-history XMP`

## Repair review generator

Generate a static, portable report whose images remain local to the run:

- full-frame thumbnail with all candidate locations;
- before, after and absolute/amplified difference crops;
- wider context and 100% crop for each operation;
- source-region overlay and overlap warnings;
- confidence/risk reason codes and AI verdict, clearly separated;
- clean control crops and full-frame miss overlays; and
- links/IDs back to raw, profile, repair plan, sidecar and export hashes.

Queues include `auto_sample`, `manual`, `uncertain`, `ai_veto`,
`boundary_review`, `miss_check` and `failed_validation`. Sampling must be seeded
and recorded so it is reproducible.

## Review decision importer

- Use a versioned CSV or JSON template with frame, defect, decision, reason and
  optional comment.
- Validate that each decision targets the displayed packet hash.
- Preserve reviewer identity as a local label or pseudonymous ID according to
  policy.
- Append decisions; corrections supersede earlier records rather than deleting
  them.
- Do not turn batch acceptance into profile truth automatically. Confirmed
  detector errors become labelled fixtures through a separate reviewed action.

## Miss detection

- Render predicted-location overlays before repair and residual/difference maps
  after repair.
- Re-run a conservative detector on exports or suitable intermediates to flag
  remaining spot-like structures, while documenting that this is not equivalent
  to raw-domain detection.
- Sample locations with no known defect, stratified by aperture and scene type.
- Report miss estimates with sample counts and uncertainty, not as a guarantee
  of zero missed dust.

## House-style measurement

Before measuring, audit each base/finished reference pair:

- dimensions, crop, orientation, output profile, rendering intent and bit depth
  must match;
- the histories may differ only in the declared candidate look modules; and
- the pixel registration check must pass within a declared tolerance.

Quarantine a failed pair rather than attempting to align away an unexplained
crop or technical edit.

Implement measurements from the house-style workflow as pure functions where
possible:

- exposure and highlight/shadow clipping summaries;
- tone curve or monotonic response measurements from controlled charts;
- neutral/colour-patch error in a declared working/output colour space;
- local/global contrast and edge-acutance indicators;
- saturation/hue behaviour by luminance band; and
- noise/sharpening/halo indicators on controlled crops.

Store measurement units, colour transforms, crop coordinates and uncertainty.
Do not reduce all style behaviour to a single score.

## Style history inspector

- Parse sidecar history structurally and list active module instances and order.
- Compare expected and actual modules with configurable allowed variation.
- Flag duplicate display transforms, disabled required modules, unexpected
  scene-specific masks and version-incompatible parameters.
- Produce a concise semantic diff suitable for both a human and the export gate.

## LUT approximation experiment

If requested by the house-style plan:

- sample the style only on controlled, pointwise colour transforms;
- separate spatial, mask-based, exposure-adaptive and frequency operations;
- fit/evaluate a LUT on disjoint samples;
- report colour error distributions and outliers; and
- label the result an approximation with an explicit supported scope.

It must never replace the canonical darktable style without human approval.

## Tests

- Golden review pages checked for missing/broken artefact links and packet IDs.
- Image tests for crop placement, difference scaling and source overlays.
- Schema and supersession tests for review decisions.
- Synthetic images with known clipping, contrast, colour shifts, halos and
  noise to validate metric direction and units.
- Registered reference renders for supported darktable versions, using numeric
  tolerance plus a generated visual diff.

## Human checkpoints

1. Approve the review layout at normal viewing size and 100% zoom.
2. Review all manual/uncertain cases plus the required automatic and clean
   samples.
3. Approve house-style tolerances per metric and inspect known failure scenes.
4. Decide whether any LUT approximation is useful within its measured scope.

## Exit criteria

- A reviewer can trace and decide every displayed item without consulting logs.
- Decisions against stale packets are rejected.
- Batch acceptance includes both repair-quality sampling and a miss estimate.
- Style validation reports each metric and failure example, not only pass/fail.
- The style history inspector blocks duplicate or incompatible active modules.
