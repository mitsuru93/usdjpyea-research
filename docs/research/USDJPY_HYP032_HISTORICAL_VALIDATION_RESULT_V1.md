# USDJPY-HYP-032 Historical Validation

- Decision: `FAIL_HISTORICAL_VALIDATION_NO_RETUNING`
- Candidate: `C1_SHORT_SHARED_SESSION_LOSS_CAP_2`
- Baseline trades: `2782`; candidate trades: `2760`; blocked: `22`.
- Net: baseline `¥275.92` / candidate `¥288.06` / delta `¥12.14`.
- PF: baseline `1.089413` / candidate `1.094321`.
- Realized DD reduction: `¥-0.00`.
- Full-equity DD reduction: `¥-2,479.20`.
- Winner retention: `99.412820%`; top-20 winner loss: `¥0.00`.
- Positive years: `1/3`; positive half-years: `3/6`; minimum half-year delta: `¥-8.03`.
- Bootstrap lower 95%: `¥-13.85`; P(non-positive): `18.080000%`.
- Failed gates: `realized_dd_reduction_positive, full_equity_dd_reduction_positive, positive_calendar_years_at_least_2of3, positive_halfyears_at_least_4of6, largest_positive_year_share_at_most_60pct, largest_positive_session_share_at_most_60pct, largest_positive_month_share_at_most_25pct, top3_events_removed_positive, date_session_bootstrap_lower_95_positive, date_session_bootstrap_probability_nonpositive_at_most_5pct`.
- 2025 was not accessed. No retuning is permitted.
