# USDJPY Joint H2 Pre-registration — A1 and E3 v1

## Status

This document pre-registers the untouched-period validation of the two candidates retained by the corrected H1 multi-family screen.

It is committed before any 2024-07 through 2024-12 candidate result is inspected.

Authoritative H1 result:

```text
docs/research_reboot/usdjpy_h1_multi_family_screen_v2_result_v1.md
run_id: 29547232643
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
```

The earlier impulse-only H2 pre-registration is superseded and must not be used.

## Development and test blocks

```text
development / candidate-selection block:
  2024-01-01T00:00:00Z through 2024-07-01T00:00:00Z exclusive

untouched H2 validation block:
  2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
```

The H2 block may not be used to change either candidate or any gate below.

## Data source and processing

H2 must use newly collected Dukascopy USDJPY bid/ask tick data processed through the same monthly public-FX pipeline used for H1.

Required source conditions for every H2 month:

```text
effective coverage: 100%
final hard errors: 0
bar timeframe used for signals and outcomes: M15
cost spread mode: max_base_public
Rakuten USDJPY base spread: 0.5 pips
DST-aware hard no-trade configuration: enabled
```

The public M1 reference series may not replace Dukascopy bars, entry spreads or P&L.

Aggregate-repair bars must be included when the monthly pipeline uses them.

## Candidate A1 — M15 impulse-confirmed breakout

```text
candidate_id: A1_impulse_breakout_lb3_hold6
symbol: USDJPY
timeframe: M15
entry hours UTC: 13, 14, 15, 16
entry: next M15 bar open
hold: 6 M15 bars
exit: close of the sixth held M15 bar
```

At the close of completed signal bar `t`:

```text
long:
  close[t] > max(high[t-1], high[t-2], high[t-3])
  and range[t] > range[t-1]

short:
  close[t] < min(low[t-1], low[t-2], low[t-3])
  and range[t] > range[t-1]

range[x] = high[x] - low[x]
```

Equality does not pass the range-expansion condition.

## Candidate E3 — 96-bar trend resumption

```text
candidate_id: E3_trend_24h_resumption_hold6
symbol: USDJPY
timeframe: M15
entry hours UTC: 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
trend window: 96 completed M15 bars
entry: next M15 bar open
hold: 6 M15 bars
exit: close of the sixth held M15 bar
```

At the close of completed signal bar `t`:

```text
trend_return = close[t-1] - open[t-96]

long:
  trend_return > 0
  previous bar is bearish: close[t-1] < open[t-1]
  close[t] > high[t-1]

short:
  trend_return < 0
  previous bar is bullish: close[t-1] > open[t-1]
  close[t] < low[t-1]
```

The 96-bar window is a fixed count of completed M15 bars. It is not recalculated as elapsed wall-clock hours around weekends or market closures.

## Hard no-trade rule

The project configuration remains authoritative:

```text
configs/market_sessions/fx_market_sessions_v1.json
```

The hard exclusion is applied to the actual next-bar entry timestamp.

Any entry inside an applicable DST-aware no-trade interval is removed before evaluation.

## Cost scenarios

Default:

```text
spread basis: max(0.5 pips, Dukascopy entry-bar spread_mean_pips)
spread multiplier: 1.0
slippage: 0.0 pips per side
```

Severe:

```text
spread basis: max(0.5 pips, Dukascopy entry-bar spread_mean_pips)
spread multiplier: 3.0
slippage: 0.5 pips per side
```

## Official intervention sensitivity

Official Ministry of Finance USD-selling / JPY-buying operation dates inside H2:

```text
2024-07-11
2024-07-12
```

These are retrospective diagnostic labels, not live entry filters.

Every candidate must be reported both:

1. with all H2 dates included; and
2. with both official dates excluded.

No other H2 date may be removed after results are opened.

## Common H2 promotion gate

Each candidate is judged independently against the same gate.

A candidate passes only if every condition below is met.

1. All six H2 monthly source datasets have 100% effective coverage and zero final hard errors.
2. At least four of six H2 calendar months have positive default-cost average net pips.
3. Aggregate default-cost average net pips is positive.
4. Aggregate default-cost profit factor is at least 1.10.
5. After excluding 2024-07-11 and 2024-07-12, aggregate default-cost average net pips remains positive.
6. After excluding those dates, aggregate default-cost profit factor is at least 1.05.
7. Aggregate default-cost total net pips remains positive after excluding the best two UTC trading days for that candidate.
8. At least 300 retained H2 trades are present in aggregate.
9. Every H2 calendar month contains at least 35 retained trades.
10. Severe-stress aggregate average net pips is no worse than -0.5 pips per trade.
11. Severe-stress aggregate profit factor is at least 0.90.
12. No retained entry violates the project hard no-trade configuration.
13. The candidate implementation passes fixed H1 regression assertions before H2 evaluation is accepted.

Failure of any condition means that candidate does not advance.

The common sample gates are below both H1 populations while still rejecting sparse H2 outcomes:

```text
A1 H1: 391 trades, minimum month 55
E3 H1: 361 trades, minimum month 49
H2 gate: 300 trades, minimum month 35
```

## Candidate comparison

Candidate comparison occurs only after independent gate evaluation.

Required comparison fields:

- monthly default and severe metrics;
- long and short attribution;
- intervention sensitivity;
- best-two-day concentration;
- exact entry overlap between A1 and E3;
- daily net-pips correlation;
- combined trade-day exposure reported descriptively.

A1 and E3 may not be combined into a new entry rule during H2.

If both pass, both advance to Step 4 family comparison. No winner is selected solely from higher H2 total net pips.

If one passes, only that candidate advances.

If neither passes, neither may be repaired using H2 information. Research returns to new independent strategy families.

## Prohibited responses after H2 is opened

The following changes are prohibited:

- changing either entry-hour set;
- changing either hold from six bars;
- changing A1 breakout lookback from three;
- changing A1 range comparison into a fitted ratio, ATR threshold or percentile;
- changing E3 trend window from 96 bars;
- replacing E3 trend return with a moving average or alternative trend estimator;
- changing either candidate to long-only or short-only;
- excluding a losing month;
- excluding any non-official event date;
- reducing the sample-size gates;
- optimizing an exit;
- merging A1 and E3 conditions;
- promoting B3 or any rejected H1 candidate into the H2 set.

## Advancement path

```text
Step 3C: this joint pre-registration
-> Step 3D: collect and evaluate 2024-07 through 2024-12 in one batch
-> Step 4: compare candidates that pass every independent gate
-> separate exit-policy pre-registration
-> exit-policy research
-> MT4 implementation candidate
```

No exit-policy optimization, Core migration or MT4 implementation begins before the H2 artifact is evaluated against this document.