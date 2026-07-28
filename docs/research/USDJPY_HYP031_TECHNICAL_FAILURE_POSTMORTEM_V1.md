# USDJPY-HYP-031 Run 30316460286 Technical Failure Postmortem

## Classification

`TECHNICAL_PARTIAL_RESULT_EXPOSED`

The evaluator completed the source-native 2023–2024 study, created `final_decision.json`, candidate metrics and partial ledgers, and exposed `NO_PORTABLE_REGIME_RULE` in receipt Issue #348 before the workflow stopped. This was not a scientific no-result stop.

## Exact failure

At failed head `ed477f3edcc4aa36bc8d7a5388aa60e2e73cf4b0`, line 107 of `.github/workflows/usdjpy_asian_range_sweep_regime_development_v1.yml` ran a wrapper `jq -e` postcondition requiring `audits.chronology_unresolved == 0`. The completed result recorded `4`, so the predicate returned false and the shell step exited nonzero. Evidence packaging and artifact upload were skipped. The evaluator itself did not crash.

## Result-preserving repair

Commit `2ce710467fb44efbeb904064736c76ad36b01efb` finalized stdout logging after evaluator completion, regenerated package checksums, and limited wrapper postconditions to schema/firewall invariants. Evaluator SHA-256 remained `652c55d408339cf6609896071fdddcb7c50241a874e163a4a6aede1731b6fc2c`. Candidate definitions, source contract, formulas, thresholds, gates and period roles were unchanged.

Run `30317593695` completed with artifact `8672872755`, digest `sha256:a59aec0841568c0036e4031631e1f009a65527a1828af4290e4dbe05be7636ee`, and receipt Issue #350. No pre-2023 strategy outcome, Core/MT4 or 2025 evidence was opened.
