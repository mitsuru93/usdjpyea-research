# USDJPY EA Research (Pre-MT4)

> **AI / Codex / new-thread start point:** read `AGENTS.md`, then follow
> `configs/research/usdjpy_research_memory_manifest_v1.json` in order.
> No USDJPY hypothesis, candidate proposal, result interpretation, or period-access
> decision is valid without the required start-up read receipt and hypothesis-ledger comparison.

This repository is dedicated to **pre-MT4 research and simulation** for a USDJPY Expert Advisor (EA).

## Canonical USDJPY research memory

The append-only causal history is maintained in:

- `configs/research/usdjpy_hypothesis_ledger_v1.json`
- `docs/research/usdjpy_research_memory_system_v1.md`
- `configs/research/usdjpy_research_candidate_registry_v24.json`

The ledger records not only final decisions, but the analysis that generated each hypothesis, its pre-result predictions, exact tests, failed gates, falsified claims, retained findings, prohibited reuse, and successor questions.

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

1. Choose a cloud study config:
   - smoke/validation default: `configs/studies/cloud_timing_rv_close_confirm_first.yaml`
   - main public research: `configs/studies/cloud_timing_rv_close_confirm_main_public.yaml`
2. Ensure dataset IDs map in:
   - `configs/datasets/dataset_registry.yaml`
   - smoke dataset_id: `usdjpy_m1_tiny_sample`
   - main dataset_id: `usdjpy_m1_2024_01_02_to_2026_02_18_public_main`
   - main dataset file: `USDJPY_M1_2024-01-02_2026-02-18.csv` (resolved from deterministic GitHub Release asset URL)
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
