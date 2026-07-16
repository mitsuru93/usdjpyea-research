# USDJPY Post-Q2 Regime Diagnostic Results v1

## Scope

This diagnostic uses only the verified 2024-01 through 2024-06 session-baseline artifacts.

Canonical baseline runs:

```text
2024-01: 29307131333
2024-02: 29383810487
2024-03: 29421329471
2024-04: 29455059447
2024-05: 29469227483
2024-06: 29475803893
```

The two fixed candidates were not retuned:

```text
M5 pullback continuation
  session: UTC 13-16
  pullback_min_pips: 2
  trend_lookback_bars: 12
  trend_min_pips: 10
  hold_bars: 6

M15 breakout close follow-through
  session: UTC 13-16
  lookback_bars: 3
  hold_bars: 6
```

## Data-source separation

P&L, public spread and trade timestamps come from the canonical Dukascopy baseline `trades.csv` files.

The canonical public M1 series is used only to calculate descriptive market-state fields that were not retained inside the baseline artifacts.

```text
market-state dataset:
USDJPY_M1_2024-01-02_2026-02-18.csv

server-time interpretation:
Europe/Helsinki EET/EEST -> UTC
```

The two price series were reconciled at the 1,529 fixed-candidate entry timestamps:

```text
median absolute entry-price difference: 0.25 pips
90th percentile:                       0.50 pips
99th percentile:                       1.10 pips
share within 2.0 pips:                 99.35%
```

This agreement is adequate for descriptive range and excursion fields. It is not evidence that the public-M1 series can replace Dukascopy for signal generation or P&L.

## Fixed-family result

### M5 pullback

| Month | Trades | Avg net pips | Total net pips | PF |
|---|---:|---:|---:|---:|
| 2024-01 | 244 | +2.022 | +493.33 | 1.287 |
| 2024-02 | 129 | +2.164 | +279.11 | 1.483 |
| 2024-03 | 135 | +1.912 | +258.07 | 1.646 |
| 2024-04 | 110 | +0.430 | +47.27 | 1.108 |
| 2024-05 | 161 | -1.902 | -306.25 | 0.701 |
| 2024-06 | 152 | -0.767 | -116.51 | 0.836 |

The Q2 failure remains the verified decision. Direction-only interpretation does not repair it: May is primarily a short-side collapse, but June is negative on both sides.

### M15 breakout

| Month | Trades | Avg net pips | Total net pips | PF |
|---|---:|---:|---:|---:|
| 2024-01 | 114 | +2.100 | +239.43 | 1.179 |
| 2024-02 | 114 | +2.909 | +331.59 | 1.432 |
| 2024-03 | 85 | -1.365 | -116.06 | 0.766 |
| 2024-04 | 95 | +3.493 | +331.80 | 1.716 |
| 2024-05 | 103 | -0.240 | -24.71 | 0.965 |
| 2024-06 | 87 | -1.216 | -105.75 | 0.826 |

The unfiltered breakout family remains unpromoted.

## Q1 versus Q2 descriptive market-state change

Median fields derived from the reconciled public M1 series:

| Candidate | Field | Q1 | Q2 |
|---|---|---:|---:|
| M5 pullback | prior 60m range | 35.0 | 32.4 |
| M5 pullback | signal-bar range | 9.0 | 7.9 |
| M5 pullback | primary-session-so-far range | 54.1 | 39.3 |
| M5 pullback | full primary-session range | 71.6 | 57.5 |
| M5 pullback | holding-window MFE | 10.95 | 6.75 |
| M5 pullback | holding-window range | 21.9 | 16.1 |
| M15 breakout | prior 60m range | 26.0 | 24.6 |
| M15 breakout | signal-bar range | 13.7 | 11.7 |
| M15 breakout | primary-session-so-far range | 38.7 | 32.9 |
| M15 breakout | full primary-session range | 65.0 | 46.8 |
| M15 breakout | holding-window MFE | 12.9 | 8.85 |
| M15 breakout | holding-window range | 26.9 | 21.5 |

The repeated difference is weaker primary-session expansion and weaker post-entry excursion in Q2. Prior 180-minute range is nearly unchanged, so this is not simply a broad reduction in pre-entry volatility.

## M5 pullback diagnosis

Natural pre-entry interpretations were checked without fitting profitable numeric thresholds:

- 1h, 3h, 6h, 12h and 24h direction alignment;
- pre-primary-session direction alignment;
- primary-session-so-far direction alignment;
- signal-range expansion versus the previous bar;
- recent one-hour volatility versus the preceding three-hour average;
- entry outside the pre-primary-session range.

No condition produced positive Q1 and Q2 averages, repeated monthly performance, acceptable severe-cost behavior and low day concentration together.

The M5 pullback branch therefore remains rejected. No regime filter is promoted.

## Provisional M15 mechanism observed with reconciled features

When the existing Dukascopy breakout trade rows are labeled by public-M1 descriptive features, the strongest observed condition is:

```text
signal-bar range > immediately preceding M15 bar range
```

The labeled Dukascopy trade rows show:

```text
trades: 393
positive months: 4 / 6
avg net pips: +1.748
total net pips: +687.02
profit factor: 1.235
Q1 avg net pips: +2.141
Q2 avg net pips: +1.302
severe avg net pips: -0.421
severe PF: 0.951
event-excluded avg net pips: +1.145
event-excluded PF: 1.154
total excluding best two days: +150.38
```

This is a useful diagnostic lead, not yet a valid H2 candidate.

## Signal-generation equivalence check

The exact impulse rule was then regenerated directly from the public-M1 OHLC bars for the same H1 period.

That result changed materially:

```text
trades: 395
positive months: 3 / 6
avg net pips: +1.099
total net pips: +434.00
profit factor: 1.143
severe avg net pips: -0.901
severe PF: 0.897
total excluding best two days: -29.10
```

The public-M1 signal generation therefore does not reproduce the robustness profile obtained by labeling the Dukascopy baseline trades.

The cause is not the small median entry-price difference alone. Small OHLC differences change whether a close exceeds a three-bar high or low and whether one bar range exceeds the preceding range. The selected trade population changes.

## Current decision

```text
M5 pullback branch:
  closed in current form

Unfiltered M15 breakout:
  remains rejected

M15 impulse-confirmation lead:
  provisional only

H2 pre-registration:
  withdrawn before any July-December result was inspected
```

## Required next action

Before defining any H2 candidate, rerun the impulse diagnostic using the original Dukascopy M15 source bars from the six verified source runs.

Required source runs:

```text
2024-01: 29189903048
2024-02: 29329511595
2024-03: 29386417671
2024-04: 29423451609
2024-05: 29455212697
2024-06: 29469210771
```

The exact-source diagnostic must:

1. download the original day-bar artifacts;
2. reconstruct monthly Dukascopy M15 bars;
3. apply `range[t] > range[t-1]` on those bars;
4. join the condition to the canonical baseline trade rows;
5. reproduce monthly, severe-stress, event-sensitivity and day-concentration metrics;
6. compare the resulting trade population with the public-M1 labeled population.

Only if the Dukascopy-bar result independently meets the robustness requirements may the candidate and H2 gate be committed.

No 2024-07 through 2024-12 performance result has been inspected or accepted.
