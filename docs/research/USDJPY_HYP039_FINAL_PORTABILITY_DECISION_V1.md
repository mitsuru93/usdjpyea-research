# USDJPY-HYP-039 — Final Portability Decision v1

## Formal decision

`FAIL_CORE_MT4_PORTABILITY`

HYP-039 is complete and closed. The frozen unchanged Short Pullback candidate is not authorized to proceed to the 2025H1 validation-period gate, portfolio integration, production, or live execution.

## Candidate identity

- Hypothesis: `USDJPY-HYP-039`
- Candidate: `C1_SHORT_DUKASCOPY_NATIVE_16BAR_UNCHANGED`
- Contract version: `v2`
- Trading direction: Short only
- Holding contract: unchanged 16 M15 bars
- Suppression population: both raw sides inherited from HYP-036 before the HYP-037 Short filter
- Accepted Long events: shadow lifecycle occupancy only
- Long orders: prohibited
- Long P/L: prohibited
- HYP-038 filter reuse: prohibited and not used

## Gate result

| Gate | Result |
|---|---|
| Frozen Research candidate | PASS |
| Research/Core parity | PASS — 500/500, zero row-field mismatch |
| MetaEditor compile | PASS — 0 errors, 0 warnings |
| Rakuten 2023–2024 portability | **FAIL** |
| 2025H1 validation | Not entered |

The portability gate failed before candidate-specific 2025H1 outcome access. Therefore, the validation-period unseen claim remains unconsumed.

## Rakuten 2023–2024 result

The Rakuten-native implementation was profitable in aggregate, but aggregate profitability does not satisfy the exact portability requirement.

- Trades: 499
- Net: ¥10,739
- Gross profit: ¥82,025
- Gross loss: -¥71,286
- Profit factor: 1.1506466908
- Positive folds: 3/4
- Realized drawdown: ¥7,131
- Execution anomalies: 0
- Currency mismatches: 0
- Algorithm or information-time mismatches: 242

### Fold result

| Fold | Expected | Actual | Net | PF | Full-equity DD |
|---|---:|---:|---:|---:|---:|
| 2023H1 | 124 | 124 | ¥3,314 | 1.239 | ¥3,266 |
| 2023H2 | 137 | 137 | ¥6,586 | 1.416 | ¥4,804 |
| 2024H1 | 97 | 98 | -¥1,958 | 0.862 | ¥3,582 |
| 2024H2 | 142 | 142 | ¥2,311 | 1.083 | ¥7,400 |

## Why portability failed

The Dukascopy Research candidate and Rakuten-native reconstruction each produced 500 candidate events, but only 417 event keys were common.

- Common events: 417
- Common rate: 83.4%
- Dukascopy-only events: 83
- Rakuten-only events: 83

The mismatch set includes fold-boundary signal differences, signal-time shifts, entry and exit price differences, and one-second exit chronology differences. These are not currency-accounting errors or broker execution anomalies. They show that the binding Research event chronology and the Rakuten-native Core/MT4 event chronology are not the same executable candidate.

The positive aggregate result therefore cannot be used to waive the portability gate.

## Suppression lineage audit

- Raw signals: 5,094
- Raw Long signals: 3,224
- Raw Short signals: 1,870
- Accepted Long shadow events: 827
- Accepted Short trades: 500
- Accepted shared-lifecycle events: 1,327
- Long shadow orders opened: 0

This confirms that the v2 implementation preserved the clarified shared-side suppression lineage without introducing Long trading or HYP-038 filtering.

## Period firewall

- 2020–2022: `ANALYSIS_PERIOD`
- 2023–2024: `RESEARCH_AND_CANDIDATE_CONSTRUCTION_PERIOD`
- 2025H1: `VALIDATION_PERIOD`
- Candidate-specific 2025H1 outcome accessed: **No**
- First 2025H1 access timestamp: `null`
- 2025H1 reruns: 0
- Unseen validation claim consumed: **No**
- 2025H2 accessed: **No**

2025H1 was not relabeled as an analysis, development, diagnostic, or tuning period. It was simply not entered because the preceding portability gate failed.

## Immutable evidence

- Core run: `30500520578`
- Core result issue: `#644`
- Core SHA: `2a3ec33dca6b933cd3d5501ba6932dd06f8f75b2`
- Binding Research SHA: `b6bc006952eb3355cc6a2c27e294a62771196669`
- Research/Core parity run: `30463001231`
- Core Release tag: `usdjpy-hyp039-short-pullback-recovery-v1`
- Archive SHA-256: `8a1594ac278dcde1f24388d34c3543d0e273c6ea6f7ba0c794e2f53b3e4fb194`
- Release readback: `PASS_BYTE_IDENTICAL_RELEASE_READBACK`

## Closure

Close the unchanged HYP-039 candidate at `FAIL_CORE_MT4_PORTABILITY`. Preserve the source-audit evidence. Do not rescue, retune, apply the HYP-038 filter, access 2025H1, substitute 2025H2, or authorize portfolio, production, or live use under this candidate identity.
