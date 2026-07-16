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

The public M1 series is therefore used for descriptive range, direction and excursion fields. It does not replace the Dukascopy P&L calculation.

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

## Q1 versus Q2 market-state change

Median descriptive fields:

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

The principal repeated difference is weaker primary-session expansion and weaker post-entry excursion in Q2. It is not a broad collapse in prior three-hour range: prior 180-minute range is nearly unchanged for both fixed candidates.

## M5 pullback diagnosis

Natural pre-entry interpretations were checked without fitting profitable numeric thresholds:

- 1h, 3h, 6h, 12h and 24h direction alignment;
- pre-primary-session direction alignment;
- primary-session-so-far direction alignment;
- signal-range expansion versus the previous bar;
- recent one-hour volatility versus the preceding three-hour average;
- entry outside the pre-primary-session range.

No condition produced a combination of:

- positive Q1 and Q2 averages;
- repeated positive months;
- acceptable severe-cost behavior;
- low dependence on one or two days.

The M5 pullback branch therefore remains rejected. No regime filter is promoted from this diagnostic.

## M15 mechanism comparison

Four mechanism definitions were compared. These are natural sign or relative-comparison rules, not fitted thresholds.

| Mechanism | Trades | Positive months | Q1 avg | Q2 avg | Default PF | Severe avg | Severe PF | Event-excluded avg | Event-excluded PF | Total excluding best 2 days |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Signal range > previous-bar range | 393 | 4/6 | +2.141 | +1.302 | 1.235 | -0.421 | 0.951 | +1.145 | 1.154 | +150.38 |
| Direction aligned with prior 12h | 428 | 4/6 | +0.763 | +2.319 | 1.200 | -0.683 | 0.919 | +0.890 | 1.121 | +84.17 |
| Direction aligned with prior 24h | 336 | 4/6 | +0.954 | +2.069 | 1.198 | -0.655 | 0.924 | +1.125 | 1.147 | +95.15 |
| Recent volatility acceleration | 548 | 4/6 | +1.013 | +0.839 | 1.125 | -1.228 | 0.858 | +0.584 | 1.078 | -141.69 |

Event-excluded results remove the following diagnostic dates:

```text
2024-04-29
2024-05-01
2024-05-02
```

The strongest mechanism under the predefined robustness dimensions is:

```text
signal-bar range > immediately preceding M15 bar range
```

It has:

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

The complement, breakout signals without signal-range expansion, is approximately flat in aggregate and negative in Q2. This supports an impulse-confirmation mechanism rather than a generic breakout edge.

## Interpretation

The selected hypothesis is not that the original breakout family passed. It did not.

The new hypothesis is narrower and mechanistically distinct:

> A local M15 close breakout is more likely to continue when the breakout bar itself shows immediate volatility expansion relative to the preceding completed M15 bar.

The rule is observable at the signal close and uses no fitted magnitude threshold. The comparison boundary is exactly 1.0 because it asks whether range expanded or contracted.

This is development-sample evidence only. It must be tested on a later untouched block before Dukascopy H2 collection, exit research or EA implementation.

## Decision

```text
M5 pullback branch:
  closed in current form

Unfiltered M15 breakout:
  remains rejected

New candidate for pre-registration:
  M15 impulse-confirmed breakout
  breakout lookback = 3
  signal range > previous-bar range
  hold = 6
  entry UTC hours = 13-16
```

The next step is Step 3C: commit the exact H2 candidate and gate before inspecting July-December results.
