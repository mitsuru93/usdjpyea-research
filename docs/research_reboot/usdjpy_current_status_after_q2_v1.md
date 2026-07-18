# USDJPY Research Current Status v1

## Governing boundary

```text
repository: mitsuru93/usdjpyea-research
Research role: pre-MT4 candidate screener
Core / MT4: final source of truth
research data currently permitted: canonical 2024 H1 only
H2 access for new candidates: prohibited until R6 freeze
2025 access: prohibited until the unchanged V2 replication
live capital allocation: prohibited
```

R0 through R4 are accepted. R5 Exit policies are preregistered but no accepted R5 result exists yet.

## Verified 2024 data

The accepted Dukascopy USDJPY source covers January through December 2024. Every accepted source month has effective coverage 100%, zero unobserved records and zero terminal hard errors.

November uses accepted rerun source artifact `8421758330` and baseline artifact `8423419800`. First-attempt source artifact `8412658745` remains excluded.

Durable input archive:

```text
release_tag: usdjpy-r0-artifact-archive-2024-v1
accepted original artifacts: 288
source day artifacts: 261
source aggregate artifacts: 12
baseline artifacts: 12
authoritative regression artifacts: 3
receipt: docs/research_reboot/artifact_archives/usdjpy_r0_2024_v1/
```

No 2025 artifact is an accepted input to the current programme.

## R0 — accepted canonical bundle

```text
status: PASS
run_id: 29639548804
head_sha: 2d88fb846bbe77e256ee37abdf1dcbb462e3ebe4
artifact_id: 8428199309
artifact: usdjpy-r0-canonical-2024-v1-29639548804
artifact_digest: sha256:d67db9b051a03050ddedb720d407b73cb48c5eacf7a441b1b8ff98dd77dc2015
release_tag: usdjpy-r0-canonical-2024-v1
result: docs/research_reboot/usdjpy_r0_canonical_bundle_result_v1.md
```

Canonical timeframes are M1, M5, M15 and H1. Repeated builds were byte-identical, same-priority conflicts were zero, and the historical H1 and A1/E3 H2 artifacts were reproduced from the canonical bundle. R0 made no strategy promotion.

## R1 — accepted corrected Entry registry v2

```text
status: PASS
run_id: 29642282221
head_sha: 9393e4ac9ec7d712f85c29e9ef7f44025de25403
artifact_id: 8428977454
artifact: usdjpy-r1-entry-registry-v2-29642282221
artifact_digest: sha256:0e0de71ccc56409a919d48d61e4dcb12502cefdb3944374b9163eda76d222d74
release_tag: usdjpy-r1-entry-registry-v2
result: docs/research_reboot/usdjpy_r1_entry_registry_result_v2.md
receipt: docs/research_reboot/artifact_archives/usdjpy_r1_entry_registry_v2/
```

```text
families: 12
unique Entry definitions: 60
legacy unique Entry definitions: 12
new Entry definitions: 48
Entry signal rows: 34,955
historical registered-hold regressions: 13 / 13 passed
H2 rows parsed: 0
2025 access: none
outcomes opened in R1: false
```

R1 v1 run `29641805182` and artifact `8428842719` remain excluded because the Entry-hour gate was applied to the signal-bar hour instead of the actual next-bar Entry hour. No candidate definition or parameter was changed in the v2 correction.

## R2 — accepted fixed-horizon surface

```text
status: PASS
run_id: 29646040010
head_sha: 314f286c0878b72a0f2ee2250eaa0e21ef558188
artifact_id: 8430064217
artifact: usdjpy-r2-horizon-surface-final-v1-29646040010
artifact_digest: sha256:84a495b7c7cddf1c719bb4c8ce78bfef2c990b355649d362c18481836d953426
release_tag: usdjpy-r2-horizon-surface-v1
result: docs/research_reboot/usdjpy_r2_horizon_surface_result_v1.md
receipt: docs/research_reboot/artifact_archives/usdjpy_r2_horizon_surface_v1/
```

```text
Entry definitions: 60
fixed M15 horizons: 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48
surface combinations: 660
trade rows: 383,078
monthly rows: 3,960
direction rows: 1,320
historical projected regressions: 117 / 117 passed
legacy cross-month reference rows excluded under fixed same-month rule: 5
H2 rows parsed: 0
2025 access: none
selection or promotion: false
```

R2 selected no winner and treated each horizon only as a diagnostic fixed-time Exit.

## R3 — accepted temporal and regime stability diagnostics

```text
status: PASS
run_id: 29647304892
head_sha: 22a72f0cf1185e072d16afcdc64651502f2db83c
artifact_id: 8430424186
artifact: usdjpy-r3-temporal-stability-v1-29647304892
artifact_digest: sha256:bf906aa45e426146073d099ac2cf692067b4831256cd22de11e25f0e13b3e292
release_tag: usdjpy-r3-temporal-stability-v1
receipt: docs/research_reboot/artifact_archives/usdjpy_r3_temporal_stability_v1/
```

R3 retained all 660 combinations and reported complete monthly, quarterly, rolling-block, anchored, spread, RV32, RV96, direction, concentration and neighbouring-horizon grids.

```text
sample class standard: 572
sample class moderate: 44
sample class sparse: 44
H2 rows parsed: 0
2025 access: none
shortlist or promotion: false
```

The R3 Release was rebuilt to contain exactly its own ZIP, manifest and SHA256SUMS after detecting and removing R2 work-file contamination.

## R4 — accepted Entry/horizon representative selection

```text
status: PASS
run_id: 29665005273
head_sha: 854c1ea9a841eefd3942d99b059bd40363f6bcde
artifact_id: 8435465130
artifact: usdjpy-r4-entry-horizon-selection-v1-29665005273
artifact_digest: sha256:b201565ab5d1a531f54c066849e92223d0a4fa722f110bef7925cde7c10a4a97
release_tag: usdjpy-r4-entry-horizon-selection-v1
result: docs/research_reboot/usdjpy_r4_entry_horizon_selection_result_v1.md
receipt: docs/research_reboot/artifact_archives/usdjpy_r4_entry_horizon_selection_v1/
```

R4 applied the preregistered common gates, equal-weight twelve-component percentile rank and redundancy controls to all 660 combinations.

```text
fully eligible combinations: 14
frozen representatives: 8
pairwise eligible comparisons: 91
maximum per family: 2
maximum per Entry definition: 1
H2 rows parsed: 0
2025 access: none
Exit optimization: false
Core promotion: false
MT4 promotion: false
```

Frozen representatives:

| Rank | Candidate | Family | Diagnostic time cap |
|---:|---|---|---:|
| 1 | R1H04_ramom_32_64_z125 | volatility_adjusted_momentum | 32 |
| 2 | R1B02_legacy_asia_00_07_breakout | session_range_breakout | 48 |
| 3 | R1E02_legacy_trend_8h_resumption | trend_pullback_resumption | 48 |
| 4 | R1A04_impulse_lb24_med16_x125 | impulse_breakout | 48 |
| 5 | R1F05_donchian_96 | donchian_channel_breakout | 32 |
| 6 | R1E03_trend_12h_resumption | trend_pullback_resumption | 32 |
| 7 | R1H05_ramom_48_96_z125 | volatility_adjusted_momentum | 12 |
| 8 | R1F04_donchian_64 | donchian_channel_breakout | 24 |

These are H1 research representatives, not complete strategies.

## R5 — controlled Exit research preregistered; formal result not accepted

Authoritative preregistration:

```text
configuration: configs/research/usdjpy_r5_controlled_exit_v1.json
configuration commit: b9f5f5b0836087414eaa5b905bab8c528fb1476e
preregistration: docs/research_reboot/usdjpy_r5_controlled_exit_prereg_v1.md
preregistration commit: 04474a1066b0d9358c7bbff28f339bb410c989d5
```

The exact R4 Entry cohort contains 2,982 rows. ATR14 calculated through the completed signal bar is available for all 2,982 rows.

Four common policies are frozen:

```text
T0_fixed_time_cap
S1_static_stop_2atr
B1_bracket_1p5_3atr
C1_chandelier_3atr
```

```text
representative/policy combinations: 32
Entry rows per policy: 2,982
expected policy trade rows: 11,928
parameter sweep: false
candidate-specific Exit parameters: false
same Entry keys across policies: required
T0 exact R2 regression: required
R5 selection or promotion: false
H2 / 2025 / Core / MT4: closed
```

Run `29665727132` is excluded. It failed during pre-data payload-container verification and did not download inputs or calculate Exit outcomes. The compressed-container assertion is being replaced by gzip integrity, exact source length and exact decompressed evaluator SHA-256 verification; the R5 policy specification is unchanged.

## Historical A1/E3 H2 result

```text
run_id: 29628387393
artifact_id: 8424623578
artifact: usdjpy-joint-h2-a1-e3-eval-v1-29628387393
artifact_digest: sha256:182840ea48bf9d375ce718a5c940cee064fbccb4c36b659a80e7678938664364
A1_impulse_breakout_lb3_hold6: failed
E3_trend_24h_resumption_hold6: failed
decision: neither_advances
```

A1 and E3 remain closed. Their direction, hours, lookback, hold or Exit may not be modified and presented as continuation of that H2 test.

The project-level 2024 H2 block is therefore not globally untouched. It remains candidate-specific unused validation data for strategies whose H2 outcomes have never been opened.

## Authoritative roadmap

```text
roadmap: docs/research_reboot/usdjpy_research_roadmap_2024_primary_2025_replication_v4.md
roadmap commit: 8c6ec53cedf05cfb0fc6a49d17f8cf7e79828995
```

```text
R0 canonical bundle: PASS
R1 corrected Entry registry: PASS
R2 complete fixed-horizon surface: PASS
R3 temporal/regime diagnostics: PASS
R4 maximum-eight representative selection: PASS
R5 controlled Exit research: preregistered; accepted run pending
R6 maximum-five complete-strategy freeze and H2 gates: not started
V1 one joint candidate-specific unused 2024 H2 validation: not started
Research/Core and MT4 parity: only after V1 pass
V2 one unchanged full-year 2025 replication: not started
forward/operational gate: not started
live capital allocation: prohibited
```

## Immediate operation

Complete the formal frozen R5 run and independent artifact audit. If R5 passes, preregister the R6 complete-strategy eligibility, maximum-five selection, redundancy treatment and candidate-specific unused H2 gates before selecting any Entry/Exit combination.
