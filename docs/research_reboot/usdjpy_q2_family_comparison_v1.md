# USDJPY Q2 Family Comparison v1

## Scope

This report compares the fixed USDJPY session-baseline families across 2024-04, 2024-05, and 2024-06.

Canonical baseline artifacts:

| Month | Baseline run | Artifact |
|---|---:|---|
| 2024-04 | 29455059447 | `fx-session-baseline-2024-04-USDJPY-29455059447` |
| 2024-05 | 29469227483 | `fx-session-baseline-2024-05-USDJPY-29469227483` |
| 2024-06 | 29475803893 | `fx-session-baseline-2024-06-USDJPY-29475803893` |

All three runs used:

```text
symbol: USDJPY
base_spread_pips: 0.5
cost_spread_mode: max_base_public
session_config: configs/market_sessions/fx_market_sessions_v1.json
hard_no_trade_windows_enabled: true
```

Source coverage was 100% with zero hard errors in all three months.

## Pre-registered Q2 gate

The gate was defined in `usdjpy_q1_family_comparison_v1.md` before Q2 results were known.

Promotion criteria for the retained M5 pullback family were:

1. Positive under default cost in at least two of three Q2 months.
2. The fixed band `trend_lookback=12`, `trend_min=6..10`, `pullback_min=1..2`, `hold=6` remains competitive.
3. Severe stress remains flat to mildly negative rather than deeply negative.
4. Daily concentration does not worsen materially versus Q1.
5. The edge remains primary-session driven.

## Decision summary

The Q1 retained family does not pass the Q2 gate.

```text
M5 / primary_utc_13_16_jst_22_01 / pullback_continuation
```

Fixed representative:

```json
{"pullback_min_pips": 2.0, "trend_lookback_bars": 12, "trend_min_pips": 10.0}
```

```text
hold_bars = 6
```

The M15 breakout watchlist family also fails to reproduce in Q2.

```text
M15 / primary_utc_13_16_jst_22_01 / breakout_close_followthrough
lookback_bars = 3
hold_bars = 6
```

Neither family advances to exit-policy research or EA implementation.

## M5 pullback: fixed representative

Default scenario:

```text
spread_x1_slip_0
```

| Month | Trades | Avg gross | Avg cost | Avg net | Total net | PF |
|---|---:|---:|---:|---:|---:|---:|
| 2024-04 | 110 | +1.015 | 0.585 | +0.430 | +47.27 | 1.108 |
| 2024-05 | 161 | -1.318 | 0.584 | -1.902 | -306.25 | 0.701 |
| 2024-06 | 152 | -0.200 | 0.567 | -0.767 | -116.51 | 0.836 |

Q2 aggregate:

```text
trades: 423
avg_net_pips: -0.888
total_net_pips: -375.48
positive_months: 1 / 3
```

The representative fails because May and June are negative, and June is already negative before cost.

## M5 pullback parameter-band check

Default-cost average net pips per trade:

| Pullback minimum | Trend minimum | 2024-04 | 2024-05 | 2024-06 |
|---:|---:|---:|---:|---:|
| 1 | 6 | +0.326 | -1.234 | -0.389 |
| 2 | 6 | +0.179 | -1.271 | -0.610 |
| 1 | 10 | +0.434 | -1.894 | -0.522 |
| 2 | 10 | +0.430 | -1.902 | -0.767 |

The failure is not isolated to one parameter point. The complete pre-registered band is negative in both May and June.

## Severe stress

Scenario:

```text
spread_x3_slip_0.5
```

Fixed M5 pullback representative:

| Month | Avg net | PF |
|---|---:|---:|
| 2024-04 | -1.740 | 0.673 |
| 2024-05 | -4.070 | 0.469 |
| 2024-06 | -2.869 | 0.511 |

Q2 aggregate:

```text
avg_net_pips: -3.033
total_net_pips: -1282.75
```

This is a deep cost failure rather than a flat stress result.

## M15 breakout watchlist

Fixed watchlist parameters:

```json
{"lookback_bars": 3}
```

```text
hold_bars = 6
```

Default-cost result:

| Month | Trades | Avg net | Total net | PF |
|---|---:|---:|---:|---:|
| 2024-04 | 95 | +3.493 | +331.80 | 1.716 |
| 2024-05 | 103 | -0.240 | -24.71 | 0.965 |
| 2024-06 | 87 | -1.216 | -105.75 | 0.826 |

Q2 has only one positive month. The family is not promoted.

## Official yen-buying intervention dates in the sample

The Ministry of Finance reports the following USD-selling / JPY-buying intervention operations in Q2 2024:

| Official operation date | Amount |
|---|---:|
| 2024-04-29 | JPY 5,918.5 billion |
| 2024-05-01 | JPY 3,870.0 billion |

Official source:

```text
https://www.mof.go.jp/english/policy/international_policy/reference/feio/quarter/2024_2Qe.html
```

Date interpretation note:

- The Ministry of Finance publishes an official operation date, not an intraday UTC interval.
- The second market shock is visible in UTC/Japan price data around the following calendar date, so event sensitivity must not equate the MOF date mechanically with a UTC date filter.
- These dates are diagnostic labels, not ex-ante trade filters. Official confirmation is published after the event.

## Intervention sensitivity

M15 breakout is materially intervention-sensitive.

Primary-session default-cost daily contribution around the intervention episodes:

```text
2024-04-29 UTC date: +141.35 pips
2024-05-02 UTC date: +134.96 pips
```

The Q2 M15 breakout aggregate is:

```text
total_net_pips: +201.34
avg_net_pips: +0.706
```

Removing the two UTC dates associated with the two intervention shocks changes it to:

```text
total_net_pips: -74.97
avg_net_pips: -0.274
```

Therefore the positive Q2 aggregate for M15 breakout is not independent of intervention shocks.

M5 pullback is different. Its Q2 aggregate is already negative, and removing intervention-associated dates makes it more negative. The M5 pullback failure is not explained by intervention contamination.

## Final Q2 decision

```text
M5 pullback continuation:
  reject in current form

M15 breakout close follow-through:
  reject in current form

exit-policy optimization:
  do not start

EA implementation:
  do not start
```

## Next phase

The next phase is diagnostic, not parameter optimization.

Required work:

1. Attribute Q1 versus Q2 performance by volatility, trend persistence, spread/range ratio, direction, and day concentration.
2. Label known intervention events separately from normal market regimes.
3. Do not create a live intervention filter from ex-post official dates.
4. Use the diagnostic only to formulate a new family or regime hypothesis.
5. Pre-register that hypothesis before testing on a later untouched period.
