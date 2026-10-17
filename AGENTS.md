# Repository Guidelines

## Project Structure & Module Organization

This repository contains workflow specifications, implementation plans and an
initial Python implementation for raw inventory and decode checks. The three root Markdown documents define
raw dust removal, implementation sequencing, and the darktable house-style
workflow. `plans/` covers human review checkpoints and optional ChatGPT review;
`plans/scripts/` contains six ordered software work packages and their index.

The implementation uses `src/photo_workflow/` for reusable Python,
`tests/unit/`, `tests/integration/`, and `tests/fixtures/` for verification, and
`scripts/` only for thin developer utilities. Synthetic fixtures are generated in temporary test directories.
Follow the root workflows and recorded darktable spike results when plans conflict.

## Build, Test, and Development Commands

Use Python 3.12 and `uv sync --locked --all-groups` to install the pinned
runtime and development/test dependency groups. Run `uv run --group test pytest`,
`uv run validate-pyproject pyproject.toml` and `uv build`. Regenerate model-derived
schemas with `uv run python scripts/generate-schemas.py`; schema drift is tested.
No lint or type checker is configured.

Working commands include `photo-pipeline inventory INPUT --run-dir RUN`,
`photo-pipeline decode-check INPUT --run-dir RUN` and `photo-pipeline inspect-run RUN`.
Use `uv run` to invoke them in the project environment. ExifTool is required for
inventory; missing darktable is a capability warning. See `README.md` for setup,
exit codes and unsupported coordinate paths. Review changes with
`git diff --check` and `git diff --stat`; verify relative Markdown links and
cross-document consistency.

## Coding Style & Naming Conventions

Use British English for prose, documentation, code comments, and communication.
Prefer the `british-house-style` skill when available, using `-ise` spellings
such as *organise*. Preserve identifiers, commands, paths, quoted output, and
official product names exactly as required by their sources.

Keep Markdown concise, with descriptive headings, fenced command examples, and
relative links. Use lowercase, hyphen-separated document names, matching
`raw-dust-removal-pipeline.md`; preserve numbered work-package filenames.
For new Python code, use four-space indentation, `snake_case` functions/modules,
and `PascalCase` classes. Keep algorithms importable and CLI handlers thin.
No formatter or linter is configured yet.

## Testing Guidelines

Tests use pytest and Hypothesis; no numeric coverage threshold is configured.
Implement the tests and exit criteria specified by each work package. Prioritise safe
paths, atomic writes, schema rejection, coordinate round trips, deterministic
outputs, and interrupted-run recovery. Use `test_*.py` filenames and small,
distributable fixtures; do not commit private photographs by default.

## Commit & Pull Request Guidelines

The history contains one commit, `Commit initial plans`; no broader convention
is established. Use short, imperative subjects describing the change. Pull
requests should identify affected workflows/work packages, explain behavior or
specification changes, link relevant issues, and report validation. Include
overlays or review evidence when visual behavior changes.

## Safety & Approval Rules

Keep raw sources read-only and generated artifacts in separate run directories.
Version schemas and record input/configuration hashes and tool versions. AI
output is evidence, not approval: preserve the human checkpoints in
`plans/human-ai-checkpoints.md`. Changed upstream hashes invalidate approvals.
