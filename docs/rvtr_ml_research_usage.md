# RV/TR ML Research Usage

This repository now includes a compact research pipeline for optimizing RV/TR decision criteria on the ATR shortlist bands.

Scope:
- pre-MT4 research only
- shortlist bands only
- fixed exit profile only
- hard gate stays separate
- no MT4 production code

## Inputs

The pipeline expects a directory produced by extracting a verified GitHub artifact named `batch-runlevel-label-source-*`.
That extracted root should contain run outputs under a path like:
- `shards/.../runs/<run_name>/`

Each run directory should contain verified inputs such as:
- `candidates_decision_policy_audit.csv`
- `candidates_aggregate.csv.gz`
- `study_metadata.yaml`
- `effective_band_config.yaml`

`run_metadata.yaml` is accepted as a backward-compatible per-run fallback, but `study_metadata.yaml` is the verified metadata source for the label-source artifact flow.
Legacy fallbacks (`candidates_policy_audit.csv`, `candidates.csv`) are accepted, but the verified names above are the primary inputs.

## Local CLI flow

```bash
python tools/build_rvtr_label_table.py \
  --source-root <completed_run_source_root> \
  --output-dir research/reports/rvtr_ml_research

python tools/train_rvtr_logit_v1.py \
  --label-table research/reports/rvtr_ml_research/rvtr_label_table_trainable_v1.csv.gz \
  --output-dir research/reports/rvtr_ml_research

python tools/distill_rvtr_score_v1.py \
  --coef-csv research/reports/rvtr_ml_research/rvtr_logit_v1_coef.csv \
  --output-dir research/reports/rvtr_ml_research
```

Optional review step when completed control/current/distilled run directories are available:

```bash
python tools/review_rvtr_ml.py \
  --control-run-dir <bin_env_v1_run_dir> \
  --current-run-dir <total_score_rvtr_v1_run_dir> \
  --distilled-run-dir <total_score_rvtr_v2_ml_run_dir> \
  --coef-csv research/reports/rvtr_ml_research/rvtr_logit_v1_coef.csv \
  --distilled-yaml research/reports/rvtr_ml_research/distilled_total_score_rvtr_v2.yaml \
  --output-dir research/reports/rvtr_ml_research/review
```

## Workflow

Use `.github/workflows/run_rvtr_ml_research.yml` for an end-to-end run:
- build label table
- train logistic regression
- distill score weights
- optionally review completed run directories

## Output artifacts

Main artifacts:
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
