# Analysis Runner Usage (Post-Run)

`tools/analyze_run.py` is a lightweight, pandas-only post-run layer on top of completed experiment outputs.

It is designed for **research-side diagnostics** to spot potentially favorable zones and danger zones for Rev/Trend candidates by feature buckets.

## Scope and boundaries

- This tool analyzes existing run outputs (`candidates.csv`, `summary_*.csv`, `run_metadata.yaml`).
- It does **not** redesign the simulator.
- It does **not** prove live EA profitability.
- MT4 remains the final source of truth.
- This repository remains public pre-MT4 research only.

## 1) Prepare analysis config

Use:
- `configs/experiments/analysis_run_template.yaml`

Required fields:
- `run_dir`
- `output_dir`

Common optional fields:
- `quantile_bucket_count`
- `selected_features`
- `selected_feature_pairs`
- `slice_modes`
- `bucket_mode` (`quantile` default, `fixed` when `fixed_bins_by_feature` is provided)
- `fixed_bins_by_feature`
- `notes`

## 2) Run analysis

```bash
python tools/analyze_run.py --config configs/experiments/analysis_run_template.yaml
```

Smoke-test-friendly config:

```bash
python tools/analyze_run.py --config configs/experiments/smoke_test_analysis_run.yaml
```

## 3) Output files

Outputs are deterministic and CSV-first:

- `bucket_overall__<feature>.csv`
- `bucket_by_family__<feature>.csv`
- `bucket_by_direction__<feature>.csv`
- `bucket_by_session__<feature>.csv`
- `joint__<feature1>__<feature2>__avg_pnl.csv`
- `joint__<feature1>__<feature2>__trade_count.csv`
- `analysis_metadata.yaml`
- `analysis_summary.md`

`analysis_summary.md` stays concise and mechanical:
- list of analyzed features
- highest/lowest bucket avg pnl by family (if family slice exists)
- low-sample bucket warnings via visible `trade_count`

## Research reminder

This is for pre-MT4 research prioritizing robustness and explicit diagnostics. Use it to guide hypotheses and risk filters, then validate final behavior in MT4.
