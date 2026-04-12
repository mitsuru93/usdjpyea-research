# Compare Runner Usage (Multi-Run, CSV-First)

`tools/compare_runs.py` adds a lightweight research-side comparison layer on top of completed run artifacts.

It compares completed outputs side by side in a deterministic, pandas-only, CSV-first format.

## Scope and boundaries

- This tool compares **completed run artifacts** (`summary_*.csv`, `candidates.csv`, optional analysis buckets).
- It does **not** redesign candidate generation logic.
- It does **not** redesign the simulator or post-run analysis layers.
- It does **not** prove live profitability.
- It helps rank candidate variants before MT4 validation.
- MT4 remains the final source of truth.
- This repository remains public pre-MT4 research only.

## 1) Prepare compare config

Use:
- `configs/experiments/compare_runs_template.yaml`

Required fields:
- `output_dir`
- `runs` (list of `{label, run_dir, analysis_dir?}`)

Common optional fields:
- `compare_sections` (`overall`, `by_month`, `by_session`, `by_family`, `by_direction`, `timing_overall`, `timing_by_month`, `timing_by_session`, `timing_by_family`)
- `selected_bucket_features` (for optional bucket comparisons)
- `notes`

## 2) Run compare

```bash
python tools/compare_runs.py --config configs/experiments/compare_runs_template.yaml
```

Smoke-test-friendly config:

```bash
python tools/compare_runs.py --config configs/experiments/smoke_test_compare_runs.yaml
```

## 3) Output files

Core compare outputs:
- `compare_overall.csv`
- `compare_by_month.csv`
- `compare_by_session.csv`
- `compare_by_family.csv`
- `compare_by_direction.csv`
- `compare_timing_overall.csv` (if selected and available)
- `compare_timing_by_month.csv` (if selected and available)
- `compare_timing_by_session.csv` (if selected and available)
- `compare_timing_by_family.csv` (if selected and available)
- `compare_metadata.yaml`
- `compare_summary.md`

Optional bucket compare outputs (if analysis artifacts exist):
- `compare_bucket_overall__<feature>.csv`
- `compare_bucket_by_family__<feature>.csv`

Delta columns are baseline-relative (first run in config). Column names are explicit:
- `<run_label>_trade_count`
- `<run_label>_win_rate`
- `<run_label>_avg_pnl_pips`
- `<run_label>_total_pnl_pips`
- `delta_<run_label>_trade_count_vs_baseline`
- `delta_<run_label>_win_rate_vs_baseline`
- `delta_<run_label>_avg_pnl_pips_vs_baseline`
- `delta_<run_label>_total_pnl_pips_vs_baseline`

`compare_summary.md` stays concise and mechanical:
- run labels included
- baseline run label
- generated sections
- top positive/negative `total_pnl_pips` deltas by section where available
- warnings for missing files/sections
