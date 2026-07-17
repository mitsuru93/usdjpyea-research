# USDJPY Research Status After Q2 v1

## Verified development data block

The verified Dukascopy development block covers 2024-01 through 2024-06 with 100% effective coverage and zero final hard errors.

```text
2024-01 baseline: 29307131333
2024-02 baseline: 29383810487
2024-03 baseline: 29421329471
2024-04 baseline: 29455059447
2024-05 baseline: 29469227483
2024-06 baseline: 29475803893
```

## Corrected multi-family development run

Authoritative workflow result:

```text
run_id: 29547232643
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
artifact_digest: sha256:b5fd40e7c37cd3c4c417b9e02547ce6d7195f0f989266e4f0e3ae0305947ec94
```

Canonical result record:

```text
docs/research_reboot/usdjpy_h1_multi_family_screen_v2_result_v1.md
```

The earlier run `29546116205` is invalid because it applied selected entry-hour fields to the signal bar and used a different spread field.

The corrected January–June screen is retained as a development-period diagnostic. Its `retention_pass` field does not filter the July–December validation set.

## Frozen H2 candidate set

All 13 candidates in the registered M15 universe advance to the untouched H2 batch:

```text
A1_impulse_breakout_lb3_hold6

B1_asia_00_06_breakout_hold6
B2_asia_00_07_breakout_hold6
B3_prior_utc_day_breakout_hold6

C1_failed_12bar_hold3
C2_failed_12bar_hold6
C3_failed_24bar_hold6
C4_failed_asia_00_06_hold6

D1_compression_4v4_hold6
D2_compression_8v8_hold6

E1_trend_4h_resumption_hold6
E2_trend_8h_resumption_hold6
E3_trend_24h_resumption_hold6
```

Authoritative files:

```text
configs/research/usdjpy_h1_multi_family_candidates_v1.json
configs/research/usdjpy_h2_all_candidates_v1.json
docs/research_reboot/usdjpy_joint_h2_prereg_all_candidates_v1.md
```

Candidate-set policy:

```text
all_registered_candidates_no_h1_retention_filter
```

The prior A1/E3-only H2 pre-registration is superseded and must not be used.

## M5 pullback status

The fixed M5 pullback-continuation hypothesis remains rejected in its tested form.

```text
trend_lookback_bars: 12
trend_min_pips: 10
pullback_min_pips: 2
hold_bars: 6
```

It failed the pre-registered Q2 gate:

```text
trades: 423
avg_net_pips: -0.888
total_net_pips: -375.48
positive_months: 1 / 3
severe avg_net_pips: -3.033
severe total_net_pips: -1282.75
```

This rejects the specific pullback-continuation family, not the M5 timeframe. A new M5 hypothesis requires a new family definition and a later untouched validation block. It is not part of the current H2 promotion set.

## Research roadmap position

```text
Step 3A — define and freeze the multi-family candidate universe:
  complete

Step 3B — corrected January–June development diagnostics:
  complete

Step 3C — all-candidate H2 pre-registration:
  complete after merge of the all-candidate handoff

Step 3D — untouched July–December data collection and joint validation:
  current

Step 4 — compare all candidates that pass every independent H2 gate:
  not started

Exit-policy research:
  not started

EA / Core / MT4 implementation:
  not started
```

## H2 validation block

```text
2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
```

All 13 candidates are judged independently against the common gate in `configs/research/usdjpy_h2_all_candidates_v1.json`.

Candidate definitions, directions, holds, sessions, cost scenarios, event dates and gates may not be changed after H2 is opened. Every candidate must remain in the final artifact whether it passes or fails.

Required joint reporting includes monthly default/severe metrics, long/short attribution, intervention sensitivity, best-two-day concentration, monthly sample counts, exact entry overlap, daily P&L correlation and family-level comparison.

## Immediate next action

Collect the July 2024 Dukascopy USDJPY bid/ask tick block with:

```text
Run Public FX Tick Pilot 2024-07 USDJPY
```

Workflow file:

```text
.github/workflows/run_public_fx_tick_pilot_USDJPY_2024_07.yml
```

After July reaches 100% effective coverage and zero final hard errors, preserve its source run ID. Repeat for August through December. Do not inspect candidate-level H2 results month by month. Evaluate all 13 candidates together only after the six-month block is complete.
