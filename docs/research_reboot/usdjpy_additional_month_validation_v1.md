# USDJPY Additional-Month Validation v1

## Purpose

USDJPY 2024-01 produced a retained research candidate:

```text
M5 / UTC 13-16 / pullback continuation
```

This is not deployment evidence. The next gate is additional-month validation under the same project-wide rules:

1. complete source coverage after aggregate repair,
2. dynamic spread cost using `max_base_public`,
3. hard no-trade exclusion from `configs/market_sessions/fx_market_sessions_v1.json`,
4. M5/M15 baseline families only,
5. no all-hours adoption.

## Source tick pilots

Run these workflows first.

### USDJPY 2024-02

```text
Run Public FX Tick Pilot 2024-02 USDJPY
```

Expected source range:

```text
start_utc_hour: 2024-02-01T00
end_utc_hour:   2024-03-01T00
pilot_tag:      pilot-2024-02-USDJPY
```

### USDJPY 2024-03

```text
Run Public FX Tick Pilot 2024-03 USDJPY
```

Expected source range:

```text
start_utc_hour: 2024-03-01T00
end_utc_hour:   2024-04-01T00
pilot_tag:      pilot-2024-03-USDJPY
```

Both wrappers call:

```text
.github/workflows/reusable_public_fx_tick_symbol_pilot_monthly.yml
```

The reusable monthly workflow generates weekday day-chunks from the start/end UTC boundaries. It does not require hand-maintained day lists.

A source tick pilot run is canonical only if its aggregate job passes:

```text
--min-coverage 1.0
--max-hard-errors 0
--expected-records-mode observed
```

## Monthly session baseline

After each source tick pilot succeeds, run:

```text
Run FX Session Baseline Monthly
```

### 2024-02 baseline inputs

```text
source_run_id:    <2024-02 tick pilot run id>
symbol:           USDJPY
pilot_tag:        pilot-2024-02-USDJPY
month_tag:        2024-02
base_spread_pips: auto
start_utc_hour:   2024-02-01T00
end_utc_hour:     2024-03-01T00
```

### 2024-03 baseline inputs

```text
source_run_id:    <2024-03 tick pilot run id>
symbol:           USDJPY
pilot_tag:        pilot-2024-03-USDJPY
month_tag:        2024-03
base_spread_pips: auto
start_utc_hour:   2024-03-01T00
end_utc_hour:     2024-04-01T00
```

## Interpretation rule

The January candidate advances only if February and March do not contradict it.

Minimum evidence to continue:

1. The same family remains positive in the primary session under default cost.
2. Severe stress does not collapse into a large negative expectancy.
3. The result is not explained by one or two extreme days.
4. All hard no-trade window signals remain excluded.
5. `all_hours` remains a non-decision field; it must not be used to adopt a strategy.

Failure condition:

If February and March both fail the same M5 / UTC13-16 / pullback continuation family under default cost, the January result is treated as month-specific rather than a durable candidate.
