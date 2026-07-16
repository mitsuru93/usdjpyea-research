# USDJPY M15 Impulse Breakout H2 Pre-registration v1

## Status

This document pre-registers the first untouched-period test after the verified 2024-01 through 2024-06 post-Q2 diagnosis.

The 2024-07 through 2024-12 candidate result must not be inspected before this record is committed.

## Development and test periods

```text
development / diagnostic period: 2024-01-01 through 2024-06-30
test period:                     2024-07-01 through 2024-12-31
```

The test interval is UTC and the exclusive end is:

```text
2025-01-01T00:00:00Z
```

## Research role

The first H2 stage is a public-M1 candidate screen.

Dataset registry key:

```text
usdjpy_m1_2024_01_02_to_2026_02_18_public_main
```

The `DT` column is interpreted as MT4 server time using `Europe/Helsinki` EET/EEST and converted to UTC before M15 resampling.

The public M1 series has no usable historical bid/ask spread field. Therefore:

```text
default screening cost: 0.5 pips
severe screening cost:  2.5 pips
```

A public-M1 pass does not authorize EA implementation. It authorizes collection and validation of the same H2 period with Dukascopy bid/ask ticks.

## Fixed candidate

```text
name: m15_impulse_breakout_lb3
symbol: USDJPY
timeframe: M15
entry session: UTC entry hours 13, 14, 15 or 16
breakout lookback: 3 completed M15 bars
hold: 6 M15 bars
entry: next M15 bar open after signal
exit: close of the sixth held M15 bar
```

### Breakout rule

At the close of completed signal bar `t`:

```text
long breakout:
  close[t] > max(high[t-1], high[t-2], high[t-3])

short breakout:
  close[t] < min(low[t-1], low[t-2], low[t-3])
```

### Impulse-confirmation rule

```text
range[t] > range[t-1]

where:
range[x] = high[x] - low[x]
```

Equality does not pass.

This is a relative expansion rule. No range ratio, pip threshold, ATR multiple or percentile may be selected from H2 results.

## Hard no-trade rule

The project-wide DST-aware configuration remains authoritative:

```text
configs/market_sessions/fx_market_sessions_v1.json
```

Any entry inside an applicable hard no-trade window must be excluded before evaluation.

## Official intervention sensitivity

Official Ministry of Finance USD-selling / JPY-buying operation dates inside H2 2024:

```text
2024-07-11
2024-07-12
```

These are retrospective diagnostic labels, not live filters.

The result must be reported both:

```text
including all dates
excluding both official dates
```

No other H2 date may be removed after results are seen.

## Pre-registered public-M1 gate

The candidate passes only if every condition below is met.

1. At least four of the six H2 calendar months have positive default-cost average net pips.
2. Aggregate default-cost average net pips is positive.
3. Aggregate default-cost profit factor is at least 1.10.
4. After excluding 2024-07-11 and 2024-07-12, aggregate default-cost average net pips remains positive.
5. After excluding 2024-07-11 and 2024-07-12, aggregate default-cost profit factor is at least 1.05.
6. Aggregate default-cost total net pips remains positive after excluding the best two UTC trading days.
7. At least 300 retained trades are present in aggregate.
8. Every H2 calendar month contains at least 35 retained trades.
9. Severe-stress aggregate average net pips is no worse than -0.5 pips per trade.
10. Severe-stress aggregate profit factor is at least 0.90.
11. No retained entry violates the DST-aware hard no-trade configuration.

The sample-size gates are anchored below the H1 diagnostic population of 393 trades and minimum 56 monthly trades, allowing lower H2 activity without accepting a sparse result.

## Prohibited responses to failure

After H2 results are opened, the following are prohibited:

- changing breakout lookback from 3;
- changing hold from 6;
- changing UTC entry hours;
- replacing `range[t] > range[t-1]` with a fitted ratio;
- selecting a range or ATR threshold;
- converting the strategy to long-only or short-only;
- excluding a losing month;
- excluding any non-official event date;
- optimizing an exit;
- treating H2 immediately as a new development set for another breakout variant.

Failure of any gate closes the current M15 impulse-breakout candidate.

## Advancement path

If all public-M1 gates pass:

```text
public-M1 H2 screen
-> collect 2024-07 through 2024-12 Dukascopy bid/ask ticks
-> apply the exact same candidate
-> apply max(0.5-pip base spread, public spread) cost and severe stress
-> evaluate a separately committed Dukascopy validation gate
-> only then consider exit-policy research
```

No Core or MT4 implementation begins from the public-M1 screen alone.
