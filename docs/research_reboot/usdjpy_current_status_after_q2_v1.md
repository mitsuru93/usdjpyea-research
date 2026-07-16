# USDJPY Research Status After Q2 v1

## Last verified stage

The last verified research stage is the completion of the monthly USDJPY session-baseline runs for 2024-01 through 2024-06.

Canonical baseline runs:

```text
2024-01: 29307131333
2024-02: 29383810487
2024-03: 29421329471
2024-04: 29455059447
2024-05: 29469227483
2024-06: 29475803893
```

All six baseline artifacts were generated from source data with 100% effective coverage and zero final hard errors.

## Verified family decisions

### M5 pullback continuation

Fixed representative:

```text
timeframe: M5
session: UTC 13-16
pullback_min_pips: 2
trend_lookback_bars: 12
trend_min_pips: 10
hold_bars: 6
```

Monthly default-cost average net pips:

```text
2024-01: +2.022
2024-02: +2.164
2024-03: +1.912
2024-04: +0.430
2024-05: -1.902
2024-06: -0.767
```

Q2 aggregate:

```text
trades: 423
avg_net_pips: -0.888
total_net_pips: -375.48
profit_factor: 0.827
positive_months: 1 / 3
```

The pre-registered Q2 promotion gate was not met.

### M15 breakout close follow-through

Fixed watchlist representative:

```text
timeframe: M15
session: UTC 13-16
lookback_bars: 3
hold_bars: 6
```

Monthly default-cost average net pips:

```text
2024-01: +2.100
2024-02: +2.909
2024-03: -1.365
2024-04: +3.493
2024-05: -0.240
2024-06: -1.216
```

This family did not reproduce consistently and was not promoted.

## Current phase

```text
Phase: post-Q2 failure diagnosis
Development data allowed: 2024-01 through 2024-06 only
Later untouched period: not yet selected for testing
EA implementation: not started
Exit-policy optimization: not started
```

The current phase is diagnostic. It is not a seventh monthly baseline run and it is not a July-December performance test.

## Work now being performed

The two fixed candidates are analyzed without changing their parameters.

Required diagnostic outputs:

1. Monthly attribution.
2. Long / short attribution.
3. Daily profit and loss concentration.
4. Official intervention-event sensitivity.
5. Q1 versus Q2 market-state attribution using source M5 and M15 bars:
   - prior-session realized range;
   - primary-session realized range;
   - directional efficiency;
   - spread / range ratio;
   - pre-entry trend magnitude;
   - prior-bar and prior-hour shock size.

The purpose is to determine whether the Q1-to-Q2 difference has a repeated market mechanism. The purpose is not to find a profitable threshold inside January-June.

## Decision after diagnosis

There are only two permitted outcomes.

### Outcome A: repeated mechanism found

A new strategy family or regime hypothesis may be written only when the mechanism:

- appears across multiple months;
- is not created by one intervention episode or one extreme day;
- is observable before entry;
- can be defined without selecting a profitable threshold from the same sample.

The hypothesis, exact candidate and promotion gate must then be committed before any later period is inspected.

### Outcome B: no repeated mechanism found

The pullback and breakout research branch is closed. A different family with an independent market rationale must be designed.

## Later-period rule

2024-07 through 2024-12 has not been accepted as a verified result block in this project.

No July-December result may be treated as evidence until:

1. the current January-June diagnosis is completed;
2. a candidate is specified;
3. the later test interval and gates are committed in advance;
4. the corresponding workflow is actually run;
5. its GitHub Actions artifact is inspected.

## Invalid H2 material removed

Unverified H1 diagnostic results, the unsupported 24-hour-alignment candidate, its H2 result record, screen tool and workflow were removed from the repository.

The repository is therefore reset to the verified January-June state plus the post-Q2 diagnostic plan.
