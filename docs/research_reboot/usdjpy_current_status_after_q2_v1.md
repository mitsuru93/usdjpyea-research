# USDJPY Research Status After Q2 v1

## Verified baseline block

The verified monthly USDJPY session-baseline runs cover 2024-01 through 2024-06.

```text
2024-01: 29307131333
2024-02: 29383810487
2024-03: 29421329471
2024-04: 29455059447
2024-05: 29469227483
2024-06: 29475803893
```

All six baseline artifacts were generated from source data with 100% effective coverage and zero final hard errors.

## Closed branch

The fixed M5 pullback representative failed its Q2 gate:

```text
Q2 trades: 423
Q2 avg net pips: -0.888
Q2 total net pips: -375.48
Q2 profit factor: 0.827
positive Q2 months: 1 / 3
```

No repeated M5 regime condition survived the post-Q2 diagnostic requirements. The M5 pullback branch is closed in its current form.

The unfiltered M15 breakout family also remains rejected.

## Exact-source-confirmed candidate

Candidate:

```text
name: m15_impulse_breakout_lb3
timeframe: M15
entry hours UTC: 13, 14, 15, 16
breakout lookback: 3 completed M15 bars
impulse condition: signal-bar range > previous completed M15-bar range
entry: next M15 bar open
hold: 6 M15 bars
```

Exact-source confirmation run:

```text
run_id: 29543895841
artifact: usdjpy-h1-dukascopy-impulse-confirmation-29543895841
artifact_digest: sha256:75ca6f8c86f013a4e8a3d8962d4c00d80aebcef8d21e95dd182370be38558999
```

The confirmation used the original Dukascopy M15 source bars and the canonical baseline P&L rows, including aggregate-repair bars.

Coverage:

```text
all canonical breakout trades: 598
matched signal bars: 598
missing signal bars: 0
```

Impulse-confirmed H1 result:

```text
trades: 391
positive months: 4 / 6
avg net pips: +2.016
total net pips: +788.22
profit factor: 1.281
Q1 avg net pips: +2.628
Q2 avg net pips: +1.327
```

Severe stress:

```text
avg net pips: -0.153
profit factor: 0.982
```

After excluding the 2024 Q2 intervention episode dates:

```text
avg net pips: +1.458
profit factor: 1.204
```

After excluding the two strongest UTC days:

```text
total net pips: +251.58
```

The complement population without range expansion is negative:

```text
trades: 207
avg net pips: -0.637
profit factor: 0.916
```

Result record:

```text
docs/research_reboot/usdjpy_h1_dukascopy_impulse_confirmation_result_v1.md
```

## Current phase

```text
Original roadmap position:
Step 3C - untouched-period entry-strategy validation

Development period:
2024-01 through 2024-06

Untouched H2 period:
2024-07 through 2024-12

Exit-policy optimization:
not started

EA / Core implementation:
not started
```

## Active H2 pre-registration

```text
docs/research_reboot/usdjpy_m15_impulse_breakout_h2_prereg_v1.md
```

Pre-registration commit:

```text
fc35f780659fb97e3bec5a32e74276baa868da0b
```

The exact candidate, Dukascopy data source, cost model, intervention sensitivity, sample-size conditions, monthly replication conditions, concentration test and severe-stress gate are fixed before any H2 candidate result is inspected.

## Immediate next action

Collect July 2024 Dukascopy USDJPY bid/ask ticks with:

```text
Run Public FX Tick Pilot 2024-07 USDJPY
```

Workflow file:

```text
.github/workflows/run_public_fx_tick_pilot_USDJPY_2024_07.yml
```

July wrapper commit:

```text
f864427b230f4821d786418e92027e9be49eaa59
```

After the July source run reaches 100% effective coverage and zero hard errors, run the monthly baseline with that source run. The impulse condition is evaluated from the same Dukascopy M15 bars. Repeat sequentially for August through December without changing the pre-registered candidate or gate.
