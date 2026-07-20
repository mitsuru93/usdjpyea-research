# EURUSD F v2: research-to-implementation roadmap v1

## Purpose

This document defines the remaining path from the accepted EURUSD H1 mean-reversion family to a deployable Rakuten MT4 Expert Advisor.

The authoritative iteration rule remains unchanged:

- strategy creation and modification use 2024 H1 only;
- every candidate definition is locked before evaluation;
- 2024 H2 is the permanent fixed validation period and has no consumed or retired state;
- 2024 H2 may accept or reject an H1-derived candidate but must not generate or tune rules;
- a failed iteration may be revised only from 2024 H1 evidence and then compared again on the same 2024 H2.

## Current accepted state

| Stage | Evidence | Status |
|---|---|---|
| 2024 H1 development | `eurusd_h1_h2_v2_candidate_protocol.json` and formal development lock | Complete |
| Reusable 2024 H2 validation | Research run `29724004316`, Release `eurusd-h1-h2-v2-validation-2024-v1` | Complete |
| Research-to-MT4 implementation parity | Core run `29729701567`, Release `mt4-eurusd-fv2-h2-reference-parity-v4` | Complete |
| Exact ledger parity | target 0.5: 114/114; target 0.25: 112/112 | Complete |

The retained candidates are:

1. `F_v2_z72_1p5_mean_target_0p5_max12` — primary candidate.
2. `F_v2_z72_1p5_mean_target_0p25_max12` — neighboring robustness candidate.

No parameter ranking or rule change is authorized from the 2024 H2 outcome.

## Remaining roadmap

### R3 — Untouched 2025 full-year replication

Run the two unchanged candidates over 2025-01-01 through 2026-01-01 using canonical EURUSD H1 bars. 2024 history may be supplied only as indicator warm-up. No 2025 observation may alter a rule, parameter, gate, cost assumption, or candidate priority.

Required outputs:

- full trade ledger;
- monthly metrics;
- default and severe cost metrics;
- concentration result excluding the best two UTC entry days;
- maximum drawdown in pips;
- exact source and protocol digests.

Primary gate: the existing full-year gate from the v2 protocol, applied unchanged.

### R4 — Exit-policy isolation

Only after R3 is complete, compare the already registered target-0.5 and target-0.25 exits as a bounded exit-policy pair. This stage may select an implementation default but may not introduce a new exit threshold from 2024 H2 or 2025 results.

Decision rule:

- if only one candidate passes R3, retain that candidate;
- if both pass, retain target 0.5 as the primary implementation and target 0.25 as the neighboring robustness control unless a pre-registered operational criterion resolves otherwise;
- if neither passes, return to 2024 H1 for a new locked iteration and reuse fixed 2024 H2.

### R5 — Execution and cost stress

Evaluate the retained implementation under the registered spread/slippage grid:

- spread multiplier: 1.0, 1.5, 2.0, 3.0;
- slippage per side: 0.0, 0.1, 0.3, 0.5 pips;
- spread basis: `max(0.6 pips, public entry spread mean)`.

Add broker-operational diagnostics without changing the signal rule:

- Rakuten GMT+2/GMT+3 conversion;
- weekend and session boundary handling;
- restart and duplicate-order prevention;
- missing-bar behavior;
- maximum-spread entry rejection as a separately registered operational overlay;
- order-send and close retry logging.

### R6 — Production EA construction

Promote the chosen candidate from the diagnostic parity EA into a production EA in `mitsuru93/usdjpyea-core`.

The production implementation must contain:

- completed-H1-only signal evaluation;
- next-H1-open execution;
- one open position per strategy instance;
- locked z-score, efficiency-ratio and maximum-hold logic;
- fixed no-trade window;
- deterministic magic number and symbol/timeframe checks;
- persistent state sufficient to survive terminal restart;
- CSV audit rows compatible with the Research ledger schema;
- configurable fixed-lot and risk-based sizing modes, with sizing separated from strategy validation.

### R7 — Broker-history and forward verification

Run the production EA through:

1. historical Rakuten MT4 Strategy Tester reproduction;
2. a demo forward run with audit logging;
3. reconciliation of every generated signal, attempted order, fill and close;
4. operational fault tests covering restart, connection interruption and duplicate ticks.

The demo stage tests implementation behavior, not parameter discovery.

### R8 — Limited live deployment and promotion

Begin with a separately approved minimum-risk live configuration. Promotion requires a pre-registered observation count and operational error gate. Lot-size escalation is a risk-management decision and must not be presented as additional strategy validation.

## Promotion boundary

A candidate is not deployable merely because Research and MT4 produce the same 2024 H2 ledger. Deployment requires completion of R3 through R7. The current project position is the boundary between R2 and R3.
