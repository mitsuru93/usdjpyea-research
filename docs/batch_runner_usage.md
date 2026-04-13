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
6. fixed-marker review issue comment update (Issue comment sink)

During aggregation, run outputs are deterministically re-resolved from downloaded artifact staging paths.

`review_sink` is designed for standard GitHub **Issue** comments (`issue_number` + `comment_marker`).
If the configured target is a PR number, the workflow now grants `pull-requests: write` as a compatibility fallback for integrations that require PR-scoped permission on PR-backed threads.

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

Semantics in this PR are **daily recurring JST windows**:

```yaml
blackout_windows_jst:
  - start_hhmmss: "23:55:00"
    end_hhmmss: "00:10:00"
    label: daily_rollover_guard
```

Midnight crossing windows are supported (`23:55:00 -> 00:10:00`).

Current implementation excludes candidates whose timestamps map into those recurring JST windows when calculating `kept_*` ranking metrics.
The excluded counts are shown in ranking/review outputs for auditability.
This is an explicit safety guard for current non-spread-aware runtime screening (not spread-aware execution).

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
- `configs/batches/batch_band_model_screen_v2.yaml`

This batch screens envelope band models across:
- percent envelope: `0.0005, 0.0006, 0.0007, 0.0008`
- fixed pip envelope: `8, 9, 10, 11`
- ATR*k envelope: `0.8, 1.0, 1.2`

`batch_band_model_screen_v1` keeps legacy compact settings for backward compatibility.
For new sweeps, use decimal-rate percent units (`0.0005` means `0.05%`).

`batch_band_model_screen_v2` is the cloud/public large-screening spec and expands
hundreds of variants across percent/fixed/ATR/stddev/range/vol/hybrid families.

Variant naming is compact/stable, centered on band dimension in this phase.

`batch_band_model_screen_v1` is configured for the canonical public main dataset.
For smoke-only validation, create/use a separate `*_smoke_*` batch spec.
