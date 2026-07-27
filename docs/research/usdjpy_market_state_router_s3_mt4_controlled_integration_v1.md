# USDJPY Market-State Router S3_H4_ALIGNED — MT4 Controlled Integration v1

## Decision

`PASS_MT4_CONTROLLED_ORDER_PATH_INTEGRATION`

The frozen `S3_H4_ALIGNED` rule passed controlled integration into the native B02/F05 MT4 order path over 2023–2024.

This decision is subordinate to, and does not alter, the binding preimplementation audit:

- H4 state parity Run `30237882923`: PASS
- Exact frozen 1,882-trade replay/evaluator Run `30238772493`: PASS
- Binding permission mismatch: 0
- Binding population: 671 blocked / 1,211 allowed

## Native order-path test

Core source MT4 Run: `30241240995`

- Baseline native orders: 1,898
- Router decisions: 1,898
- Router blocked: 676
- Router allowed: 1,222
- Candidate orders opened: 1,222
- Candidate orders closed: 1,222
- Blocked orders opened: 0
- Allowed orders missing: 0
- Identity mismatch rows: 0
- OrderSend failures: 0
- OrderClose failures: 0
- Router data errors: 0

The native 1,898-trade population is a non-binding integration diagnostic. It does not replace the frozen 1,882-trade Research population.

## Evaluator repair

The first result was marked FAIL because the evaluator used the close-row `OrderOpenTime` to reconstruct trade identity. Some 2024 opens occurred one second after the canonical M15 boundary. The unchanged MT4 audit was re-evaluated by mapping each close to its open through the MT4 ticket.

Repair Run: `30241915781`

- MT4 rerun: no
- Candidate rule change: no
- Parameter change: no
- Repaired mismatch rows: 0
- Repaired status: PASS

## Tester comparison — currency-label correction

The original table labelled balance and equity values as JPY. The later ticket-level Economic Attribution audit proved that the effective Strategy Tester account currency was **USD**. The JPY labels below are therefore superseded; the values were account-currency figures.

| Metric | Baseline | S3 candidate | Delta |
|---|---:|---:|---:|
| Balance net, effective account currency USD | $317.00 | $496.78 | +$179.78 |
| Original report maximum equity DD, effective account currency USD | $311.87 | $201.70 | −$110.17 |
| Maximum open orders | 9 | 9 | 0 |
| Maximum open lots | 0.09 | 0.09 | 0.00 |

The controlled-integration stage passes because permission decisions, order admission, order exclusion, order opening, and fixed-time closing are internally consistent in MT4. The authoritative economic interpretation is now:

- `docs/research/usdjpy_market_state_router_s3_mt4_economic_attribution_v1.md`
- `configs/research/usdjpy_market_state_router_s3_mt4_economic_attribution_receipt_v1.json`

The Economic Attribution audit separately reports quote-currency gross P/L in JPY and account-currency P/L in USD, reconciles every final balance, and identifies the controlled-integration JPY labels as an accounting-unit defect.

## Authorization boundary

- 2025H1 accessed: false
- 2025H2 accessed: false
- 2025 evaluation authorized by this receipt: false
- Production authorized: false
- Live orders authorized: false

A separate explicit decision is required before any 2025 out-of-sample validation.

Machine-readable Research receipt:

`configs/research/usdjpy_market_state_router_s3_mt4_controlled_integration_receipt_v1.json`

Core canonical receipt:

`docs/research/market_state_router_s3_h4_aligned_mt4_controlled_integration_v1/final_receipt.json`

Immutable Core evidence Release:

`usdjpy-market-state-router-s3-controlled-integration-v1`
