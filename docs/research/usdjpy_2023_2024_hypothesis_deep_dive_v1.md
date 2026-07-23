# USDJPY 2023/2024 Hypothesis Deep Dive v1

## Objective and period roles

2023 and 2024 are development, mechanism-analysis and falsification periods. They are not consumed holdouts. Their purpose is to produce one exact specification for the unchanged 2025 H1 Rakuten MT4 binding gate. Known 2025 results may define the required gate, but may not select a mechanism, feature, threshold, side, portfolio weight or repair.

## What the completed work actually established

The accepted historical-2024-compatible portfolio loses JPY 9,279 in 2023 because B02 loses JPY 12,459 while F05 earns JPY 3,180. The same portfolio earns JPY 22,797 in 2024 H1 and JPY 38,358 in 2024 H2.

Families G and H showed that local F05 invalidation exits remove real losses but sacrifice recovery winners at similar or greater value. The only trajectory subset with positive exit effect in every development period improved 2023 by only JPY 1,077, far below the JPY 9,279 deficit. Further F05 exit subdivision is therefore both duplicate research and impact-insufficient.

Family I showed that blocking B02 shorts with at most 20 pips of side-aligned four-hour movement improves all three full development periods, but leaves 2023 at JPY -1,487 and PF 0.991953. Expanding the threshold to 40 pips makes 2023 slightly positive but harms 2024 H2. The incremental 20-to-40-pip band is negative in 2023 and positive in both 2024 halves, and none of the tested path, session, ATR, signal-geometry or exposure partitions separates it consistently.

## Family J WIP is not a blind new hypothesis

The proposed opposite-long payoff is deterministically related to the already opened Family I short outcome. For a 0.5-pip fixed spread, the reversed long and original short sum to -1 pip, or -10 JPY at 0.01 lot. Consequently, Family J's development outcome is algebraically derivable before a new evaluator is run.

At the 20-pip boundary, the implied total portfolio nets are JPY +5,685 in 2023, +33,241 in 2024 H1 and +41,148 in 2024 H2. However, the implied effect-month breadth is 10/2, 4/2 and 3/3 positive/negative months. The WIP preregistration requires 2024 H2 breadth of at least 4 positive and at most 2 negative months, so its own frozen development gate is already false.

The unmerged Family J branch must not be merged or described as blind preregistration. A future reversal/router proposal must explicitly state that it is development-outcome-derived and must freeze its 2025 gate prospectively without relaxing the failed development breadth.

## Broader hypothesis space

### 1. Exact complete-strategy portability

The first alternative to local B02/F05 repair is an independent edge. The fixed 2024 cohort consists of B02, F05, 8-hour trend resumption, 12-hour trend resumption and volatility-adjusted momentum. A local preflight exactly reproduced all 2024 H1/H2 signal and trade rows. Its provisional 2023 reconstruction, however, shifted 1,428 M15 bars rather than the accepted 1,543 because the accepted transformer source was never committed. The provisional 2023 results are therefore not scientific evidence.

The next binding analysis must first restore the exact transformer, reproduce 1,543 shifted bars and accepted B02/F05 identities, and then evaluate the unchanged five-strategy cohort under default and severe costs. No candidate or weight may change.

### 2. Multi-day directional regime state

The 2024 fixed strategies exhibit strong side asymmetry that changes by half-year. Naive trailing strategy-health and shadow-PF features already changed sign across periods and were rejected. The unresolved possibility is a market-state variable rather than a strategy-performance variable: multi-day directional return, path efficiency, volatility ratio and position within a multi-day range.

This diagnosis is downstream of exact portability. It must use predeclared 5-day and 20-day states and report all four half-year development folds before any router family is proposed.

### 3. Regime routing rather than static blocking

A stable state may route a session breakout to continuation in persistent directional markets and to mean reversion in nonpersistent markets. This is causally broader than Family I's fixed threshold and Family J's unconditional reversal. It is authorized only if the multi-day state has consistent cross-fold information and does not require outcome-derived local cut points.

### 4. Static multi-edge portfolio

A fixed equal-weight or leave-one-strategy-out portfolio is permitted as a predeclared diagnostic after exact 2023 reconstruction. Weight optimization is prohibited. The question is whether independent fixed edges reduce regime dependence, not whether optimized weights maximize 2023/2024 profit.

## Priority order

1. Restore exact 2023 transformer/evaluator reproducibility.
2. Run the unchanged five-strategy portability screen with exact 2024 regressions.
3. Diagnose predeclared multi-day directional states across four half-year folds.
4. Only then choose between an independent edge, a regime router, or closure of the current architecture.
5. Freeze one exact specification, establish Research-to-MT4 parity, and access 2025 H1 once.

No active candidate or family exists at this stage.
