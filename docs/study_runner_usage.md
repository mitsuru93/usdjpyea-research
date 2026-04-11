# Study Runner Usage

`tools/run_study.py` adds a lightweight orchestration layer on top of existing run/analyze/compare tools.

## Purpose

Use one study YAML to orchestrate:
- one or more experiment runs (`tools/run_experiment.py`)
- optional per-run post-run analysis (`tools/analyze_run.py`)
- optional multi-run comparison (`tools/compare_runs.py`)

This stays pre-MT4 and research-only.

## Quick Start

```bash
python tools/run_study.py --config configs/studies/smoke_test_study.yaml
```

## Study Config Shape

Required top-level keys:
- `study_name`
- `output_root`
- `shared_defaults`
- `runs`

Optional top-level keys:
- `compare`
- `notes`

Minimal pattern:

```yaml
study_name: dc18ab5s_baseline_screen
output_root: research/reports/studies/dc18ab5s_baseline_screen
shared_defaults:
  input_timezone_mode: UTC
  max_holding_bars: 30
  symbol: USDJPY
  timeframe: M1
  analyze_after_run: true

runs:
  - label: baseline
    input_csv: /ABSOLUTE/OR/LOCAL/PATH/usdjpy.csv
  - label: variant_a
    input_csv: /ABSOLUTE/OR/LOCAL/PATH/usdjpy.csv
    max_holding_bars: 40

compare:
  enabled: true
  selected_bucket_features:
    - dist_from_ema_pips
```

## Deterministic Outputs

Given `output_root`, study outputs are deterministic:
- run outputs: `<output_root>/runs/<label>`
- analysis outputs: `<output_root>/analysis/<label>`
- compare outputs: `<output_root>/compare`

Study-level metadata:
- `<output_root>/study_metadata.yaml`
- `<output_root>/study_summary.md`

Runtime-generated temporary configs are stored in:
- `<output_root>/runtime_configs/`

## Behavior Notes

- The first run is the baseline run label for summary/compare context.
- `shared_defaults` are merged first, then per-run overrides are applied.
- `analyze_after_run` can be set in `shared_defaults` and overridden per run.
- Compare runs only if `compare.enabled: true` and at least two runs complete successfully.
- Failed runs are recorded in metadata and summary with error text.

## Safety / Scope

- Keep this layer orchestration-only; simulator and analysis internals are unchanged.
- Do not commit private CSV datasets.
- Keep MT4 as final source of truth; this repository remains pre-MT4 research.
