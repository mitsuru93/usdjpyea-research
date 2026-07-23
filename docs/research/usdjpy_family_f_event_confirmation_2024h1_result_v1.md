# USDJPY Family F 2024 H1 result v1

## Decision

**FAIL — no Family F specification passed every preregistered H1 gate.**

Family: `F_EVENT_CONFIRMATION_ADMISSION`

The exact 54-specification grid frozen in Research commit `143bcb7b6415f4fa9f4bb00ddffd73075e1eed7f` was evaluated on immutable 2024 H1 evidence only. No candidate-specific 2024 H2 or 2025 data was accessed.

## Baseline

| Metric | Value |
|---|---:|
| Trades | 428 |
| B02 trades | 97 |
| F05 trades | 331 |
| Net P/L | JPY 22,797 |
| PF | 1.377415029055 |

## Search result

- Frozen candidates: 54
- Eligibility-pass candidates: 54
- Research-eligible candidates after all gates: **0**
- H1 finalist: none
- H2 access: not authorized and not used

## Best headline result

`F_C5_A480_N3_B1` produced the largest gross H1 improvement:

| Metric | Value |
|---|---:|
| Candidate net | JPY 27,212 |
| Candidate PF | 1.859833 |
| Net delta | JPY +4,415 |
| Q1 delta | JPY +3,476 |
| Q2 delta | JPY +939 |
| Removed F05 trades | 158 |
| Retained F05 trades | 173 |

However, its effect was not stable enough to qualify:

| Entry month | Effect |
|---|---:|
| January | JPY +5,791 |
| February | JPY -770 |
| March | JPY -1,545 |
| April | JPY +2,144 |
| May | JPY -2,495 |
| June | JPY +1,290 |

It had only three positive-effect months and three negative-effect months. Removing the two best entry dates changed the delta to JPY -1,422, and leave-one-month-out minimum delta was JPY -1,376. Therefore the apparent improvement depended on a small subset of dates/months and failed the preregistered robustness boundary.

The second result, `F_C5_A480_N3_B0`, showed the same pattern: JPY +4,241 headline delta, but three positive and three negative months, ex-best-two delta JPY -1,596 and leave-one-month-out minimum JPY -1,109.

## Interpretation

The first-signal-as-probe architecture can improve aggregate H1 P/L, so the underlying event-confirmation idea is not empty. The problem is that the effect is not consistent across months and does not survive removal of its strongest dates. Expanding the grid after seeing this result would convert the search into post-result optimization, which was prohibited in the preregistration.

## Decision action

- Family F: `CLOSED_2024_H1_ROBUSTNESS_FAIL`
- 2024 H2 Family F evaluation: not performed
- 2025 access: none
- Next stage: activate the preregistered 2023 fast M1-bar development/falsification path
- Tick data for the initial 2023 stage: not required
- Live orders: not authorized
