# F05 failed reclaim cross-repository status v1

## Binding candidate

`F05_FAILED_RECLAIM_BASIC_V1`

## Research result

The frozen Research portfolio and raw Bid/Ask Tick validation completed successfully for the accepted historical folds.

- Research repository: `mitsuru93/usdjpyea-research`
- Run: `30104463746`
- Commit: `86426cab5ff0491a18116574860274c89b5077ea`
- Artifact: `8601002548`
- Artifact digest: `sha256:e0c0710890109298e4d65386c2a86bc75492b606c33013a0c75dd23ccb9271ef`
- Release: `f05-failed-reclaim-validation-v1`
- Status: `PASS_RESEARCH_HISTORICAL_GATES`
- Binding events: `15`

All frozen 2023H1-2024H2 historical gates passed: breadth, direction, fold total, full-signal admission, portfolio admission identity, reproduction, severe-cost stress, raw-tick event order, trigger breadth and winner damage.

This authorizes implementation work. It does not establish 2025 external-period efficacy.

## Core implementation-parity result

The M1/HST parity execution completed but failed exact implementation parity.

- Core issue receipt: `mitsuru93/usdjpyea-core#251`
- Run: `30158424871`
- Status: `FAIL_MT4_M1_HST_IMPLEMENTATION_PARITY`
- Artifact: `8619649204`
- Artifact digest: `sha256:5f5585353a39f4b04eb7203eee0469222c007a951011e845705cd893bed9fb7e`

The compile, Entry-set checks, 2024H1/H2 tester executions and runtime-error checks completed. Exact candidate event parity failed because the candidate depends on intra-minute executable Bid/Ask ordering, including permanent profit disarm after any positive executable tick and exit on the first executable tick at the qualifying M5 completion. M1 OHLC/HST pseudo-ticks do not retain that ordering.

This failure does not invalidate the Research raw-tick historical result. It establishes that M1/HST is not an adequate exact-parity or efficacy authority for this candidate.

## 2025 M1/HST executions

### 2025H1

- Core run: `30180390705`
- Core issue receipt: `mitsuru93/usdjpyea-core#253`
- Artifact: `8625412799`
- Artifact digest: `sha256:a85884fe176ed61e8749d0cbf6abedd34506b023c22e6f8793c15b13a5a8b780`
- Status: `COMPLETE`
- Opened trades: `463` in both baseline and candidate
- Closed trades: `463` in both baseline and candidate
- Gross-pips sum: `-2,080.8` in both baseline and candidate
- Observed candidate structural-exit events: `0`

### 2025H2

- Core run: `30183522505`
- Core issue receipt: `mitsuru93/usdjpyea-core#254`
- Artifact: `8626374529`
- Artifact digest: `sha256:4482758d2f645b00c6ebdc528f889228502d52a0e4a1e23936cd47066dcddd13`
- Status: `COMPLETE`
- Opened trades: `509` in both baseline and candidate
- Closed trades: `507` in both baseline and candidate
- Period-end open positions: `2` in both baseline and candidate
- Gross-pips sum: `+2,755.0` in both baseline and candidate
- Observed candidate structural-exit events: `0`

## Correct interpretation of the 2025 zero detections

The 2025H1 and 2025H2 runs used M1/HST data rather than 2025 raw executable Bid/Ask Tick data. The failed-reclaim state machine depends on intra-minute Tick ordering. Therefore the zero detected candidate events are attributed to the unavailable 2025 Tick path, not to demonstrated absence of failed-reclaim events in the market.

The 2025 M1/HST outputs must not be used as:

- evidence that the candidate had no triggers in true Tick data;
- an external-period pass;
- an external-period rejection;
- evidence that baseline and candidate are economically identical under the intended execution model.

Their valid role is limited to documenting that the M1/HST path did not detect the candidate and cannot answer the raw-Tick question.

## Current status

1. Historical 2023H1-2024H2 Research/raw-Tick validation: **passed**.
2. MT4 compilation and broad Entry-set implementation checks: **completed**.
3. Exact M1/HST event parity: **failed because the data model cannot preserve the required intra-minute ordering**.
4. 2025H1/H2 M1/HST executions: **completed but invalid for failed-reclaim efficacy because 2025 Tick data were unavailable**.
5. 2025 external-period failed-reclaim result: **pending**.
6. Live implementation authorization: **not established**.

## Required remaining work

The next binding sequence is:

1. collect and archive accepted 2025 raw Bid/Ask Tick data for the required 2025 evaluation periods;
2. verify timestamps, spread fields, row continuity, duplicates, gaps and deterministic source hashes;
3. replay the unchanged `F05_FAILED_RECLAIM_BASIC_V1` state machine on the 2025 Tick path;
4. produce event identities, trigger timestamps, executable exits and portfolio deltas;
5. apply the frozen external-period gates without threshold, side, session or year-specific changes;
6. only then decide whether the historical candidate generalizes to 2025.

Because a new Tick acquisition can require approximately 20 hours, it must be scheduled and preserved carefully. The previous statement that no new Tick collection was required was incorrect for the 2025 external-period test.
