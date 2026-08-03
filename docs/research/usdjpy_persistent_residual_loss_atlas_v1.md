# USDJPY Persistent Residual-Loss State Atlas v1

## Decision

`PASS_PERSISTENT_RESIDUAL_LOSS_ATLAS_COMPLETED`

Work ID:

`USDJPY-PERSISTENT-RESIDUAL-LOSS-ATLAS-001`

Diagnostic ID:

`USDJPY-DIAG-PERSISTENT-RESIDUAL-LOSS-ATLAS-001`

This is a read-only diagnostic result, not a new `USDJPY-HYP-*`, production configuration selection, or rule candidate study.

## Controller pilot result

The study used the Core reusable Controller and the required same-repository caller:

- Controller workflow: `.github/workflows/fx2_supervised_research_controller.yml`
- Caller workflow: `.github/workflows/usdjpy_persistent_residual_loss_atlas_controller.yml`
- Exact Controller/source SHA: `0e7180ac8b93a0d20558dd7a64191699d3d9a4b5`
- Authoritative Controller Run: `30785834609`
- Controller v1 smoke regression: `PASS`
- Controller v2 `READ_ONLY_ANALYTICAL_STUDY` validation: `PASS`
- Partitions: `19` total / `0` resumed / `0` retried / `0` failed
- Authoritative checkpoint disposition: `NEW_CHECKPOINT`

The initial Actions artifact upload failed because the repository artifact quota was exhausted. The analytical job, all partitions, and Controller finalizer had already passed. Publication restored the exact-SHA Mac persistent evidence and checkpoint, regenerated the Controller receipts without recomputing successful partitions, published the Release, and completed remote readback. This was classified as `artifact upload failure`, not a strategy failure.

## Authority

### HYP-045

- Release: `usdjpy-hyp045-b0-cross-regime-stability-improvement-v5`
- Archive SHA-256: `aa54091ed2149b2c8d6ce5da1f11c739ee0d213eb2dda2928e7dfa1c5c153065`
- Atlas architecture: `A0`
- Rule hash: `1425b4caf6c0a5e8c4f21be7efdf410442bbd6d24d329f87c9c4931eecbd4b7f`

### HYP-046

- Frozen economic snapshot SHA: `2905b6826e34830a5db3452b5afbfaeed74f3ae0`
- Authority class: `FROZEN_ECONOMIC_CHECKPOINT_AUTHORITY`
- A1: `C1_A2A_HIGHVOL_EXTENSION4_PERMISSION`
- A2: `C2_A2A_HIGHVOL_EXTENSION4_PERMISSION_PLUS_A3_SESSION_CLUSTER_CONTROL`
- Technical qualification remains in progress.
- Core PR #918, Research PR #492, Core Issue #917, Research Issue #491, and the HYP-046 branch were not changed.

Contract hashes:

- Controller manifest SHA-256: `0b1f2c414f5b527bb775838529fc837d3a1f6406549ca77af2e382de734215a0`
- Authority bundle SHA-256: `f9356dad353bf1c66deccefcf8813c78e44672db8c268a439845f5ea9e0ee82b`
- Rule-set contract SHA-256: `2278793876cb81381d6fda982398be430989dc4f13501e817285dbb576b87ead`

## Period firewall

- 2020–2024: mechanism discovery and priority ranking.
- 2025H1: read-only recurrence confirmation only.
- 2025H2: prohibited and not accessed.
- New candidate: false.
- New candidate outcome computation: false.
- Strategy rule change: false.
- Threshold search: false.
- MetaEditor compile: false.
- MT4 execution: false.
- Production authorization: false.
- Live authorization: false.

## Persistent residual population

- Architecture rows: `19,012`
- Unique events: `6,567`
- Exact-event persistent losses across A0/A1/A2: `3,538`
- Calendar-recurring persistent state groups: `103`
- Exact Level-2 state-tuple events recurring in 2025H1: `0`
- Top ranked mechanism-family 2025H1 loss events: `89`
- Top mechanism-family validation recurrence: confirmed

The zero exact Level-2 recurrence and the positive broader mechanism-family recurrence are different measurements. They are not contradictory: the full state tuple is sparse because several state dimensions are unavailable, while the strategy/side/holding-path mechanism family recurs.

## Residual attribution

| Population | Loss events | Gross loss JPY |
|---|---:|---:|
| F05 Long | 904 | -226,269 |
| F05 Short | 959 | -212,714 |
| B02 Long | 448 | -60,844 |
| B02 Short | 405 | -60,160 |
| Short Pullback (`SP39` source label) | 822 | -180,915 |

Red-period recurrence:

| Period | Loss events | Gross loss JPY | Role |
|---|---:|---:|---|
| 2021 | 690 | -92,767 | mechanism discovery |
| 2022H2 | 352 | -133,961 | mechanism discovery |
| 2022-10 | 49 | -30,062 | mechanism discovery |
| 2023Q1 | 174 | -62,140 | mechanism discovery |
| 2025Q1 | 185 | -49,181 | validation confirmation only |

## Mechanism priority

Rank 1:

`strategy_side_path:F05|LONG|LONG_DURATION_STAGNATION`

- Architecture persistence: `3/3`
- Years observed in 2020–2024: `5`
- 2025H1 loss-event recurrence: `89`
- Theoretical maximum loss capture: `¥294,187`
- Reported exposed winner population: `0`
- Reported winner contamination ratio: `0.00%`
- Information-time availability: `POST_ENTRY_ONLY`
- Rakuten execution feasibility: `REQUIRES_EXIT_OR_LIFECYCLE_STUDY`
- Source portability confidence: `MEDIUM`

The `¥294,187` value is an ex-post theoretical upper bound, not an achievable forecast. The reported zero winner contamination is also an ex-post property of the loser-only holding-path class: winners are classified as `WINNER_OR_FLAT` before this class is assigned. It must not be interpreted as evidence that a future implementable control can remove these losses with zero winner impact.

The diagnostic conclusion is therefore a mechanism priority, not a rule: F05 Long losses that survive A2A and A3 are concentrated in long-duration post-entry lifecycle failures. A separate study must first make the lifecycle state observable at valid decision time.

## Excursion and state limitations

The accepted-event authorities do not provide the normalized fields required to answer every requested sub-question:

- MFE: `NOT_AVAILABLE`
- MAE: `NOT_AVAILABLE`
- time to MFE: `NOT_AVAILABLE`
- time to MAE: `NOT_AVAILABLE`
- immediate-adverse versus giveback ratio: `NOT_AVAILABLE`; not inferred
- trend and higher-timeframe direction: `NOT_AVAILABLE`
- concurrency and same/opposite-direction exposure: `NOT_AVAILABLE`
- floating and realized drawdown: `NOT_AVAILABLE`
- full A2A/A3 state fields: `NOT_AVAILABLE`

Holding duration is available, which supports the `LONG_DURATION_STAGNATION` family. It does not by itself define an information-time-valid Exit or lifecycle rule.

## Release and readback

Release:

`usdjpy-persistent-residual-loss-atlas-v1`

- URL: `https://github.com/mitsuru93/usdjpyea-core/releases/tag/usdjpy-persistent-residual-loss-atlas-v1`
- Archive: `usdjpy-persistent-residual-loss-atlas-v1.zip`
- Archive SHA-256: `a3ce3aad1e8aa52a27685fa041e3693ff19176d8fb196f42efad441a0292126d`
- Archive members: `38`
- Remote archive byte identity: `PASS`
- Member count / missing / extra checks: `PASS`
- Member SHA checks: `PASS`
- JSON parse: `PASS`
- CSV parse: `PASS`
- Report lint: `PASS`
- Final-decision consistency: `PASS`

The immutable archive contains the package-time evidence. The standalone Release receipts and repository-bound report contain the post-readback final status.

## Cleanup

- Temporary authority downloads: removed.
- Temporary normalized ledgers: removed.
- Stale partition workspace: removed.
- Expired checkpoint temp: removed.
- One-shot status probe PR/branch: closed and reset.
- One-shot publication recovery PR/branch: closed and reset.
- One-shot final evidence binding PR/branch: closed and reset.
- Persistent checkpoints: preserved.
- Final Controller receipts: preserved.
- Authority bundle manifest: preserved.
- Final Release and remote readback: preserved.
- Final report and mechanism ranking: preserved.
- Other research runner processes/workspaces: not modified.

## Exact next action

`START_SEPARATE_F05_LONG_POST_ENTRY_LIFECYCLE_AUTHORITY_COMPLETION_AND_LONG_DURATION_STAGNATION_MECHANISM_STUDY_WITHOUT_DEFINING_A_RULE_UNTIL_MFE_MAE_AND_TIME_TO_EXCURSION_WINNER_CONTAMINATION_ARE_MEASURABLE`

The next study must first construct or bind read-only lifecycle authority for MFE, MAE, time-to-excursion, and winner exposure at valid decision times. Only after that authority is fixed may a finite Exit/lifecycle candidate study be opened. This atlas itself does not define or rank rules.
