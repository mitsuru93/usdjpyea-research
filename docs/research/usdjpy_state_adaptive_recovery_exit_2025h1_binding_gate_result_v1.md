# USDJPY Family E 2025 H1 Binding Rakuten MT4 Gate

## Decision

**FAIL — the exact Family E specification is closed.**

Candidate: `E2_ADAPTIVE_60_90__A15_B5_C15_R0`

The candidate completed the first binding 2025 H1 Rakuten MT4 stress gate. The workflow reached `COMPLETE`; both Strategy Tester runs, the evaluator, artifact upload and immutable receipt were produced. This is a strategy result, not a technical incomplete.

## Exact evidence identity

- Core execution package: `317b83a89e4f80fbb67aefe83c9180461aab5227`
- Marker PR: `mitsuru93/usdjpyea-core#150`
- Marker head: `25f9f8b89a5b2fe847d6e8cd5a082979ca0d131b`
- Run merge SHA: `05d83323a18daed5219fdeec40f5a7f44f586fac`
- Run ID: `29934029169`
- Job ID: `88970802800`
- Workflow ID: `318119335`
- Runner: `onamae-mt4-ui-01`
- Artifact ID: `8535486772`
- Artifact digest: `sha256:79238df0ffaff1df6fdb8034b63e4dd191270b5364c1ab3e12c3f04f47acc4bc`
- Receipt: Core issue `#151`

No external market-data download or tick collection occurred. The native HST hashes were unchanged after both tests. Candidate-specific 2025 H2 was not accessed.

## Baseline reproduction

The known 2025 H1 baseline reproduced before the candidate was interpreted.

| Metric | Reproduced value |
|---|---:|
| Entries | 463 |
| B02 entries | 105 |
| F05 entries | 358 |
| Net P/L | JPY -20,808 |
| PF | 0.829407665505 |
| Maximum tick-equity drawdown | JPY 42,737 / 42.7092% |
| Minimum equity | JPY 57,328 |

The exact cached Rakuten HST identities were:

- M1: `db00b63e9e7ff2dd3f785563ad7f392a7e79ccef8a2c3e696f662b397b2b5af0`, 183,828 H1 records
- M15: `b22e9fb9a6d0f397b4186ba17f6e71cae9eb38aa59f214dfd1eb5173e4e7f165`, 12,269 H1 records

## Candidate result

| Metric | Baseline | Family E | Change |
|---|---:|---:|---:|
| Net P/L | JPY -20,808 | **JPY -15,866** | **JPY +4,942** |
| PF | 0.829408 | **0.863026** | +0.033618 |
| Maximum tick-equity DD | JPY 42,737 | **JPY 39,246** | **JPY -3,491** |
| Minimum equity | JPY 57,328 | **JPY 60,819** | **JPY +3,491** |
| B02 P/L | JPY -6,964 | JPY -6,964 | 0 |
| F05 P/L | JPY -13,844 | **JPY -8,902** | **JPY +4,942** |

The candidate improved the baseline materially, but it remained a losing portfolio with PF below 1.

## Binding gate failures

Three required gates failed:

1. `candidate_net_positive`: JPY -15,866
2. `candidate_pf_at_least_1`: PF 0.863025761448
3. `january_to_march_net_nonnegative`: Q1 JPY -26,013

All other binding policy gates passed, including candidate improvement over baseline, lower tick-equity drawdown, higher minimum equity, positive Q1 and Q2 deltas, positive April–June result, six positive effect months, no negative effect months, positive ex-best-two-date effect, positive F05 delta, exact B02 outcomes and benefit greater than harm.

## Quarter and monthly behavior

| Period | Baseline | Family E | Delta |
|---|---:|---:|---:|
| 2025 Q1 | JPY -28,637 | **JPY -26,013** | **JPY +2,624** |
| 2025 Q2 | JPY +7,829 | **JPY +10,147** | **JPY +2,318** |

Candidate monthly net P/L:

| Month | Candidate P/L | Candidate-minus-baseline effect by entry month |
|---|---:|---:|
| January | JPY -13,038 | JPY +1,589 |
| February | JPY +4,607 | JPY +132 |
| March | JPY -17,582 | JPY +903 |
| April | JPY -9,105 | JPY +867 |
| May | JPY +15,795 | JPY +482 |
| June | JPY +3,457 | JPY +969 |

The exit mechanism improved every entry month, but the January–March regime loss was too large for the overlay to reverse.

## Changed-trade attribution

Family E changed 40 F05 outcomes and no B02 outcome.

- 60-minute exits: 23 positions, JPY +4,368 effect
- 90-minute exits: 17 positions, JPY +574 effect
- Beneficial changed positions: 23
- Harmful changed positions: 17
- Gross benefit: JPY 10,355
- Gross harm: JPY 5,413
- Ex-best-two-entry-dates effect: JPY +3,352

Dynamic-state attribution:

| Entry state | Exit | Positions | Net effect |
|---|---:|---:|---:|
| standalone | 60m | 16 | **JPY +4,024** |
| mixed_overlap | 60m | 2 | JPY +762 |
| opposite_overlap | 60m | 5 | JPY -418 |
| same_direction_stack | 90m | 15 | JPY -336 |
| simultaneous_same_direction | 90m | 2 | JPY +910 |

The strongest generalizing component was the standalone 60-minute loss cut. The same-direction-stack 90-minute branch was mildly harmful in 2025 H1. These observations are post-gate diagnosis only; changing state rules or thresholds after binding access would create a new candidate and is prohibited for this specification.

## Interpretation

Family E did what it was designed to do: it compressed F05 losses, reduced drawdown, preserved exact entries and B02 outcomes, improved both quarters relative to baseline, and was not dependent on one or two favorable dates. The failure is therefore not an implementation failure or a concentration artifact.

The central problem is architectural. A loss-management overlay worth JPY +4,942 cannot convert a 2025 H1 baseline loss of JPY -20,808 into a profitable portfolio. B02 remained JPY -6,964 and even the improved F05 remained JPY -8,902. The 2024-selected exit mechanism generalized directionally but not strongly enough to establish cross-period profitability.

## Decision action

- Exact Family E candidate: `CLOSED_2025_H1_BINDING_FAIL`
- Candidate-specific 2025 H2 execution: **not authorized**
- 2025 H2 accessed: false
- Parameter changes after binding access: false
- Live orders: not authorized
- Next research state: return to 2024 development for a newly preregistered family or an architecture-level diagnosis. The failed Family E specification may not be retuned on 2025 H1 and carried into 2025 H2.
