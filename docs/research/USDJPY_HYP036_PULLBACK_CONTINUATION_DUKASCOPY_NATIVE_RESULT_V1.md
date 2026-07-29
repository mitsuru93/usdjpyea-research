# USDJPY-HYP-036 Pullback Continuation Dukascopy-Native Result v1

## Decision

`NO_PORTABLE_EXECUTABLE_CANDIDATE`

The fixed Pullback Continuation rule was rebuilt and executed entirely from Dukascopy BI5 Bid/Ask Tick data. The source-native candidate retained a modest pooled profit, but failed the preregistered standalone portability gate. HYP-035 was not reopened and its Atlas event population was not reused.

## Binding result

- Source-native trades: **1,332**
- Net: **+¥17,005**
- Profit factor: **1.110**
- Win rate: **48.80%**
- Maximum realized drawdown: **¥13,284**
- Minimum equity from ¥1,000,000: **¥999,736**
- Positive folds: **3/4**, required 4/4
- Positive months: **13/24**, required at least 16/24
- Worst fold: **2024H2 −¥1,163**, required nonnegative

The binding failures were `folds_4_of_4`, `minimum_fold_nonnegative`, and `positive_months_ge_16` at `DEVELOPMENT_STANDALONE`.

## Fold results

| Fold | Trades | Net | PF |
|---|---:|---:|---:|
| 2023H1 | 318 | +¥3,953 | 1.101 |
| 2023H2 | 345 | +¥7,112 | 1.217 |
| 2024H1 | 342 | +¥7,103 | 1.244 |
| 2024H2 | 327 | −¥1,163 | 0.979 |

## Directional attribution

| Side | Trades | Net | PF |
|---|---:|---:|---:|
| Long | 832 | −¥674 | 0.993 |
| Short | 500 | +¥17,679 | 1.273 |

The pooled edge is therefore not directionally balanced. Selecting Short after observing this result would be an outcome-defined rescue and is not authorized under HYP-036.

## Source and integrity

- 24 monthly source archives
- 84,428,370 Tick rows
- 49,894 reconstructed M15 bars
- Ask below Bid: 0
- Duplicate timestamps: 0
- Nonmonotonic timestamps: 0
- Duplicate M15 bars: 0
- Unresolved executable chronology: 0
- Duplicate candidate events: 0
- Lookahead violations: 0
- JPY replay mismatches: 0

Source authority and executable integrity passed.

## Portfolio diagnostics

These values are descriptive only because the standalone gate failed before the binding portfolio stage:

- B02/F05 baseline net: **+¥51,627**
- Combined realized net: **+¥68,632**
- Baseline realized DD: **¥40,487**
- Combined realized DD: **¥34,339**
- Correlation to B02: **0.340**
- Correlation to F05: **0.446**
- Worst 5-business-day result worsened from **−¥11,585** to **−¥12,103**
- Worst 20-business-day result worsened from **−¥16,588** to **−¥18,137**
- Full-equity portfolio evaluation was not executed.

The candidate added profit and reduced realized-close DD diagnostically, but worsened both loss-cluster measures. These diagnostics cannot override the failed standalone gate.

## Stop consequences

The following were not executed: concentration binding gate, bootstrap, execution robustness binding gate, full-equity portfolio gate, candidate freeze, 2020–2022 historical validation, Core/MT4 parity, and 2025 external gates.

## Evidence

- Research PR: #396
- Scientific Run: `30414664817`
- Head SHA: `51be2404fcf060a09146c4e1f48a622cf6aa1c4d`
- Artifact: `8709903106`
- Artifact digest: `sha256:2cf0578322a9ad650ff5fe4ea60d9332624009b9f6bc1744450eb6c0ffc1afd8`
- Deterministic evidence archive SHA256: `f3a69cb60d5e39a72d2d000af54d03a563954df3a74c84db49e3c8c24086f30b`
- Archive readback: `PASS`

## Final boundary

Close HYP-036. Do not rescue it by Short-only selection, session or period exclusion, EMA/ATR/hold retuning, B02/F05 routing, lot-size changes, or 2020–2022/2025 outcome access. Production and live authorization remain `false`.
