# USDJPY EA Research (Pre-MT4)

This repository is dedicated to **pre-MT4 research and simulation** for a USDJPY Expert Advisor (EA).

## Direction

Research execution is **cloud-first**:
- primary path: GitHub Actions / Codex Cloud study runs
- fallback path: local/private study configs under `configs/local/`

Core (private MT4 side) remains the final gate.
This public repository does **not** claim MT4 parity.

## Scope

Included:
- research modules (`research/`)
- study/experiment configs (`configs/`)
- usage docs (`docs/`)
- utility scripts (`tools/`)

Excluded:
- MT4 production code (`.mq4`, `.mqh`)
- broker-specific live-trading logic
- secrets

## Cloud-First Study Flow

For iPhone/mobile operation, use:
- `docs/cloud_timing_study_playbook.md`

1. Choose a cloud study config (default):
   - `configs/studies/cloud_timing_rv_close_confirm_first.yaml`
2. Ensure dataset IDs map in:
   - `configs/datasets/dataset_registry.yaml`
   - provider types: `repo_path` (repo-local) and `url` (downloaded/cache-staged)
3. Trigger workflow:
   - `.github/workflows/run_research_timing_study.yml`
4. Download artifacts and review:
   - `compare/timing_study_review.md`
   - compare CSVs

See:
- `docs/cloud_timing_study_playbook.md`
- `docs/cloud_timing_study_usage.md`
- `docs/dataset_registry_usage.md`
- `docs/study_runner_usage.md`

URL-backed datasets are staged deterministically under each study output root:
- `<output_root>/dataset_cache/url/<dataset_id>/<filename>`

## Local Fallback Flow

Local/private absolute-path configs are still supported for debug/fallback:
- `configs/local/*.example.yaml`
- `docs/local_study_pack_usage.md`

Keep private data out of git.

## Notes

- Keep assumptions conservative when execution order is ambiguous.
- Avoid lookahead bias in all research/simulation.
- Compare by month, session, and bucket slices.
- MT4 remains final source of truth.
