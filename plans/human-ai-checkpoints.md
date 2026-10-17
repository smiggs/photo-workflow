# Human and AI collaboration checkpoints

This plan extracts the work in the three main workflow documents that requires
both machine assistance and human judgement. Fully deterministic engineering
tasks and wholly manual creative editing are not repeated here.

## Decision record contract

Every checkpoint produces a durable decision record containing:

- checkpoint and run identifiers;
- input artefact hashes;
- AI/model, prompt, code and configuration versions where applicable;
- the AI recommendation and supporting evidence;
- the human decision, reason, identity and timestamp;
- any overrides or follow-up work; and
- the released artefact IDs affected by the decision.

Silence or absence of a decision is never approval.

## Checkpoints

| Checkpoint | AI contribution | Human contribution | Recorded result |
|---|---|---|---|
| Choose the darktable application route | Build disposable experiments, compare XMP/history and rendered pixels, report failures | Inspect representative full-resolution repairs and choose or reject a route | Approved route decision, supported darktable version and known limitations |
| Establish the coordinate contract | Generate marked fixtures, exercise transforms and report round-trip error | Confirm marks land on the intended image areas in darktable | Approved coordinate convention and tolerance |
| Release a defect profile | Detect candidates, calculate evidence and render overlays/crops | Accept, reject or amend every candidate | Immutable reviewed profile and decision record |
| Confirm epoch boundaries | Propose change points and assemble before/after evidence | Confirm, move or reject each boundary | Reviewed epoch intervals with confidence and reasons |
| Define automatic-repair policy | Measure texture/edge/semantic classifier behaviour and expose failure cases | Decide which contexts are eligible and set risk tolerance | Versioned policy and labelled examples |
| Label classifier fixtures | Preselect diverse and ambiguous crops, detect duplicates and organise queues | Label context, visibility, repair safety and failure reason | Versioned ground-truth fixture set |
| Resolve uncertain repairs | Explain why each frame/spot pair failed closed and prioritise the worklist | Repair manually, decline repair or override with a reason | Per-frame override or completed manual edit |
| Review automatic repairs | Build before/after/difference crops and triage suspicious cases | Inspect flagged cases plus a random sample of unflagged cases | Batch repair-quality decision and new regression fixtures |
| Check for missed defects | Produce full-frame overlays, flat-field analysis and likely miss candidates | Verify suspected misses at full resolution | Miss-rate assessment and profile/detector corrections |
| Write the house-style contract | Summarise reference edits and measured common behaviour | State the intended look and decide which differences are deliberate | Versioned creative contract |
| Build the house style | Measure paired base/finished renders and suggest candidate settings | Edit the representative frame and make creative choices | Candidate `.dtstyle`, provenance and rendered references |
| Validate held-out style results | Group recurring deviations by capture condition and prepare comparisons | Judge colour, tone, skin and failure conditions on a calibrated display | Release, revise or split decision |
| Approve a LUT approximation | Measure colour-patch and representative-image differences | Decide whether the approximation is acceptable for its named use | Versioned LUT, declared limits or rejection |
| Accept a production batch | Reconcile manifests, warnings, repair QA, miss checks and style checks | Make the final accept/reject decision | Signed-off batch manifest or rework list |

## Checkpoint detail

### 1. Darktable route approval

The AI runs and documents the spike from
[`dust-pipeline-implementation-plan.md`](../dust-pipeline-implementation-plan.md),
including transfer of retouch masks and source points, database/XMP precedence,
idempotence and style composition.

The human must examine exported pixels rather than trusting history entries or
command success. Approval states exactly which application route may touch
production work and what remains prohibited.

### 2. Defect-profile review

The AI supplies a full-frame overlay, per-defect evidence across source frames,
aperture behaviour, confidence and possible scene-content explanations. The
human reviews every candidate before the profile becomes immutable.

Rejected candidates remain in the decision record so the same false positive
can be recognised later. Each newly reviewed epoch receives its own immutable
profile ID, evidence and approval. An `equivalent_to` relationship records a
recurring defect state; it never transfers the earlier epoch's approval.

### 3. Epoch-boundary review

The AI presents the evidence series and independently built profiles on each
side of a proposed boundary. The human confirms that the apparent change is a
real defect-state change rather than insufficient data, aperture mix or scene
content.

Where evidence is inadequate, the correct result is `insufficient-evidence`,
not a guessed boundary.

### 4. Repair-policy and fixture labelling

The AI assembles a balanced queue across sky, gradients, water, walls, foliage,
fabric, faces, hair, text, strong edges, low signal and ambiguous cases. The
human supplies the ground-truth judgement for whether unattended repair would
be acceptable.

The dataset must include difficult negative examples and must be split by
shoot, not by random crop, to reduce leakage between training/tuning and held-
out evaluation.

The approved operating policy records whether semantic veto is enabled. An
outage never disables it: affected candidates become `uncertain` and require
human review. Switching to deterministic-only processing requires an explicit
human policy decision and invalidates dependent plans, approvals and outputs
before recomputation.

### 5. Batch review

AI triage may reduce the queue but may not eliminate human sampling. The human
reviews:

- every flagged automatic repair;
- every manual or uncertain entry that matters to the final image;
- a statistically useful random sample of unflagged automatic repairs;
- full-frame or flat-field evidence for missed defects; and
- frames around epoch boundaries.

Observed AI misses and false alarms become labelled regression fixtures.

### 6. House-style development and release

The AI measures registered base/finished pairs and identifies consistent or
condition-dependent behaviour. The human writes the creative intent, performs
the decisive edits and judges held-out renders on a calibrated display.

AI visual review may identify comparative patterns, but it is not a calibrated
colour instrument and cannot approve the style.

## Work queues

Maintain separate machine-readable queues for:

- `profile-review`;
- `epoch-review`;
- `repair-policy-labelling`;
- `manual-repair`;
- `automatic-repair-qa`;
- `miss-review`;
- `style-reference-review`;
- `style-held-out-review`; and
- `batch-acceptance`.

Every queue item has a stable ID and links to source hashes rather than relying
on a display filename alone.

## Completion criteria

This collaboration plan is operational when every checkpoint has:

- an input and output schema;
- a generated review artefact;
- an explicit human decision action;
- fail-closed behaviour for missing decisions;
- an audit trail in the run manifest; and
- at least one fixture proving that rejection and rework behave correctly.

