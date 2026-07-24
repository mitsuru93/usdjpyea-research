# USDJPY HYP-024 B02/F05 profit-armed state-collapse exact evaluation

## Decision

- Scientific status: `CLOSED_NO_ELIGIBLE_FAMILY_REGION`
- Frozen cells evaluated: `8`
- Core cells: `0`
- Full cells: `0`
- Eligible within-arm family regions: `0`
- Finalist: `null`
- MT4: not accessed
- 2025 H1/H2: not accessed
- Grid, components, arms and gates: unchanged

Therefore HYP-024 is closed before MT4 and 2025. The P2 and P1 arms may not be combined after the result.

## Frozen identity

- Research authorization commit: `e56c3dac189bf283b528253cee3ed718f4358fa8`
- Protocol SHA-256: `390fe646b904a07e3bd29394edabfc1a26ea311a9e0311aafd85118bbc5a69b7`
- Evaluator SHA-256: `9195a97f900e5e4782000dac967389919e401a534d72150f9ff6b72463d37f30`
- Trade ledger: 1,882 rows / SHA-256 `98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca`
- State ledger: 68,955 rows / SHA-256 `2caddc38cdb16ce7504fe1e3b625f8425ccc6f7d579d02590f9ee92bbf013eda`
- Development folds: `2023H1`, `2023H2`, `2024H1`, `2024H2`

## Cell summary

| Candidate | Arm | Quorum | Persistence | Min fold total delta (pips) | Min fold target benefit (pips) | Min top-decile winner retention | Core all folds | Full all folds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `O_P2_Q2_R1` | P2 | 2 | 1 | -614.0 | 1282.0 | 0.843 | false | false |
| `O_P2_Q2_R2` | P2 | 2 | 2 | -844.2 | 819.0 | 0.879 | false | false |
| `O_P2_Q3_R1` | P2 | 3 | 1 | -792.9 | 656.3 | 0.874 | false | false |
| `O_P2_Q3_R2` | P2 | 3 | 2 | -609.2 | 403.2 | 0.902 | false | false |
| `O_P1_Q2_R1` | P1 | 2 | 1 | -2118.7 | 1649.7 | 0.484 | false | false |
| `O_P1_Q2_R2` | P1 | 2 | 2 | -1430.5 | 1181.6 | 0.528 | false | false |
| `O_P1_Q3_R1` | P1 | 3 | 1 | -1591.5 | 1313.4 | 0.816 | false | false |
| `O_P1_Q3_R2` | P1 | 3 | 2 | -1462.9 | 763.4 | 0.871 | false | false |

All eight cells had a negative minimum-fold total delta. No cell passed core in all four folds.

## Gate diagnosis

Counts below are passing fold-cells out of 16 per arm (4 candidates × 4 folds). These are diagnostics only; gates were not modified.

| Arm | Default net/PF | Severe net/PF | Target benefit | Target exits | Winner tail | Strategy breadth | Direction breadth | Quarter breadth | Month breadth | Ex-best-two dates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P2 | 12/16 | 10/16 | 16/16 | 16/16 | 12/16 | 4/16 | 4/16 | 4/16 | 4/16 | 3/16 |
| P1 | 12/16 | 10/16 | 16/16 | 16/16 | 2/16 | 3/16 | 5/16 | 0/16 | 2/16 | 3/16 |

### P2 early-failure arm

- P2 target-class benefit was positive in all 16 fold-cells, and every fold-cell had at least five target exits.
- Nevertheless, total portfolio delta was negative in three of four folds for every P2 candidate. Minimum-fold total delta ranged from `-609.2` to `-844.2` pips.
- The Exit removed too much Winner profit. Minimum top-decile Winner retention ranged from `0.843` to `0.902`.
- `O_P2_Q3_R2` was the only P2 cell that retained at least 90% of top-decile Winner profit in all folds, but it still failed strategy, direction, quarter, month/date breadth and had negative total delta in 2023H2, 2024H1 and 2024H2.

### P1 giveback arm

- P1 target-class benefit was positive in all 16 fold-cells, with 61–129 target exits per fold depending on cell.
- The same state-collapse Exit cut Winner profits much more heavily than it saved P1 losses. Minimum-fold total delta ranged from `-1,430.5` to `-2,118.7` pips.
- Top-decile Winner retention passed in only `2/16` P1 fold-cells; the minimum by candidate ranged from `0.484` to `0.871`.
- Quarter breadth passed in `0/16` P1 fold-cells. No P1 cell approached a connected core region.

## Scientific interpretation

The three nonpositive state primitives do identify deterioration after profit has been established: both P2 and P1 target losses improve consistently. However, the state is not specific to losing trajectories. It also fires during ordinary pullbacks inside profitable trades, so the right tail is cut and the portfolio effect becomes unstable across strategy, direction and sub-period.

This falsifies the frozen claim that a common finite state-collapse rule can terminate P2/P1 failures while preserving the Winner tail across all four development folds. It does not reopen P3 Entry analysis, HYP-023, indicator thresholds, arm definitions or gates.

## Boundary

- Historical 2024 source mutated: false
- Later 2024 derived bars substituted: false
- 2025 used for mechanism, feature or threshold selection: false
- MT4 Strategy Tester used: false
- Live orders: false

MT4 parity is not performed because no eligible Research family region or finalist exists.
