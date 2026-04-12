# Local Study Variant Pack Usage (Fallback / Debug)

Local study packs are kept for fallback/debug workflows.
Preferred execution path is cloud-first study dispatch via GitHub Actions.

Use this doc when you intentionally run private/local CSV studies on your own machine.

## Local Templates (unchanged, still supported)

- `configs/local/local_study_variant_pack.example.yaml`
- `configs/local/local_study_rv_close_confirm_pack.example.yaml`
- `configs/local/local_study_rv_close_confirm_first_real.example.yaml`

## 1) Copy example to ignored local file

```bash
cp configs/local/local_study_rv_close_confirm_first_real.example.yaml configs/local/local_study_rv_close_confirm_first_real.yaml
```

## 2) Replace private CSV path

Replace:
- `/ABSOLUTE/LOCAL/PATH/TO/usdjpy_m1_private.csv`

## 3) Run checks + study

```bash
python tools/check_research_env.py --study-config configs/local/local_study_rv_close_confirm_first_real.yaml
python tools/run_study.py --config configs/local/local_study_rv_close_confirm_first_real.yaml
```

## 4) Generate compact timing review

```bash
python tools/review_timing_study.py --study-dir <output_root>
```

Output:
- `<output_root>/compare/timing_study_review.md`

This local path is pre-MT4 research convenience only.
MT4 remains the final source of truth.
