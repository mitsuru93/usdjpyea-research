# USDJPY-PORTABILITY-001

## Formal name

`USDJPY Dukascopy–Rakuten Signal Chronology and Source Portability Root-Cause Study`

## Work classification

This is cross-cutting technical research, not a strategy Hypothesis. It does not create a strategy, candidate, Entry, Exit, permission, threshold, side, session, suppression or holding rule.

## Immutable boundaries

- HYP-039 and HYP-040 remain closed under their existing formal decisions.
- No retrospective PASS, rescue, reopening or retuning is authorized.
- 2023–2024 is the primary portability diagnostic period.
- 2025H1 may be read only when needed to reconcile already-completed HYP-039/HYP-040 evidence; it cannot select a technical contract.
- 2025H2 is prohibited.
- 2020–2022 is `ANALYSIS_ONLY_NON_BINDING_EVIDENCE` when the certified authority is available.
- Rakuten HST, FXT, terminal history and Model=0 fixed-spread tester output are not broker-native raw Bid/Ask Tick authority.
- Production and live authorization remain false.

## Required root-cause chain

Every mismatch must be assigned once to its first divergence stage:

1. raw source
2. timestamp normalization
3. bar population
4. bar OHLC
5. indicator
6. signal condition
7. information time
8. suppression
9. Entry executable Tick
10. holding
11. Exit executable Tick
12. JPY accounting

Downstream differences must not be double-counted as additional causes.

## Common contract candidates

- T1 — timestamp normalization
- T2 — canonical bar reconstruction from the same raw input
- T3 — information-time and executable-Tick separation
- T4 — close-before-entry chronology and observed-bar holding

Acceptance is based only on deterministic semantic parity, future-information exclusion, cross-strategy applicability and MT4 implementability. Strategy P/L cannot select a correction.

## Required completion evidence

Source inventory, common schemas, full HYP-039/HYP-040 mismatch catalogs, first-divergence attribution, deterministic Research/MQL4 fixtures, correction gate, B02/F05 regression, deterministic archive, SHA-256 manifest, Release/readback receipts, Common Portfolio handoff, Notion synchronization and a final cross-cutting decision.
