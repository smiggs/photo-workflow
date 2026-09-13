# Package 02: detection, profiles and epochs

## Outcome

Implement a deterministic detector that accumulates evidence across compatible
raw frames, distinguishes persistent sensor candidates from scene detail and
proposes camera-cleaning epochs for human confirmation.

## Commands delivered

- `photo-pipeline detect RUN [--cohort ID]`
- `photo-pipeline segment-epochs RUN [--cohort ID]`
- `photo-pipeline build-profile RUN --epoch ID`
- `photo-pipeline render-detection-evidence RUN`

## Inputs and outputs

Inputs are the reviewed inventory, coordinate contract and detector
configuration. Outputs are:

- per-frame normalisation metadata and residual maps;
- `candidates.jsonl` with evidence per frame and aperture;
- `epoch-proposals.json` and boundary evidence packets;
- `defect-profile.json` per approved epoch; and
- thumbnails, full-resolution crops and aggregate maps for review.

Large arrays use a documented binary format; JSON records hold hashes, shapes,
dtypes, coordinate spaces and links rather than embedding arrays.

## Modules and responsibilities

### Linear decode adapter

- Reuse package 01 settings; fail if a frame would be decoded differently.
- Expose raw colour-filter layout and valid-pixel masks where available.
- Mask optical black, clipped, invalid and decoder-repaired pixels.

### Illumination normalisation

- Estimate low-frequency illumination without erasing defect-scale structure.
- Calculate residuals in a documented linear domain.
- Make scale selection relative to image dimensions and expected defect radius.
- Record diagnostic percentiles and detect frames unsuitable for aggregation.

### Evidence-frame selection

- Prefer declared flat-field frames when they pass exposure, clipping and blur
  checks.
- Otherwise select a temporally stratified, visually varied subset rather than
  one contiguous or convenient sequence.
- Enforce and report minimum sample size and aperture coverage.
- Record selected and rejected frame IDs plus reason codes so selection can be
  reproduced and reviewed.

### Persistent-candidate detector

- Register evidence in the approved sensor coordinate system.
- Combine robust per-frame residual evidence rather than averaged rendered RGB.
- Track support count, aperture relationship, darkness, shape, channel/CFA
  consistency and positional stability.
- Reject or flag clusters caused by borders, repeated scene alignment, clipping
  or insufficient coverage.
- Preserve negative evidence: a predicted point absent in a frame must affect
  confidence rather than silently disappearing.

### Evidence renderer

For every candidate, render:

- the aggregate map with location and scale;
- a frame/contact sheet ordered by aperture and capture time;
- representative full-resolution crops;
- clean control locations; and
- a compact table of feature values and thresholds.

Images are evidence only; numeric source data remains addressable from the
candidate record.

### Epoch segmentation

- Convert per-frame candidate evidence into a sequence of profile states.
- Propose boundaries for abrupt appearance/disappearance, displacement or broad
  confidence change.
- Penalise unnecessary boundaries and report confidence plus alternatives.
- Treat camera cleaning, sensor service, body changes and long capture gaps as
  metadata hints, not automatic truth.
- Never merge across an unreviewed ambiguous boundary.

### Profile builder

- Create stable defect IDs within an epoch.
- Store centre, extent, shape representation, confidence, evidence coverage and
  applicability limits.
- Store detector and coordinate versions plus all supporting artefact hashes.
- Support a superseding profile without mutating a released profile.

### Previous-profile comparator

- Find only profiles compatible in body identity, active-area geometry and
  coordinate-contract version.
- Perform a bijective defect match using declared coordinate, extent, contrast
  and confidence tolerances.
- Reuse the prior immutable profile ID only when there are no unexplained
  additions, removals or material changes.
- Otherwise write the new profile with `supersedes` or a documented divergence
  relationship; never overwrite or silently redirect the old profile.
- Include an A -> B -> A fixture to prove repeated states can reference an
  earlier equivalent profile.

## Tests and evaluation

- Synthetic residual maps with known circles, irregular blobs, gradients,
  clipping, hot pixels and scene-like edges.
- Sequence fixtures with known appearance/disappearance points and no-change
  controls.
- Golden tests for stable candidate/profile serialisation.
- Real local fixtures labelled independently by a human; keep labels separate
  from tunable thresholds.
- Report location error, precision/recall by confidence band, boundary error,
  false positives by scene class and misses by aperture band.
- Test on at least one frame where the defect is visually weak and one where
  scene texture resembles a spot.

## Human checkpoints

1. Review proposed epoch boundaries in capture order and approve or edit them.
2. Review each proposed defect with aggregate, per-frame and control evidence.
3. Approve a versioned profile or return candidate IDs with rejection reasons.

Approvals bind to detector configuration, inventory, coordinate transform and
evidence hashes. Threshold changes invalidate them.

## Exit criteria

- A fixed fixture/configuration produces the same candidates and epoch proposal.
- Synthetic location and radius errors stay within the coordinate contract.
- The measured pilot precision/recall meets thresholds chosen in the master
  plan; results are reported by confidence band rather than as one headline.
- Every released defect can be traced to multi-frame evidence and a human
  approval.
- Boundary ambiguity is represented explicitly and cannot fall through to one
  default profile.
