# USDJPY-HYP-032 Historical Validation — Currency-Corrected v2

> Superseded by `docs/research/USDJPY_HYP032_HISTORICAL_VALIDATION_RESULT_V2_1.md`.
>
> Run `30364472840` is scientifically valid, but its raw gate matrix treated a floating-point residue of `8.731149137020111e-11 JPY` as a positive full-equity DD reduction. v2.1 normalizes that value to `¥0.00`, marks `full_equity_dd_reduction_positive=false`, and preserves the same final decision: `FAIL_HISTORICAL_VALIDATION_NO_RETUNING`.

The underlying currency-corrected Run and immutable evidence remain at Release `usdjpy-hyp032-historical-validation-currency-v2`. Use v2.1 for the canonical decision and gate list.
