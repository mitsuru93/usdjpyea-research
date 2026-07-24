# USDJPY HYP-024 Profit-Armed Directional-State Collapse — Exact Four-Fold Result

## Decision

`CLOSED_NO_ELIGIBLE_FAMILY_REGION`

The frozen eight-cell family produced **0 core cells, 0 full cells, 0 eligible candidates and no finalist**. Neither the P2 arm nor the P1 arm formed a connected eligible family region. HYP-024 is closed before MT4 parity and before any 2025 access.

## Frozen identity

- Hypothesis: `USDJPY-HYP-024`
- Family: `O_PROFIT_ARMED_DIRECTIONAL_STATE_COLLAPSE`
- Preregistration commit: `63aaa803ca872cfdfd15c280d449c13d608c42a1`
- Evaluator SHA-256: `9195a97f900e5e4782000dac967389919e401a534d72150f9ff6b72463d37f30`
- Preregistration SHA-256: `390fe646b904a07e3bd29394edabfc1a26ea311a9e0311aafd85118bbc5a69b7`
- Trade ledger SHA-256: `1f4732f429fc9b4fb4c34b8c2431ed1c4ac207e24d81dd0aac7cf893b4ce8113`
- State ledger SHA-256: `6b38aafde15da4310971a9610ec19a027c2d065bfce19c79c2492982be351149`
- Lineage: `USDJPY_HISTORICAL_2024_LEGACY_CONTRACT_APPLIED_TO_2023_V1`
- Periods: 2023H1, 2023H2, 2024H1, 2024H2
- Population: 1,882 B02/F05 trades
- Grid: P2/P1 × quorum 2/3 × persistence 1/2 = 8 cells

## Primary result

All **32 candidate-fold rows** improved the target path class and changed at least five target trades. This demonstrates that the synchronized nonpositive momentum/MACD/EMA state captures real post-profit deterioration. It did **not** establish a robust Exit rule: the improvement was offset by aggregate-net instability, winner-right-tail loss and failure across strategy, direction, quarter, month and date-removal gates.

### Gate coverage across 32 candidate-fold rows

| Gate | Passed rows |
|---|---:|
| Default net positive and PF ≥ 1 | 24 / 32 |
| Severe net positive and PF ≥ 1 | 21 / 32 |
| Target-class benefit positive | 32 / 32 |
| At least five target exits | 32 / 32 |
| Top-decile winner retention ≥ 0.90 | 14 / 32 |
| B02 delta nonnegative | 16 / 32 |
| F05 delta nonnegative | 7 / 32 |
| Long delta nonnegative | 11 / 32 |
| Short delta nonnegative | 18 / 32 |
| Both quarter deltas nonnegative | 4 / 32 |
| Month breadth | 6 / 32 |
| Ex-best-two-dates effect positive | 6 / 32 |

No candidate passed the default-net/PF gate or severe-net/PF gate in all four folds. No candidate passed B02, F05, long, short, quarter, month or date-removal gates in all four folds.

## P2 arm

P2 was less destructive than P1, but still had an aggregate default-delta sum of `-3575.8` pips across its 16 candidate-fold rows. Its target-class benefit summed to `18974.6` pips, while Winner impact summed to `-29821.2` pips.

`O_P2_Q3_R2` was the only cell retaining at least 90% of top-decile Winner profit in all four folds. It nevertheless failed total-net stability and breadth:

| Fold | Default Δ | Target benefit | Winner retention | B02 Δ | F05 Δ | Long Δ | Short Δ | Min quarter Δ | Ex-best-two-date Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023H1 | 444.7 | 1212.9 | 0.959 | 341.1 | 103.6 | 87.0 | 357.7 | 0.0 | -32.4 |
| 2023H2 | -609.2 | 403.2 | 1.000 | -177.3 | -431.9 | -506.0 | -103.2 | -677.2 | -763.7 |
| 2024H1 | -491.8 | 734.2 | 0.902 | -71.3 | -420.5 | -898.3 | 406.5 | -752.4 | -754.4 |
| 2024H2 | -186.8 | 1241.5 | 0.950 | 225.6 | -412.4 | -189.8 | 3.0 | -328.6 | -631.6 |

## P1 arm

P1 detected giveback deterioration but sacrificed substantially more Winner profit. Across its 16 candidate-fold rows, default delta summed to `-8976.1` pips, target-class benefit to `41720.0` pips and Winner effect to `-50696.1` pips. Minimum top-decile retention ranged from `0.484` to `0.871`, below the frozen 0.90 gate for every P1 cell.

## Scientific interpretation

The state transition is a **deterioration detector**, but not a portable termination mechanism. The same collapse state occurs in target losses and in Winners that later recover or continue. Tightening quorum/persistence does not solve the causal ambiguity: the least harmful P2 cell still fails across folds, while all P1 cells materially truncate the Winner right tail.

The retained finding is therefore negative but specific: future Exit research must add genuinely distinct information about **recoverability**, not another threshold or persistence repair of momentum/MACD/EMA collapse. HYP-024 thresholds, arms, components and gates must not be reopened.

## Boundaries

- MT4 parity: not executed
- 2025H1: not accessed
- 2025H2: not accessed
- Live orders: not accessed
- Grid expansion: none
- Gate changes: none

## Reproducibility outputs

- Result: `configs/research/usdjpy_b02_f05_profit_armed_state_collapse_result_v1.json`
- Cell summary: `configs/research/usdjpy_b02_f05_profit_armed_state_collapse_cell_summary_v1.csv`
- Fold metrics: `configs/research/usdjpy_b02_f05_profit_armed_state_collapse_fold_metrics_v1.csv`
- Evaluation receipt: `configs/research/usdjpy_hyp024_exact_evaluation_receipt_v1.json`
- Trade-level output SHA-256: `988bf0a38694f16731681e1e323b7531828ecbdc07fbcad43f8b81092ab179ed`
