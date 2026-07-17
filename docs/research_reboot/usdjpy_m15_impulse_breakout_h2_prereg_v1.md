# USDJPY M15 Impulse Breakout H2 Pre-registration v1

## Status

This document pre-registers the first untouched-period test of the exact-source-confirmed M15 impulse-breakout candidate.

It is committed before any 2024-07 through 2024-12 Dukascopy candidate result is inspected.

## Development and test periods

```text
development / diagnostic period: 2024-01-01 through 2024-06-30
test period:                     2024-07-01 through 2024-12-31
exclusive end:                   2025-01-01T00:00:00Z
```

The H2 period must not be used to change the candidate or gates below.

## Data source

The test must use newly collected Dukascopy USDJPY bid/ask tick data, processed through the same public-FX pilot and monthly baseline pipeline used for 2024-01 through 2024-06.

Required source conditions:

```text
effective coverage: 100%
final hard errors: 0
bar timeframes: M5 and M15
cost spread mode: max_base_public
Rakuten USDJPY base spread: 0.5 pips
DST-aware hard no-trade rule: enabled
```

The public M1 dataset must not replace Dukascopy bars or P&L for this test.

## Fixed candidate

```text
name: m15_impulse_breakout_lb3
symbol: USDJPY
timeframe: M15
entry session: UTC entry hours 13, 14, 15 or 16
breakout lookback: 3 completed M15 bars
hold: 6 M15 bars
entry: next M15 bar open after the signal
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

No range ratio, ATR multiple, pip threshold, percentile or alternative comparison window may be selected after H2 is opened.

## Hard no-trade rule

The project-wide configuration remains authoritative:

```text
configs/market_sessions/fx_market_sessions_v1.json
```

Any entry inside an applicable DST-aware hard no-trade window must be excluded before evaluation.

## Cost scenarios

Default:

```text
spread basis: max(0.5 pips, public entry spread)
spread multiplier: 1.0
slippage: 0.0 pips per side
```

Severe:

```text
spread basis: max(0.5 pips, public entry spread)
spread multiplier: 3.0
slippage: 0.5 pips per side
```

## Official intervention sensitivity

Official Ministry of Finance USD-selling / JPY-buying operation dates inside the H2 block:

```text
2024-07-11
2024-07-12
```

These are retrospective diagnostic labels and not live entry filters.

Results must be reported both including all dates and excluding both official dates. No other H2 date may be removed after results are seen.

## Pre-registered H2 promotion gate

The candidate passes only if every condition below is met.

1. All six monthly source datasets have 100% effective coverage and zero final hard errors.
2. At least four of the six H2 calendar months have positive default-cost average net pips.
3. Aggregate default-cost average net pips is positive.
4. Aggregate default-cost profit factor is at least 1.10.
5. After excluding 2024-07-11 and 2024-07-12, aggregate default-cost average net pips remains positive.
6. After excluding 2024-07-11 and 2024-07-12, aggregate default-cost profit factor is at least 1.05.
7. Aggregate default-cost total net pips remains positive after excluding the best two UTC trading days.
8. At least 300 retained trades are present in aggregate.
9. Every H2 calendar month contains at least 35 retained trades.
10. Severe-stress aggregate average net pips is no worse than -0.5 pips per trade.
11. Severe-stress aggregate profit factor is at least 0.90.
12. No retained entry violates the DST-aware hard no-trade configuration.

Failure of any condition means the candidate does not advance.

The sample-size gates are anchored below the H1 exact-source population of 391 trades and minimum monthly count of 55, allowing lower H2 activity without accepting a sparse result.

## Prohibited responses to failure

After H2 results are opened, the following are prohibited:

- changing breakout lookback from 3;
- changing hold from 6;
- changing UTC entry hours;
- replacing `range[t] > range[t-1]` with a fitted ratio;
- selecting a range or ATR threshold;
- converting the candidate to long-only or short-only;
- excluding a losing month;
- excluding any non-official event date;
- optimizing an exit;
- treating H2 immediately as a development set for another breakout variant.

## Advancement path

If all H2 gates pass:

```text
H2 Dukascopy bid/ask validation
-> separate exit-policy pre-registration
-> exit-policy research
-> MT4 implementation candidate
```

If any gate fails, the current Pullback/Breakout branch is closed and research moves to a different strategy family with an independent market mechanism.

No Core or MT4 implementation begins before the H2 gate is evaluated from the actual workflow artifacts.
