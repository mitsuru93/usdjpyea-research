# USDJPY Full Frozen Architecture Census Result v1

## Decision

`RQ-020E` is closed with **no passing family region**. The exact 2023 historical-2024-compatible lineage and unchanged 2024 lineage were evaluated across the complete frozen `60 Entry × 11 horizon = 660` universe. No candidate, exact cell, family, MT4 work or 2025 access is authorized.

## Exact reproducibility

- 2023 uses the accepted historical 2024 contract; 2024 is unchanged.
- Input SHA-256 values matched the frozen protocol.
- 2024 H1 signals reproduced all `34,955` accepted R1 rows exactly.
- The Stage-2 2024 H1 trade engine reproduced all 660 R2 cells exactly for trade count, default/severe net, PF, positive-month count and ex-best-two-date result.
- One first attempt stopped before outcome aggregation because the fixed-five signal library did not implement all twelve families. It is recorded as technical incomplete and the successful run used the canonical R1 v2 `SIGNAL_FUNCTIONS` source without changing any scientific gate.

## Four-fold result

| Gate | Passing cells |
|---|---:|
| Support: ≥20 trades in every fold | 660 / 660 |
| Default-positive/PF≥1 in all four folds | 14 / 660 |
| Severe-positive/PF≥1 in all four folds | 1 / 660 |
| Full cell gate | 0 / 660 |
| Entry contiguous-horizon neighbourhood | 0 / 60 |
| Family region | 0 / 12 |

The weakest severe-cost fold was 2024 H2 for 248 cells, 2024 H1 for 162, 2023 H1 for 140 and 2023 H2 for 110. The failure is therefore distributed across years and halves rather than caused by one defective period.

## Sole core-pass cell

`R1K03_london_to_ny_cont` with a 24-bar horizon was the only cell positive with PF≥1 under both default and severe costs in all four folds. It still failed the frozen full gate:

| Fold | Trades | Default net | Severe net | Positive / negative months | Ex-best-two dates |
|---|---:|---:|---:|---:|---:|
| 2023 H1 | 22 | +150.3 | +106.3 | 4 / 1 | -87.2 |
| 2023 H2 | 29 | +98.7 | +40.7 | 3 / 3 | -151.3 |
| 2024 H1 | 25 | +233.8 | +179.1 | 4 / 1 | +106.7 |
| 2024 H2 | 35 | +130.7 | +49.3 | 4 / 2 | -71.7 |

Its neighbouring horizons did not form the required three-horizon core run, so selecting the 24-bar maximum would violate the preregistered architecture gate.

## Interpretation

The complete pre-existing R1/R2 Entry-and-fixed-horizon architecture does not transport robustly across 2023 H1/H2 and 2024 H1/H2. The result is stronger than a failure of the earlier five-strategy subset: all 660 frozen combinations were evaluated, every cell had adequate support, and no family-level region survived.

The result does **not** imply that all market structure is exhausted. It shows that the information contained in the existing twelve Entry families plus fixed time horizons is insufficient under the frozen cross-fold, severe-cost, breadth and concentration requirements. The one isolated session-handoff cell cannot be promoted or locally repaired.

## Next authorized work

Open `USDJPY-RQ-021` as descriptive architecture-failure taxonomy only. Use the existing 660-cell outputs to attribute failures by family, horizon, direction and weakest fold; identify information dimensions absent from R1/R2; compare them against the full ledger and define at most one genuinely distinct architecture question. No cell retuning, new horizons, candidate generation, family preregistration, MT4 or 2025 access is authorized.
