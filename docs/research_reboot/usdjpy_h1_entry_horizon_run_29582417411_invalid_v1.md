# USDJPY H1 Entry-Horizon Run 29582417411 — Invalid

## Run

```text
workflow: Run USDJPY H1 Entry-Horizon Diagnostic
run_id: 29582417411
head_sha: 9f38731cbc72e2e9e7a139b0fedccaa28277a05e
artifact: usdjpy-h1-entry-horizon-diagnostic-v1-29582417411
artifact_digest: sha256:482d6095468c97efdec86f14710a3f2651598a0382df2b92540bb9caff5cc7a0
```

All workflow steps completed, and the A1 six-bar regression passed. The run is nevertheless invalid for research interpretation.

## Defect

The v1 runner loaded and evaluated each month separately. The authoritative corrected H1 screen concatenates January-June bars before generating signals.

The monthly reset removed valid entries at the start of a month or first trading day when a candidate required history from the preceding month. Examples at the registered hold period:

```text
B3: authoritative 94 trades; v1 diagnostic 90
E2: authoritative 372 trades; v1 diagnostic 368
E3: authoritative 361 trades; v1 diagnostic 354
```

A1 remained at 391 trades because its three-bar lookback did not expose this defect on the affected boundaries. Therefore the A1-only regression did not protect the other candidate families.

## Decision

- Do not use any horizon, stability, MFE or MAE result from run 29582417411.
- Do not make an exit or promotion decision from its artifact.
- Replace v1 with a contiguous-block v2 runner.
- Require regression of all 13 candidates at their registered hold periods before accepting the replacement run.
- The active A1+hold6 / E3+hold6 H2 is unchanged.
