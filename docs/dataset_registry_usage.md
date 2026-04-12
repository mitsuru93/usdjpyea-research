# Dataset Registry Usage (Cloud-First)

Use `configs/datasets/dataset_registry.yaml` to map stable `dataset_id` values to deterministic, repo-resolvable CSV paths.

## Why

- Makes study configs cloud-runnable without local absolute paths.
- Keeps input selection explicit and repeatable in GitHub Actions / Codex Cloud.
- Preserves local `input_csv` as a fallback path.

## Registry Shape

```yaml
datasets:
  usdjpy_m1_tiny_sample:
    path: research/data_sample/usdjpy_m1_tiny_sample.csv
    source_ref: repo://research/data_sample/usdjpy_m1_tiny_sample.csv
```

Required:
- `datasets.<dataset_id>.path`

Optional metadata:
- `source_ref`
- `note`

## Study Config Link

```yaml
dataset_registry: configs/datasets/dataset_registry.yaml
runs:
  - label: baseline_touch
    dataset_id: usdjpy_m1_tiny_sample
```

Resolution rule in study runner:
- If `input_csv` is set, it is used directly (local fallback compatibility).
- Otherwise `dataset_id` is resolved through the registry to produce `input_csv` for run execution.
