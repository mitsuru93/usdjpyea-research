# Cloud Timing Study Usage

Research in this repository is **cloud-first**: prefer GitHub Actions / Codex Cloud execution for candidate timing studies.
Local configs under `configs/local/` remain fallback/debug tools.

For quick mobile operation, start with:
- `docs/cloud_timing_study_playbook.md`

## Cloud Study Configs (Smoke vs Main)

### Smoke / validation / workflow sanity check (default)

- `configs/studies/cloud_timing_rv_close_confirm_first.yaml`
- dataset: `usdjpy_m1_tiny_sample`
- use this for fast checks that cloud workflow + artifacts + compare wiring are healthy.

### Main public timing research

- `configs/studies/cloud_timing_rv_close_confirm_main_public.yaml`
- dataset: `usdjpy_m1_2024_01_02_to_2026_02_18_public_main`
- canonical file: `USDJPY_M1_2024-01-02_2026-02-18.csv` (via deterministic GitHub Release asset URL)
- modes: `baseline_touch`, `rv_close_confirm`, `all_close`
- compare sections include overall/month/session/family and timing breakdowns.

## Dataset input model

Preferred path:
- use `dataset_id` linked through `configs/datasets/dataset_registry.yaml`

Fallback path:
- direct `input_csv` remains supported for local/debug use

Registry providers:
- `repo_path`: repo-local file
- `url`: HTTP(S) download staged to deterministic local cache

Downloaded URL datasets are staged under:
- `<study_output_root>/dataset_cache/url/<dataset_id>/<filename>`

## Run from GitHub Actions

Workflow:
- `.github/workflows/run_research_timing_study.yml`

Inputs:
- `study_config` (default: cloud timing config)
- `dataset_id` (optional override for all runs)
- `output_tag` (optional extra folder suffix under study output root)

Dispatch flow:
1. Trigger workflow (from desktop or mobile).
2. Optionally set `dataset_id` override (leave blank for normal config-driven datasets).
3. Optionally set `output_tag` to isolate this run under output root.
4. Wait for completion and read the Actions job summary.
5. Download artifact and review `compare/timing_study_review.md` first.

## Artifacts

The workflow uploads a single artifact (name includes config + dataset/tag + run id) containing:
- study run outputs (`runs/`)
- compare outputs (`compare/`)
- `study_metadata.yaml`
- `study_summary.md`

## Scope reminder

Research outputs are pre-MT4 candidate evaluation only.
This repository does not claim MT4 parity.
MT4 remains the final source of truth.
