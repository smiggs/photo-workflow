# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains workflow specifications and implementation
plans, not an executable application. The three root Markdown documents define
raw dust removal, implementation sequencing, and the darktable house-style
workflow. `plans/` covers human review checkpoints and optional ChatGPT review;
`plans/scripts/` contains six ordered software work packages and their index.

The planned implementation uses `src/photo_workflow/` for reusable Python,
`tests/unit/`, `tests/integration/`, and `tests/fixtures/` for verification, and
`scripts/` only for thin developer utilities. These directories do not yet exist.
Follow the root workflows and recorded darktable spike results when plans conflict.

## Build, Test, and Development Commands

There are currently no build scripts, dependency manifest, test runner, or
configured lint commands. Review changes with `git diff --check` and
`git diff --stat`; verify relative Markdown links and cross-document consistency.

Package 01 will establish `pyproject.toml`, development/test extras, and the
`photo-pipeline` entry point. Planned usage includes
`photo-pipeline inventory INPUT --run-dir RUN` and
`photo-pipeline decode-check INPUT --run-dir RUN`. These commands are design
targets until implemented; document working setup and test commands when adding
the package.

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

No testing framework or numeric coverage threshold has been selected. Implement
the tests and exit criteria specified by each work package. Prioritize safe
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
