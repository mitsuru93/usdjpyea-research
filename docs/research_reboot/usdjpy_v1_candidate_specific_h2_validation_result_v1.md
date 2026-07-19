# USDJPY V1 Candidate-Specific 2024 H2 Validation Result v1

## Decision

```text
V1 execution contract: PASS
H2 exposure ordinal: 2
H1 signal regressions: 5 / 5
H1 fixed-time trade regressions: 5 / 5
H2 signals: 1,879
H2 trades: 1,859
individual passes: 2
individual failures: 3
2025 access: none
Core promotion in V1: false
MT4 promotion in V1: false
```

## Accepted run

```text
run_id: 29673802426
workflow_head_sha: 64f63276968b0f7de4a7d27f7ebd7b86b6fab53a
evaluator_lock_commit: 64f37f0702678659d7523b5ad48e6b56896dff92
artifact_id: 8438161821
artifact: usdjpy-v1-candidate-specific-h2-validation-v1-29673802426
artifact_digest: sha256:19acb99e0ad286b3d2593b6f9df59a6675920eb3734d5901b70e4d8dc9a7c6b8
release_tag: usdjpy-v1-candidate-specific-h2-validation-v1
```

## Individual results

| Freeze rank | Strategy | Trades | Avg default | Avg severe | Default PF | Severe PF | Default +months | Severe +months | Ex-best-two days | Decision |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | R1H04_ramom_32_64_z125__T0_fixed_time_cap | 193 | -3.915760 | -6.284587 | 0.851212 | 0.771616 | 3 | 2 | -1474.329 | FAIL |
| 2 | R1B02_legacy_asia_00_07_breakout__T0_fixed_time_cap | 101 | +14.077434 | +11.723390 | 1.648370 | 1.518084 | 6 | 5 | +982.876 | PASS |
| 3 | R1E02_legacy_trend_8h_resumption__T0_fixed_time_cap | 390 | +3.060460 | +0.743687 | 1.113908 | 1.026630 | 3 | 3 | -583.010 | FAIL |
| 4 | R1F05_donchian_96__T0_fixed_time_cap | 386 | +6.082569 | +3.696412 | 1.274643 | 1.158457 | 5 | 5 | +721.998 | PASS |
| 5 | R1E03_trend_12h_resumption__T0_fixed_time_cap | 789 | +2.533418 | +0.144868 | 1.117139 | 1.006354 | 4 | 4 | +673.746 | FAIL |

Passed unchanged strategies:

- `R1B02_legacy_asia_00_07_breakout__T0_fixed_time_cap`
- `R1F05_donchian_96__T0_fixed_time_cap`

Failed exact specifications and primary failed gates:

- `R1H04_ramom_32_64_z125__T0_fixed_time_cap`: negative aggregate default/severe expectancy and PF, insufficient positive months, negative Q3, and negative total after excluding the best two Entry dates.
- `R1E02_legacy_trend_8h_resumption__T0_fixed_time_cap`: only three default-positive months and negative total after excluding the best two Entry dates.
- `R1E03_trend_12h_resumption__T0_fixed_time_cap`: Q3 was negative under both default and severe cost assumptions.

## Joint diagnostic

The equal-weight five-strategy diagnostic produced default total +1241.279 pips and severe total +360.458 pips, with 4 default-positive months and 4 severe-positive months. It is diagnostic only and did not rescue an individual failure.

## Research handling

The two passing strategies may proceed unchanged to Research/Core and MT4 parity. V1 itself made no Core or MT4 promotion.

The three failed exact specifications are not passed or rescued under V1. Research may return to H1 and create a new versioned, preregistered optimization or hypothesis branch, including designs informed by the validation feedback. The same 2024 H2 remains the fixed reusable validation gate for later branches; every exposure must be logged and direct H2 parameter sweeps or H2 ranking remain prohibited.

Because H2 is reusable, it is not the final untouched holdout after repeated exposures. The 2025 period remains unopened and is reserved for the later unchanged replication after specification freeze and Research/Core/MT4 parity.
