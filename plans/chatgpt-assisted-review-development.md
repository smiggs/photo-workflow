# Development plan: ChatGPT-assisted semantic and visual review

This plan adds an optional multimodal model layer to the fixed-sensor-defect
pipeline. It uses image understanding for semantic risk detection and review
triage. It does not use generative image editing and does not replace the
deterministic detector, coordinate system, repair engine or human release
decisions.

For unattended operation, implement the capability through the OpenAI Responses
API rather than depending on an interactive ChatGPT session. Current OpenAI
models can accept image and text inputs and selected models support Structured
Outputs and function calling. Model support must still be verified when a model
is selected.

## Safety contract

- The model may downgrade a deterministic `auto` candidate to `manual` or
  `uncertain`.
- The model may never upgrade a deterministic rejection to `auto`.
- Model failure, timeout, refusal, invalid output or low confidence fails closed
  to `uncertain`.
- The model never creates or changes pixel coordinates, masks, source regions
  or repair pixels.
- Generative image-editing models are not used on production photographs.
- Human approval is required to change the policy, release a model/prompt
  version or accept a production batch.
- The pipeline remains usable with the model layer explicitly disabled under
  an approved operating policy. Record the mode before processing; an outage
  must never change it automatically. A mode change invalidates dependent
  repair plans, approvals and outputs before recomputation.

## Intended capabilities

### Semantic veto

Given a deterministic target and source proposal, classify whether the
surrounding image contains high-risk content such as a face, skin, hair, text,
fabric, foliage, a strong edge or an ambiguous subject boundary.

### Repair-quality triage

Given labelled before, after and difference crops, flag likely smearing,
repeated texture, halos, edge discontinuities, unintended facial changes or a
repair that remains visible.

### House-style review assistance

Given held-out reference comparisons and the written creative contract,
describe recurring relative deviations and group them by capture condition.
This is advisory and cannot replace calibrated human colour judgement.

## Known model limits

OpenAI's vision documentation warns that models can make mistakes, struggle
with precise spatial localisation and counting, may resize images, and do not
read filenames or embedded metadata. Therefore:

- crop coordinates are calculated locally;
- identifiers and EXIF values are supplied as text;
- the model receives a target overlay rather than being asked to find the
  target;
- inputs use original-detail processing where supported, within documented
  resizing limits; and
- all claims are evaluated against project-specific labelled fixtures.

## Phase C0: privacy, data handling and operating mode

1. Decide whether personal photographs may be sent to the OpenAI API.
2. Define crop minimisation: send only the context required for the decision,
   with a reduced full-frame preview only where necessary.
3. Strip unrelated metadata locally and supply only required fields as text.
4. Set the Responses storage option explicitly rather than relying on its
   default, and document applicable organisation/project retention controls.
5. Define access, logging and deletion rules for uploaded images and model
   outputs.
6. Provide a local-only/no-model mode with identical downstream schemas.

### Exit test

A human approves a written data-handling decision, and a dry run proves exactly
which pixels and metadata would leave the machine.

## Phase C1: labelled evaluation set

1. Derive candidate crops from the detector without model involvement.
2. Include target, proposed source and a wider context crop.
3. Cover smooth backgrounds, gradients, low signal, foliage, fabric, text,
   skin, faces, hair and strong edges.
4. Include good repairs, bad repairs and unchanged controls for QA evaluation.
5. Split by shoot or scene so near-duplicate crops cannot leak into held-out
   evaluation.
6. Have a human label context risks, safe/unsafe judgement, repair artefacts and
   ambiguity.
7. Measure inter-reviewer disagreement where possible and retain `ambiguous` as
   a valid label.

### Exit test

The versioned dataset has an approved label guide, balanced difficult examples,
stable IDs and a held-out set untouched by prompt development.

## Phase C2: deterministic input renderer

For each frame/spot pair, render:

- a moderate full-frame preview with the target marked;
- a high-resolution target crop;
- a wider context crop;
- the proposed source crop and source/target overlay, where applicable;
- a before/after/difference triptych for QA; and
- a text record containing stable IDs and relevant aperture, orientation and
  processing metadata.

Keep source pixels and rendered-input hashes in the manifest. Do not rely on
filenames embedded in an image.

### Exit test

Every model input can be traced back to exact raw coordinates, and a human can
understand the proposed decision from the rendered packet alone.

## Phase C3: structured model contract

Define a versioned Structured Output schema. A semantic-veto response should
contain at least:

```json
{
  "frame_id": "string",
  "spot_id": "string",
  "verdict": "safe | risky | uncertain",
  "risk_labels": ["face | skin | hair | text | fabric | foliage | strong_edge | source_mismatch | other"],
  "confidence": 0.0,
  "reason": "short string"
}
```

The production parser must reject unknown IDs, missing fields, out-of-range
confidence and output that does not validate. The prompt must state the safety
contract, describe each label and forbid coordinate inference or image-editing
instructions.

Version and hash the prompt, schema and examples independently.

### Exit test

Valid responses round-trip through the schema, and malformed, mismatched,
refused and timed-out responses all produce `uncertain` without invoking the
repair engine.

## Phase C4: model and prompt evaluation

1. Establish a quality ceiling with a capable current vision model.
2. Evaluate lower-cost candidates only after the metric and dataset are fixed.
3. Test supported image-detail settings; never assume that the nominal original
   dimensions reach the model unchanged.
4. Measure risky-case recall, unsafe-safe errors, uncertain rate, consistency,
   latency and cost.
5. Repeat runs to measure non-deterministic disagreement.
6. Review every unsafe-safe error with a human and add a regression case where
   appropriate.
7. Select a model only if it improves the combined deterministic gate on the
   held-out set.

The primary safety metric is the rate at which risky content is incorrectly
declared safe. Overall accuracy is secondary. Model confidence is not assumed
to be calibrated unless the evaluation demonstrates it.

### Exit test

A human approves a model, exact model ID, prompt/schema versions, thresholds and
measured operating point. Otherwise the feature remains disabled.

## Phase C5: semantic-veto integration

Insert the model after deterministic classification and before repair:

```text
deterministic candidate
        |
        +-- manual/uncertain/not-visible --> unchanged
        |
        `-- auto --> ChatGPT semantic veto
                         |
                         +-- safe and above threshold --> auto
                         `-- risky/error/uncertain -----> uncertain
```

1. Cache decisions by hashes of model ID, prompt, schema and rendered inputs.
2. Enforce the state transition table in code rather than in the prompt alone.
3. Record raw and validated model outputs in the manifest according to the
   approved data policy.
4. Add retry limits and fail-closed handling.
5. Prevent the model tool surface from writing files or invoking repairs.

### Exit test

Property tests prove the model can never promote an ineligible candidate, and
end-to-end fault injection proves every API failure path fails closed.

## Phase C6: repair-QA triage

1. Send the before/after/difference review packet only after repair succeeds.
2. Return `pass`, `review` or `uncertain` with named artefact categories.
3. Put every `review` and `uncertain` result into the human queue.
4. Continue to send a random sample of model-passed repairs to humans so model
   misses remain measurable.
5. Add confirmed misses and false alarms to the next evaluation dataset
   version.

The model does not accept the batch. It only orders the review queue.

### Exit test

The triage layer reaches the agreed bad-repair recall on held-out fixtures, and
the human sampling procedure can estimate misses among model-passed repairs.

## Phase C7: house-style review experiment

Treat style review as a separate prompt and evaluation task from dust repair.

1. Supply paired, colour-managed held-out previews and the written style
   contract.
2. Ask for comparative observations, not absolute calibrated colour claims.
3. Group repeated observations by lighting and subject condition.
4. Compare the model's observations with human review notes.
5. Retain the feature only if it helps humans find repeatable failures without
   creating excessive noise.

### Exit test

The experiment has a human-reviewed usefulness result. It is never a gate on
style release by itself.

## Phase C8: shadow rollout and release

1. Run the model without changing repair decisions for at least one real pilot
   batch.
2. Compare its vetoes and QA flags with complete human review.
3. Investigate all disagreements.
4. Enable QA triage first; it has less authority than a pre-repair gate.
5. Enable the semantic veto only after a separate human release decision.
6. If the enabled semantic-veto model or schema is unavailable, mark affected
   `auto` candidates `uncertain` and queue human review. Preserve earlier vetoes;
   never switch automatically to deterministic-only processing. If QA triage is
   unavailable, put affected results in the human queue rather than treating
   them as model-passed.
7. Permit deterministic-only processing only through an explicitly approved
   policy change. Record the new mode and invalidate dependent plans, approvals
   and outputs before recomputation.

### Exit test

The released feature has an approved model card, prompt/schema bundle, metrics,
known limitations, data policy, monitoring plan and one-command disable path.

## Ongoing monitoring

For each model-assisted run, track:

- model, prompt and schema versions;
- image-detail setting and rendered-input hashes;
- valid, invalid, refused, timed-out and retried responses;
- verdict and risk-label distributions;
- model/human disagreement;
- bad repairs missed by model triage;
- automatic-repair coverage lost to vetoes; and
- latency and cost.

Any model, prompt, schema, renderer or policy change requires the held-out suite
to pass again. Use an exact dated model snapshot where the selected model offers
one; otherwise treat any alias update as a new release candidate.

## Human approvals

Human approval is required for:

- the photo data-handling policy;
- the label guide and held-out dataset;
- the first production model and every material upgrade;
- risk thresholds and permitted automatic state transitions;
- enabling semantic veto after shadow mode;
- changes to random human sampling; and
- batch and house-style acceptance.

## References

- [OpenAI images and vision](https://developers.openai.com/api/docs/guides/images-vision)
- [OpenAI Responses API](https://developers.openai.com/api/reference/cli/resources/responses/methods/create)
- [OpenAI model catalogue](https://developers.openai.com/api/docs/models)
