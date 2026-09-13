# Package 06: end-to-end orchestration and release

## Outcome

Integrate the proven commands into a resumable run without weakening their
individual validation or human gates. A run can stop safely, explain what it is
waiting for and resume only when the relevant inputs still match.

## Commands delivered

- `photo-pipeline run INPUT --run-dir RUN [--through STAGE] [--dry-run]`
- `photo-pipeline resume RUN [--through STAGE]`
- `photo-pipeline status RUN [--json]`
- `photo-pipeline approve RUN CHECKPOINT DECISION_FILE`
- `photo-pipeline verify-run RUN`

## Stage graph

```text
inventory
  -> decode and coordinate approval
  -> detection
  -> epoch-boundary approval
  -> profile approval
  -> per-frame repair planning
  -> optional ChatGPT veto
  -> repair-plan approval where required
  -> darktable application
  -> export
  -> validation and review packets
  -> batch approval
```

House-style measurement can run beside detector work, but its approved style
and darktable composition check are dependencies of production export.

## Orchestrator design

- Represent the graph and stage states as data, not a chain of opaque command
  strings.
- Call importable stage APIs in-process where safe; keep external programs in
  the shared subprocess adapter.
- Give each stage declared inputs, outputs, configuration subset, capability
  requirements and approval gates.
- Compute a stage fingerprint from all of those inputs. Reuse outputs only on
  an exact match.
- Model states explicitly: `pending`, `ready`, `running`, `awaiting_approval`,
  `complete`, `failed`, `blocked`, `superseded` and `skipped_optional`.
- Acquire a scoped run lock and include stale-lock recovery that requires
  inspection rather than blind deletion.
- Write state transitions and artefact creation atomically to an append-only
  event log, then derive the readable run status.

## Approval handling

- Generate a checkpoint packet and decision template; never infer approval from
  the presence of a file alone.
- Validate reviewer decision, packet hash, upstream fingerprints and allowed
  disposition.
- If an upstream stage changes, mark dependent approvals and artefacts
  superseded and explain the smallest required rerun.
- Allow rejection with structured reason codes and a return target.
- Keep profile release, individual repair disposition and final batch acceptance
  as distinct approvals.

## Resume and failure behaviour

- A process interruption leaves the active stage incomplete and preserves its
  diagnostic workspace.
- `resume` verifies every completed stage before starting new work.
- `--dry-run` shows proposed stages, capability gaps, expected outputs and human
  gates without decoding or writing production artefacts.
- Optional ChatGPT unavailability becomes a recorded optional-stage outcome
  and follows the configured safe fallback.
- Missing or unverified darktable blocks application/export but still permits
  inventory, detection, planning and evidence generation.
- Never continue past corrupt output, stale approval, coordinate mismatch or an
  unknown schema/tool version.

## Run manifest and reporting

The final manifest contains:

- source inventory/content hashes and exclusions;
- all configuration/schema/tool/model/prompt versions;
- cohort, epoch, profile, repair-plan, sidecar, style and output IDs/hashes;
- stage transitions, warnings, failures and approvals;
- export properties and verification results; and
- review sample definition, dispositions and batch release state.

Produce a short human summary with counts by state, unresolved items, capability
warnings and direct links to review artefacts. The machine manifest remains the
source of truth.

## Tests

- Unit tests for graph ordering, fingerprints, invalidation, approval binding,
  exit codes and state transitions.
- Failure injection at every write and external-process boundary.
- Resume tests after interruption before, during and after each stage commit.
- Tests that mutate one upstream hash and verify the correct dependent stages
  and approvals are invalidated.
- End-to-end fixture run without ChatGPT, with cached ChatGPT results and with
  simulated ChatGPT failure.
- End-to-end fixture run with a fake darktable adapter; then a separate
  installation test using the approved real version.
- Read-only source-tree assertion before and after every integration run.

## Pilot and release sequence

1. Run synthetic fixtures and publish the complete verification report.
2. Run a copied, expendable real batch with all repairs requiring review.
3. Resolve failures and freeze configuration/tool versions for a release
   candidate.
4. Run a second real batch with the proposed automation thresholds.
5. Review difficult cases, automatic sample, clean controls and miss estimate.
6. Record human batch acceptance and archive the manifest, configuration,
   decision records and shareable evidence.

Production use remains a deliberate command/configuration choice; passing a
pilot must not silently enable automatic repair for future cameras or profiles.

## Human checkpoint

The human reviews the complete pilot summary, difficult cases, automatic and
clean-control samples, miss estimate, unresolved warnings and reproducibility
report. They either approve this exact release candidate and operating policy or
return structured rejection reasons to the appropriate stage. Approval is bound
to the full run and release fingerprints.

## Exit criteria

- The run can be interrupted at any point and safely resumed or explained.
- No stage can consume stale or unapproved inputs.
- The final summary and manifest account for every source frame and proposed
  defect.
- Both deterministic-only and optional-AI paths pass end-to-end fixtures.
- A human has accepted a real pilot using the review and miss criteria in the
  master plan.
