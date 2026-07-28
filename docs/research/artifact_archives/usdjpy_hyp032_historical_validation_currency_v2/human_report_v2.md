# USDJPY-HYP-032 Historical Validation — Currency-Corrected v2

- Decision: `FAIL_HISTORICAL_VALIDATION_NO_RETUNING`
- Scientific result valid: `true`
- Invalidated prior run: `30361067984` (`FAIL_HISTORICAL_VALIDATION_NO_RETUNING`)
- Transport account inferred: `USD`; canonical reporting currency: `JPY`.
- Candidate: `C1_SHORT_SHARED_SESSION_LOSS_CAP_2`
- Baseline trades: `2782`; candidate trades: `2760`; blocked: `22`.
- Net: baseline `¥29,019.63` / candidate `¥30,096.71` / delta `¥1,077.07`.
- PF: baseline `1.077956` / candidate `1.081614`.
- Realized DD reduction: `¥0.00`.
- Full-equity DD reduction: `¥0.00`.
- Winner retention: `99.399696%`; top-20 winner loss: `¥0.00`.
- Positive years: `1/3`; positive half-years: `3/6`; minimum half-year delta: `¥-1,048.74`.
- Bootstrap lower 95%: `¥-1,941.24`; P(non-positive): `23.850000%`.
- Technical failures: `none`.
- Failed scientific gates: `realized_dd_reduction_positive, positive_calendar_years_at_least_2of3, positive_halfyears_at_least_4of6, largest_positive_year_share_at_most_60pct, largest_positive_session_share_at_most_60pct, largest_positive_month_share_at_most_25pct, top3_events_removed_positive, date_session_bootstrap_lower_95_positive, date_session_bootstrap_probability_nonpositive_at_most_5pct`.
- 2025 was not accessed. Candidate rule and scientific gates were not retuned.
