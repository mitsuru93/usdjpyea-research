# F05 failed reclaim binding validation v1

## Scope

This validation covers only:

- binding: `F05_FAILED_RECLAIM_BASIC_V1`
- non-binding sensitivity: `F05_FAILED_RECLAIM_WEAK_QUICK_V1`

The sensitivity was not executed and cannot replace the binding candidate. No Notion task, prior HYP, P1/P2/P3 rule, fixed-pips SL, indicator exit, direction exception, year exception, or alternative candidate was used.

## Execution identity

- protocol merge commit: `2cd04c1a22874b02452f9ffa8a4aae7c4f0b0123`
- binding workflow event: `workflow_dispatch`
- binding Run: `30095266485`, attempt `1`
- job: `89487718219`
- binding head: `dd70ed0495aecaff8de9629838122015036fd94e`
- artifact: `8597314851`
- artifact archive SHA-256: `0989ca20749d3100c40d411fed7534351e6c4fbb28941161055b6ce0f4b69ebc`
- Release tag: `f05-failed-reclaim-validation-v1`
- Release asset SHA-256: `4b8819b6b3545adab586671eac65544d8c0a4ce839e4b8258ff92bbd7702eafd`

## Exploration reproduction

The raw-authority extraction reproduced the exploration report exactly:

- stopped trades: 14
- total delta: +202.1 pips
- Long: +65.2 pips
- Short: +136.9 pips
- 2023H1: 4 trades / +70.8 pips
- 2023H2: 4 / +14.1 pips
- 2024H1: 5 / +110.7 pips
- 2024H2: 1 / +6.5 pips

This is a technical reproduction, not a scientific PASS.

## Direct-instruction identity

The direct instruction explicitly forbids using an M5 close whose completion timestamp equals the reclaim M1 close. Under that strict rule:

- stopped trades: 15
- total delta: +200.6 pips
- Long: +65.2 pips
- Short: +135.4 pips

One trade exists only under the direct rule:

- trade key: `F05|2023-06-08T15:45:00Z|-1`
- reclaim M1 close: `2023-06-08T16:35:00Z`
- direct failure M5 completion: `2023-06-08T16:40:00Z`
- baseline: -5.0 pips
- candidate: -6.5 pips
- delta: -1.5 pips

The exploration used the M5 completion at the reclaim timestamp. The direct instruction requires the next completed M5. Therefore, the changed-trade identity is not the same.

## Original bundle status

`F05_structural_SL_event_sequence_bundle_v1.zip` with expected SHA-256
`463850652d08f7c3d6b170a345ba92a1f7228c9efb24eb0f89f90b13a59b686d`
was not recovered as raw bytes. No reconstructed file is represented as that original bundle.

## Decision

`TECHNICAL_MISMATCH_STOP`

Stop before:

- scientific historical-gate interpretation
- full accepted-signal portfolio replay
- concurrency, stacking, capacity, reopened-capacity, balance and drawdown evaluation
- non-binding sensitivity execution
- MT4 parity or Strategy Tester
- 2025 H1 or H2 access

This is neither a scientific PASS nor a scientific FAIL. The binding candidate remains unchanged but technically unresolved because the direct event-time definition and the exploration identity conflict.

## Boundaries confirmed

- scientific outcomes interpreted: false
- historical gates evaluated: false
- portfolio replay computed: false
- non-binding sensitivity computed: false
- MT4 accessed: false
- 2025 H1/H2 accessed: false
- new HYP created: false
- Notion used as task source: false
