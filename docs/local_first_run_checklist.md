# Local First-Run Checklist (Codex CLI / PC)

Use this checklist before running real-data research studies locally.

## 1) Install requirements

```bash
python -m pip install -r requirements.txt
```

## 2) Prepare a private local study config

Start from:
- `configs/local/local_study_template.example.yaml`

Copy it to a local-only file (kept out of git by `.gitignore`), for example:

```bash
cp configs/local/local_study_template.example.yaml configs/local/local_study.yaml
```

Then edit:
- `input_csv` to your private absolute/local CSV path
- `output_root` to your local output location
- run labels / policy settings as needed (`policy` inline or `policy_file` preset)

## 3) Run lightweight environment checks first

```bash
python tools/check_research_env.py --study-config configs/local/local_study.yaml
```

Optional: check individual configs too.

```bash
python tools/check_research_env.py \
  --experiment-config configs/experiments/smoke_test_candidate_run.yaml \
  --analysis-config configs/experiments/smoke_test_analysis_run.yaml \
  --compare-config configs/experiments/smoke_test_compare_runs.yaml
```

## 4) Run the study

```bash
python tools/run_study.py --config configs/local/local_study.yaml
```

## Operational reminders

- Keep real datasets local/private; do not commit private CSV files.
- Raw timeline handling remains server-aligned (`datetime` as provided in CSV).
- JST session/month labels remain derived from the configured input timezone mode.
- This repository remains pre-MT4 research only; MT4 is the final source of truth.
