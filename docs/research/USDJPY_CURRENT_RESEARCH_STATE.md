# USDJPY B02/F05 current research state

Updated: 2026-07-26

## Executive status

The shared research platform is implemented on Research main. Historical 2023H1, 2023H2, 2024H1 and 2024H2 evidence has substantially narrowed the remaining scientific direction.

- Static M15-local entry factors do not provide a portable winner/loser separator.
- Broad common structural-stop families are closed after the comprehensive atlas found no robust survivor.
- `F05_FAILED_RECLAIM_BASIC_V1` is the only narrow termination candidate that passed frozen historical Research/raw-tick gates.
- Exact MT4 implementation parity for that candidate remains unresolved because M1/HST pseudo-ticks do not preserve the required intra-minute Bid/Ask ordering.
- 2025H1 and 2025H2 M1/HST tester runs completed but produced zero candidate triggers and therefore do not confirm or reject the raw-tick candidate.
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

Historical Research/raw-tick status: `PASS_RESEARCH_HISTORICAL_GATES`

- Run `30104463746`
- 15 binding events
- all frozen historical gates passed
- implementation work authorized

MT4 M1/HST parity status: `FAIL_MT4_M1_HST_IMPLEMENTATION_PARITY`

The failure is a data-path limitation: M1 OHLC/HST pseudo-ticks do not preserve permanent profit-disarm and first-executable-tick ordering required by the candidate. It is not a failure of the Research raw-tick historical result.

2025H1 M1/HST run `30180390705` and 2025H2 run `30183522505` completed. Both had identical baseline and candidate gross-pips totals and zero candidate structural exits. Because exact HST parity failed, these runs are non-decisive for external raw-tick efficacy.

See `docs/research/f05_failed_reclaim_cross_repo_status_v1.md`.

## Current strategy-specific direction

### F05

Retain `F05_FAILED_RECLAIM_BASIC_V1` as a historically passed Research candidate, but do not describe it as MT4-parity-complete or externally validated.

Required next gate:

1. use an MT4-compatible replay mechanism preserving executable Bid/Ask Tick order;
2. reproduce the six Research-confirmed 2024 events exactly;
3. match trigger time and executable exit identity;
4. then perform raw-tick-equivalent 2025 external-period evaluation.

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

No new Tick collection is currently required. Existing accepted raw Tick releases are the source authority. The unresolved F05 gap is MT4-compatible replay/parity, not absence of source Tick data.

## Priority order

1. Resolve exact F05 raw-tick-to-MT4 replay parity.
2. Re-evaluate 2025H1/H2 only under a parity-capable replay path.
3. Freeze and evaluate the B02/common native H1/H4 transition hypothesis.
4. Keep the experiment registry and this current-state document synchronized after every binding result.
