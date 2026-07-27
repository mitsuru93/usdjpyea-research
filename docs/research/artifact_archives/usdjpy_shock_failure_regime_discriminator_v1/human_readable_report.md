# USDJPY Shock Failure Regime Discriminator Study v1

## Decision

`NO_PORTABLE_CANDIDATE`

- Hypothesis: `USDJPY-HYP-028`
- Selected candidate: `None`
- Best diagnostic model: `RD_TREE_D2_V1`
- Development only: 2023H1, 2023H2, 2024H1, 2024H2
- 2025 used for selection: `false`
- Production authorized: `false`

## Classification audit

- Fixed candidate opportunities reconstructed: 114
- Exact Raw Tick lifecycle labels reproducible: `True`
- Label differences versus the preserved historical approximation: 3
- Lookahead violations in feature ledger: 0

## Best diagnostic model

- Model: `RD_TREE_D2_V1`
- Frozen development threshold: 0.350
- Accepted trades: 69 / 114
- Net: ¥10521; PF: 3.401; MDD: ¥1232
- Net benefit versus unfiltered fixed candidate: ¥-1981
- Sustained-reversal profit retention: 67.9%
- Continuation-resumption loss rejection: 48.8%
- Nonnegative fold benefit: 2/4
- Portable gates passed: `False`

## Boundary

The rejected fixed candidate `B_EXECUTABLE_T0_8BAR` was not retuned. Oracle lifecycle labels were used only as development labels. Every candidate feature is timestamped at or before the entry decision boundary. Profit-then-giveback exit optimization was not mixed into admission. Core/MT4 and production remain locked unless a portable Research candidate passes every preregistered gate.

## Source authority

```json
{
  "2025_inputs_present_in_selection_process": false,
  "core_sha_read_only": "151d84b0dca3fe92a59663f56fd458727de2dbe0",
  "development_periods": [
    "2023H1",
    "2023H2",
    "2024H1",
    "2024H2"
  ],
  "m15_2023_sha256": "4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78",
  "m15_2024_sha256": "d22a008247e2a8bed49a5169648661ab21eff404a6bc2985bca0c3b5af290020",
  "phase2_ledger_sha256": "8de783dd8b560f976f31b7a28a640997b92c4814013692dde8ad4f3f48758011",
  "raw_2023_monthly_archives": 12,
  "raw_2024_monthly_archives": 12,
  "research_sha": "8d1b13b5d6ff51e589e345bb13b25d9924694eab",
  "run_id": "30259805223",
  "schema_version": "usdjpy_shock_failure_regime_discriminator_v1_source_manifest"
}
```
