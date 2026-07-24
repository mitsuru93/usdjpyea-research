# USDJPY HYP-024 Profit-Armed Directional-State Collapse — Exact Eight-Cell Result v1

## Decision

`CLOSED_FAIL_NO_ELIGIBLE_FAMILY_REGION`

- Frozen cells: 8
- Core cells across all four folds: 0
- Full cells across all four folds: 0
- Eligible connected family regions: P2 0 / P1 0
- Finalist: `null`
- MT4 / 2025 H1 / 2025 H2: not accessed

The P2 and P1 state-collapse rules consistently save target-class losses, but they do not preserve total expectancy, strategy/direction symmetry, quarter breadth and the Winner right tail across all four folds. No cell advances to MT4.

## Exact identities

- Protocol SHA-256: `390fe646b904a07e3bd29394edabfc1a26ea311a9e0311aafd85118bbc5a69b7`
- Evaluator SHA-256: `9195a97f900e5e4782000dac967389919e401a534d72150f9ff6b72463d37f30`
- Trade ledger: 1,882 rows, `98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca`
- State ledger: 68,955 rows, `2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda`
- Lineage: `HISTORICAL_2024_LEGACY_US_DST_CONVERSION_APPLIED_TO_2023_ONLY`

## Cell summary

| Candidate | Arm | Core folds | Full folds | Min fold Δ pips | Pooled Δ pips | Min target benefit | Min top-decile retention |
|---|---:|---:|---:|---:|---:|---:|---:|
| O_P2_Q2_R1 | P2 | 0/4 | 0/4 | -614.0 | -776.8 | 1282.0 | 0.843 |
| O_P2_Q2_R2 | P2 | 0/4 | 0/4 | -844.2 | -606.1 | 819.0 | 0.879 |
| O_P2_Q3_R1 | P2 | 0/4 | 0/4 | -792.9 | -1205.9 | 656.3 | 0.874 |
| O_P2_Q3_R2 | P2 | 0/4 | 0/4 | -609.2 | -830.1 | 403.2 | 0.902 |
| O_P1_Q2_R1 | P1 | 0/4 | 0/4 | -2118.7 | -3632.4 | 1649.7 | 0.484 |
| O_P1_Q2_R2 | P1 | 0/4 | 0/4 | -1430.5 | -2452.3 | 1181.6 | 0.528 |
| O_P1_Q3_R1 | P1 | 0/4 | 0/4 | -1591.5 | -1938.2 | 1313.4 | 0.816 |
| O_P1_Q3_R2 | P1 | 0/4 | 0/4 | -1462.9 | -961.8 | 763.4 | 0.871 |

## P2 arm

- Every P2 cell has positive P2 target-class benefit in every fold.
- The broadest rule, `O_P2_Q2_R1`, improves 2023H1 by +773.9 pips, but changes sign in 2023H2 (-549.5), 2024H1 (-387.2) and 2024H2 (-614.0).
- `O_P2_Q3_R2` is the least aggressive P2 cell and retains at least 90.23% of the top-decile Winner tail, but total delta is negative in all four folds and quarter/date breadth fails.
- No P2 cell passes one complete fold core gate set across all four folds; no connected component exists.

## P1 arm

- Every P1 cell has positive P1 target-class benefit in every fold, confirming that the collapse event occurs in real giveback losses.
- Winner harm is much larger. Minimum top-decile retention ranges from 48.36% to 87.14% for the first three P1 cells; the narrowest rule retains 87.14%.
- `O_P1_Q3_R2` is positive only in 2023H2 (+410.4 pips) and negative in 2023H1 (-559.5), 2024H1 (-468.8) and 2024H2 (-1,462.9).
- No P1 cell passes all-fold core gates; no connected component exists.

## Binding interpretation

Target-loss reduction alone is not deployable evidence. The same state-collapse event also occurs during profitable continuation and produces large Winner sacrifice, F05/B02 sign reversals, long/short reversals, negative quarter deltas and date/month concentration. Aggregate or single-fold positives cannot override these binding failures.

## Boundaries

- No parameter, component, arm, threshold, observation time, execution time or gate was changed.
- The evaluator was executed once after exact v2 input readback.
- The timezone-to-quarter warning only reflects pandas dropping timezone metadata when deriving calendar-quarter labels; timestamps were already UTC and the quarter strings are unchanged.
- `stdout.json` was created by shell redirection before evaluation and therefore appears as an empty-file hash inside the evaluator output manifest. It is not a scientific output and does not alter any result file.
- No MT4 and no 2025 data were accessed.
