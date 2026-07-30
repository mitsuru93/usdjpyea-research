# USDJPY-HYP-043 C2 2025H1 Revalidation Addendum

## Correction

The prior HYP-043 closure incorrectly treated the historical candidate-admission gate as permission to omit candidate-specific 2025H1 economic replay. The user did not authorize that omission and explicitly directed that C2 be run.

This addendum does not reopen HYP-041, retune C2, alter another hypothesis decision, access 2025H2, or authorize production.

## Frozen C2 rule

`C2_LOCALIZED_SHORT_ACCEPTANCE_COMPRESSION`

- Short only
- HIGH historical ATR-tertile volatility state
- `extension_atr >= 2.00`
- At the completed 60-second observation: `current_pips <= 0`
- At the same observation: `MFE < 0.25 × Entry ATR`
- Exit at the observed 60-second excursion price

The rule was not modified after observing the new C2-specific 2025H1 result.

## Historical evidence retained

| Metric | C2 |
|---|---:|
| Affected trades | 154 |
| Modified share | 10.61% |
| F05 net | +¥38,329 |
| F05 net retention | 97.90% |
| Gross-profit retention | 88.26% |
| Winner-count retention | 91.74% |
| PF | 1.1604 |
| Realized DD | ¥23,847 |
| Positive-effect half-year folds | 2/4 |

The historical fold-breadth gate remains failed because the preregistered minimum was 3/4.

## 2025H1 economic result

| Metric | Baseline F05 | C2 F05 | Change |
|---|---:|---:|---:|
| Trades | 358 | 358 | 0 |
| Net | -¥13,844 | -¥7,935 | **+¥5,909** |
| Gross profit | ¥74,489 | ¥61,254 | -¥13,235 |
| Gross loss | -¥88,333 | -¥69,189 | +¥19,144 |
| PF | 0.8433 | 0.8853 | +0.0420 |
| Realized DD | ¥29,339 | ¥24,118 | **-¥5,221** |
| Minimum realized equity | ¥70,661 | ¥75,882 | +¥5,221 |
| Modified trades | 0 | 63 | 17.60% of F05 |

C2 reduced losses materially but did not restore F05 to positive net.

## Portfolio result

| Portfolio | Net | PF | Change vs baseline |
|---|---:|---:|---:|
| B02 baseline + F05 baseline | -¥20,808 | 0.8294 | — |
| B02 baseline + F05 C2 | -¥14,899 | 0.8551 | **+¥5,909** |
| B02 C3 reserve + F05 baseline | -¥11,523 | — | — |
| B02 C3 reserve + F05 C2 | -¥5,614 | — | **+¥5,909** |

B02 was unchanged. B02 C3 remains a research counterfactual reserve only.

Event-level combined realized DD and Tick full-equity DD require the separate Core/MT4 replay and are not inferred from aggregate net figures.

## Robustness and concentration

- Event bootstrap, 10,000 samples: positive net share 22.23%; p05 -¥24,393; median -¥7,738; p95 +¥8,798.
- Extra spread +0.5 pip: -¥9,725.
- Extra spread +1.0 pip: -¥11,515.
- Extra spread +2.0 pips: -¥15,095.
- Entry-delay proxy +1 second: -¥8,114.
- Entry-delay proxy +5 seconds: -¥8,293.
- Entry-delay proxy +15 seconds: -¥8,651.
- Largest winner: ¥1,368.
- Largest loser: -¥3,473.
- Top-one winner removal: -¥9,303.

The result is not dependent on one oversized winner, but the candidate remains negative and has weak bootstrap positivity.

## Decisions

- Formal historical decision: `NO_HISTORICALLY_ADMISSIBLE_LOCALIZED_F05_CANDIDATE`
- Economic 2025H1 decision: `PARTIAL_RECOVERY_ECONOMIC_HISTORICAL_GATE_FAIL`
- Deployment eligibility: false
- Common Portfolio integration eligibility: false
- Diagnostic/economic evidence eligibility: true
- Production/live: false

## Exact next action

Complete event-level B02+F05 replay, Tick full-equity DD, Core/MT4 parity, and Rakuten portability for the exact unchanged frozen C2 rule. Do not retune C2 or convert the 2/4 historical fold result into a pass.
