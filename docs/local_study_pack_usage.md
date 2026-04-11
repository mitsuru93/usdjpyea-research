# Local Study Variant Pack Usage

Use this when you want a compact baseline-vs-variants study setup without writing every run block from scratch.

## 1) Copy the example to a local ignored file

```bash
cp configs/local/local_study_variant_pack.example.yaml configs/local/local_study_variant_pack.yaml
```

The copied file path (`configs/local/local_study_variant_pack.yaml`) is git-ignored for local/private use.

## 2) Replace private CSV path

In your copied file, replace:

- `/ABSOLUTE/LOCAL/PATH/TO/usdjpy_m1_private.csv`

Use your real local absolute path and keep it private.

## 3) Run environment check

```bash
python tools/check_research_env.py --study-config configs/local/local_study_variant_pack.yaml
```

## 4) Run the study

```bash
python tools/run_study.py --config configs/local/local_study_variant_pack.yaml
```

## 5) Inspect compare outputs

Review side-by-side ranking outputs under:

- `<output_root>/compare/`

Use baseline vs variant comparison as **pre-MT4 candidate ranking only**.
MT4 remains the final source of truth.
