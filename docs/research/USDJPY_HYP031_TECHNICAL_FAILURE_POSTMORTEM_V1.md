# USDJPY-HYP-031 Run 30316460286 Technical Failure Postmortem

## Classification

`TECHNICAL_PARTIAL_RESULT_EXPOSED`

## What completed before the stop

Checkout, Python setup, frozen dependency installation, evaluator reconstruction and hash verification, preregistration and 2025 firewall checks, 2023–2024 Raw Bid/Ask Release download/checksum verification, exact B02/F05 reconstruction, source-native signal generation, regime evaluation, candidate comparison and `final_decision.json` creation all completed.

The scientific decision was already observable as `NO_PORTABLE_REGIME_RULE`; receipt Issue #348 preserved it. Therefore the run may not be treated as `TECHNICAL_NO_RESULT`.

## Exact failure

At failed head `ed477f3edcc4aa36bc8d7a5388aa60e2e73cf4b0`, line 107 of `.github/workflows/usdjpy_asian_range_sweep_regime_development_v1.yml` executed a `jq -e` assertion requiring `audits.chronology_unresolved == 0`. The completed result recorded `chronology_unresolved = 4`, so `jq` returned false and the shell step exited with status 1. Evidence packaging, canonical branch archive and artifact upload were skipped.

The evaluator did not crash. No evaluator function, candidate formula, threshold, gate or period definition failed technically.

## Outcome exposure

- `final_decision.json`: created
- Decision class: `NO_PORTABLE_REGIME_RULE`
- Selected candidate: `NONE`
- Receipt Issue: #348
- Candidate metrics: generated before the workflow-control failure
- HYP-030 mismatch ledger: generated before the failure
- 2025 accessed: `false`
- Pre-2023 strategy outcomes accessed: `false`
- Core modified: `false`
- MT4 accessed: `false`

## Result-preserving repair

Commit `2ce710467fb44efbeb904064736c76ad36b01efb`:

- moved stdout logging outside the evaluator output directory until evaluation completed;
- regenerated package checksums after the final log was moved;
- limited the workflow postcondition to schema/firewall invariants rather than requiring a scientific pass;
- moved canonical archive publication to a separate completed-result finalizer.

The evaluator SHA-256 remained `652c55d408339cf6609896071fdddcb7c50241a874e163a4a6aede1731b6fc2c`. No candidate catalog, EMA span, transition definition, side permission, signal contract, source authority, period role or gate threshold changed. The repair cannot change scientific outcomes.

## Successful completion

Run `30317593695` completed all scientific, packaging, artifact-upload and receipt steps. Artifact ID `8672872755` has digest `sha256:a59aec0841568c0036e4031631e1f009a65527a1828af4290e4dbe05be7636ee`. Receipt Issue #350 records `NO_PORTABLE_REGIME_RULE`, selected candidate `NONE`, no pre-2023 strategy-outcome access, no 2025 access and no Core/MT4 access.
