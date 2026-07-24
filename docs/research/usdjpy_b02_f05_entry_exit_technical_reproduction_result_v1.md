# USDJPY B02/F05 Entry–Exit Technical Reproduction and Entry Closure v1

## Decision

Stage E1/E2 completed from exact Release/Actions authorities. The 1,882-trade dataset, path classes, technical features, pooled statistics and portable-factor result reproduce independently. The Entry technical family is **CLOSED_NO_PORTABLE_LOCAL_TECHNICAL_ENTRY_SEPARATOR**.

The original uploaded bundle bytes were not required: the source market/trade data were recovered from their exact repository artifacts and rebuilt with committed lineage logic. The original model script was not available, so the independent logistic AUCs are reported separately rather than called byte-identical.

## Source identity

- 2023 preparation: run 29997167048 / artifact 8559483151 / `22d66bf76c60362b78e9badff2113bc196b80e3657f5083ae470d1d62df70c01`
- 2023 binding baseline: run 29998477805 / artifact 8560057457
- 2023 Atlas: run 30001786384 / artifact 8561286612 / `9e6aa5cebccc44a51e8e0aa86fd87653d2e471446c4a92cd62d8699f4c6bf591`
- 2024H1: run 29787357305 / artifact 8479048161 / `e078758343995c8254244dd36385c93a61a7124cb5037beb458afdf5d0e208e5`
- 2024H2: run 29873856877 / artifact 8512432416 / `9c5846e8b6e47b4b981a3ceeec856391311d3864a8cd7c2bef7caf7d21e6375b`

Lineage: `USDJPY_HISTORICAL_2024_LEGACY_CONTRACT_APPLIED_TO_2023_V1`. Historical 2024 was not changed; 2025 was not accessed.

## Population

| strategy   | fold   |   P1_GIVEBACK_TO_LOSS |   P2_MINOR_FAVORABLE_THEN_LOSS |   P3_NEVER_PROFITABLE |   WINNER |
|:-----------|:-------|----------------------:|-------------------------------:|----------------------:|---------:|
| B02        | 2023H1 |                    30 |                             16 |                    14 |       61 |
| B02        | 2023H2 |                    26 |                             19 |                     7 |       57 |
| B02        | 2024H1 |                    16 |                             18 |                     6 |       57 |
| B02        | 2024H2 |                    22 |                              9 |                     7 |       64 |
| F05        | 2023H1 |                    88 |                             58 |                    51 |      170 |
| F05        | 2023H2 |                    79 |                             71 |                    34 |      179 |
| F05        | 2024H1 |                    48 |                             64 |                    41 |      178 |
| F05        | 2024H2 |                   108 |                             34 |                    50 |      200 |

## Entry P3 result

- B02 P3: 34; F05 P3: 176.
- Portable material technical factors: B02 0; F05 0.
- Pooled medians/effects reproduce the source report, including B02 RSI14 and F05 RSI7/momentum/efficiency examples.
- No threshold search is authorized.

### Independent LOFO comparison

| strategy   | held_out_fold   |   expected_report_auc |   independent_auc |   absolute_difference |
|:-----------|:----------------|----------------------:|------------------:|----------------------:|
| B02        | 2023H1          |                 0.551 |             0.453 |                 0.098 |
| B02        | 2023H2          |                 0.461 |             0.469 |                 0.008 |
| B02        | 2024H1          |                 0.562 |             0.564 |                 0.002 |
| B02        | 2024H2          |                 0.547 |             0.546 |                 0.001 |
| F05        | 2023H1          |                 0.566 |             0.565 |                 0.001 |
| F05        | 2023H2          |                 0.629 |             0.642 |                 0.013 |
| F05        | 2024H1          |                 0.517 |             0.533 |                 0.016 |
| F05        | 2024H2          |                 0.546 |             0.530 |                 0.016 |

The independent model differs modestly because the original uploaded model script was not retained. This does not alter the negative Entry conclusion: both implementations remain weak and fold-unstable, and the exact univariate portability gate is zero for both strategies.

## P2 and P1 descriptive result

| analysis   | strategy   |   minutes |   expected_report_mean_auc |   independent_mean_auc |   absolute_difference |
|:-----------|:-----------|----------:|---------------------------:|-----------------------:|----------------------:|
| P1         | B02        |         0 |                      0.523 |                  0.513 |                 0.010 |
| P1         | B02        |        15 |                      0.547 |                  0.530 |                 0.017 |
| P1         | B02        |        30 |                      0.639 |                  0.620 |                 0.019 |
| P1         | B02        |        60 |                      0.676 |                  0.634 |                 0.042 |
| P1         | B02        |       120 |                      0.727 |                  0.697 |                 0.030 |
| P1         | F05        |         0 |                      0.528 |                  0.536 |                 0.008 |
| P1         | F05        |        15 |                      0.574 |                  0.572 |                 0.002 |
| P1         | F05        |        30 |                      0.648 |                  0.646 |                 0.002 |
| P1         | F05        |        60 |                      0.677 |                  0.668 |                 0.009 |
| P1         | F05        |       120 |                      0.778 |                  0.769 |                 0.009 |
| P2         | B02        |         0 |                      0.579 |                  0.572 |                 0.007 |
| P2         | B02        |        15 |                      0.760 |                  0.768 |                 0.008 |
| P2         | B02        |        30 |                      0.791 |                  0.801 |                 0.010 |
| P2         | B02        |        60 |                      0.843 |                  0.849 |                 0.006 |
| P2         | B02        |       120 |                      0.855 |                  0.862 |                 0.007 |
| P2         | F05        |         0 |                      0.714 |                  0.715 |                 0.001 |
| P2         | F05        |        15 |                      0.784 |                  0.781 |                 0.003 |
| P2         | F05        |        30 |                      0.821 |                  0.816 |                 0.005 |
| P2         | F05        |        60 |                      0.855 |                  0.862 |                 0.007 |
| P2         | F05        |       120 |                      0.891 |                  0.897 |                 0.006 |

P2 separates materially after first profit, especially after 15–30 minutes. P1 is indistinguishable from winners at +10 pips and separates only after subsequent directional-state decay. These are hypothesis-generation findings, not an Exit rule.

## Entry information audit

All Entry features are based on executable M15 opens known at the Entry decision time or earlier. Future path values are used only for labels. Direction normalization and training-fold-only imputation are explicit.

## OHLC feasibility

A single accepted full-OHLC lineage is not available across all four folds because the accepted 2024H2 source exposes executable M15 opens but not canonical full OHLC. ATR/ADX/Stochastic/CCI/candle features are not mixed from another source.

## Scientific boundary

No candidate Exit outcome has been evaluated in this package. A separate, outcome-free finite state-transition protocol requires registry authorization before execution.
