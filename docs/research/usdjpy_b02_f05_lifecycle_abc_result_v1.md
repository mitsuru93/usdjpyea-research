# USDJPY B02/F05 lifecycle Stage A/B/C Research result v1

## Decision

- Status: `CLOSED_NO_ALL_FOLD_PASS`
- Frozen candidates: 20
- Development/falsification folds: 2023H1, 2023H2, 2024H1, 2024H2
- All-four-fold passing candidates: **0**
- Eligible connected family regions: **0**
- MT4 authorization: **false**
- 2025 H1/H2 access: **none**

All 20 specifications are closed without repair, chaining or parameter expansion. No candidate advances to MT4.

## Stage-level result

|Stage|Question|Candidates|Stage-gate pass rows|Common-gate pass rows|Full fold passes|Best pooled candidate|Pooled default Δ|
|---|---|---:|---:|---:|---:|---|---:|
|A|P3 breakout establishment|8|18/32|0/32|0/32|`ABC_A_B02_ABORT_Q2`|-1247.1 pips|
|B|P2 early continuation / expansion|4|3/16|1/16|1/16|`ABC_B_B02_Q2`|-875.1 pips|
|C|P1 peak-relative deterioration|8|32/32|0/32|0/32|`ABC_C_M15_Q3_R2`|-415.4 pips|

### Stage A — P3 establishment

Stage A sometimes reduced the never-profitable P3 target, but no fold row passed the complete common portfolio gate. Winner-tail loss, sub-block instability, date concentration and negative aggregate effects dominated. The least-negative pooled Stage A cell was `ABC_A_B02_ABORT_Q2` at -1,247.1 pips.

### Stage B — P2 continuation

Only `ABC_B_B02_Q3` in 2023H1 passed both the target and common gates (+782.5 default pips). It failed portability in the other three folds, and every Stage B candidate was negative when pooled. `ABC_B_B02_Q2` was the least-negative pooled Stage B cell at -875.1 pips.

### Stage C — P1 deterioration

All 32 Stage C candidate-fold rows passed the P1-specific loss-reduction and no-pre-peak-trigger checks. This confirms that the price-geometry rules detect real giveback deterioration. They are not portable exit rules: every cell failed at least one binding common gate, primarily sub-block stability, ex-best-two-date robustness, Winner-tail retention and leave-one-month-out stability. The least-negative pooled cell was `ABC_C_M15_Q3_R2` at -415.4 pips.

## Candidate summary

|Candidate|Stage|Fold passes|Pooled default Δ|Pooled severe Δ|Minimum top-10 Winner retention|
|---|---:|---:|---:|---:|---:|
|`ABC_A_B02_ABORT_Q2`|A|0/4|-1247.1|-1204.3|0.8157|
|`ABC_A_B02_ABORT_Q3`|A|0/4|-1326.9|-1212.6|0.7589|
|`ABC_A_B02_DELAY_Q3`|A|0/4|-1619.2|-955.9|0.7511|
|`ABC_A_B02_DELAY_Q2`|A|0/4|-1638.1|-1229.8|0.7965|
|`ABC_A_F05_ABORT_Q2`|A|0/4|-2174.1|-1970.0|0.6689|
|`ABC_A_F05_ABORT_Q3`|A|0/4|-2767.9|-2509.6|0.3520|
|`ABC_A_F05_DELAY_Q2`|A|0/4|-3193.8|-1767.6|0.6006|
|`ABC_A_F05_DELAY_Q3`|A|0/4|-3369.1|-968.9|0.3383|
|`ABC_B_B02_Q2`|B|0/4|-875.1|-849.2|0.8628|
|`ABC_B_B02_Q3`|B|1/4|-1079.1|-1042.8|0.8628|
|`ABC_B_F05_Q2`|B|0/4|-1150.5|-987.5|0.6334|
|`ABC_B_F05_Q3`|B|0/4|-2021.8|-1816.7|0.6334|
|`ABC_C_M15_Q3_R2`|C|0/4|-415.4|-167.8|0.8102|
|`ABC_C_M5_Q3_R2`|C|0/4|-604.2|-364.8|0.7539|
|`ABC_C_M15_Q3_R1`|C|0/4|-1646.8|-1416.6|0.6908|
|`ABC_C_M5_Q3_R1`|C|0/4|-2200.6|-1954.4|0.6637|
|`ABC_C_M15_Q2_R2`|C|0/4|-2559.5|-2310.3|0.5455|
|`ABC_C_M15_Q2_R1`|C|0/4|-2598.0|-2277.8|0.3690|
|`ABC_C_M5_Q2_R2`|C|0/4|-3785.8|-3449.5|0.2959|
|`ABC_C_M5_Q2_R1`|C|0/4|-5338.3|-4966.8|0.1436|

## Only complete fold pass

`ABC_B_B02_Q3` passed 2023H1 only:

- default delta: +782.5 pips
- severe delta: +782.5 pips
- positive/negative effect months: 5 / 1
- top-10 Winner retention: 0.9553
- all B02/F05, long/short, sub-block, concentration and target gates passed in that fold

It is not a finalist because all four folds were required.

## Frozen interpretation

1. Breakout establishment contains useful local information, but immediate abort and delayed confirmation remove too much Winner mass and do not generalize.
2. Early continuation failure can work in one B02 fold, but the benefit is not portable and Winner sacrifice commonly exceeds P2 benefit.
3. Peak-relative deterioration is a valid descriptive detector of P1 giveback, but not an economically stable termination mechanism under the frozen gates.
4. Combining Stage A, B and C after outcomes is prohibited. Such chaining would be a new hypothesis, not a continuation of HYP-025.

## Reconstruction and evidence boundary

The original successful scientific execution reported `CLOSED_NO_ALL_FOLD_PASS`, but its temporary output directory was not persisted before closure. The result files were reconstructed from the merged frozen evaluator logic, the 1,882-trade common-M1 ledger, the accepted 2023 M1 lineage, the 2024 derived M1 Release, and an independent scan of 40,969,081 exact Bid/Ask ticks. The common-M1 and exact-Tick class counts exactly match the preregistered Stage-1 identities. No candidate, threshold, gate, timeframe or period was changed.

Large trade-level outputs are included in the closure bundle identified by the committed output manifest; the repository summary files are the binding human-readable closure.

## Boundaries

- HYP-023 and HYP-024 were not re-executed or used as substitutes.
- MT4 was not accessed.
- 2025 H1 and 2025 H2 were not accessed.
- No live-order authorization exists.
