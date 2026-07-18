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

R0 unblocks R1 only. It does not promote any strategy to Core or MT4.

## Corrected H1 screen

```text
run_id: 29547232643
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
artifact_digest: sha256:b5fd40e7c37cd3c4c417b9e02547ce6d7195f0f989266e4f0e3ae0305947ec94
```

The screen evaluated thirteen registered candidates, twelve unique Entry definitions and mostly six-bar time exits.

Retained complete strategies:

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

For all candidate definitions whose H2 results have never been opened, including C1-C4, B1-B3, D1-D2, E1-E2 and future H1-developed definitions, 2024 H2 remains candidate-specific unused validation data.

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
  next
  not started
  maximum sixty unique Entry definitions
  registry and parameter bounds must be committed before opening results

R2 — full fixed-horizon surface on 2024 H1:
  not started

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

2024 H1 plus candidate-specific unused 2024 H2 is sufficient to complete development, first confirmation and the decision to begin implementation parity. The full-year 2025 block is retained only because the expanded H1 programme will compare many Entry, horizon and controlled Exit configurations; a single six-month H2 pass may still reflect selection luck or a 2024-specific regime.

The 2025 block is one unchanged full-year replication, not two separate mandatory half-year gates and not an Exit-development block.

## Immediate operations

1. Define the R1 family taxonomy, candidate-generation rules and hard parameter bounds without viewing new H1 results.
2. Commit the expanded H1 Entry registry with at most sixty unique Entry definitions.
3. Run the R1 Entry screen on canonical 2024 H1 only.
4. Run the H1 horizon-surface and stability programme.
5. Select at most eight Entry/horizon representatives.
6. Perform controlled Exit research on H1 representatives.
7. Freeze at most five complete strategies and all H2 gates.
8. Run those strategies once on their candidate-specific unused 2024 H2 data.
9. Begin Research/Core and MT4 parity only for H2 survivors.
10. Run one unchanged full-year 2025 historical replication before live allocation.
