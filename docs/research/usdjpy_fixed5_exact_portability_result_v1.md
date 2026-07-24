# USDJPY Fixed-Five Exact Portability Result v1

Decision: **close RQ-020A and RQ-020D; proceed to descriptive RQ-020B**

## Exact transformer repair

The accepted 2023 compatibility builder was reconstructed from the normalized M15 field `first_timestamp_mt4_server`, not from the rounded normalized UTC timestamp. Applying the historical EA `ServerToUtc` rule to that server timestamp reproduces exactly:

- 24,825 M15 rows;
- 1,543 shifted timestamps;
- zero duplicate or nonascending timestamps;
- canonical 2023 B02/F05 ledger: 964 exact rows;
- historical-compatible 2023 baseline: 961 opened / 960 closed, B02 JPY -12,459, F05 JPY +3,180, total JPY -9,279.

The prior 1,428-shift reconstruction remains a technical-incomplete orientation run and is not evidence.

## 2024 regression

The unchanged five-strategy evaluator exactly reproduced every accepted 2024 H1 and H2 signal row and every T0 fixed-time trade key/numeric field. Historical 2024 data and outcomes were not modified.

## 2023 portability

No fixed strategy passed the full-year/default/severe and both-half-year gates.

| Entity | Default pips | Severe pips | Worst default half | Worst severe half |
|---|---:|---:|---:|---:|
| H04 volatility-adjusted momentum | +51.2 | -590.8 | -554.8 | -858.8 |
| F05 Donchian 96 | +524.9 | -923.1 | -1,063.7 | -1,789.7 |
| B02 session breakout | -1,226.0 | -1,686.0 | -1,418.8 | -1,660.8 |
| E02 8-hour resumption | -1,047.5 | -2,401.5 | -756.1 | -1,460.1 |
| E03 12-hour resumption | -256.8 | -2,992.8 | -1,280.8 | -2,638.8 |

F05 and H04 only appear positive after pooling 2023. Both lose in 2023 H1 and under severe cost; they therefore do not transport as fixed edges.

## Static portfolio result

All predeclared equal-weight portfolios fail. The least-negative default portfolio excludes B02, but still returns -728.2 pips default and -6,908.2 pips severe over 2023. The equal-weight five-strategy portfolio returns -1,954.2 pips default and -8,594.2 pips severe. No weight was optimized.

## Interpretation

The frozen 2024 strategy universe is not a static cross-year solution. The 2023 H1 loss is broad across all five mechanisms, while 2023 H2 is materially stronger. This strengthens the hypothesis that the relevant distinction is a market regime state rather than a missing fixed strategy or a local B02/F05 repair.

## Next analysis

RQ-020B will descriptively test only predeclared 5-day and 20-day no-lookahead market states across 2023 H1, 2023 H2, 2024 H1 and 2024 H2:

- directional return and 5d/20d agreement;
- path efficiency;
- short/long realized-volatility ratio;
- position inside the 20-day range.

No router, threshold optimization, MT4 test or 2025 access is authorized at this stage.
