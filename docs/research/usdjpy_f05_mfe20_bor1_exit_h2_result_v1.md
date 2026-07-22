# USDJPY F05 MFE20 BOR1 Exit — 2024 H2 binding result v1

## Decision

`F05_MFE20_BOR1_EXIT_v1` is **CLOSED_FAIL_H2**.

The exact rule was evaluated on 2024 H2 using Rakuten MT4 Strategy Tester. The entry set remained unchanged, B02 remained exactly unchanged, and all implementation identities and accepted H2 baseline values reconciled. The candidate nevertheless failed two preregistered binding gates. The exact specification is closed and is not eligible for 2025 H1 execution.

## Evidence

### Rakuten MT4 execution

- source Run: `29895387329`
- source artifact: `8519879009`
- artifact digest: `sha256:1341850d4530d9bb8ea6522aefaa796dd5ea70abc698913633cb523f55d51981`
- baseline audit SHA-256: `a5a871d7105c6e68548e804c9ab517ee6bc0b08553474b158799f47ebd32edcd`
- candidate audit SHA-256: `bfd65081b2d086cd2264406653f236c3d655edcc0de70d8f92b5f3c2dc50abdd`

Both the unchanged baseline and the frozen candidate completed in MT4. No candidate-specific 2025 H1 data was accessed.

### Binding evaluator repair

The unique period-end open-position audit row omitted `signal_utc` and `entry_utc`. Research authorization allowed only those two blank cells in each audit copy to be populated from the unique same-ticket `order_opened` row. Source audits were not overwritten, P/L and risk fields were not changed, and MT4 was not rerun.

- binding evaluation Run: `29896667418`
- result artifact: `8520231535`
- artifact digest: `sha256:0614d69f460889e6f93a490325c3436979669effa76a3cd7d9804d7448b5faef`
- result SHA-256: `ddeb00dd18b25a2dcc025d9a2d4671ebb3a4e2843165b5d91922f5d99a341f69`
- changed outcomes SHA-256: `755e916aa54799c72bb40284335db03eeeb47adeac7e4fb430055be57c7b55eb`

## Metrics

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| Closed net JPY | 38,358 | 41,676 | +3,318 |
| Complete-outcome net JPY | 38,109 | 41,427 | +3,318 |
| Closed PF | 1.354963 | 1.430822 | +0.075859 |
| Complete-outcome PF | 1.351848 | 1.427149 | +0.075301 |
| Tick-equity DD JPY | 19,603 | 15,063 | -4,540 |
| Minimum equity JPY | 95,271 | 95,271 | 0 |
| Final equity JPY | 138,109 | 141,427 | +3,318 |
| Changed F05 outcomes | — | 76 | — |

B02 remained exactly unchanged at complete-outcome net `+15,627 JPY`. F05 complete-outcome net increased from `+22,482 JPY` to `+25,800 JPY`.

## Month and concentration results

| Month | Effect JPY |
|---|---:|
| 2024-07 | +73 |
| 2024-08 | -3,560 |
| 2024-09 | +6,195 |
| 2024-10 | -354 |
| 2024-11 | +1,695 |
| 2024-12 | -731 |

- positive effect months: 3
- negative effect months: 3
- Q3 delta: `+2,708 JPY`
- Q4 delta: `+610 JPY`
- benefit: `15,906 JPY`
- harm: `12,588 JPY`
- largest positive entry-date share: `19.71%`
- delta after removing the two strongest positive entry dates: `-1,944 JPY`

## Failed binding gates

1. `negative_effect_months_at_most_1`
   - observed: 3 negative months
   - required: at most 1
2. `ex_best_two_positive_entry_dates_delta_positive`
   - observed: `-1,944 JPY`
   - required: positive

All other frozen H2 gates passed. A positive aggregate delta, higher PF and lower drawdown do not override a failed binding gate.

## Closure rule

- no H2 retuning or threshold repair;
- no combination with closed S1-S3 or closed Entry filters;
- no 2025 H1 execution for this exact specification;
- any successor must receive a new candidate ID and return to 2024 H1 under a preregistered independent mechanism or finite procedure;
- no live-order use is authorized.
