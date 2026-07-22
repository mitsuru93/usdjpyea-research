# USDJPY D Early-Failure Persistence — 2024 H1 Formal Result v1

## Decision

The new H1 mechanism is **persistent early adverse failure in F05**.

The leading rule records executable marked P/L 30 minutes after entry and, at exactly 60 minutes, closes the still-open F05 position when:

- the 30-minute marked result was at or below `-15 pips`; and
- the 60-minute marked result remains at or below `-5 pips`.

This is not an intrabar stop. It waits for two fixed post-entry observations and targets persistent failed acceptance rather than temporary noise.

## Why this mechanism was selected for research

The union of S1, S2, S3 and Family C affected 55 unique H1 trades, but their coverage was concentrated in F05 P1 giveback-to-loss. Their union covered only:

- 5 of 66 F05 P2 losses;
- 6 of 41 F05 P3 losses.

The largest untreated population was therefore F05 early failure, especially P2/P3.

## Formal H1 evaluation

- Evaluated specifications: 12
- Parameter-equivalence classes: 12
- Formal H1 eligible specifications: 2
- Parameter-equivalent adjacent cells: none
- Ranking winner across total delta, ex-best-two and leave-one-month-out: the same cell
- New H2 evidence accessed: no
- Candidate-specific 2025 H1 evidence accessed: no
- MT4 executed for this family: no

### Eligible specifications

| Rule | Changed | H1 delta | PF | Q1 delta | Q2 delta | Ex-best-two | LOMO minimum |
|---|---:|---:|---:|---:|---:|---:|---:|
| 30m ≤ −15, 60m ≤ −5 | 17 | **+2,416円** | 1.4353 | +2,296円 | +120円 | +780円 | +869円 |
| 30m ≤ −20, 60m ≤ −5 | 10 | +1,868円 | 1.4214 | +1,586円 | +282円 | +504円 | +694円 |

## Leading H1 cell

| Metric | Baseline | Candidate |
|---|---:|---:|
| Net JPY | 22,797 | **25,213** |
| PF | 1.3774 | **1.4353** |
| B02 net | 9,554 | 9,554 |
| F05 net | 13,243 | **15,659** |

Additional properties:

- affected positions: 17;
- affected entry dates: 15;
- trigger months: all six H1 months;
- positive-effect months: five;
- negative-effect months: one;
- benefit: 3,469円;
- harm: 1,053円;
- benefit/harm: 3.29;
- final-loss trades: 16 of 17;
- P2/P3 trades: 16 of 17;
- overlap with prior candidate union: 4 of 17;
- winner harm: 157円.

### Monthly effect

| Month | Effect |
|---|---:|
| January | +1,547円 |
| February | +26円 |
| March | +723円 |
| April | +501円 |
| May | −438円 |
| June | +57円 |

### What it actually fixes

The total improvement was not evenly distributed across P2 and P3.

| Path | Changed | Effect |
|---|---:|---:|
| P2 minor-favourable-then-loss | 3 | **−785円** |
| P3 never-profitable | 13 | **+3,358円** |
| Winner | 1 | −157円 |

The mechanism is therefore best understood as an **F05 persistent never-profitable protection rule**, not a general P2/P3 repair.

## Why the exact threshold is not frozen yet

The H1 result passes every preregistered gate, but only 17 positions are changed. The mechanism is coherent, has low prior-candidate overlap and survives concentration tests, yet the sample is too small to distinguish whether `-15/-5` is the correct threshold across broader 2024 conditions.

Formal classification:

**FRAGILE_H1_PASS_REQUIRES_PERIOD_ROLE_REVIEW**

The only automatic fragility flag is:

- `changed_positions_below_20`.

## Period-role decision

The H1 result justifies continuing the mechanism but does not justify spending 2024 H2 as a one-shot validation block.

The research design is therefore changed as follows:

1. 2024 H1 and 2024 H2 become the development and analysis period.
2. The already-frozen 12-cell D-family grid is evaluated over H2 and full-year 2024 without expansion.
3. One exact threshold may be frozen only after separate H1, H2 and full-year robustness analysis.
4. 2025 H1 becomes the first candidate-specific Rakuten MT4 stress gate.
5. 2025 H2 becomes the final unchanged Rakuten MT4 validation gate and may be opened only after 2025 H1 PASS.

This change does not authorize access to 2025 candidate results and does not reopen any closed candidate.
