# Package 03: repair planning and ChatGPT-assisted veto

## Outcome

Turn an approved epoch profile into an explicit per-frame repair plan. The
deterministic planner decides what is eligible, what source geometry is safe
and what needs review. An optional ChatGPT stage may demote a proposed automatic
repair but may never promote one.

## Commands delivered

- `photo-pipeline plan-repairs RUN [--epoch ID]`
- `photo-pipeline render-ai-packets RUN`
- `photo-pipeline ai-review RUN [--offline-cache-only]`
- `photo-pipeline evaluate-ai LABELS RUN`

## Deterministic repair planner

### Applicability and confidence

- Match each frame to exactly one approved epoch or mark it unresolved.
- Re-evaluate defect visibility for that frame using aperture and local evidence.
- Calculate a documented risk vector: texture, edge/line strength, saturation,
  face/skin likelihood if available, border proximity, source availability and
  overlap with another repair.
- Assign one of `auto`, `manual`, `uncertain` or `not-visible`, with
  machine-readable reason codes. Quarantine unsupported/corrupt frames at the
  frame level rather than inventing another repair-decision state.

### Source selection

- Search candidate source regions within a bounded sensor/display-space radius.
- Score exposure/colour agreement, gradient continuity, texture similarity and
  collision with defects or earlier repairs.
- Prefer a simple local source when evidence is strong; do not synthesize a
  source in this package.
- Store the chosen source, mask/shape, feather, method and score alternatives.
- Detect dependency cycles and overlapping operations before writing a plan.

### Plan state and schema

- Write an immutable `repair-plan.json` linked to the frame, profile and
  coordinate hashes.
- Keep deterministic decision, AI recommendation and human disposition as
  separate fields; do not overwrite history.
- Require a new plan version if thresholds, geometry or sources change.
- Apply immutable global overrides from a separately approved profile policy
  and per-frame overrides from their own append-only review file. Preserve the
  source, reviewer and reason for each effective override.

## ChatGPT adapter

The adapter is deliberately optional and read-only with respect to darktable.
It sends bounded visual evidence and receives a schema-validated classification.

### Review packet construction

For each eligible spot include:

- a context crop, close crop and marked location before repair;
- a deterministic repair preview and absolute-difference view;
- scale, crop relationship and a non-sensitive subset of risk features;
- a packet ID and hashes, with filenames and EXIF stripped unless explicitly
  allowed by policy.

The renderer must be deterministic so evaluation and production see the same
kind of evidence.

### API client

- Use the OpenAI Responses API with image inputs and a strict Structured Output
  schema. The response contains only verdict, confidence band, reason codes and
  a short rationale.
- Put the model ID, prompt version, schema version and packet hash in every
  result. Pin a tested model snapshot where the API exposes one.
- Set the API's storage option explicitly according to the privacy policy;
  default this project to no response storage unless the user decides otherwise.
- Read credentials from the process environment or OS credential mechanism;
  never write them to config, logs or manifests.
- Bound requests by image size, count, timeout and retry budget. Retry only
  transient failures with jitter; cache completed results by packet/model/prompt
  hash.
- Treat refusal, timeout, invalid JSON, unknown enum, low confidence and model
  change as `needs_human_review`.

The [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create)
supports image input and structured JSON responses. The selected model must
also list image input and Structured Outputs in its current official model
documentation before implementation is released.

### One-way safety rule

The merge logic is a small pure function:

```text
deterministic auto + AI accept         -> auto candidate
deterministic auto + AI veto/unclear   -> uncertain, human review
deterministic non-auto + any AI result -> unchanged
AI stage deliberately disabled         -> deterministic result unchanged
AI stage enabled but result missing     -> uncertain, human review
```

No prompt or model output is allowed to select a new source, change repair
geometry, write XMP or approve a batch.

## Evaluation harness

- Maintain a blinded human-labelled packet set with difficult texture, faces,
  wires, foliage, gradients, repeated patterns and clean controls.
- Separate tuning and held-out sets by shoot or scene, not by random crop, to
  reduce leakage.
- Compare deterministic-only and deterministic-plus-AI flows.
- Report false approvals, unnecessary vetoes, abstention, latency, request
  count and estimated cost by model/prompt version.
- Run a no-network replay entirely from cached responses to verify merge logic.
- Require an explicit human decision on acceptable false-approval risk. Cost or
  throughput improvement cannot compensate for a worse safety result.

## Human checkpoints

1. Approve which images/metadata may leave the machine and the response-storage
   policy.
2. Approve the packet design and label guide before evaluation.
3. Review disagreements and set the release threshold.
4. Approve any model or prompt-version change as a new evaluated release.

## Exit criteria

- The deterministic planner works without network access or an API key.
- Every planned operation is spatially valid, non-cyclic and traceable.
- Malformed or unavailable AI responses fail closed.
- The held-out evaluation shows the optional layer does not increase false
  automatic approvals above the agreed tolerance.
- Results can be reproduced from packets, configuration, model/prompt metadata
  and response cache without resending private imagery.
