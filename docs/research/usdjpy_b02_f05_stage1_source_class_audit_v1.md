# USDJPY B02/F05 Stage 1 source and path-class audit v1

- Research base: `9569c23f63616fa67a8565e45b53b063d4d73a52`
- Core base: `b31405cd4c5380a376655ba240ccb100e230e775`
- Baseline accepted trades: **1,882**
- 2024 exact ticks scanned: **40,969,081**
- 2025 accessed: **No**

## Source parity

- 2024 M1: 373,383
- 2024 M5: 74,975
- 2024 M15: 24,999
- 2024 accepted Entry Bid: 922/922 exact
- 2024 H1 M15 OHLC: 11,884/11,884 exact
- 2024 H2 accepted snapshots: 12,209/12,250 matched, all matched opens exact
- 2023 shifted M15 rows: 1,543; duplicate timestamps: 0

## Path-class migration

|Authority|WINNER|P1|P2|P3|
|---|---:|---:|---:|---:|
|Old M15 sampled|969|412|291|210|
|Common M1|966|567|322|27|
|2024 exact Tick only|499|258|151|14|

The old M15 class is not used as the binding target. Common M1 is binding across all four folds; 2024 exact Tick is sensitivity authority.

## Technical attempts

Two technical incomplete attempts occurred before candidate outcomes. Both were repaired without changing definitions. See `configs/research/usdjpy_b02_f05_lifecycle_abc_technical_attempts_v1.json`.
