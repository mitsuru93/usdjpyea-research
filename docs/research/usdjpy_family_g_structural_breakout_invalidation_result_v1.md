# USDJPY Family G Structural Breakout Invalidation Result v1

Decision: **CLOSED — no eligible specification**

## What was tested

The exact preregistered 18-cell grid tested whether an open F05 position should be closed when executable price returned inside its original breakout reference level at 30, 60 or state-dependent 90 minutes. B02 and the entry set remained unchanged. Candidate-adjusted exposure state was recomputed dynamically.

The pre-result missing-checkpoint amendment was applied: when the exact scheduled M15 bar-open was absent, execution used the first available market M15 bar-open after the schedule, with no interpolation or synthetic bar.

## Development evidence

- 2023 historical-2024-compatible baseline: JPY -9,279
- 2024 H1 historical baseline: JPY 22,797
- 2024 H2 historical baseline: JPY 38,358
- 2025 accessed: no
- 2024 source mutated: no

## Result

No candidate passed all gates. No finalist is frozen.

The highest minimum-period candidate was `G1_C30_I10`:

- 2023 delta: JPY +1,655
- 2024 H1 delta: JPY -2,146
- 2024 H2 delta: JPY +384
- pooled delta: JPY -107
- changed positions / dates: 134 / 119
- positive / negative effect months: 14 / 10
- benefit / harm: JPY 23,487 / JPY 23,594
- ex-best-two-entry-dates delta: JPY -3,053
- leave-one-month-out minimum: JPY -4,455

The state-adaptive checkpoint cells also failed. The best 60-minute cell improved 2024 H2 by JPY 3,089 but lost JPY 2,474 in 2023 and JPY 1,850 in 2024 H1.

## Interpretation

Returning inside the original breakout level identifies real losses, but it also cuts recovery winners at a similar or larger value. The sign reverses by development period, and the apparent effects are not broad after removing the strongest dates or months.

This is not a threshold-identification problem. The mechanism lacks an additional observable that separates temporary structural failure followed by recovery from permanent failure.

## Retained findings

- Structural invalidation alone is not a general exit rule.
- State-adaptive timing alone does not repair the mechanism.
- A successor must measure recovery capacity or market support after invalidation rather than use a nearby checkpoint or buffer.

## Prohibited reuse

- Do not expand the same 30/60/90-minute or 0/5/10-pip grid.
- Do not repair Family G from 2025 outcomes.
- Do not relabel structural return alone as a new family.

## Next work

Analyze Family G benefit and harm populations across 2023 and both 2024 halves to identify a genuinely new recovery-capacity observable before preregistering a successor family.
