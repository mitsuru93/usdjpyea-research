# Local Study Variant Pack Usage

Use this when you want a compact baseline-vs-variants study setup without writing every run block from scratch.

If you want the first timing-only pack (`baseline_touch` vs `rv_close_confirm` vs `all_close`), use:

- `configs/local/local_study_rv_close_confirm_pack.example.yaml`

If you want the **first real private-data timing run template** with practical compare sections and reading order, use:

- `configs/local/local_study_rv_close_confirm_first_real.example.yaml`
- `docs/first_timing_study_reading_guide.md`

## 1) Copy the example to a local ignored file

```bash
cp configs/local/local_study_variant_pack.example.yaml configs/local/local_study_variant_pack.yaml
```

The copied file path (`configs/local/local_study_variant_pack.yaml`) is git-ignored for local/private use.

Timing pack option:

```bash
cp configs/local/local_study_rv_close_confirm_pack.example.yaml configs/local/local_study_rv_close_confirm_pack.yaml
```

First-real timing option:

```bash
cp configs/local/local_study_rv_close_confirm_first_real.example.yaml configs/local/local_study_rv_close_confirm_first_real.yaml
```

## 2) Replace private CSV path

In your copied file, replace:

- `/ABSOLUTE/LOCAL/PATH/TO/usdjpy_m1_private.csv`

Use your real local absolute path and keep it private.

## 3) Run environment check

```bash
python tools/check_research_env.py --study-config configs/local/local_study_rv_close_confirm_first_real.yaml
```

## 4) Run the study

```bash
python tools/run_study.py --config configs/local/local_study_rv_close_confirm_first_real.yaml
```

## 5) Inspect compare outputs

Review side-by-side ranking outputs under:

- `<output_root>/compare/`

For first-real timing packs, prioritize in this order:
- `compare_overall.csv`
- `compare_by_family.csv`
- `compare_timing_by_decision_event.csv`
- `compare_timing_by_reject_reason.csv`
- `compare_timing_by_family_reject_reason.csv`
- `compare_timing_by_still_touch_status.csv`

Optional compact readout first:

```bash
python tools/review_timing_study.py --study-dir <output_root>
```

This writes `<output_root>/compare/timing_study_review.md` from existing compare CSVs.
It is a convenience review layer only (not MT4 validation).

Interpretation details are in `docs/first_timing_study_reading_guide.md`.

Use baseline vs variant comparison as **pre-MT4 candidate ranking only**.
MT4 remains the final source of truth.
