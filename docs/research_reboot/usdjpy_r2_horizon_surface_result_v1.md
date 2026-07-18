# USDJPY R2 Fixed-Horizon Surface Result v1

## Decision

```text
R2 fixed-horizon surface: PASS
R3 temporal-stability diagnostics: unblocked but not started
candidate selection: none
H2 rows parsed: 0
2025 access: none
Core promotion: false
MT4 promotion: false
```

R2 evaluated every frozen R1 v2 Entry definition at every pre-registered fixed horizon. R2 does not choose a strategy or operational Exit.

## Accepted run

```text
workflow: Run Final Locked USDJPY R2 Fixed-Horizon Surface v1
run_id: 29646040010
head_sha: 314f286c0878b72a0f2ee2250eaa0e21ef558188
artifact_id: 8430064217
artifact: usdjpy-r2-horizon-surface-final-v1-29646040010
artifact_digest: sha256:84a495b7c7cddf1c719bb4c8ce78bfef2c990b355649d362c18481836d953426
```

The downloaded artifact ZIP was independently hashed and matched the GitHub artifact digest exactly.

## Frozen execution

```text
runner_blob: 2f629358edb861c74155319cc25ab77a3bd8e914
runner_content_sha256: fad3a5468fc819dfd7bede38021b78f49ad082080b753587d2a65fca56e35ff0
lock_blob: 5f0d4ea55191dd072d7202d443ba612b6f208e29
Entry definitions: 60
horizons: 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
surface combinations: 660
```

The runner and lock were committed before the accepted outcome run. The run read only their committed blobs.

## Input corrections completed before the accepted run

Two input-contract errors were corrected without changing any Entry definition, horizon, price rule, cost rule or performance gate:

1. the accepted R1 registry snapshot file digest is `3bb43eeb...67549`, not the previously transcribed `113f6f...` value;
2. the historical horizon regression source is authoritative artifact `8408094591`, not a path assumed to exist inside the R0 canonical artifact.

The legacy horizon artifact contains five May-Entry/June-Exit rows. The R2 preregistration requires Entry and Exit to remain in the same UTC month, so the historical reference was projected onto that fixed R2 domain before comparison. Exactly five legacy reference rows were excluded.

## Complete output shape

```text
trade rows: 383,078
candidate/horizon summary rows: 660
monthly rows: 3,960
direction rows: 1,320
surface rows: 60
ledger-hash rows: 660
historical regression rows: 117
zero-trade candidates: 0
```

All sixty R1 v2 Entry definitions generated at least one H1 signal. The earlier statement that five candidates had no signal was incorrect.

## Acceptance

All twenty-five acceptance checks passed, including:

- committed evaluator and lock blobs matched;
- R0 and R1 Release ZIP digests matched;
- authoritative horizon artifact digest matched;
- canonical M15, R1 signal and R1 registry snapshot internal digests matched;
- all sixty candidates and eleven horizons were present;
- all 660 combinations and complete monthly/direction grids were present;
- Entry followed signal and Entry/Exit remained in the same UTC month;
- hard no-trade violations were zero;
- default and severe cost formulas were exact;
- MFE/MAE fields were complete;
- deterministic trade ledger passed;
- exactly five cross-month legacy rows were excluded;
- all 117 projected historical horizon regressions passed;
- H2 rows parsed were zero;
- no 2025 artifact was accessed;
- no selection or promotion decision was emitted.

The maximum absolute difference in the historical numeric regressions was `1e-12`, below the fixed `1e-9` tolerance.

## Surface description

```text
default-cost positive combinations: 206 / 660
severe-cost positive combinations: 75 / 660
candidates with at least one default-positive horizon: 42 / 60
candidates with at least one severe-positive horizon: 32 / 60
```

These counts are descriptive. They are not a shortlist and do not account for the R3 temporal, concentration, spread or volatility diagnostics.

## Highest diagnostic points

The following are the ten largest H1 average default-cost values. They are not selected strategies and the listed horizon is not an approved Exit.

| Candidate | Family | Horizon | Trades | Avg default net | Default PF | Positive months | Avg severe net |
|---|---|---:|---:|---:|---:|---:|---:|
| R1K03_london_to_ny_cont | session_handoff | 32 | 24 | +16.202805 | 2.522926 | 4 | +14.008416 |
| R1K01_asia_to_london_cont | session_handoff | 48 | 31 | +13.529650 | 2.052852 | 4 | +11.398629 |
| R1H04_ramom_32_64_z125 | volatility_adjusted_momentum | 32 | 146 | +12.874060 | 2.120088 | 6 | +10.731084 |
| R1B02_legacy_asia_00_07_breakout | session_range_breakout | 32 | 99 | +10.690133 | 1.949010 | 5 | +8.550196 |
| R1H04_ramom_32_64_z125 | volatility_adjusted_momentum | 24 | 147 | +9.965267 | 1.946705 | 6 | +7.823013 |
| R1B02_legacy_asia_00_07_breakout | session_range_breakout | 48 | 97 | +9.919393 | 1.729683 | 6 | +7.780860 |
| R1K01_asia_to_london_cont | session_handoff | 32 | 31 | +9.631263 | 1.702627 | 4 | +7.500242 |
| R1K03_london_to_ny_cont | session_handoff | 24 | 25 | +9.351974 | 1.915774 | 4 | +7.163922 |
| R1K03_london_to_ny_cont | session_handoff | 16 | 25 | +9.083974 | 1.984366 | 4 | +6.895922 |
| R1K03_london_to_ny_cont | session_handoff | 48 | 24 | +8.890305 | 1.553720 | 2 | +6.695916 |

Several leading points have only 24–31 trades. R3 must distinguish genuine neighbouring-horizon structure from sparse-sample maxima and must test monthly, rolling-block, spread and realized-volatility attribution before any R4 representative selection.

## Principal hashes

```text
candidate_horizon_trades.csv.gz:
  70c2313147607096976a76328b72a628e42fa0001816f14824bcd9e9a3ead6c6
candidate_horizon_summary.csv:
  fa46a5db3e73c4d25b8e8c97ef4727c39d737cc8823080b23d21b0419d9e44f6
candidate_horizon_monthly.csv:
  43dcb463a1a6f7a668f56ab5339eddbec8c0a04cd506f3161204a7f2edf3ec3c
legacy_horizon_regression.csv:
  7fb451d5d5dbcc0080d6e0263a673994264eee568b6c26fe1fadbb980d48efe9
r2_acceptance.json:
  c1e37ec8721e9a0617d20da646fea11e8373c4c4cdbf8b64dea523d3950dca46
run_metadata.json:
  0593225bc449d8558a7f9acbfada4138a38e952b3672700eceb7e92a9c42e066
```

## Next stage

R3 may now evaluate all 660 combinations using H1-only temporal-stability diagnostics. R3 may not modify the sixty Entry definitions, eleven horizons, Entry/Exit timing or cost rules. Candidate reduction remains deferred to R4.
