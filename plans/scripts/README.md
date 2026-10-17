# Scripting implementation plans

This folder turns the workflow documents into bounded software work packages.
It specifies what each script must do, the artefacts it owns, how it fails and
the evidence required before the next package starts.

These plans do not replace the algorithm and safety decisions in the root
documents. In a conflict, the root workflow documents and the recorded
darktable spike results take precedence.

## Shared implementation shape

Build one installable Python package with one command, `photo-pipeline`, rather
than a collection of unrelated scripts. Keep algorithms in importable modules;
the command line should validate inputs, call those modules and write durable
artefacts.

Proposed layout:

```text
CLAUDE.md
pyproject.toml
docs/
plans/
scripts/                 # thin developer/fixture utilities only
src/photo_workflow/
  cli.py
  config.py
  schemas/
  io/
  inventory/
  coordinates/
  detection/
  epochs/
  repair/
  ai/
  darktable/
  review/
  style/
  orchestration/
config/
profiles/
styles/
manifests/
work/
tests/
  unit/
  integration/
  fixtures/
```

This preserves the root workflow's operational directories while putting
reusable Python in `src/`. Do not put core behaviour in shell scripts or
one-off notebook cells.

The initial command surface is:

```text
photo-pipeline inventory
photo-pipeline decode-check
photo-pipeline detect
photo-pipeline segment-epochs
photo-pipeline build-profile
photo-pipeline plan-repairs
photo-pipeline ai-review
photo-pipeline apply
photo-pipeline export
photo-pipeline review
photo-pipeline style-measure
photo-pipeline style-validate
photo-pipeline run
photo-pipeline resume
```

## Work packages

1. [`01-foundation-and-inventory.md`](01-foundation-and-inventory.md) — package,
   schemas, safe artefact storage, raw inventory and coordinate contract.
2. [`02-detection-and-epochs.md`](02-detection-and-epochs.md) — raw-domain
   detector, confidence evidence, profile construction and epoch segmentation.
3. [`03-repair-planning-and-chatgpt.md`](03-repair-planning-and-chatgpt.md) —
   per-frame repair decisions, source selection and optional ChatGPT veto.
4. [`04-darktable-application-and-export.md`](04-darktable-application-and-export.md)
   — darktable capability spike, XMP application backend and reproducible export.
5. [`05-review-and-style-analysis.md`](05-review-and-style-analysis.md) — review
   packets, miss detection and house-style measurement/validation.
6. [`06-end-to-end-orchestrator.md`](06-end-to-end-orchestrator.md) — resumable
   dependency graph, approvals, run manifests and pilot release.

## Cross-cutting rules

- Raw source files are read-only. Generated files go to a separate run
  directory.
- Every JSON artefact is schema-versioned and written atomically.
- Every stage records input hashes, configuration hash, tool versions and the
  IDs of upstream artefacts.
- Coordinates are never passed between stages without an explicit coordinate
  space and transform version.
- A failed or unavailable enabled AI veto leaves affected repairs `uncertain`;
  it never switches itself off. Deterministic-only mode requires an explicitly
  approved operating policy; mode changes invalidate dependent artefacts.
- Each newly reviewed epoch has its own immutable profile and approval, even
  when linked to an earlier equivalent defect state.
- Coordinate mappings declare valid domains and nonlinear behaviour. Unsupported
  mappings block application and coordinate-dependent review; cropped-out
  points never become border repairs.
- Human approvals are immutable records; a changed upstream hash invalidates
  the approval.
- Tests use small distributable fixtures. Private photographs may be referenced
  by a local fixture manifest but must not be committed by default.

## Suggested delivery order

Complete packages 01 and 02 first. Package 03 can then implement deterministic
planning before adding its optional AI adapter. Start the darktable spike from
package 04 early, but do not implement the production writer until the spike
selects a supported route. Package 05 can grow alongside detector development.
Package 06 is last because it integrates the stable commands rather than hiding
unfinished behaviour.

Each package is complete only when its exit criteria and required human
checkpoint have been recorded, not merely when its command exits successfully.
