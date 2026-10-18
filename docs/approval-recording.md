# Package 01 approval recording

The minimal interface records human decisions for `cohort-rules` and
`coordinate-contract`. It follows Package 06's future
`photo-pipeline approve RUN CHECKPOINT DECISION_FILE` contract. It does not run
later stages or release a pipeline.

## Prepare a packet

Complete inventory and the available decode checks, then generate the packet:

```bash
uv run photo-pipeline review-packet RUN cohort-rules --json > REVIEW.json
uv run photo-pipeline review-packet RUN coordinate-contract --json
```

`RUN` is an existing owned run directory outside the source tree. `REVIEW.json`
is a separate working copy of the command output. The packet lists evidence
paths relative to the run, camera/orientation coverage, exclusions, limitations,
and blockers. Inspect the referenced inventory, cohorts, decode report and
calibration images, rather than treating a successful command as approval.

Copy the returned `decision_template` object into `DECISION.json`. A human must
fill in `reviewer`, `decision` (`approved` or `rejected`), `timestamp_utc` (an
explicit UTC timestamp), and `reason`. All four fields start empty; there is no
default decision. Preserve the packet hash, run ID, scope, input hashes and
supersession field exactly. An automated assistant must never fill in the human
decision for an actual run.

## Record and inspect a decision

```bash
uv run photo-pipeline approve RUN cohort-rules DECISION.json --dry-run --json
uv run photo-pipeline approve RUN cohort-rules DECISION.json --json
uv run photo-pipeline inspect-run RUN --json
```

Both approval commands accept `--config`, `--dry-run`, `--log-level` and `--json`.
An explicit configuration must match the run. Dry runs do not publish packets
or decisions. An approval dry run still requires a previously published packet.

Packets are stored under `reviews/PACKET_SHA256.json`. Decisions are stored
under `approvals/DECISION_SHA256.json`, then published in `run-manifest.json`.
Existing files are never overwritten. A manifest write interrupted after the
decision file leaves an uncommitted record: inspection does not count that file
as approval, and retrying refuses to overwrite it. Inspect before recovery.

Correct a decision by generating a new packet/template and submitting a new
human decision. `supersedes_sha256` must identify the latest decision for the
same checkpoint, and the correction must not predate that decision. Earlier
records and evidence remain intact.

## Scope and invalidation

The packet binds the run, inventory, configuration, tools and implementation,
stage fingerprints, every stage artefact and resolved transforms when decode
evidence exists. Scope includes cohort IDs, cohort-rule version, coordinate
contract version and named native coordinate spaces. Listed source-file hashes
are verified before recording a decision. Changing tools or implementation
requires a new run. Adding stage evidence changes the packet and makes an
existing decision stale, requiring fresh review and explicit supersession.

`inspect-run.review_status` derives `awaiting_approval`, `approved`, `rejected`
or `stale` for each checkpoint and its cohorts. Historical `cohorts.json`,
inventory status and stage states remain unchanged. Legacy approval records
without packet/scope binding cannot open these checkpoint gates. Inspection
also checks current tool/implementation compatibility when scoped decisions
exist; its `verified` flag alone is not approval.

Cohort approval does not approve geometry or release Package 01. Coordinate
approval is currently blocked by unverified full-resolution darktable
calibration, even if native previews are available. Rejection can be recorded
for a blocked packet. Missing decode evidence, incomplete orientation coverage,
no reviewable cohorts and inventory errors are surfaced as blockers where
applicable. Full-resolution repair support, camera/mode coverage and the human
checkpoint remain release requirements.
