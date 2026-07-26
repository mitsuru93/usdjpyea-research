# Reproduction

Run `.github/workflows/usdjpy_csos_shock_failure_phase2_v1.yml` on the frozen Research ref. The workflow downloads only 2023/2024 authorities, verifies digests, materializes the 1,882-trade baseline ledger, and invokes `tools/evaluate_usdjpy_csos_shock_failure_phase2_v1.py`.
