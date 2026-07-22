# USDJPY 2024 H1 Validation Roadmap v2

## Status

This roadmap supersedes the prior two-stage candidate handling for all new USDJPY successor candidates created after S1-S3 closure.

The binding sequence is:

1. 2024 H1 development and exact MT4 parity;
2. unchanged 2024 H2 validation;
3. unchanged 2025 H1 binding stress validation.

A candidate is not retained for production-oriented work unless it passes all three stages.

## Data-boundary note

2025 H1 has already been inspected diagnostically to understand the known B02/F05 loss deterioration and to compare the already-closed S1-S3 mechanisms. Therefore it is not described as a pristine blind holdout.

For every new candidate, however:

- the exact candidate rule, thresholds, target strategy, processing order, MQ4/builder/evaluator identities and 2025 H1 gates must be frozen before candidate-specific 2025 H1 execution;
- no candidate-specific 2025 H1 result may be used to alter that exact specification;
- candidate-specific 2025 H1 execution is allowed only after unchanged 2024 H2 PASS;
- a failed 2025 H1 gate closes the exact specification.

2025 H1 is therefore a binding adverse-regime stress gate, not a tuning interval.

## Closed specifications

The following exact specifications remain closed and are not repaired, retuned or combined from H2 or 2025 evidence:

- `SC70/C240` exact specification;
- `F05_SW70_R10_E90_A240_v1` (S1);
- `B02F05_DSHOCK60_R20_E90_EXIT_v1` (S2);
- `F05_EXTATR25_LOC80_F30_v1` (S3).

Any successor must use a new candidate ID and return to 2024 H1.

## Stage 0 — registry and evidence lock

Maintain a candidate registry recording:

- mechanism family and candidate ID;
- parent diagnostic evidence;
- all data periods accessed;
- source, evaluator, workflow, MQ4 and EX4 identities;
- exact-specification exposure ordinal;
- H1, H2 and 2025 H1 decisions;
- closure reason.

No candidate may be dispatched to H2 or 2025 H1 unless its preceding-stage evidence is recorded and reproducible.

## Stage 1 — Entry-State Atlas v2 on 2024 H1

Reconstruct every 2024 H1 B02/F05 entry on one canonical trade key and attach only information available at entry time.

Required feature groups:

1. breakout acceptance and rejection;
2. range re-entry and false-break structure;
3. ATR-normalized displacement and path efficiency;
4. signal-bar close location and wick structure;
5. existing B02/F05 portfolio state;
6. same-direction, opposite-direction and mixed overlap;
7. stack ordinal, age, open P/L and prior-position path state;
8. UTC session, weekday and volatility context.

Outcome labels are descriptive only and include never-profitable, minor-favourable-then-loss, giveback-to-loss, MFE/MAE and final P/L.

Atlas completion requires exact reconciliation with the accepted 2024 H1 MT4 baseline trade keys.

## Stage 2 — independent 2024 H1 candidate families

### Family A — non-shock false breakout / failed price acceptance

Priority mechanisms:

- breakout rejection back inside the explicit breakout level;
- weak acceptance outside the breakout level;
- ordinary-range re-entry after a failed break.

These are distinct from S1-S3 shock and extension thresholds.

### Family B — conditional portfolio overlap

Priority mechanisms:

- underwater same-direction add-on;
- conditional simultaneous B02/F05 separation;
- stale same-direction stack;
- mixed/counter-exposure stress.

Uniform stack caps, uniform entry spacing and unconditional simultaneous-entry deletion are not repeated.

### Family C — structural exits

Only after entry-family screening, test:

- breakout-origin invalidation;
- failed acceptance after MFE;
- conditional giveback protection tied to structure rather than fixed pips.

Entry and exit mechanisms remain separate candidates until each independently passes H2 and 2025 H1.

## Stage 3 — 2024 H1 screening

Before inspecting candidate results, each family must declare a finite search grid or deterministic candidate-generation procedure.

Minimum action breadth for a freeze-eligible candidate:

- entry candidate: at least 12 affected trades, eight entry dates and four months;
- exit candidate: at least 10 changed positions, eight entry dates and four months.

H1 selection gates:

- net delta positive;
- PF not below baseline;
- direct MT4 tick-equity DD not above baseline;
- Q1 and Q2 deltas nonnegative;
- target-strategy delta positive;
- non-target strategy unchanged or nonnegative;
- at least three positive effect months and at most one negative effect month;
- ex-best-two entry-date delta positive;
- leave-one-month-out minimum delta positive;
- largest positive entry-date share at most 50%;
- top-two positive entry-date share at most 60%;
- exact research/MT4 affected-trade parity.

At most one candidate per independent mechanism family proceeds to H2.

## Stage 4 — 2024 H2 binding validation

Before H2, freeze:

- candidate rule and thresholds;
- target strategy and processing order;
- H1 affected trade keys;
- builder, evaluator, workflow, MQ4 and evidence identities;
- all H2 gates.

H2 is executed once for the exact specification. One failed binding gate closes it. H2 repair, threshold search and candidate combination are prohibited.

Required H2 gates include:

- exact H1 implementation parity before H2 access;
- correct entry-key relation for entry candidates or unchanged entry set for exit candidates;
- candidate net positive and above same-run baseline;
- PF at least baseline;
- tick-equity DD not worse;
- both H2 quarters positive and both quarter deltas nonnegative;
- target-strategy delta positive;
- non-target strategy unchanged or nonnegative;
- at least three positive effect months and at most one negative effect month;
- ex-best-two effect-date delta positive;
- largest positive date share at most 50%;
- benefit greater than harm.

Only H2 PASS unlocks candidate-specific 2025 H1 execution.

## Stage 5 — 2025 H1 binding stress gate

The H2-passing candidate is run unchanged on accepted cached 2025 H1 MT4 history under the same portfolio, lot, model and spread contract used for the accepted 2025 H1 baseline.

No threshold, scope, entry/exit order, lot rule, gate or candidate ID may change between H2 PASS and 2025 H1 execution.

### Binding 2025 H1 gates

All gates must pass:

1. source, builder, evaluator and generated MQ4 identities equal the H2-frozen identities;
2. baseline reproduces the accepted 2025 H1 contract;
3. trade-key relation matches the candidate type with zero unexpected trades;
4. no order-send or order-close failure;
5. candidate net JPY is positive;
6. candidate net JPY exceeds the same-run baseline;
7. PF is at least 1.00 and at least the same-run baseline PF;
8. direct tick-equity DD is below the same-run baseline DD;
9. minimum tick equity is above the same-run baseline minimum;
10. H1 January-March and April-June candidate net are each nonnegative;
11. both half-quarter deltas versus baseline are positive;
12. at least four of six monthly effects are positive;
13. at most one monthly effect is negative;
14. ex-best-two positive effect-date delta is positive;
15. largest positive effect-date share is at most 50%;
16. target-strategy delta is positive;
17. non-target strategy is unchanged or has nonnegative delta;
18. benefit exceeds harm.

A candidate that merely reduces the known 2025 H1 loss but remains negative fails this stage. S1 and S3 demonstrated that loss compression alone does not establish a production candidate.

### Decision

- all gates PASS: `THREE_STAGE_PASS`, eligible for tick/execution robustness and forward-test preparation;
- any gate FAIL: `CLOSED_FAIL_2025H1`, exact specification closed;
- technical evaluator defects may be repaired against the same MT4 audits without rerunning MT4, provided candidate logic, audits and frozen gates do not change.

## Stage 6 — post-gate robustness

Only `THREE_STAGE_PASS` candidates proceed to:

- repaired Dukascopy Bid/Ask tick-import testing;
- spread and slippage stress;
- lot-sizing and stop-out analysis;
- persistent-state and restart verification;
- demo forward testing.

No live-order use is authorized by this roadmap alone.

## Immediate execution order

1. create candidate registry v2 and three-stage gate policy;
2. build Entry-State Atlas v2 from accepted 2024 H1 baseline evidence;
3. screen Family A non-shock false-break mechanisms;
4. screen Family B conditional-overlap mechanisms;
5. implement freeze-eligible candidates in MT4;
6. perform unchanged H2 validation;
7. for H2 PASS only, perform unchanged binding 2025 H1 stress validation.
