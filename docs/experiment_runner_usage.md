# Experiment Runner Usage (Config-Driven)

`tools/run_experiment.py` runs simulator v1 candidate generation, attaches decision-time features, evaluates conservative outcomes, and writes summaries.

## 1) Prepare a config

Use template:

- `configs/experiments/candidate_run_template.yaml`

Required fields:
- `input_csv`
- `output_dir`
- `input_timezone_mode` (`UTC` or `JST`)
- `max_holding_bars`
- `symbol`
- `timeframe`
- `notes` (optional but recommended)

## 2) Run

```bash
python tools/run_experiment.py --config configs/experiments/candidate_run_template.yaml
```

Smoke test-sized config:

```bash
python tools/run_experiment.py --config configs/experiments/smoke_test_candidate_run.yaml
```

## 3) Outputs

The runner writes:
- `candidates.csv` (feature-enriched candidate rows used for outcome evaluation; policy-screened if enabled)
- `candidates_policy_audit.csv` (all pre-evaluation candidates with policy decision audit fields)
- `summary_overall.csv`
- `summary_by_month.csv`
- `summary_by_session.csv`
- `summary_by_family.csv`
- `run_metadata.yaml`

## 4) Metadata notes

`run_metadata.yaml` includes:
- feature set version
- pip size
- timezone handling policy
- assumption version
- explicit reminder that this is not MT4 parity

## Research boundaries reminder

This runner is for public pre-MT4 research only:
- no `.mq4` / `.mqh`
- no live broker logic
- no claim of full MT4 behavior parity

## 5) Optional policy screening

You can add a `policy` block in experiment YAML to filter candidate rows after feature attachment and before outcome evaluation.

Use:
- `configs/experiments/policy_run_template.yaml`
- `configs/experiments/smoke_test_policy_run.yaml`

Semantics are deterministic (`last_match_wins`) and run metadata records base/included/excluded counts.

See `docs/policy_layer_usage.md` for schema and examples.
