# USDJPY Q1 Family Comparison v1

## Scope

This report compares USDJPY session-baseline results across 2024-01, 2024-02, and 2024-03.

Canonical baseline artifacts:

| Month | Baseline run | Artifact |
|---|---:|---|
| 2024-01 | 29307131333 | `fx-session-baseline-2024-01-USDJPY-29307131333` |
| 2024-02 | 29383810487 | `fx-session-baseline-2024-02-USDJPY-29383810487` |
| 2024-03 | 29421329471 | `fx-session-baseline-2024-03-USDJPY-29421329471` |

All three runs used:

```text
symbol: USDJPY
base_spread_pips: 0.5
cost_spread_mode: max_base_public
session_config: configs/market_sessions/fx_market_sessions_v1.json
hard_no_trade_windows_enabled: true
```

Source coverage status:

| Month | Effective coverage | Downloaded | No ticks | Hard errors | Hard-excluded signal trades |
|---|---:|---:|---:|---:|---:|
| 2024-01 | 100.0% | 520 | 8 | 0 | 8,997 |
| 2024-02 | 100.0% | 496 | 8 | 0 | 5,464 |
| 2024-03 | 100.0% | 491 | 13 | 0 | 5,574 |

## Decision summary

The Q1 retained family is:

```text
M5 / primary_utc_13_16_jst_22_01 / pullback_continuation
```

The most stable parameter band is:

```text
trend_lookback_bars: 12
trend_min_pips:      6 to 10
pullback_min_pips:   1 to 2
hold_bars:           6
```

The preferred current representative is the stricter variant:

```json
{"pullback_min_pips": 2.0, "trend_lookback_bars": 12, "trend_min_pips": 10.0}
hold_bars = 6
```

Rationale:

1. It is positive in all three Q1 months under default `max_base_public` cost.
2. It performs best or near-best inside the retained M5 pullback family.
3. It is not an all-hours strategy; primary-session concentration remains the research basis.
4. Severe stress weakens it to flat/slightly negative, so it is not deployment evidence yet.

The secondary/watchlist family is:

```text
M15 / primary_utc_13_16_jst_22_01 / breakout_close_followthrough
```

This family is not currently promoted because it is strong in February but fails in March.

## Primary-session default-cost comparison

Scenario:

```text
spread_x1_slip_0
```

### M5 pullback: January exact candidate

Parameters:

```json
{"pullback_min_pips": 1.0, "trend_lookback_bars": 12, "trend_min_pips": 6.0}
hold_bars = 6
```

| Month | Trades | Win rate | Avg gross | Avg cost | Avg net | Total net | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024-01 | 349 | 54.4% | +3.020 | 0.645 | +2.375 | +828.84 | 1.373 |
| 2024-02 | 254 | 52.4% | +0.838 | 0.598 | +0.240 | +61.05 | 1.046 |
| 2024-03 | 258 | 55.0% | +1.779 | 0.561 | +1.218 | +314.14 | 1.383 |

Interpretation: the exact January candidate survives March but is too weak in February.

### M5 pullback: stricter representative

Parameters:

```json
{"pullback_min_pips": 2.0, "trend_lookback_bars": 12, "trend_min_pips": 10.0}
hold_bars = 6
```

| Month | Trades | Win rate | Avg gross | Avg cost | Avg net | Total net | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024-01 | 244 | 55.3% | +2.671 | 0.649 | +2.022 | +493.33 | 1.287 |
| 2024-02 | 129 | 55.8% | +2.766 | 0.602 | +2.164 | +279.11 | 1.483 |
| 2024-03 | 135 | 57.8% | +2.473 | 0.562 | +1.912 | +258.07 | 1.646 |

Interpretation: this is the best Q1 representative for the M5 pullback family. It is lower frequency than the January exact candidate, but more stable across months.

### M5 pullback: stricter trend, looser pullback

Parameters:

```json
{"pullback_min_pips": 1.0, "trend_lookback_bars": 12, "trend_min_pips": 10.0}
hold_bars = 6
```

| Month | Trades | Win rate | Avg gross | Avg cost | Avg net | Total net | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024-01 | 292 | 53.8% | +2.700 | 0.647 | +2.053 | +599.43 | 1.302 |
| 2024-02 | 175 | 54.3% | +1.957 | 0.599 | +1.359 | +237.76 | 1.310 |
| 2024-03 | 171 | 55.6% | +2.439 | 0.562 | +1.878 | +321.07 | 1.664 |

Interpretation: this variant is also valid within the retained parameter band. The final representative should be chosen after Q2 expansion and daily-return concentration review.

### M15 breakout: February winner, March failure

Parameters:

```json
{"lookback_bars": 3}
hold_bars = 6
```

| Month | Trades | Win rate | Avg gross | Avg cost | Avg net | Total net | PF |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2024-01 | 114 | 53.5% | +2.742 | 0.642 | +2.100 | +239.43 | 1.179 |
| 2024-02 | 114 | 56.1% | +3.498 | 0.590 | +2.909 | +331.59 | 1.432 |
| 2024-03 | 85 | 50.6% | -0.817 | 0.548 | -1.365 | -116.06 | 0.766 |

Interpretation: M15 breakout is a watchlist family, not the Q1 lead. The March failure prevents promotion.

## Severe-stress comparison

Scenario:

```text
spread_x3_slip_0.5
```

| Family / params | 2024-01 avg net / PF | 2024-02 avg net / PF | 2024-03 avg net / PF | Interpretation |
|---|---:|---:|---:|---|
| M5 PB p1 / trend6 / hold6 | +0.084 / 1.011 | -1.955 / 0.694 | -0.905 / 0.788 | Too cost-sensitive in February/March. |
| M5 PB p2 / trend10 / hold6 | -0.277 / 0.966 | -0.041 / 0.993 | -0.212 / 0.947 | Near flat/slightly negative under severe stress; retained but not deployment evidence. |
| M5 PB p1 / trend10 / hold6 | -0.241 / 0.970 | -0.838 / 0.847 | -0.246 / 0.937 | Acceptable family member but weaker stress profile. |
| M15 BO lookback3 / hold6 | -0.183 / 0.986 | +0.730 / 1.094 | -3.462 / 0.504 | February-only strength; March failure is severe. |

## Daily concentration: strict M5 pullback representative

Parameters:

```json
{"pullback_min_pips": 2.0, "trend_lookback_bars": 12, "trend_min_pips": 10.0}
hold_bars = 6
```

| Month | Active days | Positive days | Negative days | Total net | Best days | Worst days |
|---|---:|---:|---:|---:|---|---|
| 2024-01 | 22 | 12 | 10 | +493.33 | 2024-01-31 +160.85; 2024-01-09 +147.25; 2024-01-08 +114.46 | 2024-01-30 -126.76; 2024-01-24 -66.25; 2024-01-26 -47.81 |
| 2024-02 | 19 | 13 | 6 | +279.11 | 2024-02-13 +86.12; 2024-02-02 +63.28; 2024-02-20 +57.04 | 2024-02-23 -51.56; 2024-02-08 -33.24; 2024-02-29 -21.52 |
| 2024-03 | 21 | 12 | 9 | +258.07 | 2024-03-21 +78.14; 2024-03-08 +58.25; 2024-03-06 +40.15 | 2024-03-28 -17.74; 2024-03-01 -15.02; 2024-03-04 -13.94 |

Interpretation: January has stronger concentration risk than February/March. Q2 expansion should check whether the strict M5 pullback representative remains supported without one or two extreme days.

## Session interpretation

The result must remain interpreted as session-dependent.

Current decision field:

```text
primary_utc_13_16_jst_22_01
```

Do not promote all-hours rows. All-hours can be used only as a diagnostic field. A strategy that is positive only because of all-hours aggregation is not retained.

## Implementation note: static excluded session label

The runner still has an old diagnostic session label:

```text
excluded_utc_21_23_jst_06_08
```

This label should not be used after the project-wide hard no-trade window became New-York-local and DST-aware.

Authoritative exclusion source:

```text
excluded_trades.csv
hard_no_trade_windows in configs/market_sessions/fx_market_sessions_v1.json
```

Next runner change: remove the static excluded session from `DEFAULT_SESSIONS` and rely on `excluded_trades.csv` for hard-excluded signal review.

## Q2 gate

Before EA implementation, run the same family comparison for 2024-04, 2024-05, and 2024-06.

Promotion criteria for M5 pullback:

1. The family remains positive in at least two of three Q2 months under default cost.
2. The stricter band `trend_lookback=12`, `trend_min=6..10`, `pullback_min=1..2`, `hold=6` remains competitive.
3. Severe stress remains flat to mildly negative rather than deeply negative.
4. Daily concentration does not worsen materially versus Q1.
5. The result remains primary-session driven and not all-hours driven.

If these criteria pass, the next phase is not full EA implementation. The next phase is exit-policy research for the retained family.
