# USDJPY HYP-024 Profit-Armed Directional-State Collapse — Exact Four-Fold Result

## Decision

`CLOSED_NO_ELIGIBLE_FAMILY_REGION`

The frozen eight-cell family produced **0 core cells, 0 full cells, 0 eligible candidates and no finalist**. Neither P2 nor P1 formed an eligible connected family region. HYP-024 is closed before MT4 and all 2025 access.

## Binding identity

- Preregistration commit: `63aaa803ca872cfdfd15c280d449c13d608c42a1`
- Input rematerialization commit: `e56c3dac189bf283b528253cee3ed718f4358fa8`
- Evaluator SHA-256: `9195a97f900e5e4782000dac967389919e401a534d72150f9ff6b72463d37f30`
- Protocol SHA-256: `390fe646b904a07e3bd29394edabfc1a26ea311a9e0311aafd85118bbc5a69b7`
- v2 trade ledger SHA-256: `98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca`
- v2 state ledger SHA-256: `2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda`
- Population: 1,882 trades; 68,955 state rows
- Folds: 2023H1, 2023H2, 2024H1, 2024H2
- Grid: P2/P1 × quorum 2/3 × persistence 1/2 = 8 cells

## Gate result

All 32 candidate-fold rows improved their target loss class and changed at least five target trades. The signal therefore detects genuine post-profit deterioration. It does not identify irrecoverable deterioration robustly enough to terminate trades.

| Gate | Passed rows |
|---|---:|
| Default net positive and PF ≥ 1 | 24 / 32 |
| Severe net positive and PF ≥ 1 | 20 / 32 |
| Target-class benefit positive | 32 / 32 |
| Target exits ≥ 5 | 32 / 32 |
| Top-decile Winner retention ≥ 0.90 | 14 / 32 |
| B02 delta nonnegative | 17 / 32 |
| F05 delta nonnegative | 7 / 32 |
| Long delta nonnegative | 11 / 32 |
| Short delta nonnegative | 18 / 32 |
| Both quarter deltas nonnegative | 4 / 32 |
| Month breadth | 6 / 32 |
| Ex-best-two-date delta positive | 6 / 32 |

No candidate passed aggregate default/severe, strategy, direction, quarter, month or date-removal requirements in all four folds.

## P2

Across its 16 rows, P2 default delta summed to `-3418.9` pips, target-class benefit to `18974.6` pips and Winner impact to `-29667.8` pips. `O_P2_Q3_R2` alone retained at least 90% of top-decile Winner profit in all folds, but still failed stability and breadth.

| Fold | Default Δ | Target benefit | Winner retention | B02 Δ | F05 Δ | Long Δ | Short Δ | Min quarter Δ | Ex-best-two-date Δ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023H1 | 444.7 | 1212.9 | 0.959 | 341.1 | 103.6 | 87.0 | 357.7 | 0.0 | -32.4 |
| 2023H2 | -609.2 | 403.2 | 1.000 | -177.3 | -431.9 | -506.0 | -103.2 | -677.2 | -763.7 |
| 2024H1 | -469.3 | 734.2 | 0.902 | -38.5 | -430.8 | -875.8 | 406.5 | -752.3 | -731.9 |
| 2024H2 | -196.3 | 1241.5 | 0.950 | 225.6 | -421.9 | -189.8 | -6.5 | -328.6 | -641.1 |

## P1

Across its 16 rows, P1 default delta summed to `-8984.7` pips, target-class benefit to `41806.1` pips and Winner impact to `-50790.8` pips. Every P1 cell failed the frozen Winner-tail gate.

## Interpretation

The synchronized nonpositive momentum/MACD/EMA state is a **generic deterioration detector**, not a portable termination mechanism. It also fires in Winners that subsequently recover or continue. Tightening quorum or persistence does not resolve this causal ambiguity. Future Exit research must introduce genuinely distinct information about recoverability; HYP-024 must not be reopened by threshold, persistence, arm or component repair.

## Boundaries

- MT4: not used
- 2025H1/H2: not accessed
- Grid expansion: none
- Gate changes: none
- Scientific run: local deterministic evaluator, exit 0, 11.34 seconds
