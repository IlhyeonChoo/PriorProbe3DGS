---
name: "prior-geometry-check"
description: "Use when gaussian-direct prior insertion geometry must be verified, especially for the blocking `prior-runtime` check immediately after aligned prior preparation and the advisory `quality-gate` audit before result interpretation or reporting."
---

# Prior Geometry Check

Use this shared skill whenever prior insertion geometry is in scope.

- `prior-runtime` uses the Runtime Profile as a blocking gate before optimization.
- `quality-gate` uses the Quality-Gate Profile as an advisory audit before analysis or reporting.
- This skill is not a substitute for direct code review or patch review.

## Core rules

- Metadata consistency is necessary but not sufficient for geometry correctness.
- Treat the actual aligned prior as the geometry source of truth, not just the alignment payload.
- Prefer scene-relative evidence over target-only evidence.
- If visual evidence contradicts metadata, record the contradiction and treat the visual evidence as authoritative for the audit conclusion.
- Do not invent thresholds. Use this precedence:
  1. explicit runtime config or `geometry_validation_policy`
  2. thresholds already written to `prior_init/metadata.json`
  3. approved plan thresholds referenced by the active experiment notes
- If no thresholds are available from any level, the check must use scene-relative evidence only and record the absence of quantitative thresholds in the output.

## Shared evidence

Check the smallest set of available artifacts needed for a defensible decision:

- `prior_init/aligned_prior_*.ply`
- `prior_init/metadata.json`
- current run scene proxy or base scene point cloud
- dataset `scene_meta.json` room bounds when available
- `prior_specs.json`, `backend_run.json`, or equivalent provenance records when needed
- viewer screenshots, iter_0 renders, contact sheets, or side-by-side comparisons when available

## Shared checks

Run these checks in order and stop only when the active profile says to stop:

1. Metadata consistency
- compare actual aligned prior AABB with alignment payload or recorded expected AABB when present
- inspect center and bottom-anchor error when target anchors exist
- inspect emitted runtime geometry metrics such as outside-scene ratios and nearest-neighbor distances

2. Scene-relative placement
- compare prior AABB and center against the base scene or scene proxy AABB
- compare against room bounds from `scene_meta.json` when available
- treat a prior center outside the base scene AABB or room AABB as a strong failure signal
- treat large nearest-scene distances or clear separation from room geometry as a floating signal

3. Visual evidence
- inspect screenshots or renders for floating priors, room-outside protrusion, or room-structure mismatch
- for baseline/prior comparisons, first ask whether both runs preserve the same room structure before making performance claims

## Red flags

- `oracle_target_box` or another path that can bypass scene-relative sanity checks
- prior AABB min or max materially outside base scene or room bounds
- prior center far from the nearest base-scene geometry
- viewer evidence showing a detached cluster in empty space
- large objects such as sofa, table, or lamp protruding through room boundaries
- runtime pass with contradictory visual evidence

## Runtime Profile

Use this profile only for `prior-runtime`.

### Goal

Block obviously wrong prior placement before optimization begins.

### Timing

Run after aligned prior preparation and selected-prior metadata resolution, and before any optimization step.

### Required behavior

- Load the aligned prior artifact and available scene proxy for the current run.
- Use configured runtime thresholds when available.
- Emit per-prior geometry validation payloads into runtime metadata.
- Fail the run if the blocking criteria are violated.
- Write validation metadata before stopping the run.
- If room bounds or visual artifacts are unavailable at runtime, continue with the available scene-proxy evidence and record the missing evidence.
- If a lightweight audit summary can be emitted cheaply, include it, but lack of a visual summary alone must not block the run.
- Run all available shared checks to completion before applying blocking criteria, so the validation payload includes the full evidence set even on failure.

### Blocking criteria

Block the run when at least one of the following is true:

- runtime geometry metrics exceed their configured thresholds
- the actual aligned prior is clearly outside the available scene proxy or room bounds
- emitted metadata and actual aligned prior geometry contradict each other in a way that makes placement untrustworthy

### Runtime decision states

- `pass`
- `fail`

## Quality-Gate Profile

Use this profile only for `quality-gate`.

### Goal

Audit a completed run before conclusions, comparisons, or reports rely on geometry correctness.

### Timing

Run after runtime validation exists and before result interpretation or reporting closes geometry correctness.

### Required behavior

- Read runtime geometry validation first and treat it as the starting claim, not as sufficient proof.
- Re-check scene-relative placement against base scene or room bounds.
- Use screenshots, iter_0 renders, or viewer evidence when available.
- Escalate contradictions between runtime metadata and visible geometry.
- Keep the audit advisory: it does not retroactively stop a finished run, but it controls how confidently later agents may talk about geometry correctness.

### Advisory decision states

- `pass`
- `advisory_fail`
- `insufficient_evidence`

### Downstream rule

If the audit result is `advisory_fail` or `insufficient_evidence`:

- downstream analysis and reporting may continue
- geometry risk and uncertainty must be stated explicitly
- no agent may claim that geometry correctness is closed

## Output contract

Return findings in this format:

- `stage`
- `decision`
- `files or artifacts checked`
- `key metrics`
- `key findings`
- `remaining uncertainty`
- `next recommended action`
