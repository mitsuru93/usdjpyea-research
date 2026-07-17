# USDJPY H2 2024-09 through 2024-12 Batch Execution Plan v1

## Purpose

Complete the remaining four untouched H2 months in one GitHub Actions run without changing either pre-registered candidate or any H2 gate.

Active candidates remain:

```text
A1_impulse_breakout_lb3_hold6
E3_trend_24h_resumption_hold6
```

Candidate evaluation is still deferred until all six H2 monthly baselines, 2024-07 through 2024-12, are available.

## Workflow

```text
name: Run USDJPY H2 2024-09 to 2024-12 Collect and Baseline
file: .github/workflows/run_usdjpy_h2_2024_09_12_collect_and_baseline.yml
```

## Execution order

The source months run sequentially:

```text
2024-09 source collection
-> 2024-10 source collection
-> 2024-11 source collection
-> 2024-12 source collection
```

Each monthly source collection uses:

```text
collect_max_parallel: 4
min_coverage: 1.0
max_hard_errors: 0
```

Running the months sequentially prevents four monthly collectors from expanding into sixteen simultaneous day-collection jobs.

After all four source months pass, the four monthly baseline jobs run as one matrix with:

```text
max-parallel: 4
base spread: 0.5 pips
cost spread mode: max_base_public
hard no-trade configuration: enabled
```

## Fixed month boundaries

```text
2024-09: 2024-09-01T00 through 2024-10-01T00 exclusive
2024-10: 2024-10-01T00 through 2024-11-01T00 exclusive
2024-11: 2024-11-01T00 through 2024-12-01T00 exclusive
2024-12: 2024-12-01T00 through 2025-01-01T00 exclusive
```

## Expected artifacts

The caller run ID is shared by the four source collectors and four baseline jobs, while month-specific pilot tags keep the artifacts separate.

Expected aggregate source artifacts:

```text
public-fx-data-pilot-2024-09-USDJPY-aggregate-<run_id>
public-fx-data-pilot-2024-10-USDJPY-aggregate-<run_id>
public-fx-data-pilot-2024-11-USDJPY-aggregate-<run_id>
public-fx-data-pilot-2024-12-USDJPY-aggregate-<run_id>
```

Expected monthly baseline artifacts:

```text
fx-session-baseline-2024-09-USDJPY-<run_id>
fx-session-baseline-2024-10-USDJPY-<run_id>
fx-session-baseline-2024-11-USDJPY-<run_id>
fx-session-baseline-2024-12-USDJPY-<run_id>
```

## Acceptance

Every month must independently show:

```text
effective coverage: 100%
final hard errors: 0
M5 and M15 source files: present
monthly baseline artifact: present
```

A failure stops progression to later source months. The H2 A1/E3 evaluation begins only after the combined run and all eight expected aggregate/baseline artifacts have been inspected.