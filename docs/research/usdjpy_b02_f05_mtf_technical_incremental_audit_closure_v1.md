# USDJPY B02/F05 Multi-Timeframe Technical Incremental Audit — HYP-026 Closure

## Conclusion

HYP-025のprice-only 20候補だけでは、元のEntry／Exit technical factor課題に対して十分ではなかった。

そこで、B02／F05の1,882 tradeについて、M1・M5・M15・M30・H1のcompleted-barから42 technical featuresを各timeframeで作成し、2023H1・2023H2・2024H1・2024H2の4foldで次を比較した。

- price-path only
- technical only
- price-path + technical（timeframe別）
- price-path + all timeframes

最終判断：

> オシレーターおよびテクニカル状態は、一部の失敗tradeを記述する情報を持つ。しかし、price-path情報とWinner opportunity costを含めると、経済的に有効かつ4fold portableなEntry／Exit ruleにはならない。

Status: `CLOSED_NO_ECONOMICALLY_VALID_INCREMENTAL_TECHNICAL_RULE`

Binding candidate: none. Portfolio replay、MT4、2025H1、2025H2には進まない。

## Scope and sources

- Baseline trades: 1,882
- Feature rows: 8,129
- Strategies: B02 / F05
- Folds: 2023H1 / 2023H2 / 2024H1 / 2024H2
- Timeframes: M1 / M5 / M15 / M30 / H1
- Completed bars only
- Technical features per timeframe: 42

Source identities:

- 2023 M1 Bid OHLC: 371,128 rows; SHA-256 `167509bde6553a468ffe48b082ed79de183cc57991f668cf4b3e7341350d307e`
- 2024 Release-derived M1 Bid/Ask/Mid OHLC: 373,383 rows; SHA-256 `f9f56be2daa39f07dc39cec197306fb87821ead01e4a640a73f17715bf27dde0`
- common-M1 trade ledger: 1,882 rows; SHA-256 `c8b3cef29945367adc2f5ec88e16f45c0a909af9e51b3fe5b106b5643fab7ded`

2024 sourceは変更していない。2025およびMT4はアクセスしていない。

## Technical features

Oscillator:

- RSI 7 / 14 / 28
- RSI14 three-bar change
- MACD 12/26/9 line / histogram / histogram change
- Stochastic 14/3/3
- CCI 20

Trend:

- price-to-EMA20 / 50 / 100 / 200 distance
- EMA20 and EMA50 slopes
- EMA20–EMA50 and EMA50–EMA200 alignment
- ADX 14
- directional DI alignment

Bollinger:

- z-score 20 / 50
- width 20 / 50

Momentum / volatility:

- momentum 4 / 8 / 16 / 32 bars
- realized volatility 8 / 16 / 32 bars
- mean absolute movement
- path efficiency
- ATR 14 / ATR-to-price / true-range expansion

Bar geometry:

- directional body/range
- directional wick ratios
- directional close location

すべてtrade方向へ符号を正規化した。

## Observation contract

- P3 F05: Entry後5分
- P3 B02: Entry後10分
- P2: first positive executable mark後15分・30分。＋10pipsへ先に到達したtradeはP2 armから除外
- P1: first +10pip executable mark後15分・30分・60分

各時点で完成済みのbarだけを使用し、partial barやfuture barは使用していない。

## Statistical contract

固定L2 logistic regression:

- C = 0.1
- solver = liblinear
- class_weight = balanced
- training-fold median imputation and standardization
- leave-one-fold-out
- parameter tuningなし
- threshold gridなし

Primary gate:

- mean AUC gain over price-only >= 0.03
- minimum fold AUC gain >= 0.01
- 4foldすべてpositive gain
- 4fold共通univariate support

Primary pass後の頑健性診断では、price baselineへ同一timeframeのbody・wick・close-location geometryを追加し、technicalの純粋な増分を再計算した。さらに2,000回のstratified bootstrapと、probability threshold 0.5固定のnext-M1-open Exit counterfactualを実施した。

この頑健性診断はprimary passを棄却するためだけに使用し、新しい候補・threshold・timeframeを作るためには使用していない。

## Results

### P3 — B02

common-M1 P3件数はfold別に3 / 1 / 1 / 0件。2024H2にP3が0件であるため、4fold technical ruleとして評価不能。

Decision: `UNTESTABLE_AS_FOUR_FOLD_TECHNICAL_RULE`

### P3 — F05, Entry後5分のM5

P3は4fold合計22件。

Basic price baselineに対するM5 technical追加:

- mean AUC gain: +0.1225
- minimum fold gain: +0.0462
- 4foldすべてpositive

同じM5のbody・wick・close-locationをprice側へ追加すると、technicalの純増分は縮小した。

- robust mean AUC gain: +0.0295
- fold gains: +0.0117 / +0.0799 / +0.0179 / +0.0085
- bootstrap 95% CI: +0.0011 ～ +0.0699
- P(gain <= 0): 0.017

したがって、M5 oscillator／technicalにはprice geometryを超える小さな情報が残る。

しかし、threshold 0.5固定で次のM1 openに退出したcounterfactualでは:

- P3 loss saved: +660.9 pips
- P2 loss saved: +1,883.9 pips
- P1 loss saved: +1,161.9 pips
- Winner profit lost: -3,978.1 pips
- total delta: -271.4 pips
- spread stress: -317.7 pips

fold別total delta:

- 2023H1: +301.3
- 2023H2: -269.7
- 2024H1: -231.9
- 2024H2: -71.1

P3は86.4%検出したが、Winnerも10.9%退出させ、Winner側の機会損失が損失削減を上回った。

Decision: `ROBUST_DESCRIPTIVE_INFORMATION_BUT_REJECT_ECONOMICALLY`

### P2 — B02, first positive後15分のM15

P2 failure 52件、＋10未到達Winner comparator 163件。

Basic price baselineに対するM15 technical追加:

- mean AUC gain: +0.0792
- minimum fold gain: +0.0425
- 4foldすべてpositive

Enriched price geometry baselineに対する純増分:

- robust mean AUC gain: +0.0428
- fold gains: +0.0316 / +0.0447 / +0.0912 / +0.0039
- bootstrap 95% CI: -0.0591 ～ +0.1416
- P(gain <= 0): 0.2005

固定threshold counterfactual:

- P2 loss saved: +1,361.1 pips
- Winner profit lost: -3,313.5 pips
- total delta: -1,952.4 pips
- spread stress: -1,978.2 pips

fold別total delta: -234.0 / -466.4 / -420.6 / -831.4 pips。全foldで経済効果がマイナス。

Decision: `REJECT_UNCERTAIN_AND_ECONOMICALLY_NEGATIVE`

### P2 — F05

F05ではprice-path baseline自体が強く、M1・M5・M15・M30・H1のtechnicalを追加した全モデルでmean AUC gainがマイナス。

Decision: `NO_PORTABLE_INCREMENTAL_TECHNICAL_INFORMATION`

### P1 — B02 / F05

＋10pips到達後、RSI、momentum、EMA distance、Bollinger position、MACD等が悪化する記述的傾向は再確認した。しかし、price pathを既知とした後の増分はportableではない。

- B02最良: +15分 M15 mean gain +0.0071; minimum fold -0.0927
- F05最良: +15分 M15 mean gain -0.0047

どのtimeframe、どの観測時点でも4fold incremental gateを通過しなかった。

Decision: `DESCRIPTIVE_DECAY_NOT_INCREMENTAL`

## Why no portfolio replay

2つのprimary-pass cellについて、portfolio replayより前の固定ledger counterfactualが総損益を悪化させた。

- F05 P3 M5: -271.4 pips
- B02 P2 M15: -1,952.4 pips

B02 P2は4foldすべてマイナス。F05 P3も4fold中3foldマイナス。この状態でportfolio replay、MT4またはthreshold調整へ進むことはnegative result後のrepairになるため実施しない。

## Retained findings

1. F05 P3: Entry後最初のM5のRSI・momentum・bar stateには単純price-pathを超える情報が少量あるが、Winner false positiveが大きく、Exit ruleにはならない。
2. B02 P2: first positive後15分のM15 technical stateに局所情報はある可能性があるが、不確実性と全foldの負の経済効果から不採用。
3. F05 P2: oscillatorよりM1/M5 price participation・expansionが主要情報で、technicalは独立情報を追加しない。
4. P1: oscillator deteriorationは価格状態崩壊の別表現であり、独立したExit alphaではない。

## Process disclosure

Outcome-free preregistration was committed before outcomes on branch commit `7e50b58ef1ea9d178d389959b114d75e10100f01`, but it was not merged to main before local execution. Therefore this negative closure is recorded as an independently reproducible audit and cannot authorize a binding candidate.

## Closure boundary

- Binding candidate: none
- Signal generation: unauthorized
- Portfolio replay: not authorized
- MT4: not accessed / not authorized
- 2025H1: not accessed / not authorized
- 2025H2: not accessed / not authorized
- Indicator threshold repair: prohibited
- HYP-023 / HYP-024: not reused
- HYP-025 cells: not repaired, chained or retuned
