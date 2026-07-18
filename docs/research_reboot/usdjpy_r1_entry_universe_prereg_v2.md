# USDJPY R1 Entry Universe Preregistration v2

## Decision

R1 freezes exactly sixty unique M15 Entry definitions before any expanded H1 outcome is calculated.

```text
families: 12
unique Entry definitions: 60
legacy unique Entries carried forward: 12
new Entries: 48
R1 outcome metrics: prohibited
R2 fixed horizons: 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
H2 access for new candidates: prohibited
2025 access: prohibited
Core promotion: false
MT4 promotion: false
```

The authoritative registry is:

```text
configs/research/usdjpy_r1_entry_universe_v1.json
```

## Why the universe is broad

The literature does not support one universally dominant FX Entry rule. It supports recurring mechanism classes whose profitability varies by market, era, volatility regime, transaction cost and sampling frequency. R1 therefore tests a bounded set of transparent representatives rather than one preferred narrative.

The registered mechanisms are:

1. impulse breakout with range expansion;
2. session and prior-range breakout;
3. failed breakout / excursion reversion;
4. range compression followed by expansion;
5. trend pullback and resumption;
6. Donchian / trading-range channel breakout;
7. exponential moving-average trend cross;
8. volatility-adjusted time-series momentum;
9. statistical-band re-entry mean reversion;
10. large-return shock reversal;
11. major-session handoff continuation or reversal;
12. ATR-normalized directional-change filter rules.

These families cover the principal price-only hypotheses available from the accepted canonical M15 bid/ask bars: trend persistence, delayed price discovery, breakout, volatility clustering, contraction/expansion, overextension and reversal, session periodicity and classic filter-rule state changes.

## Evidence standard

The family selection is based on peer-reviewed research, central-bank research and long-sample studies. The evidence establishes that these mechanism classes merit testing; it does not establish that any specific R1 definition will be profitable in 2024 USDJPY M15 data.

Principal references:

- Moskowitz, Ooi and Pedersen, “Time Series Momentum,” *Journal of Financial Economics* 104 (2012), DOI `10.1016/j.jfineco.2011.11.003`.
- Burnside, Eichenbaum and Rebelo, “Carry Trade and Momentum in Currency Markets,” *Annual Review of Financial Economics* 3 (2011), DOI `10.1146/annurev-financial-102710-144913`.
- Hsu, Taylor and Wang, “Technical trading: Is it still beating the foreign exchange market?”, *Journal of International Economics* 102 (2016), DOI `10.1016/j.jinteco.2016.03.012`.
- Coakley, Marzano and Nankervis, “How profitable are FX technical trading rules?”, *International Review of Financial Analysis* 45 (2016), DOI `10.1016/j.irfa.2016.03.010`.
- Schulmeister, “Aggregate trading behaviour of technical models and the yen/dollar exchange rate 1976–2007,” *Japan and the World Economy* 21 (2009), DOI `10.1016/j.japwor.2008.08.005`.
- Baillie and Bollerslev, “Intra-Day and Inter-Market Volatility in Foreign Exchange Rates,” *Review of Economic Studies* 58 (1991), DOI `10.2307/2298012`.
- Brooks and Hinich, “Detecting Intraday Periodicities with Application to High Frequency Exchange Rates,” *JRSS Series C* 55 (2006), DOI `10.1111/j.1467-9876.2006.00534.x`.
- Chaboud, Chernenko and Wright, “Trading Activity and Exchange Rates in High-Frequency EBS Data,” Federal Reserve IFDP 903 (2007).
- Ito and Roley, “Intraday Yen/Dollar Exchange Rate Movements: News or Noise?”, NBER Working Paper 2703 and *Journal of International Financial Markets, Institutions and Money* 1 (1991).
- Dudler, Gmuer and Malamud, “Risk Adjusted Time Series Momentum,” Swiss Finance Institute Research Paper 14-71 (2014).

## Fixed family caps

| Family | Cap |
|---|---:|
| impulse_breakout | 5 |
| session_range_breakout | 5 |
| failed_excursion_reversion | 6 |
| compression_expansion | 5 |
| trend_pullback_resumption | 5 |
| donchian_channel_breakout | 5 |
| ema_trend_cross | 5 |
| volatility_adjusted_momentum | 5 |
| bollinger_reentry_reversion | 5 |
| return_shock_reversal | 5 |
| session_handoff | 4 |
| atr_filter_directional_change | 5 |
| **Total** | **60** |

No family may add a candidate after R1 output is opened. No family may exceed its cap.

## Legacy definitions

The prior thirteen-strategy screen contained twelve unique Entry definitions because `C1_failed_12bar_hold3` and `C2_failed_12bar_hold6` share the same Entry. R1 carries those twelve unique Entries as fixed reference definitions and adds forty-eight new definitions.

A1 plus hold6 and E3 plus hold6 have known failed H2 outcomes. Their Entry definitions remain in R1 only as historical references. They cannot enter a future candidate-specific unused H2 shortlist as if their H2 information were unopened.

## R1 firewall

R1 is an Entry-registry audit, not a performance screen.

Permitted outputs:

- normalized definition hashes;
- signal timestamps;
- actual next-bar entry timestamps;
- direction;
- total, monthly and hourly signal counts;
- pairwise signal overlap;
- signal-equivalent definition groups.

Prohibited outputs:

- entry price;
- any Exit or holding period;
- gross or net pips;
- transaction cost;
- expectancy;
- profit factor;
- winner/loser labels;
- promotion decisions.

This separation prevents the Entry universe from being selected for an arbitrary six-bar Exit before the R2 horizon surface is opened.

## Common execution rule

Every signal uses completed bars only. The theoretical order is entered at the next available M15 bar open. The project-wide New York local 16:00–19:00 hard no-trade window is applied to the actual next-bar entry timestamp with IANA time-zone conversion.

R1 reads the accepted canonical M15 file only until:

```text
2024-07-01T00:00:00Z exclusive
```

No H2 row is parsed. No 2025 source is accessed.

## R1 acceptance

R1 passes only if all of the following hold:

1. accepted canonical M15 gzip digest matches the R0 receipt;
2. H2 rows parsed equals zero;
3. 2025 access equals false;
4. twelve families are present;
5. sixty candidates are present;
6. all family caps are exact;
7. candidate IDs are unique;
8. normalized functional definitions are unique;
9. no candidate contains an Exit or horizon parameter;
10. every family has an implemented deterministic signal function;
11. all sixty candidates appear in the summary;
12. the six-month candidate grid is complete;
13. the twenty-four-hour candidate grid is complete;
14. all 1,770 candidate pairs appear in the overlap table;
15. every retained order uses a later next-bar timestamp;
16. hard no-trade violations equal zero;
17. no entry timestamp reaches H2;
18. outcome columns are absent;
19. the signal ledger gzip is deterministic;
20. the run metadata states that outcomes were not opened.

## Next stage

A passing R1 freezes the Entry universe and unblocks R2. R2 will calculate the eleven fixed horizons on 2024 H1 only. No Entry definition may be added or altered after R1 output is opened.
