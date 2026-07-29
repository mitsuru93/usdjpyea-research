# USDJPY-HYP-037 Protocol-Corrected Research Candidate Result v2

## Decision

`FAIL_2023_2024_RESEARCH_CANDIDATE_GATE_NO_RETUNING`

First binding stop: `CONCENTRATION / top_decile_removed_positive`.

Candidate freeze, Core, MT4, 2025H1, 2025H2, production and live authorization are all false.

## Protocol correction

HYP-037 v1 is retained unchanged as the historical record of `TECHNICAL_NO_RESULT_HISTORICAL_SOURCE_AUTHORITY_UNRESOLVED`. Its scientific outcome was not rewritten or hidden.

Before any 2020–2022 candidate outcome or 2025 outcome was accessed, the period roles were restored to the repository-wide firewall:

- 2020–2022: nonbinding analysis period.
- 2023–2024: Research and candidate-construction period.
- 2025: sole binding unseen external-validation period.

No new Hypothesis ID was created. `C1_SHORT_DUKASCOPY_NATIVE_16BAR` was unchanged. HYP-036 remained closed as `NO_PORTABLE_EXECUTABLE_CANDIDATE`.

## Candidate contract

Short only; Dukascopy BI5 Bid/Ask Tick; source-native M15; EMA20/EMA96; ATR20; prior `ts<=-1`; 0.25 ATR pullback tolerance; next observed boundary Bid Entry; Ask Exit after 16 observed M15 bars; HYP-036 active suppression; 0.01 lot; JPY; no SL or TP.

## 2023–2024 standalone

- Trades: 500
- Net: +¥17,679
- PF: 1.2727693518
- Win rate: 49.0%
- Positive folds: 4/4
- Positive months: 13/24
- Realized MDD: ¥6,312
- Minimum realized equity from ¥1,000,000: ¥999,914
- Mean MAE: -28.0916 pips
- Mean MFE: +33.7626 pips

Fold net:

- 2023H1: +¥4,862 / 125 trades
- 2023H2: +¥4,694 / 135 trades
- 2024H1: +¥1,272 / 97 trades
- 2024H2: +¥6,851 / 143 trades

Session net:

- Tokyo: +¥7,504
- London: +¥1,918
- London/NY overlap: +¥6,170
- New York: +¥187
- Transition: +¥1,900

## Concentration

- Best event removed: +¥15,057
- Top 3 removed: +¥11,146
- Top 5 removed: +¥8,009
- Top winner decile: 25 winners
- Top winner decile removed: **-¥11,216 — binding FAIL**
- Largest positive fold share: 38.7522%
- Largest positive month share: 23.3443%
- Largest positive session share: 42.4458%

The pooled edge survives a few isolated-event removals, but does not survive removal of the strongest 10% of winning events. The edge is therefore materially dependent on its right tail.

## Bootstrap

10,000 replicates, seed 37037:

- Event bootstrap lower 95%: -¥1,221.875; P(non-positive)=3.20%
- Date bootstrap lower 95%: -¥1,349.025; P(non-positive)=3.44%
- Session-block bootstrap lower 95%: -¥1,281.05; P(non-positive)=3.45%

P(non-positive) passed the 5% threshold, but all lower 95% bounds remained below zero. These are additional failures after the first concentration stop.

## Execution robustness

- Observed Bid/Ask: +¥17,679
- Spread +0.5 pip: +¥15,179
- Spread +1.0 pip: +¥12,679
- Spread +2.0 pips: +¥7,679
- Entry delay +5 seconds: +¥17,980
- Entry delay +15 seconds: +¥17,612
- Adverse slippage 0.5 pip per execution: +¥12,679

Execution robustness passed. The failure is not explained by ordinary spread or short execution delay.

## B02/F05 portfolio diagnostics

- Baseline net: +¥51,627
- Combined net: +¥69,306
- Baseline realized DD: ¥40,487
- Combined realized DD: ¥35,420
- Baseline full-equity DD: ¥42,660
- Combined full-equity DD: ¥36,511
- Baseline minimum full equity: ¥959,118
- Combined minimum full equity: ¥965,267
- Baseline worst 5-business-day: -¥11,585
- Combined worst 5-business-day: **-¥12,053 — FAIL**
- Baseline worst 20-business-day: -¥16,588
- Combined worst 20-business-day: -¥15,675
- Baseline worst month: -¥12,395
- Combined worst month: -¥12,096
- Correlation to B02: +0.211015
- Correlation to F05: +0.345754
- Candidate contribution on negative baseline days: -¥13,331
- Candidate peak concurrency: 1
- Combined peak concurrency: 10 against baseline 9
- Maximum incremental margin: ¥6,453.96
- Minimum margin level: 1,737.84%
- Chronology mismatch: 0
- Currency mismatch: 0
- B02/F05 trade outcomes changed: false

The candidate improves net, realized DD, full-equity DD, minimum equity, 20-day loss and worst month, but worsens the worst 5-business-day cluster. This confirms that the earlier diagnostic loss-cluster concern remains relevant even after restricting the family to Short.

## Final interpretation

The Short directional asymmetry is real within the 2023–2024 Research period and is resilient to ordinary execution stress. It also improves several portfolio drawdown measures. However, the edge is not sufficiently diffuse: removing the strongest winner decile turns net negative, all bootstrap lower bounds remain below zero, and the worst 5-day portfolio cluster worsens.

Under the fixed no-retuning protocol, HYP-037 closes at the Research candidate gate. The candidate is not frozen and 2025 remains unopened.

## Evidence

- Research start SHA: `1841ed3fba757a9a44496faeb9a6c7e014efa9d6`
- Research execution SHA: `498296a4e147a5fa958fb45f467342d7039a75f8`
- Core start/end SHA: `f897b250b808207d960417b2306935dcb0655acf`
- Run: `30428356407`
- Artifact: `8714601229`
- Artifact digest: `sha256:046f56e519fd8e047dd54c98962c7e7ad24bcbc9d159445cb9a3fb227fa8a2d4`
- Deterministic archive SHA256: `2353f2f3b08f3b686a6244ce661ab043d7b488a41ca9f1d5e0f1cebaba6c44fd`
- Archive readback: PASS
