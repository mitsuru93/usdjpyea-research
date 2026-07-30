# USDJPY-HYP-039 — 2025H1 Validation Final Decision v2

## Final status

- Hypothesis: `USDJPY-HYP-039`
- Candidate: `C1_SHORT_DUKASCOPY_NATIVE_16BAR_UNCHANGED`
- Candidate contract: `v2`
- Formal deployment decision: `FAIL_CORE_MT4_PORTABILITY_WITH_2025H1_VALIDATION_COMPLETED`
- Economic 2025H1 decision: `PASS_SHORT_PULLBACK_PORTABILITY_PARTIAL_2025H1_RECOVERY`
- Candidate status: `CLOSED_PORTABILITY_FAILURE_WITH_2025H1_EVIDENCE`

This document supersedes the earlier statement that candidate-specific 2025H1 was not executed. It does not reverse the historical portability failure.

## Period roles and outcome access

- 2020–2022: `ANALYSIS_PERIOD`
- 2023–2024: `RESEARCH_AND_CANDIDATE_CONSTRUCTION_PERIOD`
- 2025H1: `VALIDATION_PERIOD`
- First candidate-specific 2025H1 access: `2026-07-30T00:43:08.7774609Z`
- Outcome visibility at first access: `UNSEEN_AT_FIRST_VALIDATION`
- Candidate modified after result: `false`
- 2025H2 accessed: `false`

The unchanged candidate proceeded after the historical portability diagnostic failure only because of an explicit user instruction to complete 2025H1. This continuation did not waive the portability failure for adoption.

## Contract integrity

The executed candidate remained unchanged:

- Short orders only
- 16 M15 bars holding contract
- Shared suppression population: `BOTH_RAW_SIDES_FROM_HYP036_BEFORE_HYP037_SHORT_FILTER`
- Accepted Long events were shadow lifecycle occupancy only
- Long order permission: `false`
- Long P/L computation: `false`
- HYP-038 filter reuse: `false`
- Retuning after result: `false`

Research/Core parity remained `PASS_ZERO_MISMATCH_500_OF_500`, and the validation execution reported zero Research/Core, chronology, currency, and execution-failure mismatches.

## Historical portability result

The Rakuten-native 2023–2024 result remained a binding failure even though aggregate P/L was positive:

- 499 trades
- Net: `+¥10,739`
- PF: `1.1506466907948265`
- Positive folds: `3/4`
- Algorithm or information-time mismatches: `242`
- Common Dukascopy/Rakuten events: `417/500` (`83.4%`)
- Dukascopy-only events: `83`
- Rakuten-only events: `83`
- 2024H1 expected/actual trades: `97/98`

The failure concerns candidate identity and exact portability, not aggregate profitability.

## 2025H1 standalone result

- Trades: `172`
- Net: `+¥3,483`
- PF: `1.12615451483212`
- Win rate: `50.58%`
- Full-equity DD: `¥6,919`
- Realized DD: `¥6,109`
- Minimum equity: `¥95,757`
- Stopout breached: `false`

The candidate therefore produced valid positive economic evidence in the fixed 2025H1 validation period.

## Portfolio comparison

| Configuration | Net | PF | Full-equity DD |
|---|---:|---:|---:|
| B02 + F05 baseline | `-¥20,808` | `0.82941` | `¥42,737` |
| HYP-039 standalone | `+¥3,483` | `1.12615` | `¥6,919` |
| B02 + F05 + HYP-039 | `-¥17,325` | `0.88418` | `¥46,281` |
| B02 + HYP-039 | `-¥3,481` | `0.94317` | `¥18,601` |
| F05 + HYP-039 | `-¥10,361` | `0.91064` | `¥33,628` |

Adding HYP-039 improved the baseline net result by `¥3,483`, but the combined portfolio remained negative and full-equity DD worsened by `¥3,544`.

## Robustness and concentration

- Daily correlation to B02/F05 baseline: `0.4118563198783911`
- Weekly correlation to B02/F05 baseline: `0.2901816869794503`
- Event-bootstrap probability of non-positive net: `26.33%`
- Session-block probability of non-positive net: `29.74%`
- Net after removing top five winners: `-¥1,668`
- Net after removing the top winner decile: `-¥5,209`
- Largest positive month share: `57.95%`
- Maximum losing streak: `10`

The positive standalone result is not sufficiently independent of concentration risk to override the candidate-identity failure.

## Binding decision

The 2025H1 result is valid economic evidence, but HYP-039 is not authorized for portfolio integration, production, or live deployment under this candidate identity.

The exact final action is:

1. Preserve the completed 2025H1 result and immutable Release.
2. Keep the historical `FAIL_CORE_MT4_PORTABILITY` binding.
3. Do not reopen, rescue, retune, re-identify, or apply HYP-038 filters to this candidate.
4. Do not access or substitute 2025H2.
5. Do not include HYP-039 in the authorized Common Portfolio Integration set.

## Authority

- Core scientific Run: `30503084961`
- Core result Issue: `mitsuru93/usdjpyea-core#676`
- Core SHA: `92fa706c5e4957b9250c97cc91be891927565ad6`
- Binding Research SHA: `b6bc006952eb3355cc6a2c27e294a62771196669`
- Release tag: `usdjpy-hyp039-short-pullback-2025h1-validation-v2`
- Release ID: `362131716`
- Release asset ID: `494741716`
- Archive SHA-256: `e13015f77679a230685a867748f5ac000f5f43c920d1574e181b003df353ae4c`
- Release readback: `PASS_BYTE_IDENTICAL_RELEASE_READBACK`
