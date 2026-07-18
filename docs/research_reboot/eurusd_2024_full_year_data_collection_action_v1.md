# EURUSD 2024 Full-Year Data Collection Action v1

## Purpose

Create one manually dispatched GitHub Actions run that collects and audits the full 2024 EURUSD public market-data block for later EA research.

This action is source-data infrastructure only. It does not define an EURUSD strategy, candidate registry, broker spread, cost gate or promotion decision.

## Workflow

```text
name: Run EURUSD 2024 Full-Year Public Data Collection
path: .github/workflows/run_eurusd_2024_full_year_collect.yml
```

The workflow uses:

```text
.github/workflows/reusable_public_fx_tick_symbol_pilot_monthly_v2.yml
```

## Source and outputs

```text
symbol: EURUSD
source: Dukascopy public BI5 bid/ask ticks
year: 2024-01-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
timeframes: M1, M5, M15, H1
```

The final annual artifact contains:

- combined terminal source manifest;
- annual and twelve monthly fixed-weekday coverage audits;
- any annual aggregate-repair tick and bar outputs;
- deterministic annual M1/M5/M15/H1 bar files;
- input-file manifest and SHA-256 hashes;
- monthly row counts;
- annual bar validation summary;
- run metadata.

Artifact name:

```text
public-fx-data-EURUSD-2024-annual-<run_id>-a<run_attempt>
```

Retention:

```text
90 days
```

## Parallelism

The twelve monthly collectors run in three waves:

```text
wave 1: January-April
wave 2: May-August
wave 3: September-December
```

Four months run concurrently. Each monthly collector processes one weekday chunk at a time, keeping the intended total collection concurrency near four rather than opening twelve independent four-way matrices.

The run-attempt suffix is included in monthly pilot tags so rerun artifacts remain distinguishable. The annual bundler accepts artifacts from all attempts in the same run and applies deterministic duplicate handling.

## Coverage gates

The full-year fixed weekday expectation is:

```text
262 weekdays x 24 hours = 6,288 symbol-hours
```

Monthly expectations:

```text
2024-01: 552
2024-02: 504
2024-03: 504
2024-04: 528
2024-05: 552
2024-06: 480
2024-07: 552
2024-08: 528
2024-09: 504
2024-10: 552
2024-11: 504
2024-12: 528
```

Acceptance requires, for the annual block and every month:

```text
expected_records_mode: weekdays
observed_records == expected_records
unobserved_records: 0
hard_error_records: 0
effective_coverage: 1.0
```

Explicit no-tick or market-closed records are observed terminal states and are not treated as missing hours.

## Missing-day and error recovery

The annual bundler does not trust the presence of daily artifacts alone. It:

1. combines every available daily manifest;
2. synthesizes an error record for every absent Monday-Friday UTC hour;
3. retries all terminal errors and synthetic gaps;
4. resamples recovered ticks;
5. applies the fixed weekday coverage gate again.

This prevents a completely absent daily artifact from disappearing from the coverage denominator.

## Bar construction

Annual bars are assembled by:

- loading all downloaded daily M1/M5/M15/H1 files;
- adding annual repair bars;
- prioritizing repair bars at duplicate timestamps;
- rejecting conflicting same-priority duplicate bars;
- sorting timestamps monotonically;
- producing one gzip CSV per timeframe;
- validating bid/ask OHLC, spreads, tick counts and duplicate timestamps.

Builder:

```text
tools/build_fx_annual_bar_bundle.py
```

## Research boundary

No EURUSD broker spread is assumed in this collection workflow. Rakuten MT4 EURUSD spread and cost scenarios must be specified separately before strategy evaluation.

EURUSD research must receive its own candidate registry and preregistration. USDJPY strategy results and gates are not automatically transferred to EURUSD merely because the data pipeline is shared.
