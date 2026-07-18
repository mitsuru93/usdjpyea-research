# USDJPY R0 Canonical Bundle Result v1

## Decision

```text
R0: PASS
R1: unblocked but not started
Core promotion: false
MT4 promotion: false
2025 data access: none
```

R0 establishes one durable and byte-deterministic 2024 USDJPY research input and proves that the authoritative H1 and known A1/E3 H2 results are reproduced from it. It does not promote any strategy.

## Accepted run

```text
workflow: Run USDJPY R0 Canonical Bundle v1
run_id: 29639548804
head_sha: 2d88fb846bbe77e256ee37abdf1dcbb462e3ebe4
artifact_id: 8428199309
artifact: usdjpy-r0-canonical-2024-v1-29639548804
artifact_digest: sha256:d67db9b051a03050ddedb720d407b73cb48c5eacf7a441b1b8ff98dd77dc2015
```

The downloaded artifact ZIP was independently hashed after the run and matched the GitHub Actions artifact digest exactly.

## Frozen durable input

```text
release_tag: usdjpy-r0-artifact-archive-2024-v1
release_assets: 29
accepted_original_artifacts: 288
source_day_artifacts: 261
source_aggregate_artifacts: 12
baseline_artifacts: 12
authoritative_regression_artifacts: 3
excluded_artifact_id: 8412658745
```

All 28 payload assets listed in `SHA256SUMS` matched their stored SHA-256 digests. The twenty-ninth Release asset is `SHA256SUMS` itself. All 288 original artifact ZIPs matched their recorded GitHub Actions artifact digests.

The excluded first November aggregate artifact `8412658745` was absent from the accepted inventory. No 2025 artifact was read or included.

## Source coverage

The accepted monthly baseline manifest is the coverage authority. Every month passed the fixed weekday-hour audit:

| Month | Expected | Observed | Unobserved | Hard errors | Effective coverage |
|---|---:|---:|---:|---:|---:|
| 2024-01 | 528 | 528 | 0 | 0 | 1.0 |
| 2024-02 | 504 | 504 | 0 | 0 | 1.0 |
| 2024-03 | 504 | 504 | 0 | 0 | 1.0 |
| 2024-04 | 528 | 528 | 0 | 0 | 1.0 |
| 2024-05 | 552 | 552 | 0 | 0 | 1.0 |
| 2024-06 | 480 | 480 | 0 | 0 | 1.0 |
| 2024-07 | 552 | 552 | 0 | 0 | 1.0 |
| 2024-08 | 528 | 528 | 0 | 0 | 1.0 |
| 2024-09 | 504 | 504 | 0 | 0 | 1.0 |
| 2024-10 | 552 | 552 | 0 | 0 | 1.0 |
| 2024-11 | 504 | 504 | 0 | 0 | 1.0 |
| 2024-12 | 528 | 528 | 0 | 0 | 1.0 |

January begins at `2024-01-02T00:00:00Z`, matching the accepted collection range.

## Canonical annual bars

All canonical files use the fixed 22-column bid/ask/mid/spread schema, UTF-8, LF, `%.17g` float round-trip serialization and gzip `mtime=0`.

| Timeframe | Rows | Start UTC | End UTC | Canonical content SHA-256 | Gzip SHA-256 |
|---|---:|---|---|---|---|
| M1 | 360,759 | 2024-01-02T01:00:00Z | 2024-12-31T21:59:00Z | `bce1219722d28b5b1d990c9cc0a4cf11ec0b575590ad1501a5e73401db2f57e8` | `bd2d2643191e79a2655c5703e861ead23bee547e8c94a55a8f1582237a735722` |
| M5 | 73,302 | 2024-01-02T00:00:00Z | 2024-12-31T21:55:00Z | `8ad007fa08f96f04ff462a04860a0ce88091865ea95adcdfb05a43a1eb478d56` | `65ab9d3d9b830a169058010fd5ca06249330631b4522efb56e838807890e431b` |
| M15 | 24,439 | 2024-01-02T00:00:00Z | 2024-12-31T21:45:00Z | `a79c6c023e7602edc784a69ae9ccde98ad362982c679763a83c5e2d287d47754` | `1566b9d0497f3a2aa156868144d31b89721fca48329feaf82035826ada7ee25c` |
| H1 | 6,034 | 2024-01-02T01:00:00Z | 2024-12-31T21:00:00Z | `43c2181055189f91ed4e25116719547c835a8f8b5a476d243fd4ceaedc527ead` | `235cae3c81c3c9e33d08dc670cd6beb2a4a2a220f1b55626a0df4d575f8ce5bb` |

The complete canonical output was generated twice independently in the same run. All eight compared output files matched byte-for-byte. No same-priority conflict or unresolved duplicate remained.

Canonical manifest:

```text
sha256:38991daed90f836217af7d871a5799d8645dc7738cb9e5bf93a7e4ace2b71cf6
```

## H1 regression

The canonical M15 input reproduced the authoritative corrected H1 screen:

```text
candidate_summary.csv: 13 rows, all 20 columns exact within 1e-9
candidate_monthly.csv: 78 rows, all 8 columns exact within 1e-9
candidate_trades.csv: normalized SHA-256 exact
normalized_ledger_sha256: 98f67e110cb641263b629234b1b0401ece3a613f695f6c829bd007cc231894f8
```

Retained historical results remain unchanged:

| Candidate | Trades | Average net pips | Total net pips | Profit factor | Positive months | Minimum monthly trades |
|---|---:|---:|---:|---:|---:|---:|
| A1 impulse breakout hold6 | 391 | +2.015899 | +788.216501 | 1.280577 | 4 | 55 |
| E3 trend resumption hold6 | 361 | +1.783355 | +643.791082 | 1.305343 | 4 | 49 |

## H1 entry-horizon reference lock

The archived accepted horizon diagnostic passed the structural lock:

```text
registered candidates: 13
unique Entry definitions: 12
registered-hold regression rows: 13 passed
H2 data read: false
promotion decision: false
```

## Known A1/E3 H2 regression

The canonical M15 input reproduced every required H2 output:

```text
h1_regression.csv: exact
h2_candidate_summary.csv: exact
h2_candidate_monthly.csv: exact
h2_gate_results.csv: exact
h2_direction_attribution.csv: exact
h2_daily_net_pips.csv: exact
h2_candidate_trades.csv: normalized SHA-256 exact
h2_decision.json: exact
normalized_ledger_sha256: e4eca229dc886abd239dc9a424a0ca7c2414f87acb761da952e11ab39a07ba04
```

| Candidate | Trades | Positive months | Average net pips | Total net pips | Profit factor | Promotion |
|---|---:|---:|---:|---:|---:|---|
| A1 impulse breakout hold6 | 408 | 0 / 6 | -4.373667 | -1784.456321 | 0.665936 | failed |
| E3 trend resumption hold6 | 379 | 1 / 6 | -1.876125 | -711.051333 | 0.842863 | failed |

```text
decision: neither_advances
hard no-trade violations: H1 0, H2 0
```

A1 and E3 remain closed. R0 does not reopen them or permit post-H2 rescue.

## Acceptance

All twenty R0 acceptance checks passed:

1. Release asset count 29.
2. Original artifact count 288.
3. Source months 12.
4. Source effective coverage 100%.
5. Source unobserved records 0.
6. Source hard errors 0.
7. Excluded November artifact absent.
8. No 2025 artifact access.
9. Canonical M1/M5/M15/H1 present.
10. Forty-eight month-timeframe blocks present and non-empty.
11. Repeated canonical builds byte-identical.
12. Same-priority conflicts 0.
13. H1 thirteen-candidate summary exact.
14. H1 monthly output exact.
15. H1 normalized ledger exact.
16. H2 required outputs exact.
17. H2 normalized ledger exact.
18. H2 decision `neither_advances`.
19. Hard no-trade violations 0.
20. Horizon reference structure locked.

## Frozen implementation

```text
configs/research/usdjpy_r0_canonicalization_v1.json blob: 109f992a0c8edd1f00328f7b2b0f528240891a61
configs/research/usdjpy_r0_regression_lock_v1.json blob: df724f7661d9669382a585bee88a86e9694824cc
tools/build_fx_annual_bar_bundle.py blob: 8657582159d7a5345965af62b409334d36890a6c
tools/run_usdjpy_r0_canonical_bundle_v1.py blob: ff09e5c27616c227416b8db482224534fc18acf9
.github/workflows/run_usdjpy_r0_canonical_bundle_v1.yml blob: 063dd2e39187adec5d9dcd4b395ac8d04a98f6fa
```

## Next step

R1 may now begin. Before any expanded H1 results are opened, commit the expanded Entry registry and all family-level parameter bounds. R1 remains limited to 2024 H1 and at most sixty unique Entry definitions. R0 PASS does not permit 2025 access, Core migration or MT4 implementation.
