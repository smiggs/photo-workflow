# Package 04: darktable application and export

## Outcome

Prove how the installed darktable version represents and applies retouching,
then implement one supported backend that composes repairs with the house style
and exports verifiable outputs. Do not choose an XMP-writing strategy before the
capability spike.

## Commands delivered

- `photo-pipeline darktable-probe FIXTURES --run-dir RUN`
- `photo-pipeline apply RUN [--frame ID] [--backend NAME]`
- `photo-pipeline export RUN [--frame ID]`
- `photo-pipeline verify-export RUN`

## Phase A: executable capability spike

Use copied fixtures, a disposable darktable configuration directory and no
production catalogue.

Automate these experiments:

1. Record darktable version, database/schema information and relevant CLI help.
2. Create one manual retouch operation in the target darktable version, then
   snapshot and structurally diff the sidecar.
3. Test whether supported CLI/Lua paths can create or parameterise the same
   operation.
4. Test whether style application preserves, replaces or duplicates retouch and
   display-transform modules.
5. Export controlled variants and compare decoded pixels as well as metadata.
6. Test repeated application for idempotence.
7. Test isolated sequential exports; test parallel workers separately for
   database/configuration contention.

Write `darktable-capabilities.json`, normalised XMP diffs, commands, logs and
render comparisons. Secrets and machine-specific absolute paths are redacted
from shareable reports.

The human records an architecture decision selecting exactly one backend:

- supported darktable automation/Lua;
- a version-pinned, structurally validated XMP transformation; or
- no automatic darktable application, with an intermediate/manual hand-off.

An unsupported route must remain unavailable in the production command.

## Phase B: application backend

Define a narrow interface independent of the selected route:

```text
inspect(input, sidecar) -> EditState
apply(input, base_sidecar, repair_plan, style) -> CandidateSidecar
validate(candidate_sidecar) -> ValidationReport
```

The implementation must:

- verify all upstream hashes and the darktable capability signature;
- transform geometry only through the approved coordinate module;
- preserve unrelated existing history and metadata;
- enforce one owner for each retouch/style operation;
- reject duplicate active module instances or ambiguous ordering;
- write a candidate sidecar atomically beside generated working copies, never
  over an original sidecar by default; and
- reparse the result and compare semantic state before declaring success.

Keep XMP parsing namespace-aware and structural. Never edit base64/history
payloads with regular expressions or line-based substitutions.

## Phase C: export runner

- Use argument arrays and explicit input/sidecar/output paths.
- Use the isolated pinned configuration proven in the spike.
- Fix colour profile, intent, dimensions, bit depth, quality, metadata and
  naming policy in versioned configuration.
- Begin sequentially. Enable concurrency only after the spike proves isolation
  for the chosen catalogue/configuration arrangement.
- Write output to a temporary name, verify it decodes and matches expected
  dimensions/profile, then rename and append the manifest entry atomically.
- Treat existing outputs as a conflict unless their complete provenance matches.
- Detect crashes, timeouts, warnings, missing output and stale output timestamps.

## Verification

- Re-open the candidate sidecar and check module count, order, parameters and
  repair geometry.
- Render a control export with no repair and compare changed pixels to an
  expected bounded region, allowing for documented pipeline-wide effects.
- Check for double tone/display transforms and duplicate retouch operations.
- Verify each output's dimensions, colour metadata and link to source/plan/style.
- Rerun the same input to establish byte identity or a documented pixel-equivalent
  tolerance with explained metadata differences.

## Tests

- Parser/serializer fixtures from every supported darktable version.
- Golden semantic diffs rather than brittle whole-file string snapshots.
- Hostile filenames, read-only originals, corrupt XMP and interrupted export.
- Coordinate edge cases near borders and after orientation/crop.
- Integration test that opens generated XMP in darktable and checks a render.
- A version-mismatch test that refuses to run instead of attempting a best guess.

## Human checkpoint

A human reviews the capability report, architecture decision, before/after/diff
renders and one generated sidecar in darktable. They approve the exact darktable
version/backend signature. A version change automatically returns the backend
to unverified state.

## Exit criteria

- The capability spike has selected and documented a supported path.
- Raw files and original sidecars remain unchanged.
- Applying the same plan twice is either idempotent or safely rejected.
- Every export is traceable and passes semantic XMP plus pixel/output checks.
- The house style and repair stack compose without duplicate active modules.
