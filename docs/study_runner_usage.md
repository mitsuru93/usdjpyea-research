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
python tools/check_research_env.py --study-config configs/studies/smoke_test_study.yaml
python tools/run_study.py --config configs/studies/smoke_test_study.yaml
```

For local/private data workflows, start from:
- `configs/local/local_study_template.example.yaml`
- `configs/local/local_study_variant_pack.example.yaml` (compact multi-variant baseline-vs-preset example)
- `configs/local/local_study_rv_close_confirm_pack.example.yaml` (timing-only pack for `baseline_touch` vs `rv_close_confirm` vs `all_close`)
- `configs/local/local_study_rv_close_confirm_first_real.example.yaml` (first real private-data timing run template with practical compare defaults)
- `docs/local_first_run_checklist.md`
- `docs/local_study_pack_usage.md`

For timing interpretation on first private runs, use:
- `docs/first_timing_study_reading_guide.md`
- `tools/review_timing_study.py` (compact post-run markdown helper over compare outputs)

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
    policy_file: configs/policies/trend_bias_example.yaml

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
- `policy_file` can be placed in `shared_defaults` or per-run overrides.
- Per run, use either `policy` or `policy_file` (not both).
- Policy override normalization is explicit during merge:
  - run-level `policy` removes inherited `policy_file` (unless the run also explicitly sets `policy_file`).
  - run-level `policy_file` removes inherited `policy` (unless the run also explicitly sets `policy`).
  - explicit null/empty values (`policy: null`, `policy: {}`, `policy_file: null`, `policy_file: ""`) clear that field.
- For study runs, relative `policy_file` values are normalized before runtime config write:
  - first against the original study config directory
  - then against repo root as fallback
  - runtime config stores the resolved absolute path for stable execution
- `analyze_after_run` can be set in `shared_defaults` and overridden per run.
- Compare runs only if `compare.enabled: true` and at least two runs complete successfully.
- Compare also requires the configured baseline run (the first run label) to complete successfully; otherwise compare is skipped with an explicit warning.
- Failed runs are recorded in metadata and summary with error text.
- Run labels must remain unique after sanitization (for example, avoid pairs like `a/b` and `a b`).

## Safety / Scope

- Keep this layer orchestration-only; simulator and analysis internals are unchanged.
- Do not commit private CSV datasets.
- Run `tools/check_research_env.py` before local real-data study execution.
- For timing-study packs, you can generate a compact first-pass review after compare completes:
  - `python tools/review_timing_study.py --study-dir <output_root>`
  - Output: `<output_root>/compare/timing_study_review.md`
- Keep MT4 as final source of truth; this repository remains pre-MT4 research.
