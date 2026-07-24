# USDJPY RQ-020B Long-Horizon Regime Diagnosis Result v1

## Decision

`RQ-020B` retained one descriptive state for a separate architecture review. No family, router, candidate, MT4 work or 2025 access is authorized by this result.

- Passing state: `range_position_20d = UPPER_THIRD`
- Preferred action: continuation of the unchanged fixed-five signal
- Passed states: `1 / 19`
- Historical 2024 source mutation: none
- Parameter, bin, interaction, strategy-subset and weight optimization: none
- 2025 and MT4 access: none

## Exact lineage and regression gates

- 2023 historical-compatible transform: 24,825 M15 rows, 1,543 shifted timestamps, zero duplicates and monotonic order.
- 2023 canonical baseline ledger reconciliation: 964 rows, exact keys and numeric values.
- Historical-compatible 2023 B02/F05 baseline: 961 opened, 960 closed, B02 JPY -12,459, F05 JPY +3,180, total JPY -9,279.
- Fixed-five 2024 H1/H2 signal and T0 trade regressions: all exact.

## Passing state

The signal close is inside the upper third of the trailing 1,920-M15-bar high-low range. This state was fixed before outcome evaluation. It is not a selected threshold.

| Fold | Trades | Strategies | Default net | Severe net | Default PF | Severe PF | Default top-two positive-date share |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023H1 | 917 | 5 | +3862.1 | +2028.1 | 1.269 | 1.133 | 0.171 |
| 2023H2 | 898 | 5 | +2430.3 | +634.3 | 1.223 | 1.054 | 0.250 |
| 2024H1 | 1,147 | 5 | +3611.6 | +1121.2 | 1.229 | 1.066 | 0.229 |
| 2024H2 | 779 | 5 | +7345.7 | +5548.9 | 1.651 | 1.459 | 0.237 |

Every fold is positive under default and severe costs. The preferred continuation sign remains unchanged after excluding each one of the five strategies in every fold. The minimum fold contains 779 trades and all five strategies.

## Strategy-level qualification

The state is a cross-strategy aggregate finding, not proof that every strategy is independently robust in every fold. Notable weak cells are:

- B02 severe net in 2023 H1: `-87.1 pips`.
- F05 default/severe net in 2023 H2: `-23.1 / -421.1 pips`.
- F05 severe net in 2024 H1: `-53.7 pips`.

Therefore the result does not authorize selecting an individual strategy or claiming universal strategy invariance.

## Near-pass states and failed mechanisms

- `market_direction_agreement = UP_UP` kept continuation as the preferred action in all folds and was default-positive, but severe net was `-364.3 pips` in 2023 H2.
- `trade_alignment_agreement = ALIGN_ALIGN` kept continuation as the preferred action in all folds, but severe net was `-1,011.4 pips` in 2023 H1.
- neutral 5d/20d volatility ratio was default-positive in all folds, but severe net failed in 2023 H1, 2023 H2 and 2024 H2 and leave-one-strategy-out sign stability failed.
- Path-efficiency states did not provide a four-fold distinction; nearly all supported observations fell in the low-efficiency bin.

## Interpretation

The retained evidence is broader than the closed local B02/F05 repairs: it appears in all five complete strategies and survives every leave-one-strategy-out action-sign check. However, it may represent a broad admission context rather than a continuation-versus-reversal router. The behavior outside the upper-third state is not stable enough to justify reversing or trading the complement.

## Next authorized work

Open `RQ-020C` as an architecture review only. Using the already fixed `UPPER_THIRD` state, report long/short attribution, strategy contribution, complement behavior and impact sufficiency. Compare an admission-only architecture with a continuation/reversal router, and perform the duplicate-research audit against Families A–I and RQ-019. Do not change the one-third boundary, add interactions, preregister a family, evaluate a candidate, use MT4 or access 2025 in that review.

## Evidence files

- `configs/research/usdjpy_rq020b_long_horizon_regime_result_v1.json`
- `data/research/usdjpy_rq020b_state_fold_metrics_v1.csv`
- `data/research/usdjpy_rq020b_state_strategy_fold_metrics_v1.csv`
- `data/research/usdjpy_rq020b_state_leave_one_strategy_out_v1.csv`
- `data/research/usdjpy_rq020b_state_gate_v1.csv`
