# USDJPY Joint H2 Pre-registration — All Registered Candidates v1

## Status

This document supersedes `usdjpy_joint_h2_prereg_a1_e3_v1.md`.

The corrected January–June 2024 screen remains a development-period diagnostic. It does **not** remove registered candidates from the July–December 2024 validation set. All 13 candidates in the frozen registry are evaluated together in one untouched H2 batch.

No July–December 2024 candidate result may be inspected before this pre-registration is merged.

## Frozen inputs

```text
candidate registry:
  configs/research/usdjpy_h1_multi_family_candidates_v1.json

registry blob SHA:
  68d2ad24ef278283f9addf190a2aadd26504efd6

H2 handoff config:
  configs/research/usdjpy_h2_all_candidates_v1.json
```

The registry is authoritative for every entry definition, direction, reference window, entry-hour rule and hold period.

## Time blocks

```text
development block:
  2024-01-01T00:00:00Z through 2024-07-01T00:00:00Z exclusive

untouched H2 validation block:
  2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
```

H2 may not be used to alter any candidate or gate.

## H2 candidate set

### M15 impulse breakout

- `A1_impulse_breakout_lb3_hold6`

### Session range breakout

- `B1_asia_00_06_breakout_hold6`
- `B2_asia_00_07_breakout_hold6`
- `B3_prior_utc_day_breakout_hold6`

### Mean reversion / failed excursion

- `C1_failed_12bar_hold3`
- `C2_failed_12bar_hold6`
- `C3_failed_24bar_hold6`
- `C4_failed_asia_00_06_hold6`

### Compression expansion

- `D1_compression_4v4_hold6`
- `D2_compression_8v8_hold6`

### Higher-timeframe trend continuation

- `E1_trend_4h_resumption_hold6`
- `E2_trend_8h_resumption_hold6`
- `E3_trend_24h_resumption_hold6`

No candidate is omitted because it failed the January–June descriptive retention screen.

## Data and execution semantics

Every H2 month must use newly collected Dukascopy USDJPY bid/ask tick data processed through the same public-FX monthly pipeline used for the corrected H1 run.

Required conditions:

```text
effective coverage: 100%
final hard errors: 0
signal/outcome timeframe: M15
entry: next M15 bar open
spread basis: max(0.5 pips, Dukascopy entry-bar spread_mean_pips)
DST-aware hard no-trade configuration: enabled
aggregate-repair bars: included when produced by the monthly pipeline
```

Default and severe cost scenarios are frozen in `usdjpy_h2_all_candidates_v1.json`.

## Intervention sensitivity

The official Ministry of Finance operation dates inside H2 are:

```text
2024-07-11
2024-07-12
```

They are retrospective diagnostic labels only. Every candidate is reported with all dates included and with both dates excluded. No other H2 date may be removed after results are opened.

## Common validation gate

Each of the 13 candidates is evaluated independently. A candidate advances only if every gate in `configs/research/usdjpy_h2_all_candidates_v1.json` passes:

1. At least four of six months have positive default-cost average net pips.
2. Aggregate default-cost average net pips is positive.
3. Aggregate default-cost profit factor is at least 1.10.
4. Event-excluded average net pips remains positive.
5. Event-excluded profit factor is at least 1.05.
6. Total net pips remains positive after excluding the candidate's best two UTC trading days.
7. Severe-stress average net pips is at least -0.5 pips per trade.
8. Severe-stress profit factor is at least 0.90.
9. Aggregate trades are at least 120.
10. Every month has at least 12 trades.
11. Hard no-trade violations equal zero.
12. The corrected H1 implementation regression passes before H2 results are accepted.

A candidate that fails a gate remains in the H2 report; it is not silently removed from the artifact.

## Required joint reporting

The H2 artifact must include:

- every candidate's monthly default and severe metrics;
- long/short attribution;
- intervention-date sensitivity;
- best-two-day concentration;
- monthly sample counts;
- exact entry overlap between candidates;
- daily net-pips correlation;
- family-level comparison;
- complete results for all gate failures as well as passes.

Candidate comparison occurs only after independent gate evaluation. H2 may not be used to merge conditions, change directions, change holds, fit new thresholds, optimize exits or exclude losing months.

## M5 status

The fixed M5 pullback-continuation specification is not part of the promotion set. It failed the pre-registered Q2 gate across the tested parameter band and under severe costs.

This rejects that **specific M5 hypothesis**, not the M5 timeframe as a whole. A materially different M5 family requires a new hypothesis and a new pre-registration before testing on a later untouched block.

## Advancement path

```text
all 13 candidates frozen
-> collect 2024-07 through 2024-12 without candidate inspection
-> evaluate all 13 in one H2 batch
-> retain every independent gate passer
-> compare overlap, correlation and family behavior
-> separate exit-policy pre-registration
-> later untouched confirmation before MT4 implementation
```
