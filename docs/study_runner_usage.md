# Study Runner Usage

`tools/run_study.py` is the orchestration entrypoint for multi-run research studies.

## Direction (Cloud-First)

Preferred main path:
- GitHub Actions / Codex Cloud study execution using study configs in `configs/studies/`.

Fallback/debug path:
- local/private configs under `configs/local/` with absolute `input_csv` values.

This remains pre-MT4 research-only.

## Quick Start (Cloud-First config, local invocation example)

```bash
python tools/check_research_env.py --study-config configs/studies/cloud_timing_rv_close_confirm_first.yaml
python tools/run_study.py --config configs/studies/cloud_timing_rv_close_confirm_first.yaml
```

Optional overrides (used by workflow dispatch too):

```bash
python tools/run_study.py \
  --config configs/studies/cloud_timing_rv_close_confirm_first.yaml \
  --dataset-id usdjpy_m1_tiny_sample \
  --output-tag manual_test
```

Override-aware preflight validation:

```bash
python tools/check_research_env.py \
  --study-config configs/studies/cloud_timing_rv_close_confirm_first.yaml \
  --dataset-id usdjpy_m1_tiny_sample
```

## Dataset Input Resolution

A run can define either:
- `input_csv` (backward-compatible local fallback), or
- `dataset_id` (cloud-first)

When `dataset_id` is used, study config must include:
- `dataset_registry: configs/datasets/dataset_registry.yaml`

Resolution order per run:
1. use `input_csv` if set
2. otherwise resolve `dataset_id` through registry

## Compare + Review

After compare completes, generate compact timing review:

```bash
python tools/review_timing_study.py --study-dir <output_root>
```

This writes:
- `<output_root>/compare/timing_study_review.md`

## Notes

- Keep this layer orchestration-only; simulator logic is unchanged.
- Keep MT4 as final validation source of truth.
