# USDJPY-HYP-032 Historical Validation — Currency-Corrected v2.1

## Final decision

`FAIL_HISTORICAL_VALIDATION_NO_RETUNING`

This is the canonical numerically normalized result. It inherits the currency-corrected Run `30364472840` and corrects only a floating-point cancellation residue in the full-equity DD gate. The scientific decision is unchanged.

## Currency contract

- MT4 transport account: `USD`, initial balance `10,000.00`
- Canonical reporting currency: `JPY`
- Canonical initial capital: `¥100,000.00`
- Currency inference and all technical checks: PASS
- 2025 accessed: `false`

## Economics

- Baseline: 2,782 trades, net `¥29,019.63`, PF `1.077956`
- Candidate: 2,760 trades, net `¥30,096.71`, PF `1.081614`
- Blocked: 22 trades—13 losers and 9 winners
- Net improvement: `¥1,077.07`
- Realized DD: baseline `¥40,634.40`, candidate `¥40,634.40`, reduction `¥0.00`
- Full-equity DD: baseline `¥41,383.12`, candidate `¥41,383.12`, reduction `¥0.00`
- Minimum equity improvement: `¥1,670.70`
- Winner retention: `99.399696%`
- Top-20 winner loss: `¥0.00`

## Robustness

- Positive calendar years: `1/3`
- Positive half-years: `3/6`
- Minimum half-year delta: `¥-1,048.74`
- Largest positive year share: `100.00%`
- Largest positive session share: `74.95%`
- Largest positive month share: `39.52%`
- Best event removed: `¥395.15`
- Top-3 events removed: `¥-896.68`
- Bootstrap 95% CI: `¥-1,941.24` to `¥3,978.35`
- Bootstrap P(non-positive): `23.85%`

## Failed gates

1. `realized_dd_reduction_positive`
2. `full_equity_dd_reduction_positive`
3. `positive_calendar_years_at_least_2of3`
4. `positive_halfyears_at_least_4of6`
5. `largest_positive_year_share_at_most_60pct`
6. `largest_positive_session_share_at_most_60pct`
7. `largest_positive_month_share_at_most_25pct`
8. `top3_events_removed_positive`
9. `date_session_bootstrap_lower_95_positive`
10. `date_session_bootstrap_probability_nonpositive_at_most_5pct`

## Authority

C1 improves aggregate net and PF slightly, but the effect does not reduce realized or full-equity DD and is concentrated in 2021, London, and a small number of events. Historical portability is therefore rejected.

- No retuning is permitted.
- Core candidate implementation is not authorized.
- MT4 candidate validation is not authorized.
- 2025H1 and 2025H2 access is not authorized.
- Production and live use are not authorized.
