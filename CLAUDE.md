# Photo workflow safety contract

Follow [AGENTS.md](AGENTS.md) and the root
[raw workflow](raw-dust-removal-pipeline.md),
[implementation plan](dust-pipeline-implementation-plan.md), and
[house-style workflow](darktable-house-style-workflow.md). Work packages are
indexed in [plans/scripts](plans/scripts/README.md).

- Keep source raws and their existing sidecars read-only. Generate artefacts in
  a separate run directory.
- Never overwrite a released profile/style or an unrelated sidecar.
- Validate versioned schemas and record source/configuration/tool fingerprints.
- Use atomic writes and publish the manifest after its artefacts. Never reuse
  incomplete, changed or unverified data.
- Carry explicit coordinate spaces and validated transforms. Unsupported
  geometry blocks application and coordinate-dependent review.
- Apply no repair to `manual` or `uncertain` entries. An enabled AI veto must
  fail closed and must never disable itself after an outage.
- Use exactly one approved display transform during export.
- AI evidence is never approval. Preserve the
  [human checkpoints](plans/human-ai-checkpoints.md); changed upstream hashes
  invalidate dependent approvals.

Run `uv run --group test pytest` and `git diff --check`. See
[README.md](README.md) for setup and working commands. The current implementation
only inventories and decodes evidence; production repairs/exports are disabled.
