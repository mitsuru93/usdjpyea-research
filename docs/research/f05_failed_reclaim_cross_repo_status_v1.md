# F05 failed reclaim cross-repository status v1

## Binding candidate

`F05_FAILED_RECLAIM_BASIC_V1`

## Research result

The frozen Research portfolio and raw Bid/Ask Tick validation completed successfully.

- Research repository: `mitsuru93/usdjpyea-research`
- Run: `30104463746`
- Commit: `86426cab5ff0491a18116574860274c89b5077ea`
- Artifact: `8601002548`
- Artifact digest: `sha256:e0c0710890109298e4d65386c2a86bc75492b606c33013a0c75dd23ccb9271ef`
- Release: `f05-failed-reclaim-validation-v1`
- Status: `PASS_RESEARCH_HISTORICAL_GATES`
- Binding events: `15`

All frozen historical gates passed: breadth, direction, fold total, full-signal admission, portfolio admission identity, reproduction, severe-cost stress, raw-tick event order, trigger breadth and winner damage.

This authorizes implementation work. It does not by itself establish MT4 exact implementation parity or external-period efficacy.

## Core implementation-parity result

The M1/HST parity execution completed but failed exact implementation parity.

- Core issue receipt: `mitsuru93/usdjpyea-core#251`
- Run: `30158424871`
- Status: `FAIL_MT4_M1_HST_IMPLEMENTATION_PARITY`
- Artifact: `8619649204`
- Artifact digest: `sha256:5f5585353a39f4b04eb7203eee0469222c007a951011e845705cd893bed9fb7e`

The compile, Entry-set checks, 2024H1/H2 tester executions and runtime-error checks completed. Exact candidate event parity failed because the candidate depends on intra-minute executable Bid/Ask ordering, including permanent profit disarm after any positive executable tick and exit on the first executable tick at the qualifying M5 completion. M1 OHLC/HST pseudo-ticks do not retain that ordering.

This failure does not invalidate the Research raw-tick result. It establishes that M1/HST is not an adequate exact-parity authority for this candidate.

## 2025 tester executions

### 2025H1

- Core run: `30180390705`
- Core issue receipt: `mitsuru93/usdjpyea-core#253`
- Artifact: `8625412799`
- Artifact digest: `sha256:a85884fe176ed61e8749d0cbf6abedd34506b023c22e6f8793c15b13a5a8b780`
- Status: `COMPLETE`
- Baseline rows: `13,190`
- Candidate rows: `13,191`
- Opened trades: `463` in both baseline and candidate
- Closed trades: `463` in both baseline and candidate
- Gross-pips sum: `-2,080.8` in both baseline and candidate
- Candidate-only extra row: `candidate_contract`
- Observed candidate structural-exit events: `0`

### 2025H2

- Core run: `30183522505`
- Core issue receipt: `mitsuru93/usdjpyea-core#254`
- Artifact: `8626374529`
- Artifact digest: `sha256:4482758d2f645b00c6ebdc528f889228502d52a0e4a1e23936cd47066dcddd13`
- Status: `COMPLETE`
- Baseline rows: `13,542`
- Candidate rows: `13,543`
- Opened trades: `509` in both baseline and candidate
- Closed trades: `507` in both baseline and candidate
- Period-end open positions: `2` in both baseline and candidate
- Gross-pips sum: `+2,755.0` in both baseline and candidate
- Candidate-only extra row: `candidate_contract`
- Observed candidate structural-exit events: `0`

## Interpretation boundary

The completed 2025H1 and 2025H2 M1/HST tester runs produced no candidate trigger and therefore no baseline-candidate gross-pips difference. These runs must not be described as an external-period pass or rejection of the raw-tick candidate because exact M1/HST implementation parity already failed for the event-order mechanism.

The evidence supports the following precise status:

1. Historical Research/raw-tick scientific validation: **passed**.
2. MT4 compilation and broad Entry-set implementation checks: **completed**.
3. Exact MT4 M1/HST event parity: **failed because the data model cannot preserve required intra-minute ordering**.
4. 2025H1/H2 M1/HST runs: **completed, zero candidate triggers, scientifically non-decisive for raw-tick efficacy**.
5. TDS parity: **not established**.
6. Live implementation authorization: **not established by this evidence**.

## Required remaining gate

A valid completion path requires an MT4-compatible replay source that preserves executable Bid/Ask Tick ordering, followed by:

- exact 2024 event-identity parity against the six Research-confirmed events;
- matching trigger timestamps and executable exits;
- unchanged candidate semantics;
- only then a raw-tick-equivalent 2025 external-period evaluation.

No new Tick collection is required while accepted raw Tick releases remain available. The missing element is an MT4-compatible replay/parity mechanism, not source-market-data acquisition.
