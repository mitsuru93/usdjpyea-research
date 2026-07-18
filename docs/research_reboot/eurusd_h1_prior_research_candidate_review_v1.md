# EURUSD H1 prior-research candidate review v1

Created: 2026-07-18 JST  
Status: candidate universe registered; execution blocked until the EURUSD 2024 annual source artifact is accepted  
Registry: `configs/research/eurusd_h1_prior_literature_candidates_v1.json`

## 1. Purpose

This document defines the initial EURUSD H1 strategy-family universe before any 2024 EURUSD strategy result is inspected.

The objective is not to collect popular indicators. It is to select transparent, economically interpretable families that have one of the following evidence bases:

1. direct EURUSD intraday evidence;
2. broad foreign-exchange evidence, transferred cautiously to H1;
3. a microstructure or volatility mechanism documented in FX research and translated into a falsifiable H1 rule.

The EURUSD candidate universe and results must remain separate from USDJPY. USDJPY results, winning parameter values, and artifacts are not evidence for EURUSD.

## 2. Research boundary

No strategy run may start until the annual EURUSD 2024 source bundle passes the existing source-data gate:

- all twelve months present;
- `expected_records_mode=weekdays`;
- `unobserved_records=0`;
- `hard_error_records=0`;
- `effective_coverage=1.0`;
- M1, M5, M15, and H1 validation status accepted;
- annual artifact identified by exact artifact ID, digest, creation time, run ID, and run attempt.

The H1 study then uses:

- development: 2024-01-01 through 2024-06-30;
- validation: 2024-07-01 through 2024-12-31;
- completed H1 bars only;
- next-H1-open entry;
- no same-bar execution;
- no overlapping position for the same candidate;
- Rakuten MT4 EURUSD base spread 0.6 pips as the floor under `max_base_public`;
- the same spread and slippage stress method used in the USDJPY research;
- project-wide hard no-trade windows.

## 3. Main findings from prior research

### 3.1 Technical-rule profitability exists, but is unstable and easy to overstate

A long literature reports that moving-average, filter, channel, trading-range-break, Bollinger-band, and RSI rules can produce positive FX returns in some samples. The strongest modern large-universe studies also show that significance falls sharply after data-snooping adjustment and that profitability varies across periods.

Implication for this project:

- include these families;
- pre-register a narrow parameter universe;
- judge families, not the single best row;
- require out-of-sample validation and transaction-cost survival;
- do not interpret a temporary winner as a stable edge.

### 3.2 Intraday FX technical rules often fail after realistic costs

Research using intraday FX data has found stable patterns without reliable excess returns after realistic transaction costs and trading-hour restrictions.

Implication:

- H1 is not assumed superior to lower-frequency research;
- every result must be evaluated after bid/ask spread and slippage stress;
- trade count alone is not evidence;
- low-liquidity hours remain excluded.

### 3.3 EURUSD has documented time-of-day structure

High-frequency EURUSD research reports strong intraday seasonality in activity, volatility, spreads, returns, and order flow. Breedon and Ranaldo report that currencies tend to depreciate during their local trading hours and state that the EURUSD pattern can form a simple profitable strategy in their sample. Ito and Hashimoto document EURUSD intraday activity and volatility patterns and the concentration of activity during market overlaps.

Implication:

- include a fixed-direction local-session family;
- use DST-aware local time rather than fixed UTC labels;
- include session-range and session-half hypotheses separately;
- do not infer that all-hours aggregation is valid.

### 3.4 Momentum is well documented at longer horizons, but H1 transfer is unproven

Time-series momentum has been documented across currency futures and other liquid futures, especially over one- to twelve-month formation horizons. Cross-sectional currency momentum is also documented, but it requires multiple currencies and is not a single-pair EURUSD strategy.

Implication:

- include simple return-sign and moving-average trend families on H1;
- label them as horizon-transfer hypotheses rather than direct replications;
- exclude cross-sectional currency momentum from the single-pair core screen.

### 3.5 FX volatility is periodic and persistent

FX volatility research documents pronounced intraday periodicity, macro-announcement effects, and volatility persistence. Activity, spreads, and volatility vary materially by time of day.

Implication:

- include volatility-compression breakout as a mechanism-derived family;
- keep volatility regime filters as stage-two overlays unless the filter is essential to define a mean-reversion family;
- use local-session and same-session normalization where possible;
- avoid treating raw H1 volatility as identically distributed across the day.

## 4. Registered H1 family universe

### A. Intraday local-currency direction

Evidence class: direct EURUSD intraday.

Hypothesis:

- EURUSD tends to fall during the European local trading window because the euro tends to depreciate during its local trading hours;
- EURUSD tends to rise during the U.S. local trading window because the dollar tends to depreciate during its local trading hours.

Registered variants:

- Europe/Berlin 08:00 local short, hold 4 H1 bars;
- Europe/Berlin 08:00 local short, hold 8 H1 bars;
- America/New_York 09:00 local long, hold 4 H1 bars;
- America/New_York 09:00 local long, hold 8 H1 bars.

This is the only core family with an asymmetric direction fixed by prior research.

Primary failure mode:

- a historical time-of-day effect may have weakened as execution, participation, and market structure changed.

### B. Return-sign time-series momentum

Evidence class: FX and multi-asset momentum transferred to H1.

Signal:

- long when the cumulative H1 close-to-close return over the lookback is positive;
- short when it is negative;
- enter at the next H1 open.

Registered lookbacks:

- 24 H1 bars;
- 72 H1 bars;
- 120 H1 bars.

Registered holds:

- 12 H1 bars;
- 24 H1 bars.

Primary failure mode:

- the academic effect is strongest at much longer horizons, so H1 may be dominated by noise and spread.

### C. Moving-average trend

Evidence class: direct FX technical-rule evidence transferred to H1.

Signal:

- long when the fast SMA is above the slow SMA;
- short when the fast SMA is below the slow SMA;
- enter only from completed H1 information.

Registered pairs:

- 12 / 48;
- 24 / 96;
- 48 / 192.

Registered holds:

- 12 H1 bars;
- 24 H1 bars.

Primary failure mode:

- repeated whipsaw in range regimes and cost accumulation.

### D. Trading-range or channel breakout

Evidence class: direct FX technical-rule evidence transferred to H1.

Signal:

- long after a completed H1 close above the previous rolling high;
- short after a completed H1 close below the previous rolling low.

Registered lookbacks:

- 24 H1 bars;
- 48 H1 bars;
- 120 H1 bars.

Registered holds:

- 12 H1 bars;
- 24 H1 bars.

Primary failure mode:

- false breaks around session transitions or macro announcements.

### E. Asia-range London breakout

Evidence class: FX intraday seasonality and microstructure derived.

Signal:

- construct the 00:00-06:00 UTC range;
- trade the first completed H1 close outside that range from 07:00 through 12:00 UTC;
- enter next H1 open in the break direction.

Registered holds:

- 6 H1 bars;
- 12 H1 bars.

This exact rule is not claimed as an academic replication. It is a falsifiable translation of documented session-dependent activity and price discovery.

Primary failure mode:

- the range can be broken by transient liquidity or scheduled-news shocks rather than persistent information.

### F. Bollinger or z-score mean reversion

Evidence class: direct FX technical-indicator evidence transferred to H1.

Signal:

- fade a close that is far from its rolling mean;
- require a low-trend regime using the 24-bar Kaufman efficiency ratio at or below 0.35;
- enter next H1 open.

Registered mean windows:

- 24 H1 bars;
- 72 H1 bars.

Registered absolute z thresholds:

- 1.5;
- 2.0.

Registered holds:

- 6 H1 bars;
- 12 H1 bars.

Primary failure mode:

- persistent directional repricing can make an apparent extreme continue rather than revert.

### G. RSI-extreme mean reversion

Evidence class: direct FX technical-indicator evidence transferred to H1.

Signal:

- RSI(14) below the lower threshold: long;
- RSI(14) above the upper threshold: short;
- require the same low-trend regime as family F.

Registered threshold pairs:

- 30 / 70;
- 25 / 75.

Registered holds:

- 6 H1 bars;
- 12 H1 bars.

Primary failure mode:

- RSI can remain extreme throughout a genuine trend, so an unfiltered rule can repeatedly fade information.

### H. Failed-breakout reversal

Evidence class: channel-rule and liquidity-reversal derived.

Signal:

- the H1 bar trades beyond the prior 24- or 48-bar range;
- the same bar closes back inside the prior range;
- the excursion must be at least 0.10 ATR(24);
- trade against the failed break at the next H1 open.

Registered holds:

- 6 H1 bars;
- 12 H1 bars.

Primary failure mode:

- a temporary reclaim may precede a second, successful break.

### I. Volatility-compression breakout

Evidence class: FX volatility persistence and band-rule derived.

Signal:

- identify a 6- or 12-hour range whose width is in the bottom 25% or 35% of the trailing 20 comparable sessions;
- trade the first completed H1 close outside the compressed range;
- enter next H1 open.

Registered hold:

- 12 H1 bars.

Primary failure mode:

- low volatility can persist without expansion, while the first apparent break can be a head fake.

### J. Session-half momentum

Evidence class: intraday momentum transferred from related FX evidence.

Signal variants:

- use the direction of Europe/Berlin 08:00-10:00 local return and enter at 11:00 local for 3 H1 bars;
- use the direction of America/New_York 09:00-11:00 local return and enter at 12:00 local for 3 H1 bars.

Primary failure mode:

- the available direct intraday-momentum evidence is not specific enough to EURUSD to justify a high prior probability.

This family is retained as a lower-priority falsification candidate, not as a lead hypothesis.

## 5. Families deliberately excluded from the core H1 screen

### Cross-sectional currency momentum

Excluded because the strategy requires ranking multiple currencies. Evidence for a currency portfolio cannot be treated as evidence for one EURUSD time series.

### Standalone carry

Excluded from the bar-only H1 screen because it requires synchronized rate or forward-point data and changes too slowly to define a broad H1 trade universe. Carry may later be used as a regime variable.

### Macro-surprise trading

Excluded because proper testing requires point-in-time consensus expectations, release timestamps, revisions, and surprise values. A current economic calendar reconstructed after the fact is not adequate.

### Order flow and true VWAP

Excluded because the Dukascopy quote-tick source does not provide centralized signed market-wide order flow or centralized FX volume. Tick count is not a valid substitute for those variables.

### Genetic programming, unconstrained machine learning, and unbounded indicator search

Excluded from the first screen because they create large model-search degrees of freedom and make failure attribution difficult. They may be considered only after transparent baseline families are exhausted and a nested validation design exists.

### Named candlestick patterns

Excluded because no FX-specific evidence strong enough to rank them ahead of the registered families was identified.

## 6. Retention policy

No family is retained because its best individual parameter row ranks first.

A family must satisfy all of the following under default cost unless explicitly stated otherwise:

- positive average net pips in development;
- positive average net pips in validation;
- aggregate profit factor at least 1.10;
- validation profit factor at least 1.05;
- at least 8 positive months of 12;
- at least 3 positive months in each half;
- at least 60 aggregate trades;
- at least 20 trades in each half;
- positive total net pips after removing the best two days;
- severe-stress profit factor at least 0.90;
- at least two neighboring parameter variants positive in validation.

The neighboring-variant rule does not allow unlimited interpolation. Only variants already listed in the registry count.

## 7. Stage-two research only after family retention

The following overlays are intentionally deferred:

- realized-volatility regime filters for trend families;
- spread-percentile filters;
- day-of-week diagnostics;
- scheduled macro-event exclusions;
- exit-policy comparison;
- position sizing;
- portfolio interaction with USDJPY.

This separation prevents a weak entry family from being rescued by repeated filtering and exit optimization.

## 8. Evidence hierarchy

### Higher-priority sources

1. Breedon, Francis, and Angelo Ranaldo. “Intraday Patterns in FX Returns and Order Flow.” *Journal of Money, Credit and Banking* 45(5), 2013, 953-965. DOI: `10.1111/jmcb.12032`.
2. Ito, Takatoshi, and Yuko Hashimoto. “Intra-Day Seasonality in Activities of the Foreign Exchange Markets: Evidence from the Electronic Broking System.” *Journal of the Japanese and International Economies* 20(4), 2006, 637-664. NBER Working Paper 12413. DOI: `10.3386/w12413`.
3. Coakley, Jerry, Michele Marzano, and John Nankervis. “How Profitable Are FX Technical Trading Rules?” *International Review of Financial Analysis* 45, 2016, 273-282. DOI: `10.1016/j.irfa.2016.03.010`.
4. Hsu, Po-Hsuan, Mark P. Taylor, and Zigan Wang. “Technical Trading: Is It Still Beating the Foreign Exchange Market?” *Journal of International Economics* 102, 2016, 188-208. DOI: `10.1016/j.jinteco.2016.03.012`.
5. Zarrabi, Nima, Stuart Snaith, and Jerry Coakley. “FX Technical Trading Rules Can Be Profitable Sometimes!” *International Review of Financial Analysis* 49, 2017, 113-127. DOI: `10.1016/j.irfa.2016.12.010`.
6. Moskowitz, Tobias J., Yao Hua Ooi, and Lasse Heje Pedersen. “Time Series Momentum.” *Journal of Financial Economics* 104(2), 2012, 228-250. DOI: `10.1016/j.jfineco.2011.11.003`.
7. Andersen, Torben G., and Tim Bollerslev. “Intraday Periodicity and Volatility Persistence in Financial Markets.” *Journal of Empirical Finance* 4, 1997, 115-158. DOI: `10.1016/S0927-5398(97)00004-2`.
8. Andersen, Torben G., and Tim Bollerslev. “Deutsche Mark-Dollar Volatility: Intraday Activity Patterns, Macroeconomic Announcements, and Longer Run Dependencies.” *Journal of Finance* 53(1), 1998, 219-265. DOI: `10.1111/0022-1082.85732`.

### Important negative and methodological evidence

9. Neely, Christopher J., and Paul A. Weller. “Intraday Technical Trading in the Foreign Exchange Market.” *Journal of International Money and Finance* 22, 2003. DOI: `10.1016/S0261-5606(02)00101-8`.
10. Sullivan, Ryan, Allan Timmermann, and Halbert White. “Data-Snooping, Technical Trading Rule Performance, and the Bootstrap.” *Journal of Finance* 54(5), 1999. DOI: `10.1111/0022-1082.00163`.
11. Menkhoff, Lukas, Lucio Sarno, Maik Schmeling, and Andreas Schrimpf. “Currency Momentum Strategies.” BIS Working Papers No. 366, 2011; later *Journal of Financial Economics* 106(3), 2012.

## 9. Decision

The initial EURUSD H1 screen consists of ten families, A through J.

The lead evidence groups are:

1. direct EURUSD local-time direction;
2. moving-average and channel trend rules;
3. Bollinger/RSI mean reversion;
4. session range and volatility-compression breakout.

Return-sign momentum and session-half momentum are retained with lower prior confidence because the strongest evidence comes from different horizons or markets.

No strategy result is yet accepted, and no family has priority based on the 2024 EURUSD data because those results have not been inspected.
