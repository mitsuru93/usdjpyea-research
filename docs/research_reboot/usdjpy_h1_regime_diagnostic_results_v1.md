# USDJPY H1 Regime Diagnostic Results v1

## Scope

This report records the post-Q2 diagnostic for the fixed candidates across 2024-01 through 2024-06.

No parameter search was performed in this phase.

Canonical baseline runs:

```text
2024-01: 29307131333
2024-02: 29383810487
2024-03: 29421329471
2024-04: 29455059447
2024-05: 29469227483
2024-06: 29475803893
```

Fixed candidates:

```text
A: M5 pullback continuation
   session: entry UTC 13-16
   pullback_min_pips: 2
   trend_lookback_bars: 12
   trend_min_pips: 10
   hold_bars: 6

B: M15 breakout close follow-through
   session: entry UTC 13-16
   lookback_bars: 3
   hold_bars: 6
```

Costs use the existing baseline convention:

```text
default: max(Rakuten base spread 0.5 pips, public spread)
severe: spread x3 plus 0.5 pips slippage per side
```

## M5 pullback conclusion

The M5 pullback candidate remains rejected.

The Q1-to-Q2 break is not repaired by the descriptive local-state fields examined in this diagnostic:

- prior 15, 30, 60, 180 and 360 minute range;
- prior directional efficiency;
- prior maximum five-minute shock;
- spread / prior-60-minute-range ratio;
- 6-hour, 12-hour or 24-hour directional alignment;
- long-only or short-only interpretation.

The principal observed change is weaker post-entry continuation:

```text
median MFE, Q1: 9.975 pips
median MFE, Q2: 6.550 pips

mean holding-window range, Q1: 23.697 pips
mean holding-window range, Q2: 18.605 pips
```

The failure remains visible across descriptive quartiles of prior 60-minute efficiency, range and shock. Higher-timeframe directional alignment also fails to restore Q2 expectancy.

Therefore no M5 pullback regime filter is promoted from H1.

## M15 breakout diagnostic

The unfiltered M15 breakout candidate remains rejected, but the diagnostic identifies one mechanism that is eligible for an untouched-period test:

```text
breakout direction aligned with the completed prior 24-hour price direction
```

Operational diagnostic definition:

```text
long breakout: prior 24-hour return > 0
short breakout: prior 24-hour return < 0
```

The 24-hour direction is known at the signal-bar close and therefore does not use future information.

### H1 monthly results: 24-hour aligned subset

Default cost:

| Month | Trades | Avg net pips | Total net pips | PF |
|---|---:|---:|---:|---:|
| 2024-01 | 77 | -0.280 | -21.57 | 0.978 |
| 2024-02 | 72 | +4.113 | +296.16 | 1.749 |
| 2024-03 | 50 | -0.394 | -19.69 | 0.933 |
| 2024-04 | 62 | +6.093 | +377.78 | 2.202 |
| 2024-05 | 67 | +3.499 | +234.45 | 1.637 |
| 2024-06 | 61 | +0.161 | +9.80 | 1.025 |

H1 aggregate:

```text
trades: 389
positive months: 4 / 6
avg net pips: +2.254
total net pips: +876.92
profit factor: 1.321
```

The two negative months are near flat rather than large failures.

### Intervention sensitivity

The official Q2 intervention operations were dated 2024-04-29 and 2024-05-01. The second associated UTC-market shock is also reviewed on 2024-05-02.

Excluding the two observed UTC shock dates, 2024-04-29 and 2024-05-02:

```text
trades: 381
avg net pips: +1.563
total net pips: +595.59
profit factor: 1.223
```

Severe stress after excluding those dates:

```text
avg net pips: -0.362
total net pips: -137.90
profit factor: 0.955
```

Therefore the aligned subset remains positive without the two intervention-shock dates. It is not solely an intervention artifact.

### Daily concentration

After excluding the two intervention-shock dates:

```text
total net pips: +595.59
result excluding the best two remaining UTC days: +187.29 pips
positive active days: 46
negative active days: 67
```

The H1 aggregate does not depend exclusively on the best two days.

### Opposed subset

The H1 breakout signals opposed to the prior 24-hour direction are negative after excluding the two intervention-shock dates:

```text
trades: 206
avg net pips: -1.047
total net pips: -215.60
profit factor: 0.869
```

This supports a market-structure hypothesis: a local M15 close breakout is more likely to continue when it agrees with the preceding daily directional move.

## Interpretation limit

The 24-hour alignment condition was discovered in H1 and is not validated evidence.

It must not be treated as an accepted strategy, an EA specification or a Core implementation requirement.

The only permitted next step is a pre-registered test on an untouched period.

## Next action

Pre-register and test the exact aligned M15 breakout candidate on:

```text
2024-07-01 through 2024-12-31
```

The H2 result must be evaluated against fixed gates before any Dukascopy tick validation, exit research or MT4 implementation begins.
