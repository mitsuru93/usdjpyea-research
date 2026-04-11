# Local Data Workflow (Public Repo Safe)

This repository is public and pre-MT4 research only.

## Core Rules

- Real broker/export CSV data should remain **outside** this public repository.
- Do **not** commit private datasets into `git`.
- Use study configs with absolute/local paths during local runs.
- Keep the raw timeline server-aligned in source CSV.
- Keep JST session labels as a derived view in research processing.
- MT4 remains the final source of truth for execution validation.

## Practical Pattern

1. Store private CSV files in a local-only folder (outside repo root is preferred).
2. Keep public config templates in `configs/studies/`.
3. Keep machine-specific/private path mappings in local-only config files under `configs/local/`.
4. Reference private CSV paths from local study configs when running `tools/run_study.py`.

## Example Local Study Config Snippet

```yaml
runs:
  - label: baseline
    input_csv: /Users/yourname/private_fx_data/usdjpy_m1_2024.csv
```

## Dataset Registry Example

Use `configs/local/dataset_registry.example.yaml` as a template for your own ignored local file.

## Reminder

Research outputs under `research/reports/studies/` are local runtime artifacts and should typically remain uncommitted.
