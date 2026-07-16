# USDJPY M15 Breakout 24h Alignment H2 Result v1

## Test integrity

The candidate and gates were pre-registered in:

```text
docs/research_reboot/usdjpy_m15_breakout_24h_alignment_h2_prereg_v1.md
```

Pre-registration commit:

```text
de4cba79cb49244992e7b42cc1fefddc2a55ab11
```

The H2 result was not reviewed before that commit.

Test period:

```text
2024-07-01T00:00:00Z
through
2025-01-01T00:00:00Z exclusive
```

Dataset:

```text
usdjpy_m1_2024_01_02_to_2026_02_18_public_main
sha256: 16dc2cab7d46504082be01520c6d5b95fa7bfa9089947afb6f22e4cb1edde6ac
```

The MT4 server-time DT field was converted with `Europe/Helsinki` EET/EEST handling before UTC M15 resampling.

## Implementation-equivalence check

Before interpreting H2, the exact public-M1 implementation was rerun on H1 2024.

H1 public-M1 result:

```text
trades: 407
positive months: 4 / 6
avg net pips: +1.957
total net pips: +796.40
profit factor: 1.273
severe avg net pips: -0.043
severe profit factor: 0.995
result excluding best two UTC days: +388.20 pips
```

This reproduces the development-period pattern closely enough to use the implementation for the pre-registered H2 screen. It does not reproduce every Dukascopy trade because the source price series differs, but it reproduces the aggregate hypothesis direction before H2 is examined.

## Fixed H2 candidate

```text
M15 breakout close follow-through
lookback: 3
prior 24-hour alignment: 96 completed M15 bars
entry hours UTC: 13, 14, 15, 16
entry: next bar open
hold: 6 M15 bars
base cost: 0.5 pips
severe cost: 2.5 pips
```

No candidate parameter was changed after pre-registration.

## Monthly default-cost result

| Month | Trades | Avg net pips | Total net pips | PF |
|---|---:|---:|---:|---:|
| 2024-07 | 57 | -4.025 | -229.40 | 0.645 |
| 2024-08 | 64 | -5.950 | -380.80 | 0.646 |
| 2024-09 | 74 | -4.861 | -359.70 | 0.666 |
| 2024-10 | 74 | +3.712 | +274.70 | 1.561 |
| 2024-11 | 69 | -4.535 | -312.90 | 0.670 |
| 2024-12 | 84 | -3.679 | -309.00 | 0.686 |

Only October is positive.

## Aggregate result

Default cost:

```text
trades: 422
positive months: 1 / 6
win rate: 48.58%
avg gross pips: -2.621
avg net pips: -3.121
total net pips: -1317.10
profit factor: 0.748
```

The result is negative before cost. Transaction cost is not the primary cause of failure.

Severe stress:

```text
avg net pips: -5.121
total net pips: -2161.10
profit factor: 0.619
```

## Intervention sensitivity

Official Ministry of Finance intervention dates in the test block:

```text
2024-07-11
2024-07-12
```

Excluding both dates:

```text
trades: 420
avg net pips: -2.940
total net pips: -1234.70
profit factor: 0.760
```

The failure is not caused by the two official intervention dates.

## Daily concentration

Best two UTC days:

```text
2024-10-21: +202.30 pips
2024-09-04: +193.70 pips
```

Result excluding those two days:

```text
-1713.10 pips
```

The candidate is not a positive strategy obscured by concentration. Removing its best days worsens an already negative result.

## Direction split

Direction was not consistently responsible for the failure.

Examples:

```text
2024-07: short -213.90, long -15.50
2024-08: short -131.70, long -249.10
2024-09: short +174.30, long -534.00
2024-10: short -86.20, long +360.90
2024-11: short -378.80, long +65.90
2024-12: short -180.80, long -128.20
```

A long-only or short-only conversion after seeing these results would be an impermissible post-hoc change and would not address the unstable monthly direction dependence.

## Gate decision

Passed sample-size checks:

```text
aggregate trades >= 180
each month trades >= 15
```

Failed performance and robustness checks:

```text
positive months >= 4
aggregate average net > 0
aggregate PF >= 1.10
intervention-excluded average net > 0
intervention-excluded PF >= 1.05
result excluding best two days > 0
severe average net >= -0.5
severe PF >= 0.90
```

Final gate result:

```text
FAIL
```

## Research decision

The current M15 breakout line is closed.

```text
M15 breakout lookback 3:
  rejected

24-hour directional alignment:
  rejected as a rescue condition

Dukascopy H2 tick validation:
  do not start

exit-policy research:
  do not start

EA / Core implementation:
  do not start
```

The H2 period must not be reused immediately to tune another breakout threshold, holding period, alignment lookback or direction rule.

## Next research branch

The next candidate must be a different strategy family with an independently specified market mechanism.

It must be selected from market-structure evidence before its later untouched test period is opened. The failed Pullback and Breakout families must not be relabeled or inverted to manufacture a new candidate.
