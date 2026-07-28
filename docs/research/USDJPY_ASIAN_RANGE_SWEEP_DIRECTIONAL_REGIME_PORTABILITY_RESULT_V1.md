# USDJPY Asian Range Sweep Directional-Regime Portability Study

## Decision

**NO_PORTABLE_REGIME_RULE** (`USDJPY-HYP-031`, `S_ASIAN_RANGE_SWEEP_REGIME_ROUTING`). HYP-030 remains closed as `NO_PORTABLE_CANDIDATE`. No candidate freeze, backward-validation outcome access, Core implementation, MT4 run, or 2025 access is authorized.

## Binding source-native population

Dukascopy BI5 Bid/Ask ticks generated Asian High/Low, M15 sweep side, first executable Entry and frozen 3-hour Exit from one source. The raw-native baseline produced 544 resolved trades, +JPY4,523, PF 1.0756, MDD JPY7,781. Long contributed +JPY13,176; Short contributed -JPY8,653.

Fresh native schedule identity versus the accepted canonical schedule was 504 common events, 41 canonical-only and 40 raw-only. The native build also found 16 bars sweeping both extremes and four unresolved executable chronologies. Therefore `source_native_signal_identity_complete` failed.

## HYP-030 mismatch attribution

All 20 prior mismatch rows are preserved. Fourteen are close-back-inside failures, five are sweep/range-boundary failures and one canonical Short becomes an opposite raw-native Long. Those 20 canonical trades contributed approximately +JPY3,758 to HYP-030.

## Side x regime findings

H4 Long-Up: 147 trades, +JPY2,974, PF 1.2148. H4 Long-Down: 79 trades, +JPY8,383, PF 2.0224. H4 Short-Up: 180 trades, -JPY11,005, PF 0.4970. H4 Short-Down: 116 trades, +JPY1,867, PF 1.1246.

D1 Long-Up: 161 trades, +JPY3,400, PF 1.2189. D1 Long-Down: 58 trades, +JPY6,598, PF 2.3446. D1 Short-Up: 206 trades, -JPY8,254, PF 0.6335. D1 Short-Down: 78 trades, -JPY2,415, PF 0.8190.

Short loss is indeed concentrated in Up state, and H4 Short-Down improves to positive. However Long profit is materially stronger in Down than Up under both timeframes. The proposed mirror mechanism therefore does not explain HYP-030 Long profitability.

## Candidate results

R1 H4 symmetric: 263 trades, +JPY4,841, PF 1.1680, MDD JPY4,855, 3/4 positive folds and 17/24 positive months. It fails source identity, minimum fold (2023H1 -JPY4,586) and top-five-winner removal (-JPY760). Spread +1 pip remains +JPY2,211; +2 pips becomes -JPY419.

R2 D1 symmetric: 239 trades, +JPY985, PF 1.0341, MDD JPY6,874, 3/4 positive folds and 15/24 positive months. Aligned Short-Down is -JPY2,415; side/regime dependency is 100%. Spread +0.5 pip is already -JPY210, +1 pip -JPY1,405, Entry delay +5 seconds -JPY257, and top-five removal -JPY4,185.

## Transition and portfolio risk

R1 has 136 transitions; worst five-business-day cluster net is -JPY2,704 and maximum cluster MDD JPY2,779. R2 has 14 transitions; worst ten-business-day cluster net is -JPY2,642 and maximum cluster MDD JPY3,250.

B02/F05 negative-day contribution is positive for R1 (+JPY4,574) and R2 (+JPY4,835), but additive daily portfolio MDD rises from JPY40,487 to JPY44,428 for R1 and JPY44,365 for R2. These are reported separately from the preregistered bootstrap distributions and are not the sole rejection reason.

## Authorization boundary

Because no development candidate passes every gate, pre-2023 strategy outcomes remain unopened; 2025H1/H2 remain untouched; Core and MT4 are unchanged.
