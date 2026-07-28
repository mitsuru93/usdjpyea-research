# USDJPY-HYP-032 Historical Validation v1 — INVALIDATED

- Canonical status: `TECHNICAL_NO_RESULT_CURRENCY_CONTRACT_NOT_APPLIED`
- Invalidated Run: `30361067984`
- Invalidated decision: `FAIL_HISTORICAL_VALIDATION_NO_RETUNING`
- Scientific result valid: `false`

The MT4 transport account operated as a 10,000-unit USD account. The v1 baseline and candidate result treated raw `AccountBalance` and `AccountEquity` values as JPY. The candidate full-equity calculation also subtracted JPY position MTM from USD equity. Therefore every v1 amount labeled with `¥` and the resulting gate decision are invalid.

The original bytes remain preserved at:

`docs/research/artifact_archives/usdjpy_hyp032_historical_validation_v1/`

The authoritative replacement is the preregistered currency-corrected v2 run. Until v2 produces a technically valid scientific result:

- Core candidate implementation is not authorized.
- MT4 candidate validation is not authorized.
- 2025H1 and 2025H2 access is not authorized.
- Production and live use are not authorized.
- C1 and all scientific gates remain frozen; no retuning is permitted.
