# USDJPY CSOS D — Shock Failure candidate freeze and implementation contract v1

Date: 2026-07-27

## Decision boundary

Phase 2 selected `B_EXECUTABLE_T0_8BAR` as `PASS_PORTABLE_RESEARCH_CANDIDATE`.

This document freezes the research candidate and defines the implementation/parity boundary. It does **not** authorize a Core change, MT4 execution, 2025H1/H2 access, B02/F05 integration, production use or live orders.

Canonical Phase 2 authority:

- Research scientific merge: `4a17c07139a564bc97d358da115f451e2316c562`
- Main Run: `30206226997`
- Artifact: `8633167258`
- Artifact digest: `sha256:0c9dd9d895255567ed63126f28335f120b2e68752e0bea785dcc3f83a2a1bca2`
- Release: `usdjpy-csos-shock-failure-phase2-v1`
- Receipt Issue: `#312`
- Event identity ledger SHA-256: `31e031c61294e83f4b09ccdd4cfb373f04b2f759f2f4bddf9c920123aefa2795`
- Candidate trade ledger SHA-256: `cc4ad57b9ed339be1a6f318be492f22fed859d7f6ef93814eb1f53f59ffe8459`

## Frozen mechanism

### Bar and volatility definition

- Symbol: USDJPY.
- Signal timeframe: M15.
- Signal price: Bid OHLC.
- One pip: `0.01`.
- Bars are the continuous ordered observed bars in the accepted source. Weekend and missing calendar slots do not create synthetic bars.
- True Range is `max(high-low, abs(high-previous_close), abs(low-previous_close))`.
- The volatility reference is the median of 96 observed bars **including the shock bar itself**.
- The rolling state does not reset at month, half-year or year boundaries.
- The exact Phase 2 warm-up guard requires the failure bar zero-based index to be at least 100.

### Shock

A bar is a shock when both conditions hold:

1. True Range is at least `2.5 × median(TR, 96)`.
2. Absolute body is at least `0.65 × True Range`.

An up shock additionally requires:

- Close > Open.
- `(Close-Low)/(High-Low) >= 0.80`.

A down shock additionally requires:

- Close < Open.
- `(Close-Low)/(High-Low) <= 0.20`.

A zero-range bar is ineligible.

### Failure

The failure bar is the immediately following completed M15 bar.

- Up shock failure: failure Close is below the shock midpoint and below its own Open.
- Down shock failure: failure Close is above the shock midpoint and above its own Open.
- Shock midpoint is `(shock High + shock Low) / 2`.
- The event becomes known only when the failure bar has completed. No intra-bar OHLC ordering is inferred.

### Entry

- Entry side is opposite the original shock.
- Decision boundary is the failure-bar end, equal to the next M15 bar start.
- Entry is the first executable tick timestamp at or after the decision boundary.
- Long opens at Ask.
- Short opens at Bid.
- Mid is never an executable price.

### Exit

- Scheduled exit boundary is **decision boundary + 120 minutes**.
- The 120 minutes are not measured from the actual fill timestamp.
- Exit is the first executable tick timestamp at or after the scheduled boundary.
- Long closes at Bid.
- Short closes at Ask.
- No stop loss, take profit, trailing stop or break-even rule exists.

### Re-entry suppression

The exact Phase 2 evaluator rule is stronger than the abbreviated statement “no re-entry while the prior trade is open”.

After admitting a failure at bar index `i`, every later candidate with failure index `j <= i + 9` is rejected, regardless of side. Therefore a failure bar beginning exactly at the prior scheduled exit boundary is still suppressed. The rule is based on the theoretical event indices, not on actual fill or close timing.

This rule must be reproduced exactly. It must not be replaced with a generic “one open position” test.

### Filters that do not exist

The frozen candidate has no:

- session filter;
- Long/Short exception;
- B02/F05 same-direction or opposite-direction conflict filter;
- baseline drawdown filter;
- spread filter;
- news filter;
- position-cap rule;
- replacement/oracle rule.

The selected portfolio interpretation is additive. Conflict controls evaluated in Phase 2 are analyses, not candidate semantics.

## Evaluation boundary versus runtime rule

Phase 2 excluded a research event when its scheduled exit boundary crossed the authorized fold boundary. This is an evaluation-period admission rule, not a live calendar rule.

A live runtime must not stop at arbitrary half-year boundaries. A later historical gate must apply the same authorized-period admission rule when calculating binding results.

## MT4 information mapping

On the first tick of a new M15 bar:

- shift 1 is the completed failure bar;
- shift 2 is the completed shock bar;
- the 96-bar shock reference is shifts 2 through 97 inclusive;
- shift 98 is needed as the previous Close for the oldest True Range.

The first tick that reveals the new bar is also the entry-decision tick. Delaying evaluation to a later tick changes the frozen entry contract.

Every parity log must retain both:

1. decision quote/time; and
2. actual order fill quote/time.

The scheduled exit remains anchored to the failure completion boundary even when actual entry is delayed.

## Retry and order-error policy

The binding parity run permits no silent retry. A later-tick retry is not the first-executable-tick strategy.

Any `OrderSend` or `OrderClose` error invalidates that binding parity run. A production retry policy may be studied later, but it is a separate execution variant and cannot be introduced as an implementation convenience.

## Data-authority boundary

### 2023

The accepted signal bars are Rakuten MT4-derived Bid M15. Dukascopy Raw Bid/Ask Tick is the execution-chronology authority used in Phase 2. This is why 2023 chronology was often classified as bounded cross-source rather than exact same-source chronology.

### 2024

The accepted signal bars are Dukascopy Raw Tick-derived Bid M15, not Rakuten raw quotes. Dukascopy Raw Bid/Ask Tick is also the execution-chronology authority.

Consequently:

- an exact formula parity test must use the canonical accepted bars;
- a Rakuten 2024 MT4 event set is a broker-source portability test;
- a Rakuten 2024 MT4 result must not be described as exact reproduction of the canonical 2024 event ledger merely because it uses the same formula.

M15 or M1 HST alone cannot prove first-tick Bid/Ask chronology. Binding execution parity requires either a TDS feed with the frozen tick digest or an independently validated Raw Tick replay. The latter proves execution semantics, but is not automatically proof of the MT4 engine.

## Planned parity stages

### P0 — Research contract validation

Run on a Research GitHub-hosted runner. Verify archive hashes, Phase 2 status, selected candidate, exact contract and all authorization locks.

### P1 — Core shadow formula parity

After separate Core authorization, create a standalone no-order parity Expert. It must reproduce the 114 canonical events on the accepted-bar input with:

- zero missing and extra IDs;
- zero side mismatches;
- zero decision-boundary mismatches;
- zero shock/failure predicate mismatches;
- zero re-entry-suppression mismatches;
- price tolerance `1e-10`.

The first implementation target must not modify B02/F05.

### P2 — Raw Tick execution parity

Reproduce all 114 entry and exit ticks with:

- zero timestamp mismatches;
- zero Bid/Ask-side mismatches;
- price tolerance `1e-10`;
- PnL tolerance `1e-8` pips;
- zero order/runtime errors where MT4 orders are used.

HST-only evidence cannot pass P2.

### P3 — Rakuten broker-source portability

This is required because 2024 canonical signal bars are not Rakuten bars.

The outcome-free gates are frozen before inspecting the comparison:

- 2023: exact 56-event identity, zero missing and extra events.
- 2024H1 and 2024H2 separately: canonical recall at least 0.80 and Rakuten precision at least 0.80.
- Matched events: 100% side agreement.
- Matched decision-boundary difference: 95th percentile no more than 15 minutes.
- Match definition: same side and boundary within ±1 M15 bar.

Failure blocks Rakuten implementation and a Rakuten 2025 gate. It does not retroactively invalidate the candidate on the canonical Research authority, and it does not permit threshold repair.

### P4 — Standalone MT4 parity

Only after P1-P3 pass and the user separately authorizes MT4. This stage uses a standalone Expert, logs decision and actual fill separately, and requires zero entry blocks, order failures, duplicate orders and runtime errors.

### P5 — Portfolio integration parity

A separate later authorization may add Shock Failure as an independent additive third strategy. B02 and F05 entry/exit identities must remain unchanged, and the standalone Shock Failure event identity must remain unchanged.

No same-direction skip, opposite-direction skip, drawdown skip, position cap, replacement or oracle logic may be added.

### P6 — 2025 gate application

2025 remains locked until the prior stages pass, the candidate hashes remain unchanged, an outcome-free 2025 preregistration is merged, and the user separately authorizes the gate.

## Failure policy

- Implementation mismatch: fix the implementation, not the candidate.
- Broker-source portability failure: classify Rakuten implementation as source-blocked; do not tune thresholds, side, session or year exceptions.
- Execution-parity failure: remain research-only and do not access 2025.
- Any 2025 access before P6 invalidates the sequence.

## Current result

Candidate freeze and parity planning may proceed in Research. Core source changes, MT4, 2025, portfolio integration, production and live orders remain unauthorized.
