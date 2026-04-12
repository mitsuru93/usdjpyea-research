# Timing Mode Experiments (Research-Side, Pre-MT4)

This document defines the first narrow timing experiment layer for public research.

Important scope reminder:
- This is a **research-side screening approximation** only.
- It is **not MT4 parity** and not MT4-tested behavior.
- MT4 remains the final source of truth.

## Timing mode values

Set `timing_mode` in experiment/study run config.

### `baseline_touch`
- Preserves baseline behavior.
- Touch evidence creates and immediately enters candidate rows.

### `rv_close_confirm`
- RV candidate is created from intrabar touch evidence.
- Final RV entry decision is made at bar close.
- **Still-touch at bar close is NOT required.**
- TR/shock family timing remains baseline-equivalent (touch-entered immediately).

### `all_close`
- Research comparison mode only.
- All families use close-time decision handling.
- Not a recommended default; used to compare timing sensitivity.

## Current close-time rejection rule (conservative)

For close-time decision candidates (`rv_close_confirm` RV rows and all rows in `all_close`):
- reject when both upper and lower envelope touches happened in the same source bar (`ambiguous_dual_touch_same_bar`).
- otherwise, require close to be back inside the touched envelope side:
  - upper-touch candidate confirms only when `close < upper_env`
  - lower-touch candidate confirms only when `close > lower_env`
  - else reject with `close_not_back_inside_band`

This keeps same-bar ambiguity conservative and deterministic.

## Audit/output fields

`candidates_timing_audit.csv` includes deterministic fields:
- `timing_mode`
- `candidate_family`
- `timing_candidate_created`
- `timing_decision_event` (`touch_entered_immediately` / `close_confirmed` / `close_rejected`)
- `timing_close_confirmed`
- `timing_close_rejected`
- `timing_close_reject_reason`
- `timing_still_touch_at_close`

`timing_still_touch_at_close` is informational only.
It is **not** an entry requirement in `rv_close_confirm`.
Close-time state now affects close-decision confirm/reject via the inside-band rule above.

## Comparison artifacts

Timing summaries are emitted for compare-ready analysis:
- `summary_timing_overall.csv`
- `summary_timing_by_month.csv`
- `summary_timing_by_session.csv`
- `summary_timing_by_family.csv`

Use these with existing PnL/trade summaries to compare:
- trade count, avg pnl, total pnl, win rate
- timing candidate created/confirmed/rejected counts
- session/month/family splits where available.
