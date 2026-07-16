# USDJPY Research Status After Q2 v1

## Last verified stage

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

## Verified family decisions

### M5 pullback continuation

```text
timeframe: M5
session: UTC 13-16
pullback_min_pips: 2
trend_lookback_bars: 12
trend_min_pips: 10
hold_bars: 6
```

Monthly default-cost average net pips:

```text
2024-01: +2.022
2024-02: +2.164
2024-03: +1.912
2024-04: +0.430
2024-05: -1.902
2024-06: -0.767
```

Q2 aggregate:

```text
trades: 423
avg_net_pips: -0.888
total_net_pips: -375.48
profit_factor: 0.827
positive_months: 1 / 3
```

The pre-registered Q2 promotion gate was not met. The post-Q2 diagnosis did not identify a repeated M5 regime condition with acceptable monthly, severe-stress and concentration behavior.

The M5 pullback branch is closed in its current form.

### M15 breakout close follow-through

```text
timeframe: M15
session: UTC 13-16
lookback_bars: 3
hold_bars: 6
```

Monthly default-cost average net pips:

```text
2024-01: +2.100
2024-02: +2.909
2024-03: -1.365
2024-04: +3.493
2024-05: -0.240
2024-06: -1.216
```

The unfiltered family did not reproduce consistently and was not promoted.

## Diagnostic progress

P&L remains sourced from the canonical Dukascopy baseline trade rows.

The public M1 series was reconciled to the 1,529 fixed-candidate entries and used for descriptive market-state fields only:

```text
median absolute entry-price difference: 0.25 pips
99th percentile:                       1.10 pips
share within 2.0 pips:                 99.35%
```

The Q1-to-Q2 descriptive change is weaker primary-session expansion and weaker post-entry excursion, rather than a large change in prior three-hour range.

A provisional M15 lead appeared when the Dukascopy baseline trade rows were labeled with the descriptive condition:

```text
signal-bar range > previous completed M15 bar range
```

However, regenerating both signals and P&L directly from the public-M1 series did not reproduce the same robustness profile:

```text
public-M1 H1 regeneration:
trades: 395
positive months: 3 / 6
avg net pips: +1.099
profit factor: 1.143
severe avg net pips: -0.901
severe PF: 0.897
total excluding best two days: -29.10
```

Therefore the public M1 dataset cannot be used to validate this candidate. It remains a diagnostic lead only.

## Current phase

```text
Original roadmap position:
Step 3B - post-Q2 entry-strategy diagnosis

Current substep:
exact-source confirmation of the provisional M15 impulse mechanism

Development data allowed:
2024-01 through 2024-06 only

2024-07 through 2024-12:
not inspected and not accepted as evidence

Exit-policy optimization:
not started

EA / Core implementation:
not started
```

## Exact-source confirmation

The confirmation must use the original Dukascopy M15 bars from the source runs that generated the six verified baselines:

```text
2024-01: 29189903048
2024-02: 29329511595
2024-03: 29386417671
2024-04: 29423451609
2024-05: 29455212697
2024-06: 29469210771
```

The exact-source tool is:

```text
tools/analyze_usdjpy_dukascopy_impulse_confirmation.py
```

The workflow to run is:

```text
Run USDJPY H1 Dukascopy Impulse Confirmation
```

Workflow file:

```text
.github/workflows/run_usdjpy_h1_dukascopy_impulse_confirmation.yml
```

It downloads the six canonical baseline artifacts and all corresponding day-bar artifacts, calculates `range[t] > range[t-1]` on the original Dukascopy M15 bars, joins the condition to the canonical breakout trade rows, and reports:

- source-bar coverage;
- monthly results;
- severe-stress results;
- intervention sensitivity;
- direction split;
- best-day concentration;
- impulse versus non-impulse population comparison.

## Next decision

Only two outcomes are permitted after the exact-source artifact is inspected.

### Exact-source confirmation passes

The exact candidate, later test period and promotion gate are committed before any 2024-07 through 2024-12 result is opened.

### Exact-source confirmation fails

The impulse lead is rejected. The pullback and breakout branch is closed and a different strategy family with an independent market mechanism is designed.

No H2 pre-registration is currently active.
