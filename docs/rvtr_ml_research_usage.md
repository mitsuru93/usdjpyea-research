# RV/TR ML Research Usage

This repository contains a research-only RV/TR ML pipeline for ATR shortlist bands.

Scope:
- pre-MT4 research only
- shortlist bands only
- fixed exit profile only
- hard gate stays separate
- no MT4 production code
- GitHub-hosted Actions only
- no self-hosted runner dependency

## Primary verified inputs

The pipeline consumes a verified label-source artifact extracted from a prior GitHub Actions run.

Primary artifacts inside each run directory:
- `candidates_decision_policy_audit.csv`
- `candidates_aggregate.csv.gz`
- `effective_band_config.yaml`

Verified metadata source:
- `study_metadata.yaml`

Important:
- `study_metadata.yaml` is not required to live directly inside the run directory.
- The loader resolves `run_metadata.yaml` first when present.
- If `run_metadata.yaml` is absent, it walks upward from the run directory and uses the first `study_metadata.yaml` it finds in the ancestor hierarchy.

## How to run

Primary workflow (recommended):
- file: `/.github/workflows/run_rvtr_ml_from_batch_spec.yml`
- name: `Run RV/TR ML From Batch Spec`

Primary inputs:
- `batch_spec` (required, e.g. `configs/...yaml`)
- `dataset_id` (optional)
- `output_tag` (optional)
- `review_issue_number` (optional)
- `rvtr_ml_output_subdir` (optional, defaults to `rvtr_ml_research`)

Main path is config-driven. You trigger once with `batch_spec = configs/...yaml` and the same run executes two internal jobs after shard runs:
- `aggregate` job (shard artifact download, run-level label source staging, batch review, review publish)
- `rvtr-ml` job (fresh runner, label-source artifact download, RV/TR ML build/train/distill)

User operation stays the same: only `batch_spec = configs/...yaml` is required for the primary flow.

No manual `label_source_run_id` / `label_source_artifact_name` input is required in the primary flow.

Secondary helper workflow (manual, non-primary):
- file: `/.github/workflows/run_rvtr_ml_research.yml`
- name: `Run RV/TR ML Research`
- purpose: run ML-only from an already produced label-source artifact, when needed
- required helper inputs: `label_source_run_id`, `label_source_artifact_name`

Example flow:

```bash
python tools/build_rvtr_label_table.py \
  --source-root <extracted_batch-runlevel-label-source_root> \
  --output-dir research/reports/rvtr_ml_research

python tools/train_rvtr_logit_v1.py \
  --label-table research/reports/rvtr_ml_research/rvtr_label_table_trainable_v1.csv.gz \
  --output-dir research/reports/rvtr_ml_research

python tools/distill_rvtr_score_v1.py \
  --coef-csv research/reports/rvtr_ml_research/rvtr_logit_v1_coef.csv \
  --output-dir research/reports/rvtr_ml_research
```

In the new primary workflow this chain is run inside the `rvtr-ml` job on a fresh GitHub-hosted runner, using the staged `label_source` downloaded via artifact from `aggregate`.

Optional review step:

```bash
python tools/review_rvtr_ml.py \
  --control-run-dir <bin_env_v1_run_dir> \
  --current-run-dir <total_score_rvtr_v1_run_dir> \
  --distilled-run-dir <total_score_rvtr_v2_ml_run_dir> \
  --coef-csv research/reports/rvtr_ml_research/rvtr_logit_v1_coef.csv \
  --distilled-yaml research/reports/rvtr_ml_research/distilled_total_score_rvtr_v2.yaml \
  --output-dir research/reports/rvtr_ml_research/review
```

## Output artifacts

- `rvtr_label_table_v1.csv.gz`
- `rvtr_label_table_trainable_v1.csv.gz`
- `rvtr_label_table_v1.summary.json`
- `label_distribution_overall.csv`
- `label_distribution_by_month.csv`
- `label_distribution_by_session.csv`
- `label_distribution_by_band.csv`
- `rvtr_logit_v1_coef.csv`
- `rvtr_logit_v1_metrics.json`
- `rvtr_logit_v1_predictions.csv.gz`
- `distilled_total_score_rvtr_v2.yaml`
- `distilled_feature_importance.csv`
- `rvtr_ml_review.md`
- `rvtr_ml_compare.csv`
- `rvtr_ml_by_month.csv`
- `rvtr_ml_by_session.csv`
- `rvtr_ml_by_band.csv`

## Feature set

Block score features:
- `rv_band_score`, `tr_band_score`
- `rv_timing_score`, `tr_timing_score`
- `rv_momo_score`, `tr_momo_score`
- `rv_stretch_score`, `tr_stretch_score`
- `rv_regime_score`, `tr_regime_score`
- `rv_exit_proxy_score`, `tr_exit_proxy_score`

Raw features:
- `dist_from_ema_norm_by_band`
- `dist_from_ema_norm_by_atr`
- `band_width_norm_vs_atr`
- `pre10_change_pips`
- `pre30_change_pips`
- `pre60_change_pips`
- `net10_change_pips`
- `m5_slope`
- `m30_slope`
- `h1_slope`
- `rsi14`
- `macd_hist`
- `bb_width_ratio_to_close`
- `atr_ratio_5_14`
- `session` one-hot encoded inside the model as `session__*`

## Label spec

- `decision_group_id_v1` = one row per source run / band / timestamp / touch_side group
- `label_gap_rv_minus_tr_pips = pnl_rv_pips - pnl_tr_pips`
- `label_rvtr_v1 = rv` if gap `>= +2.0`
- `label_rvtr_v1 = tr` if gap `<= -2.0`
- `label_rvtr_v1 = ambiguous` otherwise

Trainable subset:
- `hard_gate_passed == True`
- `group_status == complete_unique_pair`
- `label_rvtr_v1 in {rv, tr}`
- no missing required features after preparation

## Performance notes

The implementation intentionally avoids row-by-row Python work where pandas/numpy can do the job:
- label build uses `merge`, `sort_values`, `drop_duplicates`, `pivot_table`, and `groupby`
- review uses `groupby` aggregations rather than manual loops

Remaining Python loops:
- one loop over run artifacts during label-source discovery
- one loop over logistic iterations in the Newton solver

Future compiled-path candidates if research scale grows:
- `numba` for the Newton solver
- `cython` for any remaining hot path that stays resistant to vectorization
