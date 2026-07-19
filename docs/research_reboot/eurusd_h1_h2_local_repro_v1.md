# EURUSD 2024 H1 development / H2 validation — local reproducibility result v1

Created: 2026-07-19 JST

## Status

This is the local reproducibility result produced with the same committed runner, registered literature candidate universe, fixed analysis protocol, hard no-trade window, and canonical EURUSD 2024 H1 bar source used by the formal GitHub Actions workflow.

It is recorded immediately so the H1/H2 research does not wait behind the concurrent EURUSD Tick archive jobs. The formal Actions result remains the independent execution record and must reproduce this result before it becomes the authoritative workflow receipt.

## Fixed period rule

- Development: 2024-01-01T00:00:00Z through 2024-07-01T00:00:00Z exclusive.
- Validation: 2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive.
- Calendar H2 is validation-only.
- H2 did not nominate families, select parameters, or modify rules.
- The development runner received a physically separate file containing no timestamp at or after 2024-07-01.
- `development_lock.json` was generated before H2 evaluation.

Market bars are one-hour bars. In this document, H1 and H2 refer to the first and second calendar half-years of 2024.

## Candidate universe

The registered A-J literature-derived family universe expanded to 46 candidates.

H1 development nominated four families:

1. A — intraday local-currency direction;
2. F — Bollinger/z-score mean reversion;
3. G — RSI-extreme mean reversion;
4. H — failed-breakout reversal.

The development representatives locked before H2 were:

- `A2_europe_local_short_hold8`
- `F_z_lb72_thr2p0_hold12`
- `F_z_lb72_thr2p0_hold6`
- `F_z_lb72_thr1p5_hold12`
- `G_rsi14_30_70_hold12`
- `G_rsi14_30_70_hold6`
- `H_failed_lb48_hold12`
- `H_failed_lb24_hold6`

## Fixed H2 result

Only family A passed the final family gate.

Only candidate `A2_europe_local_short_hold8` passed the complete H2 and full-year representative gates.

Rule:

- timezone: `Europe/Berlin`;
- entry: short at the open of the H1 bar beginning at 08:00 Europe/Berlin local time;
- hold: eight one-hour bars;
- signal and entry time are DST-aware;
- project hard no-trade windows remain applied;
- cost basis is `max(0.6 pips, public entry spread_mean_pips)`.

## A2 metrics

### Development: January-June 2024

- trades: 129
- average default-cost net: +1.995845 pips/trade
- profit factor: 1.177166
- positive months: 5 of 6
- severe-stress profit factor: 0.983449

### Fixed validation: July-December 2024

- trades: 132
- average default-cost net: +1.180005 pips/trade
- profit factor: 1.113616
- positive months: 4 of 6

### Full 2024 descriptive aggregation

- trades: 261
- average default-cost net: +1.583236 pips/trade
- total default-cost net: approximately +413.22 pips
- profit factor: 1.146317
- positive months: 9 of 12
- total after removing the best two entry days: +235.474628 pips
- severe-stress profit factor: 0.943509

The full-year figures are descriptive gate calculations after H1 nomination and fixed H2 validation. They were not used to alter the candidate definition.

## Other H1-nominated families

### Family F

Several z-score variants remained positive in H2, but no locked H1 representative passed every final condition. The strongest near miss was `F_z_lb72_thr1p5_hold12`:

- H2 average net: +1.023148 pips/trade;
- H2 profit factor: 1.102915;
- full-year positive months: 7, below the registered requirement of 8.

No threshold was relaxed after inspecting H2.

### Family G

The locked RSI representatives failed the fixed H2 candidate gate.

### Family H

The family failed the required H2 neighboring-variant support and representative-survival conditions.

## Interpretation boundary

This result identifies one candidate that survived this specific 2024 H1-development/H2-validation protocol. It is not yet evidence of stability across years, broker execution, or independent market regimes.

The immediate next research stage must preserve 2024 H2 as consumed validation data. It must not be reused for further parameter selection. Any subsequent refinement requires a new development period and a new untouched validation period.

## Reproduction files

- `configs/research/eurusd_h1_prior_literature_candidates_v1.json`
- `configs/research/eurusd_h1_h2_analysis_protocol_v1.json`
- `tools/eurusd_h1_h2_data_v1.py`
- `tools/eurusd_h1_h2_eval_v1.py`
- `tools/run_eurusd_h1_h2_screen_v1.py`
- `tools/test_eurusd_h1_h2_screen_v1.py`
- `.github/workflows/run_eurusd_h1_h2_screen_v1.yml`
