# Collaborative plans

This folder contains work that cannot be completed safely by unattended
automation alone. Each plan identifies what the AI prepares, what a human must
judge, and what evidence records the decision.

The deterministic pipeline remains defined in the repository root:

- [`raw-dust-removal-pipeline.md`](../raw-dust-removal-pipeline.md)
- [`dust-pipeline-implementation-plan.md`](../dust-pipeline-implementation-plan.md)
- [`darktable-house-style-workflow.md`](../darktable-house-style-workflow.md)

## Plans

- [`human-ai-checkpoints.md`](human-ai-checkpoints.md) extracts every material
  checkpoint that requires both AI preparation and human judgement from the
  three workflow documents.
- [`chatgpt-assisted-review-development.md`](chatgpt-assisted-review-development.md)
  defines how to build, evaluate and introduce the optional ChatGPT-assisted
  semantic veto and visual-review layer.
- [`scripts/README.md`](scripts/README.md) indexes the implementation plans for
  the command-line tools, detectors, darktable integration, review tooling and
  end-to-end runner required by the workflow.

## Operating rule

An AI result is evidence, not approval. Human approval is required wherever a
decision changes a released defect profile, confirms an epoch boundary,
permits a new class of automatic repair, releases a house style, or accepts a
production batch.
