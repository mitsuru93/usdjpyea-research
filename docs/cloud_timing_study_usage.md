# Cloud Timing Study Usage

Research in this repository is **cloud-first**: prefer GitHub Actions / Codex Cloud execution for candidate timing studies.
Local configs under `configs/local/` remain fallback/debug tools.

## Default Cloud Study Config

- `configs/studies/cloud_timing_rv_close_confirm_first.yaml`
- modes: `baseline_touch`, `rv_close_confirm`, `all_close`
- compare sections include overall/month/session/family and timing breakdowns.

## Run from GitHub Actions

Workflow:
- `.github/workflows/run_research_timing_study.yml`

Inputs:
- `study_config` (default: cloud timing config)
- `dataset_id` (optional override for all runs)
- `output_tag` (optional extra folder suffix under study output root)

## Artifacts

The workflow uploads a single artifact containing:
- study run outputs (`runs/`)
- compare outputs (`compare/`)
- `compare/timing_study_review.md`
- `study_metadata.yaml`
- `study_summary.md`

Practical next step after dispatch:
1. Wait for workflow completion.
2. Download artifacts.
3. Read `timing_study_review.md` first.
4. Inspect compare CSVs for detailed breakdown.

Research outputs are pre-MT4 candidate evaluation only.
MT4 remains the final source of truth.
