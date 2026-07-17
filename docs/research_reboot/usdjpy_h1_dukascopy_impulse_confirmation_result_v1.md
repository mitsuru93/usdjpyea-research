# USDJPY H1 Dukascopy Impulse Confirmation Result v1

## Run

```text
workflow: Run USDJPY H1 Dukascopy Impulse Confirmation
run_id: 29543895841
head_sha: 9ff003d9261a4e9376f00e55165e16e72a72114c
artifact: usdjpy-h1-dukascopy-impulse-confirmation-29543895841
artifact_digest: sha256:75ca6f8c86f013a4e8a3d8962d4c00d80aebcef8d21e95dd182370be38558999
```

All workflow steps completed successfully.

## Fixed candidate

```text
symbol: USDJPY
timeframe: M15
family: breakout_close_followthrough
breakout lookback: 3 completed M15 bars
impulse confirmation: signal-bar range > previous completed M15-bar range
entry session: UTC 13, 14, 15 or 16
entry: next M15 bar open
hold: 6 M15 bars
```

P&L and spreads come from the six canonical monthly Dukascopy baseline trade artifacts. The impulse condition is computed on the original M15 source bars from the corresponding source runs, including aggregate-repair bars used by the baseline workflow.

## Source-bar coverage

| Month | Breakout trades | Matched signal bars | Missing | M15 rows | M15 files |
|---|---:|---:|---:|---:|---:|
| 2024-01 | 114 | 114 | 0 | 2080 | 23 |
| 2024-02 | 114 | 114 | 0 | 1984 | 22 |
| 2024-03 | 85 | 85 | 0 | 1964 | 22 |
| 2024-04 | 95 | 95 | 0 | 2064 | 23 |
| 2024-05 | 103 | 103 | 0 | 2148 | 24 |
| 2024-06 | 87 | 87 | 0 | 1872 | 20 |

Coverage is complete for all 598 canonical breakout trades.

## Monthly default-cost result

| Month | Trades | Avg net pips | Total net pips | PF |
|---|---:|---:|---:|---:|
| 2024-01 | 73 | +5.479 | +399.98 | 1.510 |
| 2024-02 | 79 | +3.373 | +266.49 | 1.489 |
| 2024-03 | 55 | -2.227 | -122.47 | 0.622 |
| 2024-04 | 63 | +3.955 | +249.17 | 1.795 |
| 2024-05 | 66 | +0.535 | +35.30 | 1.080 |
| 2024-06 | 55 | -0.732 | -40.25 | 0.900 |

Aggregate:

```text
trades: 391
positive months: 4 / 6
win rate: 52.43%
avg net pips: +2.016
total net pips: +788.22
profit factor: 1.281
```

Quarter split:

```text
Q1 avg net pips: +2.628
Q2 avg net pips: +1.327
```

The impulse-confirmed subset is positive in both Q1 and Q2.

## Complement population

Breakout signals without range expansion:

```text
trades: 207
positive months: 3 / 6
avg net pips: -0.637
total net pips: -131.92
profit factor: 0.916
Q1 avg net pips: -0.840
Q2 avg net pips: -0.424
```

The range-expansion rule separates the positive subset from a negative complement on the same source and fixed breakout population.

## Cost stress

Severe stress uses the existing baseline convention:

```text
max(0.5-pip base spread, public entry spread) x 3
plus 0.5 pips slippage per side
```

Aggregate severe result:

```text
avg net pips: -0.153
total net pips: -59.85
profit factor: 0.982
```

Monthly severe results are positive in January, February and April and negative in March, May and June. The aggregate remains close to flat under severe stress rather than collapsing to the level of the non-impulse population.

## Intervention sensitivity

Diagnostic dates excluded:

```text
2024-04-29
2024-05-01
2024-05-02
```

Result after exclusion:

```text
trades: 377
avg net pips: +1.458
total net pips: +549.68
profit factor: 1.204
```

The result remains positive without the 2024 Q2 intervention episode.

## Daily concentration

Best two UTC days:

```text
2024-01-31: +314.82 pips
2024-02-02: +221.82 pips
```

Aggregate result after excluding those two days:

```text
+251.58 pips
```

The development result is concentrated, but it does not change sign after removal of the two strongest days.

## Direction attribution

Direction performance varies by month. Long and short are each positive in some months and negative in others. No direction-only rule is promoted.

Notable pattern:

```text
2024-05 long:  +2.471 pips/trade
2024-05 short: -1.288 pips/trade
2024-06 long:  +2.689 pips/trade
2024-06 short: -6.270 pips/trade
```

This is diagnostic information only. The H2 candidate remains two-sided.

## Decision

The exact-source confirmation passes the Step 3B promotion requirement.

```text
M5 pullback:
  closed in current form

Unfiltered M15 breakout:
  remains rejected

M15 impulse-confirmed breakout:
  promoted to a pre-registered untouched-period test
```

This is development-sample evidence, not an accepted EA. Exit-policy research and MT4/Core implementation remain prohibited until the candidate passes its later-period gate on newly collected Dukascopy bid/ask data.
