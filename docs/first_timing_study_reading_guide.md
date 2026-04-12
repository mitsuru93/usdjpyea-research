# First Timing Study Reading Guide

Use this guide after your first private-data timing run from:

- `configs/local/local_study_rv_close_confirm_first_real.example.yaml`

This is a narrow pre-MT4 research workflow. It does **not** claim MT4 parity.
MT4 remains the final source of truth.

## Run intent recap

The first-real template compares three timing modes on one shared private CSV path:

- `baseline_touch`: baseline touch-entry reference.
- `rv_close_confirm`: RV intrabar touch creates candidate, bar close decides entry/reject, and **still-touch at close is not required**.
- `all_close`: close-decision handling for all families, used mostly as a comparison reference.

## What to read first (in order)

Start from `<output_root>/compare/`:

1. `compare_overall.csv`
2. `compare_by_family.csv`
3. `compare_timing_by_decision_event.csv`
4. `compare_timing_by_reject_reason.csv`
5. `compare_timing_by_family_reject_reason.csv`
6. `compare_timing_by_still_touch_status.csv`

Then drill into month/session splits if needed.

## How to interpret key files

### `compare_overall.csv`

Check practical top-line movement between `baseline_touch` and `rv_close_confirm`:

- trade count compression/expansion
- avg/total pnl movement
- win-rate changes

Goal for first pass: confirm that timing changes are material but not unstable/noisy.

### `compare_by_family.csv`

Confirm where change happens:

- RV rows should carry most of the delta for `rv_close_confirm`.
- TR/shock behavior should remain close to baseline unless broader timing mode differences are expected.

If non-RV families move unexpectedly, inspect run configs and timing diagnostics before drawing conclusions.

### `compare_timing_by_decision_event.csv`

Use this as the first timing sanity check:

- `close_confirmed` and `close_rejected` should appear for close-decision candidates.
- `touch_entered_immediately` remains expected for baseline-style immediate entries.

For `rv_close_confirm`, you want a clear and explainable confirmed/rejected split rather than all-or-nothing behavior.

### `compare_timing_by_reject_reason.csv`

Check if rejections are concentrated in deterministic reasons such as:

- `ambiguous_dual_touch_same_bar`
- `close_not_back_inside_band`

A readable reject-reason distribution usually means the experiment is operational and diagnosable.

### `compare_timing_by_family_reject_reason.csv`

Verify reject reasons by family:

- RV should dominate close-reject activity under `rv_close_confirm`.
- Large reject clusters in other families may indicate you are effectively analyzing `all_close` effects rather than RV-specific behavior.

### `compare_timing_by_still_touch_status.csv`

Treat still-touch status as diagnostic context only:

- It helps profile close-time bar state.
- It is **not** an entry requirement for `rv_close_confirm`.

If results only look good when still-touch is true, note that as a hypothesis for later MT4-side validation rather than as a default rule.

## Patterns that make `rv_close_confirm` look promising

A practical first-pass signal is:

- moderate trade-count reduction vs baseline,
- cleaner reject-reason concentration,
- stable or improved avg pnl / total pnl,
- RV-led change profile (not broad unintended family distortion).

This is a screening signal only; it is not a production conclusion.

## Why `all_close` is mostly a comparison reference

`all_close` applies close-decision handling to every family and can overstate how much behavior shifts when timing logic is broadened.
Use it to bound sensitivity and understand direction/magnitude, not as a default target mode.

## Final reminder

Keep conclusions narrow: this step is for local/private pre-MT4 screening so the next action is obvious:

1. copy template,
2. replace CSV path,
3. run,
4. review the key compare files above,
5. carry shortlisted ideas to MT4 validation.
