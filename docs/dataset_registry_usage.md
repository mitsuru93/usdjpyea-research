# Dataset Registry Usage (Cloud-First)

Use `configs/datasets/dataset_registry.yaml` to map stable `dataset_id` values to deterministic CSV inputs for study runs.

## Why this exists

- Research in this repo is **cloud-first** (GitHub Actions / Codex Cloud).
- Large datasets should be resolvable without editing study configs to local absolute paths.
- `dataset_id` keeps study inputs explicit and repeatable.
- Local `input_csv` remains supported as a fallback/debug path.

## Provider types

Dataset entries support two providers:

### 1) `provider: repo_path`

Use a repo-local file path.

```yaml
datasets:
  usdjpy_m1_tiny_sample:
    provider: repo_path
    path: research/data_sample/usdjpy_m1_tiny_sample.csv
    source_ref: repo://research/data_sample/usdjpy_m1_tiny_sample.csv
```

Backward compatibility:
- If `provider` is omitted, resolver treats the entry as `repo_path`.

Current cloud study split:
- Smoke dataset: `usdjpy_m1_tiny_sample` (tiny, fast validation path)
- Main dataset: `usdjpy_m1_2024_01_02_to_2026_02_18_public_main` (broader public research path (2024-01-02 to 2026-02-18))
- Main dataset file: `USDJPY_M1_2024-01-02_2026-02-18.csv` resolved from GitHub Release asset URL for deterministic cloud download.

### 2) `provider: url`

Use an HTTP(S) URL downloaded to a deterministic local cache path.

```yaml
datasets:
  usdjpy_m1_full_example:
    provider: url
    url: https://example.com/path/usdjpy_m1_full_example.csv
    filename: usdjpy_m1_full_example.csv
    sha256: <optional-64-char-hex>
    source_ref: url://example.com/path/usdjpy_m1_full_example.csv
```

Required fields by provider:
- `repo_path`: `path`
- `url`: `url`, `filename`
- `sha256` is optional for `url` entries, but strongly recommended.

## Resolution behavior

Study orchestration resolves dataset input in this order:
1. If run/shared config has `input_csv`, use it directly (fallback compatibility).
2. Else resolve `dataset_id` from registry.
   - `repo_path`: resolve to repo-local file.
   - `url`: download to `<study_output_root>/dataset_cache/url/<dataset_id>/<filename>`.

The resolved local path is passed into run configs as `input_csv`.

## Validation

`tools/check_research_env.py --study-config ...` validates:
- provider type
- provider-required fields
- `repo_path` file existence
- `url` + `filename` presence and URL shape
- `sha256` shape when provided

## Research scope reminder

This registry is for pre-MT4 research execution convenience only.
MT4 remains the final source of truth.


## Smoke vs Main guidance

- Use smoke (`cloud_timing_rv_close_confirm_first.yaml`) for validation, CI sanity checks, and quick workflow verification.
- Use main (`cloud_timing_rv_close_confirm_main_public.yaml`) for actual main public timing research comparisons.
- Keep cloud-first execution as the primary operating mode.
- This remains pre-MT4 candidate screening only; MT4 is still the final source of truth.
