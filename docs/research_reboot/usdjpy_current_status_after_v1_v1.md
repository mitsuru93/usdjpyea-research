# USDJPY Research Current Status after V1 v1

## Governing boundary

```text
repository: mitsuru93/usdjpyea-research
Research role: pre-MT4 candidate screener
Core / MT4: final source of truth
2024 H1: development and optimization domain
2024 H2: fixed reusable validation gate
2025: unopened final replication period
live capital allocation: prohibited
```

If an exact strategy fails H2, that exact specification is closed. Research may return to H1 for a new versioned and preregistered optimization or hypothesis branch and use the same H2 again. Every H2 exposure is logged. Direct H2 parameter sweeps and H2 ranking are not part of the validation run. Because H2 is reusable, 2025 remains the final untouched replication period after specification freeze and Research/Core/MT4 parity.

## Accepted stages

| Stage | Status | Accepted run | Artifact ID | Release |
|---|---|---:|---:|---|
| R0 canonical 2024 bundle | PASS | 29639548804 | 8428199309 | `usdjpy-r0-canonical-2024-v1` |
| R1 Entry registry v2 | PASS | 29642282221 | 8428977454 | `usdjpy-r1-entry-registry-v2` |
| R2 horizon surface | PASS | 29646040010 | 8430064217 | `usdjpy-r2-horizon-surface-v1` |
| R3 stability diagnostics | PASS | 29647304892 | 8430424186 | `usdjpy-r3-temporal-stability-v1` |
| R4 representative selection | PASS | 29665005273 | 8435465130 | `usdjpy-r4-entry-horizon-selection-v1` |
| R5 controlled Exit comparison | PASS | 29666989206 | 8436023286 | `usdjpy-r5-controlled-exit-v1` |
| R6 complete-strategy freeze | PASS | 29672853145 | 8437864148 | `usdjpy-r6-complete-strategy-freeze-v1` |
| V1 candidate-specific 2024 H2 validation | PASS | 29673802426 | 8438161821 | `usdjpy-v1-candidate-specific-h2-validation-v1` |

## R6 freeze

R6 audited all 32 accepted R5 Entry/Exit combinations. Nine passed every H1 eligibility gate and five were frozen after the one-definition cap, family cap and redundancy procedure.

Frozen complete strategies:

1. `R1H04_ramom_32_64_z125__T0_fixed_time_cap`
2. `R1B02_legacy_asia_00_07_breakout__T0_fixed_time_cap`
3. `R1E02_legacy_trend_8h_resumption__T0_fixed_time_cap`
4. `R1F05_donchian_96__T0_fixed_time_cap`
5. `R1E03_trend_12h_resumption__T0_fixed_time_cap`

R6 parsed zero H2 rows and did not access 2025.

## V1 fixed reusable H2 exposure 2

```text
H1 signal regressions: 5 / 5
H1 fixed-time trade regressions: 5 / 5
H2 signals: 1,879
H2 trades: 1,859
individual passes: 2
individual failures: 3
acceptance checks: 20 / 20
2025 access: none
Core promotion in V1: false
MT4 promotion in V1: false
```

Passed unchanged strategies:

1. `R1B02_legacy_asia_00_07_breakout__T0_fixed_time_cap`
   - H2 trades: 101
   - average default net: +14.077434 pips
   - average severe net: +11.723390 pips
   - default PF: 1.648370
   - severe PF: 1.518084
   - default-positive months: 6 / 6
   - severe-positive months: 5 / 6
   - total excluding best two UTC Entry dates: +982.876 pips
2. `R1F05_donchian_96__T0_fixed_time_cap`
   - H2 trades: 386
   - average default net: +6.082569 pips
   - average severe net: +3.696412 pips
   - default PF: 1.274643
   - severe PF: 1.158457
   - default-positive months: 5 / 6
   - severe-positive months: 5 / 6
   - total excluding best two UTC Entry dates: +721.998 pips

Failed exact specifications:

- `R1H04_ramom_32_64_z125__T0_fixed_time_cap`: negative aggregate expectancy/PF and negative Q3.
- `R1E02_legacy_trend_8h_resumption__T0_fixed_time_cap`: only three default-positive months and negative ex-best-two-days total.
- `R1E03_trend_12h_resumption__T0_fixed_time_cap`: negative Q3 under default and severe costs.

These exact failed specifications are closed under V1. New H1 versions may be developed and preregistered, then evaluated on the same fixed H2 gate as a later logged exposure.

## Current authorized next work

1. Create Research/Core and MT4 parity evidence for the two V1 passers without changing Entry, Exit, time cap, costs or session rules.
2. Compare signal timestamps, Entry prices, Exit timestamps/prices, costs and trade returns between Research and Core/MT4.
3. Only strategies with accepted parity may be frozen for unchanged 2025 replication.
4. Separately preregister a new H1 research branch when resuming optimization after the three V1 failures; the same H2 may be reused and the next exposure ordinal must be logged.

2025 remains closed until parity and a separate V2 preregistration are accepted.
