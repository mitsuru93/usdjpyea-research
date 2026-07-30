# USDJPY-HYP-043 — F05 Localized State–Loss Persistence and Lifecycle Recovery

## Final decision

`NO_HISTORICALLY_ADMISSIBLE_LOCALIZED_F05_CANDIDATE`

Economic decision: `NO_RECOVERY_NOT_REVALIDATED_AFTER_BINDING_HISTORICAL_GATE`

No preregistered candidate passed every binding 2023–2024 F05 historical support and fold-breadth gate. Therefore no candidate was frozen, no candidate-specific 2025H1 replay was executed, and no Core/MT4/Rakuten candidate qualification was authorized.

## Baseline reproduction

| Scope | Trades | Net JPY | Gross profit | Gross loss | PF | Realized / Tick-equity DD |
|---|---:|---:|---:|---:|---:|---:|
| 2023–2024 F05 | 1,451 | +¥39,151 | ¥314,089 | -¥274,938 | 1.142399 | ¥28,862 realized |
| 2025H1 F05 | 358 | -¥13,844 | ¥74,489 | -¥88,333 | 0.843275 | baseline authority |
| 2025H1 B02+F05 | 463 | -¥20,808 | — | — | 0.829408 | ¥42,737 Tick-equity |
| 2025H1 B02 C3 reserve + F05 baseline | — | -¥11,523 | — | — | — | net-only reserve comparison |

JPY accounting, trade counts, chronology and baseline identities matched the canonical authority.

## Finite candidate results

| Candidate | Affected | Modified share | 2023–2024 net | Net retention | GP retention | Winner retention | Positive-effect folds | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| C1 Localized Short Loss-Persistence Permission | 0 | 0.00% | +¥39,151 | 100.00% | 100.00% | 100.00% | 0/4 | Reject: zero support |
| C2 Localized Short Acceptance Compression | 154 | 10.61% | +¥38,329 | 97.90% | 88.26% | 91.74% | 2/4 | Reject: fold breadth |
| C3 Localized Prior-Loss Giveback Exit | 0 | 0.00% | +¥39,151 | 100.00% | 100.00% | 100.00% | 0/4 | Reject: zero support |

C2 changed a genuinely localized population and preserved most historical economics. Its half-year deltas were:

- 2023H1: +¥2,805
- 2023H2: -¥2,905
- 2024H1: +¥2,274
- 2024H2: -¥2,996

The preregistered gate required the same-direction effect in at least three of four half-years. C2 achieved two. Portfolio aggregation cannot rescue a failed mandatory F05 historical subgate.

## Concentration and robustness

C2 remained positive after removal of the top one, three and five events:

- top one removal net: +¥35,877
- top three removal net: +¥31,364
- top five removal net: +¥27,337
- top winner decile removal net: -¥50,186
- worst day: -¥6,061
- worst month: -¥11,747

Historical robustness included spread +0.5/+1/+2 pips, entry-delay proxies at +1/+5/+15 seconds, same-timestamp ordering variation, one-minute timestamp precision, top-event removal, worst-day/month checks, 10,000 event bootstraps, 10,000 date/session-block bootstraps and limited adjacent-threshold sensitivity. These checks did not change the binding support/fold result.

## Candidate freeze and 2025H1

Candidate freeze status: `NO_CANDIDATE_FREEZE_PERMITTED`.

2025H1 remained `VALIDATION_PERIOD_REVALIDATION_MODIFIED_AFTER_VALIDATION_RESULT`. Its canonical baseline was reproduced, but candidate-specific outcomes were not computed because no candidate passed the historical gate. Consequently:

- F05 candidate improvement: not applicable
- portfolio candidate improvement: not applicable
- candidate PF: not applicable
- candidate realized/full-equity DD: not applicable
- candidate margin/concurrency: not applicable
- recovery classification: not applicable

This is not a technical no-result. It is the preregistered scientific stopping rule.

## Core, MT4 and Rakuten portability

No candidate module was authorized or created.

- Research/Core parity: not applicable — no selected candidate
- Core/MT4 parity: not applicable — no selected candidate
- MetaEditor compile: not applicable — no candidate module
- Rakuten 2023–2024 portability: not applicable — no selected candidate
- candidate full-equity/margin/concurrency replay: not applicable — no selected candidate

Baseline B02 remained unchanged. HYP-042 C3 remained a research counterfactual reserve only.

## 2020–2022

No selected candidate existed, and no certified 2020–2022 authority was bound to this run. No 2020–2022 result was used for candidate selection, threshold changes, Core authorization or the formal decision.

## Isolation controls

- HYP-041 was not reopened, rescued or rejudged.
- HYP-027, HYP-029, HYP-032, HYP-039, HYP-040, HYP-041 and HYP-042 formal decisions were unchanged.
- 2025H2 was not accessed.
- candidate rule changed after result: false.
- production authorized: false.
- live authorized: false.

## Evidence

- Research preregistration PR: #439
- Core execution PR: #695
- Core scientific closure PR: #696
- Scientific run: `30523476402`
- Core scientific result merge SHA: `1e6a5eda4ee9f36ad2d5c9defa61dfcc5a535cea`
- Deterministic archive: `usdjpy-hyp043-f05-localized-recovery-v1.zip`
- Archive SHA-256: `b7004225b637205623fcc38630c57c272dcf8b0de20774d6d6cb38c1ee75c157`
- Archive size: 510,084 bytes
- Archive files: 18

## Common Portfolio handoff

HYP-043 is not an eligible portfolio constituent. The immutable handoff contains diagnostic intersection and residual-loss evidence only. Common Portfolio Integration must continue with `F05_BASELINE_UNCHANGED` and must not inject HYP-043 candidate logic.

## Exact next action

Keep `F05_BASELINE_UNCHANGED`. Do not implement or integrate HYP-043 candidates. Import the localized failure/intersection evidence into Common Portfolio Integration as immutable diagnostic evidence only. Any further F05 recovery mechanism must be a new independently preregistered hypothesis rather than threshold retuning or union rescue.
