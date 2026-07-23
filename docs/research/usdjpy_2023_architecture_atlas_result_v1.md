# USDJPY 2023 Architecture Atlas Result v1

## Decision

**PASS — the 2023 Architecture Atlas was built from the exact-parity 963 closed B02/F05 trades.**

The Atlas is accepted as descriptive evidence. It does not authorize a candidate rule, threshold search, 2024 H2 access or any 2025 access.

The next required phase is a canonical-clock rebuild and audit of the corresponding 2024 H1 UTC-derived fields before any cross-year interpretation.

## Binding execution

- Core Run: `30001786384`
- Attempt: `1`
- Job: `89188413852`
- Head SHA: `9329579b68c8d7e526b63276e0afe306dfda7045`
- Environment: fresh GitHub-hosted Ubuntu runner
- Receipt: `mitsuru93/usdjpyea-core#194`
- Artifact ID: `8561286612`
- Artifact digest / downloaded ZIP SHA-256:
  `9e6aa5cebccc44a51e8e0aa86fd87653d2e471446c4a92cd62d8699f4c6bf591`
- Permanent Drive file ID: `14lqKAS28FZT2f-gAuxKe1izcckyTkwRV`
- Drive readback SHA-256: identical

Every workflow stage passed: exact builder identity, exact input artifact identities, exact Research preregistration identity, Atlas build, reconciliation, artifact upload and receipt creation. fileciteturn287file0L1-L1

The two earlier service-runner attempts (`30000786333`, `30000878692`) produced no research result. The first was cancelled after the runner accepted the job but did not begin any workflow step; the second was pending behind the same concurrency holder. They are technical superseded runs, not contradictory evidence.

## Input identities

- Builder commit: `2a5d29410144f809e9be4c3bdcb0fc059b3c253e`
- Builder SHA-256:
  `c9dbbdebb375ac040739669bb7f248e7ece78106b492943de8f846132116e9fa`
- Research preregistration commit:
  `e43fc7de8593bdb0edf16ffde8a22664348f4d64`
- Research preregistration SHA-256:
  `a36bf2760f28cd157d9123c27101e907ad5bc17a3bc7842aa127c970b5ffd79b`
- Binding 2023 MT4 artifact ID / SHA-256:
  `8560057457` / `bf2cd6e94ba4a15f764e784f4a82b8d07edd3070ab198bbf9bc27112e931f63b`
- 2023 preparation artifact ID / SHA-256:
  `8559483151` / `22d66bf76c60362b78e9badff2113bc196b80e3657f5083ae470d1d62df70c01`
- MT4 audit SHA-256:
  `a7349269db2072e24e694847e0c5517a90d10edd387aedb8baffa788caf008ff`
- Expected ledger SHA-256:
  `33d08d580d584f533bc5f9dda510184fb86c668608f76f8e9b7c014924c5f1b8`
- Normalized M15 SHA-256:
  `4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78`

## Reconciliation

All frozen gates passed:

- closed trades: 963;
- B02: 232;
- F05: 731;
- realized net: JPY -9,904;
- duplicate keys: 0;
- missing keys: 0;
- unexpected keys: 0;
- gross-pips mismatches: 0;
- future-derived entry columns: 0;
- hard-excluded entries: 0;
- regressed Deinit timestamp rows used: 0.

The entry-feature, outcome and joined tables each contain exactly 963 rows. The independently downloaded artifact reproduced all counts and aggregates.

## Strategy-level architecture

| Strategy | Trades | Net JPY | PF | Wins | Losses | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|---:|---:|---:|
| B02 | 232 | -13,266 | 0.798515 | 119 | 113 | 41.061 pips | -47.636 pips |
| F05 | 731 | +3,362 | 1.023736 | 350 | 380 | 32.609 pips | -32.348 pips |

The portfolio loss is concentrated in B02 in 2023. F05 is only marginally positive; this is not yet a basis for promotion or exclusion because the same canonical fields have not been rebuilt in 2024 H1.

## Exposure-state architecture

| Entry exposure state | Trades | Net JPY | PF |
|---|---:|---:|---:|
| standalone | 222 | -14,672 | 0.755886 |
| same-direction stack | 514 | -3,342 | 0.968059 |
| opposite overlap | 69 | -1,226 | 0.932036 |
| simultaneous same-direction | 60 | +2,313 | 1.207761 |
| mixed overlap | 98 | +7,023 | 1.517196 |

Standalone entries are the largest loss bucket. Mixed overlap and simultaneous same-direction entries are positive in this year, but these figures remain descriptive single-year partitions. Treating them as admission rules now would be result-driven selection.

## Loss-path architecture

| Path class | Trades | Net JPY | Mean MFE | Mean MAE |
|---|---:|---:|---:|---:|
| WINNER | 470 | +197,579 | 56.358 | -13.708 |
| P1 giveback to loss | 223 | -87,013 | 27.648 | -52.620 |
| P2 minor favorable then loss | 165 | -57,863 | 4.607 | -51.296 |
| P3 never profitable | 105 | -62,607 | -0.483 | -76.740 |

All three losing architectures are economically material:

- P1 shows substantial favorable excursion before failure;
- P2 shows only minor favorable movement;
- P3 is adverse almost immediately and has the deepest mean MAE.

No single exit or admission mechanism can be inferred solely from these totals.

## Monthly nonstationarity

| Month | Net JPY |
|---|---:|
| 2023-01 | -10,685 |
| 2023-02 | -182 |
| 2023-03 | -12,923 |
| 2023-04 | -2,531 |
| 2023-05 | +5,558 |
| 2023-06 | -6,424 |
| 2023-07 | +38 |
| 2023-08 | -4,551 |
| 2023-09 | -5,117 |
| 2023-10 | +2,833 |
| 2023-11 | +6,696 |
| 2023-12 | +17,384 |

The strong November–December recovery and large January–March losses show that yearly aggregate performance masks substantial regime variation.

## Data-quality attribution

- M1 gap records: 445;
- maximum missing interval: 2,997 minutes;
- entries on incomplete M15 buckets: 2;
- net result of those two trades: JPY +160;
- entries on complete M15 buckets: 961.

Incomplete M15 construction does not explain the 2023 loss.

## Output identities

- entry features CSV:
  `e7fdfd46fda776a224ca222cb84e462d9bf7f762ae4c0a5f780557f22f725c05`
- outcomes CSV:
  `70813368940164c5c26d993b92dbf3d1256ff0851604e475048fa269ab28b3ec`
- joined Atlas CSV:
  `c8fc37d937d34ccf22686d7eb22108530006be86a83154cef9cdf3adf0c36aa4`
- strategy summary CSV:
  `a0e2fa72fc02fb8a614cfe63435b3c4c37c3a0320ccf2c83a24a5293fab23393`
- exposure-state summary CSV:
  `3f79d2a8c30fe1d114f3014f66a58a17235400a2d0eeffac772194a5b88be124`
- path-class summary CSV:
  `b8b263023094d220460c24d1f6e3b5f33ea2a10a7d2788e23f4479c715e631ae`
- monthly summary CSV:
  `b895c1772766d3f807d1123583d1134cac2923912caa0a59c822e2d8ea3192a9`
- gap/incomplete JSON:
  `0a7900aa59321f9a6d5f0d6aa2e06dcf5a7bbce195bdf93886cec7ba34a36c23`
- overall summary JSON:
  `4c1fb9b67c80083ed787733234c99a7f374aea8a24178e2d5d05023acf910ccc`
- reconciliation JSON:
  `f6ea65750304f1d22df48ab0a3a95b4c7a3aebbf16f93f0b59b06df1af3a1ed0`

## Next phase

Before any new strategy family or threshold is formulated:

1. rebuild 2024 H1 signal/entry UTC keys under the canonical server clock;
2. rebuild the matching session and entry-state fields;
3. prove exact reconciliation to the accepted corrected 2024 H1 MT4 baseline;
4. only then compare 2023 and 2024 H1 architectures.

The comparison must distinguish recurring structure from single-year selection effects. Candidate generation remains blocked until that audit passes.
