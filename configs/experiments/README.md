# Experiment Configs

Config-driven research runs live here.

## Candidate experiment configs
- `candidate_run_template.yaml`: template for full runs.
- `smoke_test_candidate_run.yaml`: tiny-sample smoke-test compatible run.
- `policy_run_template.yaml`: template for research-side policy-screened runs.
- `smoke_test_policy_run.yaml`: tiny-sample smoke test for policy config structure.

Use with:

```bash
python tools/run_experiment.py --config <config_path>
```

Policy configs can be supplied either inline (`policy`) or via reusable preset reference (`policy_file`), e.g.:

```yaml
policy_file: configs/policies/rev_danger_zone_example.yaml
```

## Post-run analysis configs
- `analysis_run_template.yaml`: template for feature bucket/joint diagnostics over completed runs.
- `smoke_test_analysis_run.yaml`: tiny-sample analysis config paired with smoke test run outputs.

Use with:

```bash
python tools/analyze_run.py --config <config_path>
```


## Multi-run compare configs
- `compare_runs_template.yaml`: template for side-by-side compare across completed runs.
- `smoke_test_compare_runs.yaml`: smoke-test compare config (can reuse same run with two labels).

Use with:

```bash
python tools/compare_runs.py --config <config_path>
```
