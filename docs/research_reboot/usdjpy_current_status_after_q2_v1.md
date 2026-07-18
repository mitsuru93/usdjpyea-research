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

## Accepted H1 entry-horizon diagnostic

```text
run_id: 29583719940
artifact: usdjpy-h1-entry-horizon-diagnostic-v2-29583719940
artifact_digest: sha256:f95a0a450aa3b821dbcb20ea4f3410f345668606bf5f20a766a3e01d8a6e89e4
```

The diagnostic passed all thirteen registered-hold regressions and showed that horizon materially changes candidate assessment. C4, C3, E2 and B2 showed slower positive regions. No strategy was promoted from the diagnostic.

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
```

A1 and E3 remain closed. Their direction, hours, lookback, hold or Exit may not be changed and presented as continuation of that H2 test.

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
  next

R1 — expanded Entry registry on 2024 H1 only:
  not started
  maximum sixty unique Entry definitions

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

1. Build and hash the canonical January-December 2024 bundle.
2. Reproduce all thirteen corrected H1 registered-hold results and the known A1/E3 H2 results.
3. Commit the expanded H1 Entry registry before opening expanded results.
4. Run the H1 horizon-surface and stability programme.
5. Perform controlled Exit research on H1 survivors.
6. Freeze at most five complete strategies and all H2 gates.
7. Run those strategies once on their candidate-specific unused 2024 H2 data.
8. Begin Research/Core and MT4 parity for H2 survivors.
9. Run one unchanged full-year 2025 historical replication before live allocation.
10. Move only replication and operational-gate survivors to live capital.
