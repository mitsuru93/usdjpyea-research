# USDJPY B02/F05 current research state

Updated: 2026-07-26

## Executive status

The shared research platform is implemented on Research main. Historical 2023H1, 2023H2, 2024H1 and 2024H2 evidence has substantially narrowed the remaining scientific direction.

- Static M15-local entry factors do not provide a portable winner/loser separator.
- Broad common structural-stop families are closed after the comprehensive atlas found no robust survivor.
- `F05_FAILED_RECLAIM_BASIC_V1` is the only narrow termination candidate that passed frozen historical Research/raw-Tick gates.
- Exact MT4 implementation parity for that candidate remains unresolved because M1/HST pseudo-ticks do not preserve the required intra-minute Bid/Ask ordering.
- 2025H1 and 2025H2 M1/HST runs produced zero detected candidate events, but 2025 raw Bid/Ask Tick data were unavailable. The zero detections are therefore invalid as external-period efficacy evidence.
- Failed reclaim must be tested again after 2025 Tick collection.
- B02 has no authorized structural-stop candidate. Its principal remaining scientific direction is completed native H1/H4 state-transition confirmation and termination.

## Completed research

### Cross-year baseline and factor diagnosis

The common population contains 1,882 trades across B02 and F05. Both strategies fail in 2023H1 and recover thereafter, indicating a shared state/regime problem rather than a single strategy-local defect.

Entry-factor diagnosis rejected stable use of breakout distance, recent 4h aligned movement, fixed direction, stacking and another multivariate combination of the same local M15 feature set. Held-out-fold discrimination was weak, especially for F05.

### Lifecycle A-B-C

Status: `completed`

Decision: no lifecycle candidate passed all common fold, severe-cost, direction and winner-retention gates.

### Comprehensive structural-stop atlas v2

Status: `ATLAS_COMPLETE_NO_ROBUST_FAMILY`

- 1,882 trades
- 916 final-loss trades
- 303 deterministic candidates
- 12 structural families
- deterministic, supervised, unsupervised and nested-CV analyses

No additional common, B02-only or F05-only structural-stop family was authorized. Broad path deterioration is observable but too heterogeneous for one portable stop rule.

### F05 failed reclaim

Historical Research/raw-Tick status: `PASS_RESEARCH_HISTORICAL_GATES`

- Run `30104463746`
- 15 binding events
- all frozen 2023H1-2024H2 historical gates passed
- implementation work authorized

MT4 M1/HST parity status: `FAIL_MT4_M1_HST_IMPLEMENTATION_PARITY`

The failure is a data-path limitation: M1 OHLC/HST pseudo-ticks do not preserve permanent profit-disarm and first-executable-tick ordering required by the candidate. It is not a failure of the Research raw-Tick historical result.

2025H1 M1/HST run `30180390705` and 2025H2 run `30183522505` completed with zero detected candidate structural exits. Those runs lacked 2025 raw executable Bid/Ask Tick paths. Accordingly, the zero detections do not show that true 2025 Tick data contain no failed-reclaim events and cannot be used to pass or reject the candidate.

2025 external-period status: `PENDING_2025_TICK_COLLECTION_AND_RETEST`

See `docs/research/f05_failed_reclaim_cross_repo_status_v1.md`.

## Current strategy-specific direction

### F05

Retain `F05_FAILED_RECLAIM_BASIC_V1` as a historically passed Research candidate, but do not describe it as externally validated or rejected.

Required next gate:

1. collect and archive accepted 2025 raw Bid/Ask Tick data;
2. validate continuity, duplicates, gaps, timezone contract, Bid/Ask fields and deterministic hashes;
3. replay the unchanged failed-reclaim state machine on 2025 Tick data;
4. emit event identities, trigger timestamps, executable exits and full portfolio results;
5. apply frozen external-period gates without threshold, side, session or year-specific adjustment;
6. then decide 2025 generalization.

Do not reopen broad structural-stop threshold searches unless materially new information or a new state mechanism is introduced.

### B02

No structural-stop candidate is authorized. Do not use pooled side effects, static short suppression or another local M15 threshold as the primary direction.

Primary remaining hypothesis:

- B02 is a setup observation for transition from overnight balance;
- capital deployment requires a completed direction-symmetric native H1/H4 state transition;
- termination uses a completed opposite state transition;
- path-class predictions must reduce P2/P3 admission failure and P1 giveback without year, side or session exceptions.

This hypothesis still requires deterministic definition, duplication audit, preregistration and unchanged four-fold evaluation.

## Closed or deprioritized directions

- generic B02/F05 structural SL
- fixed-pip stop research for the current scope
- static breakout-distance threshold
- static 4h movement cutoff
- fixed direction exclusion
- stack ordinal as a deployable cause
- another model using only the already-tested local M15 entry features
- broad trajectory clustering as a stopping rule

## Infrastructure status

Implemented on Research main:

- source inventory
- canonical trade/event model
- path-ledger and result adapters
- chronology validation
- observation builder
- common fold/strategy/side/state aggregation
- numeric and categorical factor analysis
- permutation testing
- bootstrap intervals
- matched cohorts
- interaction analysis
- experiment contracts and registry
- deterministic evidence hashing
- GitHub-hosted CI

The next priority is using this infrastructure for actual experiments rather than extending infrastructure breadth.

## Data-acquisition boundary

Existing accepted 2023-2024 Tick assets remain reusable and should not be recollected. However, the 2025 failed-reclaim external-period test requires 2025 raw Bid/Ask Tick data, which were not available in the M1/HST runs.

A new 2025 Tick collection is therefore required before the binding retest. Because collection may take approximately 20 hours, the workflow must preserve partial progress where possible and immediately archive completed source files, manifests, hashes and receipts.

## Priority order

1. Collect and archive the required 2025 raw Bid/Ask Tick data.
2. Validate the 2025 Tick source contract and deterministic identities.
3. Rerun unchanged `F05_FAILED_RECLAIM_BASIC_V1` on 2025 Tick data.
4. Record the external-period pass/fail result in the registry and this current-state document.
5. Freeze and evaluate the B02/common native H1/H4 transition hypothesis.

<!-- USDJPY-DATA-2020-2022-TICK-AUTHORITY-001 -->
## USDJPY 2020–2022 Tick authority

2020–2022 Tick authorityはanalysis-onlyであり、既存candidateのformal decisionや2025H1 validation resultを変更しない。

Work ID: `USDJPY-DATA-2020-2022-TICK-AUTHORITY-001`. Release: `usdjpy-2020-2022-source-native-bidask-tick-authority-v1`. Receipt Issue: #438.
