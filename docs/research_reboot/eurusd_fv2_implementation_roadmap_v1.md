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

Retained candidates:

- `F_v2_z72_1p5_mean_target_0p5_max12`
- `F_v2_z72_1p5_mean_target_0p25_max12`

## Remaining roadmap

### R3 — 2024 H1 diagnosis and bounded revision

Analyze the retained candidates on 2024 H1 only. Required diagnostics include monthly and daily concentration, long/short symmetry, entry z-score, efficiency ratio, UTC and session timing, holding-time distribution, exit reason, bar-path MFE/MAE and registered cost sensitivity.

Any revision must satisfy all of the following before H2 is read:

- derived solely from the H1 diagnostic;
- compared with the two frozen baseline exits;
- limited to a preregistered candidate set;
- complete rule and parameter definition;
- candidate-lock SHA-256 recorded.

If H1 does not provide a clear structural basis for a revision, the frozen baseline proceeds unchanged.

### R4 — Fixed 2024 H2 revalidation

Apply the locked H1-derived candidate set to the same 2024 H2 period. Compare it with the current frozen baseline without ranking or tuning from H2.

- A failed candidate returns to R3.
- The baseline remains available and unchanged.
- No new parameter is created from the H2 result.
- H2 remains reusable for the next locked H1-derived iteration.

### R5 — Candidate and exit-policy confirmation

Select the production candidate from the bounded, preregistered set. The registered target-0.5 and target-0.25 exits remain the neighboring baseline pair. No threshold may be interpolated or invented from H2.

### R6 — Cost and execution stress

Apply the registered spread/slippage grid without modifying the signal rule:

- spread multipliers 1.0, 1.5, 2.0 and 3.0;
- slippage per side 0.0, 0.1, 0.3 and 0.5 pips;
- Rakuten GMT+2/GMT+3 conversion;
- weekend and H1-boundary handling;
- duplicate-order and missing-bar behavior;
- order-send and close retry auditing.

A real terminal disconnect, Windows sign-out, account logout or forced re-login test is prohibited because the current Rakuten MT4 behavior can invalidate the retained login state.

State recovery is tested without disconnecting the account:

1. serialize the strategy state;
2. clear the in-memory state in a test-only harness;
3. reload the serialized state;
4. reconcile it against the tester order state;
5. require identical signal, holding-bar and duplicate-entry behavior.

This is a simulated EA reinitialization test. It does not claim to prove an actual terminal-process restart or account reconnection.

### R7 — Production EA construction

Promote the selected locked candidate into a production EA with:

- completed-H1-only evaluation;
- next-H1-boundary execution;
- one-position state;
- deterministic magic-number filtering;
- persistent state serialization;
- test-only simulated reinitialization hooks;
- Research-compatible audit rows.

### R8 — Rakuten MT4 verification

Use the completed automated path:

GitHub Actions → Windows interactive self-hosted runner → MetaEditor compile → Rakuten MT4 Strategy Tester → HTML/tester/terminal log collection → artifact and Release receipt.

Required tests:

- pure signal-engine parity on 2024;
- exact trade-ledger parity on fixed 2024 H2;
- DST, weekend and H1-boundary tests;
- simulated state reinitialization and order-state reconciliation;
- injected order-send/close errors;
- spread/slippage stress.

The logged-in Rakuten terminal is not deliberately disconnected, closed for a restart experiment, signed out or forced through re-login.

### R9 — Optional final 2025 MT4 check

Only after R3-R8 are complete, the user may authorize one final Rakuten MT4 Strategy Tester run over 2025 using MT4's existing local/broker history.

Constraints:

- no external 2025 dataset download;
- no Research-side 2025 bar archive;
- no parameter or rule changes from the result;
- not a production promotion gate;
- report the exact MT4 history/model/spread limitations;
- keep the result separate from the fixed-2024 Research evidence.

If this optional test is not authorized, it is skipped.

### R10 — Limited live deployment

Begin with a separately approved fixed-lot configuration after the implementation gates pass. No demo or forward-test stage is required. Live operation must retain complete audit output and an operational fault log.

## Current position

The current stage is R3: run the 2024 H1 diagnostic, preregister any bounded revision, then reuse fixed 2024 H2. The optional 2025 MT4 test is last and is not part of current candidate development.
