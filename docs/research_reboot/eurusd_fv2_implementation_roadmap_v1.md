# EURUSD F v2: 2024-only research-to-implementation roadmap v1

## Governing boundary

- Strategy analysis and revision use 2024 H1 only.
- Every revision is locked before evaluation.
- 2024 H2 is the permanent fixed validation period.
- 2024 H2 has no consumed or retired state and is reused for every locked iteration.
- 2024 H2 may accept or reject an H1-derived revision but may not generate rules.
- 2025 data is outside this research and implementation workflow and must not be collected, inspected, evaluated, or used as a gate.

## Current accepted evidence

1. 2024 H1 development protocol is registered.
2. The retained F v2 candidates were evaluated on fixed 2024 H2.
3. Research-to-MT4 exact ledger parity has been established for the two retained exits.

Retained candidates:

- `F_v2_z72_1p5_mean_target_0p5_max12`
- `F_v2_z72_1p5_mean_target_0p25_max12`

## Remaining roadmap

### R3 — 2024 H1 diagnosis and bounded revision

Analyze 2024 H1 trade structure, monthly behavior, adverse excursions, holding-time distribution, entry z-score, efficiency ratio, session effects and cost sensitivity. Any proposed revision must be derived solely from this H1 evidence and preregistered before H2 evaluation.

### R4 — Fixed 2024 H2 revalidation

Apply the locked H1-derived revision to the same 2024 H2 period. Compare it with the current frozen baseline without ranking or tuning from H2. A failed candidate returns to R3; H2 remains unchanged and reusable.

### R5 — Exit-policy and neighboring-rule confirmation

Retain only bounded, preregistered comparisons. The registered target-0.5 and target-0.25 exits may be compared as an exit-policy pair. No new threshold may be created from H2.

### R6 — Cost and execution stress

Apply the registered spread/slippage grid and broker-operational tests without modifying the signal rule:

- spread multipliers 1.0, 1.5, 2.0 and 3.0;
- slippage per side 0.0, 0.1, 0.3 and 0.5 pips;
- Rakuten GMT+2/GMT+3 conversion;
- weekend and H1-boundary handling;
- restart, duplicate-order and missing-bar behavior;
- order-send and close retry auditing.

### R7 — Production EA construction

Promote the selected locked candidate into a production EA with completed-H1-only evaluation, next-H1-boundary execution, one-position state, persistent restart recovery, deterministic magic-number filtering and Research-compatible audit rows.

### R8 — Rakuten MT4 verification

Run pure signal parity, Strategy Tester automation, DST/boundary tests, restart/fault injection and demo-forward reconciliation. These tests validate implementation and execution, not strategy discovery.

### R9 — Limited live deployment

Begin only after the implementation gates pass, using a separately approved fixed-lot configuration and a preregistered operational-error gate.

## Current position

The current stage is R3: analyze 2024 H1 and preregister bounded revisions, then reuse fixed 2024 H2 for validation. No 2025 data is part of the workflow.
