# USDJPY Long-Horizon Regime Diagnosis Result v1

Decision: **close RQ-020B; do not create a router from the tested states**

## Scope

The unchanged fixed-five trade population was partitioned at signal close using predeclared 5-day/20-day market-state bins. The analysis covered 6,586 feature-complete trades across 2023 H1, 2023 H2, 2024 H1 and 2024 H2. No interaction, threshold optimization, MT4 run or 2025 evidence was used.

Fourteen state bins were observed. The planned 20-day path-efficiency `GE_0_25` state had no observations. No observed state passed the complete four-fold successor gate.

## Strongest retained state: upper third of the 20-day range

When the signal close was in the upper third of the trailing 20-day range, continuation was preferred in all four development folds. Default net, severe net, action advantage and five-strategy breadth were positive in every fold.

| Fold | Trades | Default pips | Default PF | Severe pips | Severe PF | + / - months | Ex-best-two dates |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 H1 | 917 | +3,862.1 | 1.269 | +2,028.1 | 1.133 | 4 / 1 | +1,726.2 |
| 2023 H2 | 898 | +2,430.3 | 1.223 | +634.3 | 1.054 | 4 / 1 | **-23.2** |
| 2024 H1 | 1,147 | +3,611.6 | 1.229 | +1,121.2 | 1.066 | 4 / 2 | +434.5 |
| 2024 H2 | 779 | +7,345.7 | 1.651 | +5,548.9 | 1.459 | **3 / 2** | +4,178.3 |

It nevertheless fails two frozen gates: 2023 H2 ex-best-two is slightly negative, and 2024 H2 has only three positive effect months rather than four. These gates are not relaxed. The state is retained as architecture evidence only, not as a candidate or router rule.

## Other directional states

`BOTH_UP` and `PERSISTENT_ALIGNED` also prefer continuation in all four folds and remain default-positive, but each fails severe-cost and concentration/breadth gates in at least one 2023 fold. Most other bins reverse preferred action between 2023 H1 and later periods.

## Scientific conclusion

A single coarse multi-day state does not provide a complete robust continuation/reversal router. RQ-020B is closed. No interactions, alternative cut points or range-position refinements may be derived from this result.

## Next non-duplicate analysis

The prior R2/R3 program evaluated all 60 frozen R1 v2 Entry definitions across eleven horizons only on 2024 H1. R4-R6 reduced this universe to eight representatives and then five complete strategies; candidate-specific 2024 H2 was opened only for those five, and none of the 660 combinations was previously evaluated on the exact 2023 lineage.

The next question is therefore `USDJPY-RQ-020E`: a descriptive family-level cross-year architecture census of the complete frozen 60 Entry × 11 horizon universe across the four development folds. The census may identify a robust family/horizon region, but may not select a single maximum, modify an Entry, expand a horizon, optimize a weight or access 2025.
