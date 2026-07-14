# FX Session Baseline v1

## Purpose

This workflow is a cross-symbol first-pass market-structure probe. It is not an EA optimizer and must not be used as deployment evidence by itself.

It answers whether simple fixed-hold baseline families retain any net expectancy after:

1. source coverage is complete,
2. aggregate repair has recovered remaining source error hours,
3. dynamic spread cost is applied,
4. project-wide hard no-trade windows are removed before summary aggregation.

## Workflow

Use:

```text
.github/workflows/run_fx_session_baseline_2024_01.yml
```

Inputs:

```text
source_run_id       Required. Symbol tick pilot run containing day artifacts.
symbol              Required. EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, USDCHF.
base_spread_pips    Use auto unless testing an explicit broker-spread assumption.
start_utc_hour      Inclusive coverage-gate start. Default 2024-01-02T00.
end_utc_hour        Exclusive coverage-gate end. Default 2024-02-01T00.
```

`base_spread_pips=auto` uses the Rakuten MT4 broker snapshot assumptions:

| Symbol | Base spread pips |
|---|---:|
| EURUSD | 0.6 |
| USDJPY | 0.5 |
| GBPUSD | 1.2 |
| AUDUSD | 1.2 |
| USDCAD | 2.0 |
| USDCHF | 1.6 |

## Hard no-trade policy

The workflow passes:

```text
--session-config configs/market_sessions/fx_market_sessions_v1.json
```

The current project-wide hard no-trade window is:

```text
America/New_York 16:00-19:00
```

This is intentionally anchored to New York local time so UTC conversion follows US daylight-saving time automatically.

Approximate UTC/JST conversion:

| Regime | UTC hard exclude | JST hard exclude |
|---|---|---|
| NY standard time | 21:00-24:00 | 06:00-09:00 |
| NY daylight time | 20:00-23:00 | 05:00-08:00 |

Any signal in this window is excluded before session summaries. It is written to `excluded_trades.csv` and must not be accepted as a research candidate or live-deployment candidate, even if its gross or default-cost metrics look attractive.

## Cost policy

The runner must use:

```text
--cost-spread-mode max_base_public
```

The cost formula is:

```text
spread_basis = max(broker_base_spread_pips, entry_public_spread_pips)
cost_pips = spread_basis * spread_multiplier + 2 * slippage_pips_per_side
net_pips = gross_pips - cost_pips
```

This prevents low-liquidity sessions from being evaluated with an unrealistically flat broker spread.

## Coverage gate

The workflow combines the original day manifests and aggregate-repair manifest, then requires:

```text
--min-coverage 1.0
--max-hard-errors 0
--expected-records-mode observed
```

A baseline result that did not pass this gate is not a canonical run.

## Output files

Artifact name pattern:

```text
fx-session-baseline-2024-01-<SYMBOL>-<RUN_ID>
```

Important files:

```text
download_summary.json
config.json
summary.csv
trades.csv
excluded_trades.csv
top_default_cost.csv
README.md
```

## Initial interpretation rule

A candidate can advance only if it satisfies all of the following:

1. It is outside hard no-trade windows.
2. It remains positive after `max_base_public` cost mode.
3. The same family/session/timeframe is not dependent on all-hours aggregation.
4. It is not supported only by a tiny trade count.
5. It survives at least part of the severe spread/slippage stress grid.
6. It will be tested on additional months before any EA implementation decision.

For USDJPY 2024-01, the current retained candidate family is M5 / UTC 13-16 / pullback continuation, but this is still a research candidate only. It requires additional-month validation.
