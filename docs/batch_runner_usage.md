# Batch Runner Usage (Cloud-First, Pre-MT4)

This repository now supports cloud-only, single-dispatch **batch research** on top of the existing `run_study` path.

- Scope: candidate screening convenience only.
- This is **not** MT4 parity.
- MT4 remains final source of truth.

## Batch spec schema

Batch specs live under `configs/batches/`.

Required fields:
- `batch_id`
- `dataset_registry`
- `dataset_id`
- `output_root`
- `shard_size`
- `output_tag_default` (optional)
- `blackout_windows_jst`
- `spread_mode` (`ignore | audit_only | column_proxy`)
- `band_model_sweep`
- `timing_modes`
- `compare_sections`
- `ranking_profile`
- `review_sink`
- `notes`

## Cloud workflow entrypoint

Use `.github/workflows/run_research_batch.yml` with workflow_dispatch inputs:
- `batch_spec`
- `dataset_id` (optional override)
- `output_tag` (optional override)
- `review_issue_number` (optional override)

The workflow performs:
1. batch validation + expansion
2. shard study matrix execution (reusing `tools/run_study.py`)
3. shard artifact aggregation
4. batch review generation
5. artifact upload
6. fixed-marker review issue comment update

## CLI tools

- `tools/expand_batch.py`: validates and expands one batch spec into shard study configs + manifest.
- `tools/run_batch.py`: sequential local convenience wrapper (`expand -> run shards -> review`).
- `tools/review_batch.py`: aggregates shard outputs into deterministic batch-level review artifacts.

## Spread audit behavior

Current runtime path does not execute spread-aware logic.

Batch spread handling is explicit:
- detect whether dataset headers include `Spread`
- record headers in metadata
- if present, record lightweight audit stats (`non_null_count`, `zero_count`, `min`, `p50`, `p90`, `max`)
- do not block execution unless profile requires spread presence

## Blackout windows (JST)

`blackout_windows_jst` are deterministic hard exclusion windows used at batch review ranking time.

Current implementation excludes candidates whose timestamps map into those JST windows when calculating `kept_*` ranking metrics.
The excluded counts are shown in ranking/review outputs for auditability.

## Batch outputs

At batch output root:
- `batch_metadata.yaml`
- `batch_manifest.yaml`
- `batch_ranking.csv`
- `batch_shortlist.csv`
- `batch_review.md`
- `batch_review_machine.yaml`

These are compact and deterministic CSV/YAML/Markdown artifacts for cloud review.

## Seeded executable batch

- `configs/batches/batch_band_model_screen_v1.yaml`

This batch screens envelope band models across:
- percent envelope: `0.05, 0.06, 0.07, 0.08`
- fixed pip envelope: `8, 9, 10, 11`
- ATR*k envelope: `0.8, 1.0, 1.2`

Variant naming is compact/stable, centered on band dimension in this phase.
