# USDJPY 2020–2025H1 P4 Residual-Loss Elimination and Cross-Regime Stability Improvement Study

- Work ID: `USDJPY-P4-RESIDUAL-LOSS-ELIMINATION-001`
- Candidate lineage: `USDJPY-HYP-044`
- Final decision: `PARTIAL_RESIDUAL_LOSS_REDUCTION_WITH_REMAINING_WEAK_REGIME`
- Selected portfolio: `B0_A2_EARLY_C3_PLUS_A4_SESSION_LOSS_CAP_2`
- Rule hash: `d8878f92e0641b10c4926966a03a46f238e4074335312003b7a6c058f8843f94`
- Production/live authorization: **NO**
- 2025H2 accessed: **false**

## Conclusion

The study is economically successful at the 2025H1 aggregate level but does not eliminate the weak regimes. The selected B0 portfolio changes the P4 2025H1 result from `-¥2,131 / PF 0.980760` to `+¥609 / PF 1.005668`, while increasing total 2020–2025H1 net from `+¥78,543` to `+¥85,405`.

This is not a full PASS. 2021 remains `-¥1,190`, 2022H2 remains `-¥21,022`, and 2025Q1 remains `-¥16,129`. The improvement is a localized loss-cluster reduction rather than complete residual-loss elimination.

## Selected architecture

- B02: early C3 giveback through completed M15 boundary 16
- F05: unchanged frozen C2 evaluated at the first executable Tick at or after 60 seconds
- Portfolio control: B02/F05 same-session consecutive realized-loss cap of 2
- Short Pullback: unchanged HYP-039, outside the parent loss cap
- Restart restoration and duplicate/occupancy state remain implemented

## Annual economic results

| Period | Net JPY | PF |
|---|---:|---:|
| 2020 | +17,886 | 1.168188 |
| 2021 | -1,190 | 0.987172 |
| 2022 | +6,003 | 1.031408 |
| 2023 | +11,926 | 1.064950 |
| 2024 | +50,171 | 1.299881 |
| 2025H1 | +609 | 1.005668 |

- 2020–2024 pooled net: `+¥84,796`
- 2020–2025H1 total net: `+¥85,405`
- 2020–2025H1 pooled PF: `1.100641`
- Positive years, 2020–2024: `4/5`
- Positive half-years: `8/11`
- Positive quarters: `12/22`
- Positive months: `41/66`
- Worst year: `2021 -¥1,190`
- Worst half-year: `2022H2 -¥21,022`
- Worst quarter: `2025Q1 -¥16,129`
- 2025Q2: `+¥16,738`
- Rolling 6-month minimum: `-¥27,731`
- Rolling 12-month minimum: `-¥32,000`

## Improvement versus frozen P4

| Metric | Improvement |
|---|---:|
| Total net through 2025H1 | +¥6,862 |
| 2020–2024 pooled net | +¥4,122 |
| 2021 | +¥3,089 |
| 2022H2 | +¥2,803 |
| 2025Q1 | +¥2,470 |
| 2025H1 | +¥2,740 |
| Positive half-years | +1 |
| Positive quarters | unchanged |
| Positive months | +3 |
| Rolling 6-month minimum | +¥2,588 |
| Rolling 12-month minimum | +¥2,880 |

## Strategy contribution, 2020–2025H1

- B02: `+¥22,653`
- F05: `+¥51,889`
- unchanged Short Pullback: `+¥10,863`
- Incremental portfolio improvement versus P4: `+¥6,862`
- Modified trades: `928`

F05 remains the principal 2025H1 weakness: B02 is `+¥4,648`, F05 is `-¥7,522`, and Short Pullback is `+¥3,483`. Long-side/F05 concentration and Q1 drawdown remain material.

## Round A and Round B

Round A used the maximum five finite candidates. Their 2025H1 results were A0 `-¥2,131`, A1 `-¥12,007`, A2 `-¥514`, A3 `-¥1,323`, and A4 `-¥293`. No Round A candidate was positive.

Round B added one family only. `B0_A2_EARLY_C3_PLUS_A4_SESSION_LOSS_CAP_2` produced `+¥609 / PF 1.005668` and was selected. No threshold rescue or post-result retuning was performed.

## Full-equity and margin

Across the separately certified period replays:

- Maximum realized DD: `¥38,144`
- Maximum full-equity DD: `¥39,650`
- Minimum equity: `¥73,309`
- Minimum free margin: `¥36,978.16`
- Minimum margin level: `177.6985%`
- Maximum concurrency: `10`
- Maximum same-direction concurrency: `10`
- Maximum opposite-direction concurrency: `3`
- Stopout breach: `false`

## Research/Core/MT4/Rakuten qualification

The candidate rule hash is identical across Research and Core. Rakuten MT4 completed Model=0 tests at spread 5 points with zero runtime errors and no duplicate orders. For 2025H1, expected and actual aggregate economics are exactly identical: 609 trades, `+¥609`, PF `1.005668`. B02 and F05 have full row parity. Short Pullback has one one-minute first-executable-Tick timestamp difference with identical close, exit reason, and P/L.

Rakuten 2023–2024 actual result is 2,386 trades, `+¥70,455`, PF `1.204625`. Full source row parity is not achieved because known source-population and price differences remain.

## Authority limitation

The latest binding 2023–2024 baseline is 1,893 total trades, including 1,464 F05 trades. The retained C2/HYP-044 ledger contains 1,451 historical F05 trades. The aggregate 1,893-trade anchor is retained, but the corresponding 1,464-row F05 source-native ledger is not present in the current repository or retained Release package. Therefore the 13 events cannot be reconstructed or classified without inventing data.

No silent synthetic mixing was performed. Exact latest-lineage Dukascopy 2023–2024 C2 certification remains open.

## Final judgment

The improved EA is materially better than P4, turns 2025H1 positive, remains profitable over the full 2020–2025H1 horizon, compiles, and executes in Rakuten MT4. It does not yet qualify as a stable residual-loss-eliminated configuration because 2021, 2022H2, and 2025Q1 remain negative and the 13-trade source-native lineage reconciliation is incomplete.

Exact next action: restore or regenerate the latest 1,464-trade Dukascopy F05 authority and mechanically apply the unchanged B0/C2 contract; concurrently complete Rakuten forward raw-Tick shadow qualification. Do not retune the candidate and do not authorize production until both receipts exist.
