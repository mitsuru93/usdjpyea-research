# F05_MFE20_BOR1_EXIT_v1 — 2024 H2 Binding Result v1

## Formal decision

**CLOSED_FAIL_H2**

The exact F05 structural-exit specification completed unchanged 2024 H2 Rakuten MT4 Strategy Tester validation. Aggregate net, PF and tick-equity DD improved, but two preregistered stability gates failed. The exact specification is closed and is not authorized for candidate-specific 2025 H1 execution.

## Evidence

- Source MT4 Run: `29895387329`
- Source MT4 artifact: `8519879009`
- Source artifact digest: `sha256:1341850d4530d9bb8ea6522aefaa796dd5ea70abc698913633cb523f55d51981`
- Binding evaluator decision Run: `29896667418`
- Decision artifact: `8520231535`
- Decision artifact digest: `sha256:0614d69f460889e6f93a490325c3436979669effa76a3cd7d9804d7448b5faef`
- Candidate logic changed after H2: no
- Parameter or gate changed after H2: no
- MT4 rerun during evaluator repair: no
- 2025 H1 accessed: no

## Result

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| Opened / closed | 494 / 493 | 494 / 493 | 0 / 0 |
| Closed net JPY | 38,358 | 41,676 | +3,318 |
| Complete marked net JPY | 38,109 | 41,427 | +3,318 |
| Closed PF | 1.354963 | 1.430822 | improvement |
| Tick-equity DD JPY | 19,603 | 15,063 | -4,540 |
| Minimum tick equity JPY | 95,271 | 95,271 | 0 |
| B02 closed net JPY | 15,627 | 15,627 | 0 |
| F05 closed net JPY | 22,731 | 26,049 | +3,318 |

The rule changed 76 F05 outcomes and left the complete entry set and B02 unchanged.

## Monthly effect

| Month | Delta JPY |
|---|---:|
| 2024-07 | +73 |
| 2024-08 | -3,560 |
| 2024-09 | +6,195 |
| 2024-10 | -354 |
| 2024-11 | +1,695 |
| 2024-12 | -731 |

Positive-effect months: 3. Negative-effect months: 3.

## Failed binding gates

1. `negative_effect_months_at_most_1`: failed with three negative-effect months.
2. `ex_best_two_positive_entry_dates_delta_positive`: failed at JPY `-1,944`.

The aggregate JPY +3,318 result depended on the two strongest positive entry dates. Removing those dates left a negative residual effect.

## Closure

- exact specification status: `CLOSED_FAIL_H2`;
- H2 repair or retuning: prohibited;
- combination from this H2 result: prohibited;
- candidate-specific 2025 H1 Rakuten MT4 execution: not authorized;
- successor requirement: new mechanism or candidate ID, return to 2024 H1 under `usdjpy_validation_operating_contract_v3`.
