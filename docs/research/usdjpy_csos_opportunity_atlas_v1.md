# USDJPY CSOS Opportunity Atlas v1

`CSOS_OPPORTUNITY_ATLAS_COMPLETE_NO_EA_AUTHORIZATION`

- Research SHA: `11643bd5c9d04dec1d8df34e681b6516cc39264b`
- Core SHA inspected: `aca45ab891d9a6da272b5111a99142d99e874929`
- Run: `30202064383`
- Periods: 2023H1, 2023H2, 2024H1, 2024H2
- 2025 accessed: false
- B02/F05 modified: false
- Optimization / EA / MT4 / Core modification: false

## Opportunity Atlas

|Rank|Family|Opp./yr|Net|Weak-market net|Coverage|Corr B02|Corr F05|Overlap|Positive folds|MDD improvement|Score|
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|1|D — Shock Failure|57.0|¥12,847|¥9,644|5.2%|0.068|-0.064|86.8%|3/4|¥2,635|71.9|
|2|F — Liquidity Sweep|467.0|¥7,708|¥30,621|23.0%|-0.252|-0.246|83.7%|2/4|¥8,203|53.3|
|3|J — Pullback Continuation|666.5|¥20,752|¥-39,589|9.6%|0.341|0.450|78.4%|4/4|¥7,259|42.1|
|4|C — Shock Continuation|321.5|¥7,545|¥-5,984|11.7%|-0.001|0.149|87.4%|2/4|¥404|41.5|
|5|E — Session Transition|168.0|¥2,484|¥-10,502|3.4%|0.294|0.345|86.3%|3/4|¥1,753|39.5|
|6|H — Volatility Compression Breakout|173.5|¥1,407|¥-5,949|5.0%|0.092|0.099|62.0%|1/4|¥-240|39.4|
|7|B — Balance Mean Reversion|173.5|¥-7,006|¥1,762|9.9%|-0.003|-0.021|73.5%|1/4|¥-1,018|37.1|
|8|A — False Breakout Reversal|569.5|¥-29,462|¥17,379|21.7%|-0.301|-0.296|79.3%|1/4|¥-3,715|35.2|
|9|G — Trend Exhaustion|620.5|¥-9,439|¥49,122|25.7%|-0.350|-0.563|80.3%|1/4|¥2,832|34.2|
|10|I — Failed Trend Continuation|31.5|¥-1,981|¥-673|1.6%|0.004|-0.008|74.6%|2/4|¥21|20.4|
|11|K — Other Literature- and Practice-Led Families|849.0|¥-14,736|¥-26,385|18.9%|0.042|0.197|78.8%|1/4|¥-17,623|19.7|

## Top 10 fixed variants

1. **D_SHOCK_FAILURE** — score 71.9; 114 opportunities; ¥12,847; 3/4 folds.
2. **F_ASIAN_RANGE_SWEEP** — score 58.0; 545 opportunities; ¥8,708; 4/4 folds.
3. **F_PREVIOUS_DAY_SWEEP** — score 55.0; 527 opportunities; ¥2,763; 3/4 folds.
4. **J_PULLBACK_CONTINUATION** — score 42.1; 1333 opportunities; ¥20,752; 4/4 folds.
5. **C_SHOCK_CONTINUATION** — score 41.5; 643 opportunities; ¥7,545; 2/4 folds.
6. **K_DAILY_TIME_SERIES_MOMENTUM** — score 40.9; 445 opportunities; ¥1,712; 2/4 folds.
7. **E_LONDON_NY** — score 40.0; 139 opportunities; ¥2,154; 3/4 folds.
8. **H_COMPRESSION_BREAKOUT** — score 39.4; 347 opportunities; ¥1,407; 1/4 folds.
9. **K_LONDON_OPENING_RANGE_BREAKOUT** — score 39.0; 607 opportunities; ¥1,070; 2/4 folds.
10. **E_TOKYO_LONDON** — score 38.5; 119 opportunities; ¥1,148; 2/4 folds.

## Top 3 next-stage priorities

1. **D — Shock Failure** — PORTABLE_POSITIVE_PRIORITY; score 71.9; ¥12,847.
2. **J — Pullback Continuation** — PORTABLE_POSITIVE_PRIORITY; score 42.1; ¥20,752.
3. **E — Session Transition** — PORTABLE_POSITIVE_PRIORITY; score 39.5; ¥2,484.

## Boundaries and limitations

The top family is a research priority, not an adopted third strategy. Portfolio values are additive fixed-lot estimates without margin, variable spread, slippage, or admission conflicts. 2024 accepted Bid/Ask-derived bars are not Rakuten quote history. Carry, value, order-flow, macro-surprise and options families remain unquantified because authoritative inputs are absent.
