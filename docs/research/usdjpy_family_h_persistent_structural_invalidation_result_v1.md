# USDJPY Family H Persistent Structural Invalidation Result v1

Decision: **CLOSED — no eligible specification**

## What was tested

The exact preregistered six-cell grid tested an F05 exit only when:

1. executable price was inside the original breakout level at a first checkpoint;
2. it remained inside at a second checkpoint; and
3. it did not reaccept above 0 or 5 pips between the two checkpoints.

Checkpoint pairs were 30/60, 30/90 and 60/90 minutes. B02 and all entry keys were unchanged. No 2025 evidence was accessed.

## Technical incomplete attempt

The first local evaluator invocation stopped before writing candidate metrics because period subsets retained non-contiguous pandas indices. The implementation was corrected by resetting each period index. Inputs, six-cell grid, formulas and gates were unchanged. This attempt is not a scientific result.

## Result

No cell passed all period and pooled gates. No finalist is frozen.

The highest-ranked cell was `H_A30_B60_R5`:

- 2023 candidate: JPY -7,655, delta +1,624, PF 0.958854
- 2024 H1 candidate: JPY 21,769, delta -1,028
- 2024 H2 candidate: JPY 36,689, delta -1,669
- pooled delta: JPY -1,073
- affected positions / dates: 329 / 250
- benefit / harm: JPY 51,253 / JPY 52,326
- positive / negative effect months: 14 / 10
- ex-best-two-entry-dates delta: JPY -5,838
- leave-one-month-out minimum: JPY -4,956

Only one affected position used a delayed checkpoint, contributing JPY +36. Excluding delayed-checkpoint effects made the pooled result slightly worse, so execution-delay handling did not cause the failure.

## Interpretation

Persistent no-reacceptance populations are economically weak as baseline groups, but closing every such position at 60 or 90 minutes still sacrifices late recovery winners.

This distinction matters: a negative conditional baseline population does not prove that an earlier replacement exit improves P/L. Family H improved 2023 but remained loss-making, while both 2024 halves deteriorated.

The unresolved mechanism is now narrower: **which trajectory observable, known by the second checkpoint, identifies positions capable of late reacceptance and recovery?**

## Retained findings

- Two-checkpoint persistence is more informative descriptively than one checkpoint, but not a robust exit rule.
- The remaining error is late recovery after the second checkpoint.
- The next diagnosis must compare recovery winners and permanent failures using trajectory features available by the second checkpoint.

## Prohibited reuse

- Do not add nearby checkpoints or reacceptance thresholds to Family H.
- Do not add shadow strategy health.
- Do not repair the family from 2025 outcomes.
- Do not infer replacement-exit value from baseline subgroup loss alone.

## Evidence identities

- evaluator SHA-256: `8c371508c14fd27bb4bc161a8a66c9ba61a8b37de1b0ba9cb7779741309aa0ca`
- candidate summary: `b3e9fcda570724ca45cabf6f49f0a55ac87155de85b60fec6f416350095fecde`
- period metrics: `b47d89de42af836965975c2fe0e8bd4f8c46a1cf963688509bb587ac03c1ca46`
- equivalence classes: `cc5fa42cb47a4536fb2606462517895b30582f83e49d820c1ec8dbaf8eb1886c`

## Next work

Diagnose trajectory and recovery-velocity differences between Family H loss-avoidance trades and late recovery winners across 2023 and both 2024 halves. No new family is authorized by this result alone.
