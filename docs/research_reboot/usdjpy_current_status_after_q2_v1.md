# USDJPY Research Status After Q2 v1

## Verified data

The accepted Dukascopy USDJPY source covers January through December 2024.

Every accepted month has:

```text
fixed weekday-hour audit: passed
unobserved records: 0
terminal hard errors: 0
effective coverage: 100%
```

November uses accepted rerun artifacts:

```text
source artifact_id: 8421758330
baseline artifact_id: 8423419800
```

First-attempt November source artifact `8412658745` remains excluded.

## Durable 2024 input archive

All accepted 2024 inputs and authoritative regression artifacts are preserved independently of GitHub Actions expiry.

```text
release_tag: usdjpy-r0-artifact-archive-2024-v1
release_assets: 29
accepted_original_artifacts: 288
source_day_artifacts: 261
source_aggregate_artifacts: 12
baseline_artifacts: 12
authoritative_regression_artifacts: 3
receipt: docs/research_reboot/artifact_archives/usdjpy_r0_2024_v1/
```

The excluded November artifact is recorded but is not archived as an accepted input. No 2025 artifact is present.

## Accepted R0 canonical bundle

```text
run_id: 29639548804
head_sha: 2d88fb846bbe77e256ee37abdf1dcbb462e3ebe4
artifact_id: 8428199309
artifact: usdjpy-r0-canonical-2024-v1-29639548804
artifact_digest: sha256:d67db9b051a03050ddedb720d407b73cb48c5eacf7a441b1b8ff98dd77dc2015
release_tag: usdjpy-r0-canonical-2024-v1
result: docs/research_reboot/usdjpy_r0_canonical_bundle_result_v1.md
```

R0 passed all twenty acceptance checks.

```text
Release assets: 29 verified
original artifact ZIPs: 288 verified
source months: 12 / 12 at effective coverage 1.0
unobserved records: 0
hard source errors: 0
canonical timeframes: M1, M5, M15, H1
deterministic repeated builds: byte-identical
same-priority conflicts: 0
H1 candidate summary/monthly/normalized ledger: exact
A1/E3 H2 required outputs/normalized ledger/decision: exact
hard no-trade violations: H1 0, H2 0
2025 artifact access: none
```

R0 did not promote any strategy to Core or MT4.

## Accepted corrected R1 Entry registry v2

```text
run_id: 29642282221
head_sha: 9393e4ac9ec7d712f85c29e9ef7f44025de25403
artifact_id: 8428977454
artifact: usdjpy-r1-entry-registry-v2-29642282221
artifact_digest: sha256:0e0de71ccc56409a919d48d61e4dcb12502cefdb3944374b9163eda76d222d74
release_tag: usdjpy-r1-entry-registry-v2
result: docs/research_reboot/usdjpy_r1_entry_registry_result_v2.md
```

R1 v2 passed the Entry-registry contract and all thirteen historical registered-hold Entry regressions.

```text
families: 12
unique Entry definitions: 60
legacy unique Entry definitions: 12
new Entry definitions: 48
Entry signal rows: 34,955
historical registered-hold regressions: 13 / 13 passed
H2 rows parsed: 0
2025 access: none
outcomes opened: false
```

All sixty definitions generated at least one Entry signal. The earlier statement that five definitions had zero signals was incorrect.

R1 v1 run `29641805182` and artifact `8428842719` are excluded because `entry_hours_utc` was applied to the signal-bar hour rather than the actual next-bar Entry hour. The candidate definitions and parameters did not change in the correction.

The corrected R1 artifact is preserved at Release `usdjpy-r1-entry-registry-v2` with receipt:

```text
docs/research_reboot/artifact_archives/usdjpy_r1_entry_registry_v2/
```

R1 unblocked R2 only. Signal count was not a performance ranking.

## Accepted R2 fixed-horizon surface

```text
run_id: 29646040010
head_sha: 314f286c0878b72a0f2ee2250eaa0e21ef558188
artifact_id: 8430064217
artifact: usdjpy-r2-horizon-surface-final-v1-29646040010
artifact_digest: sha256:84a495b7c7cddf1c719bb4c8ce78bfef2c990b355649d362c18481836d953426
release_tag: usdjpy-r2-horizon-surface-v1
result: docs/research_reboot/usdjpy_r2_horizon_surface_result_v1.md
receipt: docs/research_reboot/artifact_archives/usdjpy_r2_horizon_surface_v1/
```

R2 passed all twenty-five acceptance checks.

```text
Entry definitions: 60
fixed horizons: 11
surface combinations: 660
trade rows: 383,078
monthly rows: 3,960
direction rows: 1,320
surface rows: 60
ledger-hash rows: 660
historical projected regressions: 117 / 117 passed
legacy cross-month reference rows excluded: 5
zero-trade candidates: 0
H2 rows parsed: 0
2025 access: none
selection or promotion decision: false
```

The R2 runner and execution lock were committed before the accepted run:

```text
runner_blob: 2f629358edb861c74155319cc25ab77a3bd8e914
runner_content_sha256: fad3a5468fc819dfd7bede38021b78f49ad082080b753587d2a65fca56e35ff0
lock_blob: 5f0d4ea55191dd072d7202d443ba612b6f208e29
```

Two input-contract errors were corrected before the accepted run without changing Entry, horizon, cost or performance rules:

1. the accepted R1 registry snapshot digest is `3bb43eeb...67549`, not the previously transcribed value;
2. the historical regression source is authoritative artifact `8408094591`, rather than a nonexistent path inside the R0 artifact.

The legacy horizon artifact contained five May-Entry/June-Exit rows. They were excluded from the reference projection under the preregistered R2 same-UTC-month rule. All 117 candidate/horizon projected regressions then passed with maximum absolute numeric difference `1e-12`.

R2 evaluated the complete surface and selected nothing. R3 is unblocked and must assess temporal stability, concentration, spread and realized-volatility attribution before R4 representative selection.

## Historical corrected H1 screen

```text
run_id: 29547232643
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
artifact_digest: sha256:b5fd40e7c37cd3c4c417b9e02547ce6d7195f0f989266e4f0e3ae0305947ec94
```

The screen evaluated thirteen registered candidates, twelve unique Entry definitions and mostly six-bar time exits.

Historical retained complete strategies were:

```text
A1_impulse_breakout_lb3_hold6
E3_trend_24h_resumption_hold6
```

R0 reproduced the full thirteen-candidate summary, all seventy-eight monthly rows and the normalized trade ledger from canonical M15 input.

## Historical H1 entry-horizon diagnostic

```text
run_id: 29583719940
artifact_id: 8408094591
artifact: usdjpy-h1-entry-horizon-diagnostic-v2-29583719940
artifact_digest: sha256:f95a0a450aa3b821dbcb20ea4f3410f345668606bf5f20a766a3e01d8a6e89e4
```

This artifact is now used only as an implementation-regression reference projected onto the R2 same-month domain. It does not promote a strategy.

## Accepted A1/E3 H2 result

```text
run_id: 29628387393
artifact_id: 8424623578
artifact: usdjpy-joint-h2-a1-e3-eval-v1-29628387393
artifact_digest: sha256:182840ea48bf9d375ce718a5c940cee064fbccb4c36b659a80e7678938664364
```

```text
A1_impulse_breakout_lb3_hold6: failed
E3_trend_24h_resumption_hold6: failed
advancing candidates: none
decision: neither_advances
```

A1 and E3 remain closed. Their direction, hours, lookback, hold or Exit may not be changed and presented as continuation of that H2 test.

## Correct interpretation of 2024 H2

The 2024 H2 block has been opened only for A1+hold6 and E3+hold6.

For all other candidate definitions, including the new R1 definitions and historical B/C/D/E definitions other than A1/E3, 2024 H2 remains candidate-specific unused validation data.

```text
project-level globally untouched: no, because A1/E3 H2 results are known
candidate-specific unused: yes, for every strategy whose H2 outcome has not been opened
```

New complete strategies must be developed and frozen from 2024 H1 only, then evaluated once on candidate-specific unused 2024 H2.

## Authoritative roadmap

```text
docs/research_reboot/usdjpy_research_roadmap_2024_primary_2025_replication_v4.md
commit: 8c6ec53cedf05cfb0fc6a49d17f8cf7e79828995
```

## Research roadmap

```text
R0 — canonical 2024 bundle and regression lock:
  passed
  run_id 29639548804
  artifact_id 8428199309

R1 — expanded Entry registry on 2024 H1 only:
  passed
  corrected run_id 29642282221
  artifact_id 8428977454
  60 unique Entry definitions across 12 families

R2 — full fixed-horizon surface on 2024 H1:
  passed
  run_id 29646040010
  artifact_id 8430064217
  660 Entry/horizon combinations
  117 / 117 projected historical regressions passed
  no candidate selection or promotion

R3 — H1 temporal-stability diagnostics:
  next
  not started

R4 — select at most eight Entry/horizon representatives:
  not started

R5 — controlled Exit research on 2024 H1:
  not started
  maximum four Exit policies per mechanism

R6 — freeze at most five complete strategies and H2 gates:
  not started

V1 — one joint candidate-specific unused 2024 H2 validation:
  not started

Engineering — Research/Core and MT4 parity for V1 survivors:
  may begin immediately after V1 pass

V2 — one unchanged full-year 2025 historical replication:
  not started
  2025-01-01 through 2026-01-01 exclusive

Forward / operational gate:
  not started

Live capital allocation:
  prohibited until V2 and operational gates pass
```

## Immediate operations

1. Freeze R3 diagnostics and common interpretation rules before opening new derived rankings.
2. Run monthly, Q1/Q2, rolling two- and three-month, spread and realized-volatility attribution for all 660 combinations.
3. Evaluate neighbouring-horizon support and day/month concentration without selecting an isolated maximum.
4. Freeze the R4 common requirements and sample classes.
5. Select at most two representatives per family and eight overall.
6. Perform controlled Exit research only on the selected H1 representatives.
7. Freeze at most five complete strategies and all H2 gates.
8. Run those strategies once on candidate-specific unused 2024 H2.
9. Begin Research/Core and MT4 parity only for H2 survivors.
10. Run one unchanged full-year 2025 historical replication before live allocation.
