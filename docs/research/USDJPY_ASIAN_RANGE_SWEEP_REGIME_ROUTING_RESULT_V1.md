# USDJPY-HYP-031 Asian Range Sweep Directional-Regime Portability — Final Result

## Binding decision

`NO_PORTABLE_REGIME_RULE`

No R1/R2 candidate passed every preregistered 2023–2024 development gate. No portable candidate was frozen. The locked 2020–2022 strategy outcomes, Core/MT4, 2025H1 and 2025H2 were not opened.

## Technical-stop classification

Run `30316460286` is classified as `TECHNICAL_PARTIAL_RESULT_EXPOSED`, not a scientific no-result stop. The evaluator completed, wrote `final_decision.json`, and exposed `NO_PORTABLE_REGIME_RULE` through receipt Issue #348. The workflow then failed because its `jq -e` postcondition required `audits.chronology_unresolved == 0`, while the completed result recorded `4`.

The repair preserved evaluator SHA-256 `652c55d408339cf6609896071fdddcb7c50241a874e163a4a6aede1731b6fc2c`, candidate definitions, gates, source contract and period roles. Repaired Run `30317593695` completed packaging without changing scientific outputs.

## Source-native population and HYP-030 mismatch attribution

- Canonical events: **545**
- Raw-native executable events: **544**
- Common intersection: **504**
- Canonical-only: **41**
- Raw-only: **40**
- Side disagreement within common timestamps: **0**
- Ambiguous both-side bars: **16**
- Chronology unresolved: **4**
- HYP-030 mismatch rows attributed: **20**
- Mismatch P/L contribution: **+¥3,758**

Mismatch causes:

- `RAW_CLOSE_NOT_BACK_INSIDE_HIGH`: 9 events, +¥2,740
- `RAW_CLOSE_NOT_BACK_INSIDE_LOW`: 5 events, +¥505
- `RAW_NO_LOW_SWEEP_RANGE_OR_LOW_BOUNDARY`: 3 events, -¥557
- `RAW_NO_HIGH_SWEEP_RANGE_OR_HIGH_BOUNDARY`: 2 events, +¥1,569
- `RAW_SIDE_FLIPPED_OPPOSITE_SWEEP`: 1 event, -¥499

The mismatch ledger preserves timestamp, canonical/raw side, Asian range differences, signal OHLC differences, sweep and close-back-inside margins, P/L and cause for all 20 rows.

## Diagnostics

The source-native both-side baseline had 544 trades, +¥4,523, PF 1.0756 and MDD ¥7,781. Long-only produced 239 trades, +¥13,176 and PF 1.5792; Short-only produced 305 trades, -¥8,653 and PF 0.7666. These are diagnostics only and were not eligible for selection.

## R1 — H4 symmetric transition block

- Allowed / blocked: **263 / 281**
- Net: **+¥4,841**
- PF: **1.1680**
- MDD: **¥4,855**
- Positive folds: **3/4**
- Positive months: **17/24**
- Minimum fold: **-¥4,586** in 2023H1
- Aligned Long-Up: **+¥2,974**
- Aligned Short-Down: **+¥1,867**
- Maximum side/regime positive-net share: **61.43%**
- Blocked-winner damage / avoided-loser benefit: **¥30,683 / ¥31,001**
- Transition count: **136**
- Worst 5-business-day transition cluster net: **-¥2,704**
- Worst 10-business-day transition cluster net: **-¥2,208**
- B02/F05 negative-day contribution: **+¥4,574**
- Additive portfolio net / daily MDD: **+¥56,468 / ¥44,428**

Failed binding gates:

1. `source_native_signal_identity_complete`
2. `minimum_fold_net`
3. `top5_winner_removal_positive`

R1 therefore cannot be frozen despite positive aggregate and both aligned-side nets.

## R2 — D1 symmetric transition block

- Allowed / blocked: **239 / 305**
- Net: **+¥985**
- PF: **1.0341**
- MDD: **¥6,874**
- Positive folds: **3/4**
- Positive months: **15/24**
- Minimum fold: **-¥3,227** in 2023H1
- Aligned Long-Up: **+¥3,400**
- Aligned Short-Down: **-¥2,415**
- Maximum side/regime positive-net share: **100%**
- Transition count: **14**
- Worst 5-business-day transition cluster net: **-¥1,965**
- Worst 10-business-day transition cluster net: **-¥2,642**
- B02/F05 negative-day contribution: **+¥4,835**
- Additive portfolio net / daily MDD: **+¥52,612 / ¥44,365**

Failed binding gates:

1. `source_native_signal_identity_complete`
2. `pf_at_least_1p05`
3. `minimum_fold_net`
4. `aligned_short_nonnegative`
5. `maximum_side_dependency`
6. `maximum_regime_dependency`
7. `spread_plus_1pip_nonnegative`
8. `entry_delay_5s_positive`
9. `top5_winner_removal_positive`

R2 is directionally asymmetric and secular-trend dependent: Long-Up is positive while Short-Down remains negative.

## Directional symmetry and transition conclusion

R1 did show positive aligned contribution from both directions, but it failed source-native identity completeness, the binding minimum-fold floor, and winner-concentration robustness. R2 failed the core symmetry requirement because Short-Down remained negative and 100% of positive contribution came from Long-Up. Transition-cluster gates were not the direct rejection cause, but both candidates still had material negative transition windows.

The study therefore does not support a portable symmetric directional-regime architecture for the frozen R1/R2 catalog. It also does not authorize Long-only rescue.

## Downstream authorization

- Candidate freeze: **none**
- 2020–2022 backward validation: **not authorized / not accessed**
- Research/Core parity: **not authorized**
- MT4 standalone: **not authorized**
- MT4 integrated B02/F05: **not authorized**
- 2025H1: **not authorized / not accessed**
- 2025H2: **not authorized / not accessed**
- Production/live: **not authorized**

A successor may be studied only under a new Hypothesis ID and an outcome-free preregistration. Long-only promotion, asymmetric side thresholds, regime exceptions and retuning from these outcomes remain prohibited.
