# USDJPY Tick Pilot 2024-01 Market Profile

## Source run

- Workflow run: `29189903048`
- Artifact: `public-fx-data-pilot-2024-01-USDJPY-aggregate-29189903048`
- Head SHA: `a8921b1ffc512b97b94b87fc327e99b1dbd3b1f9`
- Source: Dukascopy BI5 tick data as public proxy data, not Rakuten MT4 execution data.
- Period: 2024-01-02T00:00Z to 2024-02-01T00:00Z, trading-day chunks.
- Symbol: USDJPY.
- Timeframes generated from tick data: M1, M5, M15, H1.

## Data coverage

Final aggregate coverage:

| Metric | Value |
|---|---:|
| Observed hour records | 528 |
| Downloaded hours | 520 |
| No-tick hours | 8 |
| Hard errors | 0 |
| Effective expected records | 520 |
| Effective coverage | 100.0% |
| Raw manifest records including retry attempts | 827 |

Validation:

| Metric | Value |
|---|---:|
| Validation status | ok |
| Validated bar files | 92 |

This run is acceptable as the first USDJPY tick-derived market-profile artifact.

## Overall profile

Rakuten comparison uses the working base spread assumption of 0.5 pips for USDJPY.

| Timeframe | Bars | Median range pips | P90 range pips | P95 range pips | Median Dukascopy spread pips | P90 Dukascopy spread pips | Median spread/range | Rakuten 0.5 spread / median range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M1 | 31,182 | 2.25 | 4.80 | 6.10 | 0.644 | 0.821 | 28.7% | 22.2% |
| M5 | 6,240 | 5.50 | 11.10 | 13.75 | 0.644 | 0.812 | 11.8% | 9.1% |
| M15 | 2,080 | 9.90 | 19.85 | 25.30 | 0.644 | 0.811 | 6.5% | 5.1% |
| H1 | 520 | 20.15 | 40.31 | 51.69 | 0.647 | 0.832 | 3.2% | 2.5% |

Initial interpretation:

- M1 is usable only if the target edge is much larger than the 0.5-pip Rakuten base spread plus stress assumptions.
- M5 and M15 are more natural first research timeframes because transaction cost consumes a smaller share of median bar range.
- H1 has favorable spread/range economics, but strategy cadence and sample size become different problems.

## Hour-of-day profile

UTC hours. JST = UTC + 9.

### Avoid / no-trade candidates

| UTC hour | JST hour | M1 median range | M1 median Dukascopy spread | M1 spread/range | Rakuten 0.5 / M1 range | Note |
|---:|---:|---:|---:|---:|---:|---|
| 21 | 06 | 1.00 | 0.735 | 80.2% | 50.0% | Pre/around rollover liquidity is poor. |
| 22 | 07 | 1.15 | 3.254 | 269.5% | 41.7% | Strong no-trade candidate. |
| 23 | 08 | 1.40 | 0.898 | 64.6% | 35.7% | Still poor for short-horizon trading. |
| 20 | 05 | 1.45 | 0.592 | 39.2% | 34.5% | Weak M1 economics. |
| 4 | 13 | 1.60 | 0.653 | 41.2% | 31.3% | Low range relative to cost. |

These hours should be excluded from early intraday candidate testing unless the strategy explicitly targets a non-spread-sensitive regime.

### Candidate hours

| UTC hour | JST hour | M1 median range | M5 median range | M15 median range | H1 median range | Rakuten 0.5 / M5 range | Note |
|---:|---:|---:|---:|---:|---:|---:|---|
| 13 | 22 | 3.50 | 8.20 | 13.60 | 36.00 | 6.1% | Good volatility, event sensitivity should be checked. |
| 14 | 23 | 3.83 | 9.13 | 17.80 | 38.38 | 5.5% | Strong candidate window. |
| 15 | 00 | 4.10 | 10.05 | 17.33 | 40.15 | 5.0% | Strong candidate window. |
| 16 | 01 | 2.95 | 7.58 | 13.18 | 24.63 | 6.6% | Still usable. |
| 7 | 16 | 2.95 | 7.03 | 12.20 | 26.55 | 7.1% | Candidate but lower priority than UTC 13-16. |
| 8 | 17 | 2.95 | 6.95 | 12.45 | 24.95 | 7.2% | Candidate but lower priority than UTC 13-16. |

## Initial research decision

For USDJPY, the next research pass should not start with all-session, all-timeframe strategy optimization.

Priority order:

1. Build session-filtered baseline experiments for M5 and M15.
2. Primary candidate window: UTC 13-16, equivalent to JST 22-01.
3. Secondary candidate window: UTC 7-9, equivalent to JST 16-18.
4. Hard exclude for initial tests: UTC 21-23, equivalent to JST 06-08.
5. Keep M1 as a diagnostic timeframe, not the first optimization target.

## Candidate family mapping

The market profile suggests the following order for USDJPY 2024-01:

1. Session-filtered breakout / expansion on M5/M15.
2. Pullback continuation during higher-range sessions.
3. Volatility-regime/no-trade classifier using hour, range, and spread/range features.
4. Mean reversion only after separating low-range and high-spread sessions; all-session mean reversion is not acceptable as a first pass.

## Acceptance requirements for the next step

Next experiments must report:

- Timeframe-specific performance: M5 and M15 at minimum.
- Session-specific performance, especially UTC 13-16 versus excluded hours.
- Rakuten base spread stress: 0.5 pips and multipliers 1.5x, 2.0x, 3.0x.
- Slippage stress: at least 0.1, 0.3, 0.5 pips per side.
- No all-session aggregate survivor may be accepted unless it also survives session decomposition.
- No small-TP system may be accepted if the TP is not materially larger than stressed transaction cost.
