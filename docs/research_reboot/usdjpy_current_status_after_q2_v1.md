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

## Durable 2024 artifact archive

All accepted 2024 inputs and authoritative regression artifacts are preserved independently of GitHub Actions artifact expiry.

```text
release_tag: usdjpy-r0-artifact-archive-2024-v1
release_assets: 29
accepted_original_artifacts: 288
source_day_artifacts: 261
source_aggregate_artifacts: 12
baseline_artifacts: 12
authoritative_regression_artifacts: 3
```

Archive receipt:

```text
docs/research_reboot/artifact_archives/usdjpy_r0_2024_v1/
```

The excluded November artifact `8412658745` is recorded but is not archived as an accepted input. No 2025 artifact is present.

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

Verified outputs:

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

## Accepted R1 Entry registry

```text
run_id: 29641805182
head_sha: 50411297d1743518371b06f0eceb039ab185bd89
artifact_id: 8428842719
artifact: usdjpy-r1-entry-registry-v1-29641805182
artifact_digest: sha256:a284e599c67910912d1e51c79d55ba4334e726ef423aba1b8ecb6a3e1ef9f27c
release_tag: usdjpy-r1-entry-registry-v1
result: docs/research_reboot/usdjpy_r1_entry_registry_result_v1.md
```

R1 passed all twenty acceptance checks.

Frozen Entry universe:

```text
families: 12
unique Entry definitions: 60
legacy unique Entry definitions: 12
new Entry definitions: 48
functional-definition duplicates: 0
exact signal-equivalent groups: 0
Entry signal rows: 34,636
H2 rows parsed: 0
2025 access: none
outcomes opened: false
```

All sixty definitions generated Entry signals. Fifty-nine were active in all six H1 months; one session-handoff definition was active in five months. The complete monthly, hourly and 1,770-pair overlap grids were generated. No Entry price, Exit, horizon, cost, PnL, profit factor, expectancy or promotion result was opened in R1.

The accepted R1 artifact is preserved independently of Actions expiry:

```text
archive_run_id: 29641911300
archive_audit_artifact_id: 8428870489
archive_audit_digest: sha256:13a897ecf822f847fc607324d00c7375d637037261881770df85b9e0d4a557df
receipt: docs/research_reboot/artifact_archives/usdjpy_r1_entry_registry_v1/
```

R1 unblocks R2 only. Signal count is not a performance ranking.

## Corrected H1 screen

```text
run_id: 29547232643
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
artifact_digest: sha256:b5fd40e7c37cd3c4c417b9e02547ce6d7195f0f989266e4f0e3ae0305947ec94
```

The screen evaluated thirteen registered candidates, twelve unique Entry definitions and mostly six-bar time exits.

Retained historical complete strategies:

```text
A1_impulse_breakout_lb3_hold6
E3_trend_24h_resumption_hold6
```

R0 reproduced the full thirteen-candidate summary, all seventy-eight monthly rows and the normalized trade ledger from the canonical M15 input.

## Accepted H1 entry-horizon diagnostic

```text
run_id: 29583719940
artifact: usdjpy-h1-entry-horizon-diagnostic-v2-29583719940
artifact_digest: sha256:f95a0a450aa3b821dbcb20ea4f3410f345668606bf5f20a766a3e01d8a6e89e4
```

The diagnostic passed all thirteen registered-hold regressions and showed that horizon materially changes candidate assessment. C4, C3, E2 and B2 showed slower positive regions. No strategy was promoted from the diagnostic.

R0 locked its structure at thirteen registered candidates, twelve unique Entry definitions, no H2 read and no promotion decision.

## Accepted A1/E3 H2 result

```text
run_id: 29628387393
artifact_id: 8424623578
artifact: usdjpy-joint-h2-a1-e3-eval-v1-29628387393
artifact_digest: sha256:182840ea48bf9d375ce718a5c940cee064fbccb4c36b659a80e7678938664364
```

Decision:

```text
A1_impulse_breakout_lb3_hold6: failed
E3_trend_24h_resumption_hold6: failed
advancing candidates: none
decision: neither_advances
```

A1 and E3 remain closed. Their direction, hours, lookback, hold or Exit may not be changed and presented as continuation of that H2 test.

R0 reproduced the H1 regression, H2 summary, monthly results, gates, direction attribution, daily attribution, normalized trade ledger and final decision from the canonical M15 input.

## Correct interpretation of 2024 H2

The 2024 H2 block has been opened only for A1+hold6 and E3+hold6.

For all candidate definitions whose H2 results have never been opened, including the new R1 definitions and the historical B/C/D/E definitions other than A1/E3, 2024 H2 remains candidate-specific unused validation data.

Methodological distinction:

```text
project-level globally untouched: no, because A1/E3 H2 results are known
candidate-specific unused: yes, for every strategy whose H2 outcome has not been opened
```

New complete strategies must be developed and frozen from 2024 H1 only, then evaluated once on 2024 H2.

## Authoritative roadmap

```text
docs/research_reboot/usdjpy_research_roadmap_2024_primary_2025_replication_v4.md
commit: 8c6ec53cedf05cfb0fc6a49d17f8cf7e79828995
```

Superseded roadmaps:

```text
docs/research_reboot/usdjpy_research_roadmap_after_h2_failure_v1.md
docs/research_reboot/usdjpy_research_roadmap_full_2024_development_v2.md
docs/research_reboot/usdjpy_research_roadmap_h1_development_h2_validation_v3.md
```

## Research roadmap

```text
R0 — canonical 2024 bundle and regression lock:
  passed
  run_id 29639548804
  artifact_id 8428199309

R1 — expanded Entry registry on 2024 H1 only:
  passed
  run_id 29641805182
  artifact_id 8428842719
  60 unique Entry definitions across 12 families

R2 — full fixed-horizon surface on 2024 H1:
  next
  not started
  horizons: 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
  complete surface: 660 Entry/horizon combinations

R3 — H1 temporal-stability diagnostics:
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

## Why 2025 is retained

2025 does not replace 2024 and is not used before the 2024 programme is complete.

2024 H1 plus candidate-specific unused 2024 H2 is sufficient to complete development, first confirmation and the decision to begin implementation parity. The full-year 2025 block is retained only because the expanded H1 programme compares sixty Entry definitions, eleven fixed horizons and controlled Exit configurations; a six-month H2 pass may still reflect selection luck or a 2024-specific regime.

The 2025 block is one unchanged full-year replication, not two separate mandatory half-year gates and not an Exit-development block.

## Immediate operations

1. Freeze the R2 evaluator, cost rules, price-path outputs and all 660 Entry/horizon combinations before opening outcomes.
2. Run the complete fixed-horizon surface on canonical 2024 H1 only.
3. Run R3 monthly, Q1/Q2, rolling-block, spread and realized-volatility stability diagnostics.
4. Select at most two representatives per family and eight overall using pre-registered common requirements.
5. Perform controlled Exit research on the H1 representatives.
6. Freeze at most five complete strategies and all H2 gates.
7. Run those strategies once on their candidate-specific unused 2024 H2 data.
8. Begin Research/Core and MT4 parity only for H2 survivors.
9. Run one unchanged full-year 2025 historical replication before live allocation.
