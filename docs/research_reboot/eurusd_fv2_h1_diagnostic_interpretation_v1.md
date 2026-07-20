# EURUSD F v2 H1 diagnostic interpretation v1

## Evidence boundary

- Diagnostic run: `29743006760`, attempt 1.
- Run head SHA: `52c6ceeb433f93e671d6964f64e4fca3f3fbbba9`.
- Artifact ID: `8461148611`.
- Artifact digest: `sha256:2d1b610167c200d06fe40c3520bb9394be597e3da6987f07c81cf730aec9d800`.
- Input was physically isolated to the 3,030 H1 bars before 2024-07-01.
- Fixed 2024 H2 was not accessed by the diagnostic.
- No candidate rule was changed during the diagnostic.

## H1 findings

### Exit pair

Both exits used the same 90 H1 entries; entry-set Jaccard similarity was 1.0.

`F_v2_z72_1p5_mean_target_0p25_max12`:

- 90 trades;
- +5.018249 net pips/trade;
- +451.642396 total net pips;
- PF 1.696219;
- six positive months;
- severe-cost PF 1.344661;
- maximum drawdown -116.95 pips.

`F_v2_z72_1p5_mean_target_0p5_max12`:

- 90 trades;
- +3.676027 net pips/trade;
- +330.842396 total net pips;
- PF 1.510002;
- five positive months;
- severe-cost PF 1.180314;
- maximum drawdown -130.90 pips.

The target-0.25 exit is stronger on H1. This is an exit-policy difference, not an entry-filter finding.

### No justified entry filter

- Long and short trades were both profitable under default costs for both exits.
- Asia, Europe and U.S.-overlap session buckets were all profitable under default costs.
- Every preregistered entry-z bin was profitable.
- Every preregistered ER bin was profitable.
- The H1 evidence therefore does not justify deleting a side, session, z-score region or ER region.

### Holding structure

Average gross path across the common entries was approximately:

- bar 1: +2.585 pips;
- bar 4: +1.628 pips;
- bar 8: +1.909 pips;
- bar 10: +3.641 pips;
- bar 11: +4.726 pips;
- bar 12: +4.397 pips.

This contradicts a blanket shortening of the 12-bar maximum hold. The edge weakens in the middle of the path and reappears around bars 10-12.

The z-target exits were profitable, while unresolved time-stop exits were negative. That identifies the unresolved non-reversion group as the main loss source, but the registered H1 diagnostic does not provide a single causal checkpoint or filter that improves the candidate without degrading another registered dimension. A new early-exit threshold would therefore be another H1 search rather than a demonstrated structural correction.

### Cost behavior

Both candidates remained positive across the full preregistered H1 grid. At 3x spread plus 0.5 pip slippage per side:

- target 0.25: +2.812525 pips/trade, PF 1.344661;
- target 0.5: +1.470302 pips/trade, PF 1.180314.

There is no H1 basis for adding a spread filter to rescue a failing baseline.

## Revision decision

No v3 candidate is created from this diagnostic.

Reasons:

1. the target-0.25 baseline already dominates the target-0.5 baseline on H1;
2. all registered entry partitions remain profitable;
3. the average path supports retaining the 12-bar maximum;
4. adding an early-exit rule would require selecting a new checkpoint and threshold without a uniquely justified H1 value;
5. the frozen baselines already passed fixed 2024 H2 and exact MT4 ledger parity.

The correct action is to preserve the two frozen candidates unchanged and proceed to the already bounded exit-policy and execution-stress stages.

## H2-first production selection

The fixed H2 result is used to select between the two rules that were locked before H2:

- target 0.5: 114 trades, +209.10 net pips, PF 1.185323, severe PF 0.966719;
- target 0.25: 112 trades, +166.40 net pips, PF 1.146757, severe PF 0.936543.

Because H2 is the primary fixed validation period, `F_v2_z72_1p5_mean_target_0p5_max12` is selected as the production primary candidate.

`F_v2_z72_1p5_mean_target_0p25_max12` remains the neighboring robustness control because it was stronger on H1 and on the full-2024 aggregate. No new exit threshold is introduced.

## Next stage

Run the preregistered cost and execution stress for the unchanged primary and robustness-control candidates. This stage may characterize degradation and implementation requirements but may not change the signal or exit rules.
