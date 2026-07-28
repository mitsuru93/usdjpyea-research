# USDJPY-HYP-032 Historical Validation Currency Invalidation v1

## Status

`TECHNICAL_NO_RESULT_CURRENCY_CONTRACT_NOT_APPLIED`

Run `30361067984` and its decision `FAIL_HISTORICAL_VALIDATION_NO_RETUNING` are not scientifically valid.

## Root cause

The MT4 Strategy Tester used a 10,000-unit USD transport account. The workflow passed `TestDeposit`, `TestCurrency`, and `TestLeverage`, but those parameters are not part of the documented MT4 Strategy Tester startup configuration. The baseline summarizer nevertheless labeled raw `AccountBalance` and `AccountEquity` values as JPY.

The historical evaluator then combined:

- raw USD balance/equity values, and
- USDJPY price-based open-position MTM calculated in JPY.

This produced a mixed-currency full-equity curve and invalidated all v1 money amounts and gate conclusions.

## What remains valid

- Candidate freeze: `C1_SHORT_SHARED_SESSION_LOSS_CAP_2`
- Candidate rule and native ordering
- Candidate-free source event identity
- 3,624 opens, 3,624 closes, and 100,055 portfolio snapshots
- No 2025 access

## Corrective action

A frozen currency-repair preregistration now requires:

1. inferring and proving the USD transport account from the immutable input;
2. converting realized account-balance deltas to JPY at contemporaneous USDJPY Bid/Ask;
3. reconstructing baseline and candidate JPY equity from canonical JPY balance and position MTM;
4. retaining the original candidate rule, scientific gates, bootstrap seed, and no-retuning contract;
5. returning a technical no-result rather than a scientific decision if currency normalization or equity-sign stability cannot be proven.

Until the v2 run is valid, Core implementation, MT4 candidate testing, 2025H1/H2, production, and live use remain unauthorized.
