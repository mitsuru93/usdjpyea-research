# EURUSD F v2: H2-first research-to-implementation roadmap v2

## Governing boundary

- Strategy analysis and revision use 2024 H1 only.
- Every revision is fully locked before evaluation.
- 2024 H2 is the permanent fixed validation period.
- 2024 H2 has no consumed or retired state and is reused for every locked iteration.
- 2024 H2 may accept or reject an H1-derived revision but may not generate rules or thresholds.
- No separate 2025 public dataset is downloaded or introduced into the Research workflow.
- If a 2025 check is later desired, it is an optional final Rakuten MT4 Strategy Tester run using the history already available inside MT4. It is not a development input, not a promotion gate, and must occur only after the production EA and all 2024 gates are complete.
- Forward testing is not part of this roadmap.

## Current accepted evidence

1. The 2024 H1 development protocol is registered.
2. The retained F v2 candidates were evaluated on fixed 2024 H2.
3. Research-to-MT4 exact ledger parity has been established for the two retained exits.
4. The preregistered H1 diagnostic was completed without H2 access. It did not justify a new revision.
5. The fixed-H2-first production selection retained target 0.5 as primary and target 0.25 as the neighboring robustness control.
6. The registered cost grid was completed and the target-0.5 production primary passed all registered acceptance checks.
7. Simulated EA state serialization, memory clearing, deserialization and per-bar control identity passed in Rakuten MT4 Strategy Tester without terminal disconnect, logout or re-login.

Retained roles:

- production primary: `F_v2_z72_1p5_mean_target_0p5_max12`;
- neighboring robustness control: `F_v2_z72_1p5_mean_target_0p25_max12`.

## Completed stages

### R3 — 2024 H1 diagnosis and bounded revision

Completed in run `29743006760`.

- H1 was physically isolated to 3,030 bars.
- H2 was not accessed.
- Both exits had the same 90 entries.
- No side, session, z-score bin or efficiency-ratio bin provided a structural basis for deletion.
- The average path recovered around bars 10-12, so a blanket shorter hold was not adopted.
- No v3 rule was created.

### R4 — Fixed 2024 H2 revalidation

No new candidate required revalidation because R3 produced no revision. The existing locked candidates and formal fixed-H2 result remain the comparison and selection evidence.

### R5 — Candidate and exit-policy confirmation

Completed.

- target 0.5 is the production primary because it was stronger on the fixed H2 in net pips, PF and severe PF;
- target 0.25 remains the neighboring robustness control because it was stronger on H1 and the full-2024 aggregate;
- no new exit threshold was introduced.

### R6 — Cost and execution stress

Research cost grid completed in run `29743806954`.

Registered target-0.5 acceptance passed:

- fixed-H2 default result remained positive and PF exceeded 1.05;
- fixed-H2 moderate-cost result remained positive and PF exceeded 1.0;
- full-2024 severe result remained positive and PF exceeded 0.9.

MT4 simulated state reinitialization completed in run `29744380290`:

1. serialize strategy state;
2. clear in-memory state;
3. reload serialized state;
4. continue the same test stream;
5. compare every bar with an uninterrupted control state.

The test passed at no-position, open-long, open-short, before-boundary, after-boundary and periodic checkpoints. It did not perform an actual terminal restart, account disconnect, logout or re-login.

## Active stage

### R7 — Production EA construction

Promote the selected target-0.5 candidate into a production EA with:

- completed-H1-only evaluation;
- next-H1-boundary execution;
- one-position state;
- deterministic magic-number filtering;
- live Bid/Ask-derived mid-bar construction;
- persistent state serialization;
- test-only simulated reinitialization hooks;
- Research-compatible audit rows;
- fixed-lot mode for initial operation.

The production EA must not substitute Bid H1 closes for the registered mid-close signal series. Until 72 completed synthetic mid closes are available, the default bootstrap mode is `cold_start_collect` and entries remain disabled.

## Remaining stages

### R8 — Rakuten MT4 verification

Use the completed automated path:

GitHub Actions → Windows interactive self-hosted runner → MetaEditor compile → Rakuten MT4 Strategy Tester → HTML/tester/terminal log collection → artifact and Release receipt.

Required tests:

- pure signal-engine parity on 2024;
- exact trade-ledger parity on fixed 2024 H2;
- DST, weekend and H1-boundary tests;
- production-EA simulated state reinitialization and order-state reconciliation;
- injected order-send/close errors;
- duplicate-order and missing-bar behavior;
- spread/slippage stress.

A real terminal disconnect, Windows sign-out, account logout or forced re-login test is prohibited because the current Rakuten MT4 behavior can invalidate the retained login state. The logged-in terminal is not deliberately disconnected, closed for a restart experiment, signed out or forced through re-login.

### R9 — Optional final 2025 MT4 check

Only after R7-R8 are complete, the user may authorize one final Rakuten MT4 Strategy Tester run over 2025 using MT4's existing local/broker history.

Constraints:

- no external 2025 dataset download;
- no Research-side 2025 bar archive;
- no parameter or rule changes from the result;
- not a production promotion gate;
- report the exact MT4 history, model, spread and date limitations;
- keep the result separate from the fixed-2024 Research evidence.

If this optional test is not authorized, it is skipped.

### R10 — Limited live deployment

Begin with a separately approved fixed-lot configuration after the implementation gates pass. No demo or forward-test stage is required. Live operation must retain complete audit output and an operational fault log.

## Current position

The project is now at R7: production EA construction. The optional 2025 MT4 test remains the last test and is not part of candidate development or promotion.
