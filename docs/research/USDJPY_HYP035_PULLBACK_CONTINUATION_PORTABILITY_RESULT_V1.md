# USDJPY-HYP-035 Pullback Continuation Portability — Final Result

## Decision

`FAIL_ATLAS_IDENTITY`

`J_PULLBACK_CONTINUATION` was closed at the first binding failure. The frozen Atlas mechanism could not be reproduced at the required event-identity level after translation to the binding source-native Dukascopy Bid/Ask Tick authority.

No candidate was frozen. 2020–2022, Core/MT4, 2025H1 and 2025H2 were not accessed. Production and live authorization remain false.

## Identity

- Hypothesis: `USDJPY-HYP-035`
- Family: `S_PULLBACK_CONTINUATION_PORTABILITY`
- Candidate: `A_EXACT_EXECUTABLE_16BAR`
- Research start SHA: `b7711c554b3ab21331537911cfb5a7d423d19cc3`
- Scientific execution SHA: `fbba359f62a5b3a3cde8c4bc2d3c7d4032398f5d`
- Core start/end-at-run SHA: `f897b250b808207d960417b2306935dcb0655acf`
- PR: #394
- Scientific Run: `30411335631`
- Artifact: `8708610330`
- Artifact digest: `sha256:1dc1018a6b9c10743b367bf698bcaa97bd4b27a4838eb5eeadbf8d2f011a3c5d`
- Effective evaluator SHA-256: `63fad89036e20269c47a1ed5e7c98e0abc2fddf5408a5b01f3dc1e9702a0c273`
- Release tag after merge: `usdjpy-hyp035-pullback-continuation-development-v1`

## Frozen Atlas contract

The Atlas contract was reproduced exactly before source-native evaluation:

- M15 Bid OHLC, UTC
- EMA20 and EMA96 using `ewm(span=N, adjust=False)`
- ATR20 rolling true range
- trend strength `(EMA20 - EMA96) / (ATR20 × 0.01)`
- prior-bar threshold `>= +1` for Long and `<= -1` for Short
- EMA20 pullback tolerance `0.25 × ATR20`
- completed-bar directional confirmation
- entry at the next observed M15 boundary in Atlas
- exit after 16 observed M15 bars
- same-variant active suppression
- no side/session/month/year exclusion
- no SL, TP, feature addition, threshold change or hold-time change

Atlas reproduction was exact: 1,333 opportunities, net ¥20,752, PF 1.135853, positive folds 4/4 and worst fold approximately +¥151. Atlas positive months were 15/24.

## Source authority

The binding Development source comprised 24 immutable 2023–2024 Dukascopy BI5 monthly archives:

- 84,428,370 Tick rows
- 49,894 reconstructed M15 bars
- Ask < Bid: 0
- duplicate timestamps: 0
- non-monotonic timestamps: 0
- duplicate M15 bars: 0
- unresolved chronology: 0

An initial workflow implementation mistakenly imposed an undocumented `M15 bars > 60,000` sanity check. Two years of observed 24×5 USDJPY trading correctly produced approximately 49,900 M15 bars. The check was technically repaired to the verified inclusive range 49,000–50,100. The repair changed no candidate, Atlas rule, execution semantics, scientific gate, period or outcome.

## Binding event-identity result

| Metric | Result | Gate |
|---|---:|---:|
| Atlas opportunities | 1,333 | — |
| Raw-native opportunities | 1,332 | — |
| Common signal/side events | 1,183 | — |
| Common exact events | 1,179 | — |
| Atlas-only events | 150 | — |
| Raw-native-only events | 149 | — |
| Side mismatches | 0 | — |
| Entry/exit boundary mismatches | 4 | — |
| Bid-open P/L mismatches | 444 | report |
| Signal/side match rate | 88.7472% | report |
| Exact event identity match rate | **88.4471%** | **>=95%** |
| Material contradiction rate | **20.1754%** | **<=5%** |

Both binding identity gates failed. No unfavorable mismatch was excluded.

## Mismatch attribution

All 299 signal-set mismatches were in 2023.

### 2023

The Atlas used Rakuten MT4 M15 Bid OHLC (`sha256:4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78`), whereas this study's binding source was M15 reconstructed from Dukascopy BI5 Bid/Ask Tick.

- Atlas events: 664
- Raw-native events: 663
- Common signal/side events: 514
- Common exact events: 510
- Atlas-only: 150
- Raw-native-only: 149
- Exact identity: 76.8072%
- Material contradiction: 36.7774%

Cross-venue OHLC differences propagate recursively through EMA20, EMA96 and ATR20. They therefore alter the trend-strength threshold, EMA20 pullback condition, confirmation condition and the chronology of same-variant active suppression. This is a source-lineage contradiction, not an execution-cost effect.

### 2024

The Atlas used public Bid/Ask-derived M15 bars (`sha256:d22a008247e2a8bed49a5169648661ab21eff404a6bc2985bca0c3b5af290020`), aligned with the Dukascopy-derived lineage used here.

- Atlas events: 669
- Raw-native events: 669
- Common exact events: 669
- Atlas-only: 0
- Raw-native-only: 0
- Exact identity: 100%

The year split demonstrates that the failure is specifically the 2023 mixed-venue Atlas lineage. It does not authorize replacement of the 2023 discovery population after seeing outcomes.

## Suppression audit

- Raw qualifying signals: 5,093
- warm-up suppressed: 8
- fold-crossing suppressed: 7
- same-variant active suppressed: 3,746
- tail suppressed: 0

Because active suppression depends on earlier accepted events, cross-venue differences can change later event identity even when later bars are close.

## Stop-rule consequences

The first binding failure occurred before executable candidate economics. Therefore the following are not missing results; they are prohibited downstream stages:

- source-native executable trade ledger and P/L
- Long/Short economics
- fold/month/session executable economics
- net, PF, MDD, minimum equity, MAE and MFE
- concentration and bootstrap
- spread, delay and slippage tests
- B02/F05 correlation and positive/negative-day contribution
- realized/full-equity portfolio DD and minimum equity
- loss-cluster, concurrency and margin gates
- candidate freeze
- 2020–2022 historical validation
- Core and MT4 parity
- 2025H1 and 2025H2

These fields are explicitly `NOT_EXECUTED_DUE_FIRST_BINDING_STOP`, not zero and not failed economics.

## Scientific interpretation

The Opportunity Atlas result cannot be carried forward as one portable executable candidate because its 2023 event population is materially dependent on Rakuten M15 venue history. Reconstructing the same concept from the binding Dukascopy Tick source changes more than one fifth of the union event population overall and more than one third in 2023.

This does not prove that pullback continuation has no economic edge. It proves that the specific Atlas-defined candidate lacks the required source-native event identity and cannot be frozen or externally validated under the preregistered contract.

## Authorization

- Candidate freeze: **NO**
- 2020–2022: **NO**
- Core: **NO**
- MT4: **NO**
- 2025H1: **NO**
- 2025H2: **NO**
- Production: **NO**
- Live: **NO**

## Next research value

Do not rescue HYP-035 by choosing a side or session, changing EMA/ATR thresholds, changing hold time, reducing lot size, using B02/F05 state, combining Sweep features, or opening 2020–2022/2025.

A future pullback-continuation hypothesis would need to be independently preregistered and discovered from a single source-native venue from the outset, with its own family definition and no reuse of HYP-035 outcome-defined exclusions.
