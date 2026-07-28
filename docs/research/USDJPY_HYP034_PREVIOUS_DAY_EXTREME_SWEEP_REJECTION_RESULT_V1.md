# USDJPY-HYP-034 / Previous-Day Extreme Sweep Rejection Mechanism Study

**Decision:** `NO_PORTABLE_REJECTION_MECHANISM`

## Scope and firewall

This study is independent from HYP-030, HYP-031, HYP-032 and the parallel HYP-033 Asian Low Sweep study. No candidate, feature threshold, event ledger or outcome was shared. 2020–2022 and 2025 were not accessed.

## Source and chronology

- Source authority: PASS
- Source: Dukascopy BI5 source-native Bid/Ask Tick
- UTC calendar days audited: 731
- M15 bars reconstructed: 49,894
- Raw sweep events: 510
- High sweeps: 284
- Low sweeps: 226
- Both-side dates: 64
- Duplicate events: 0
- Chronology mismatches: 0
- Ask/Bid inversions: 0
- Currency mismatches: 0

## Fixed previous-day calendar contract

- Trading day: `[00:00:00,24:00:00) UTC`
- Day rollover: `00:00 UTC`
- Previous trading day: latest prior complete eligible weekday; weekends and source-proven no-tick holidays are skipped
- Previous-day High/Low: maximum/minimum source-native Bid
- Sweep: Bid strictly exceeds the prior High or falls below the prior Low
- Reclaim: Bid returns strictly inside the boundary
- Entry: first executable source-native tick after the completed-M15 rejection decision; Long at Ask, Short at Bid
- Exit: first executable source-native tick at or after the fixed 12-M15-bar / 3-hour boundary; Long at Bid, Short at Ask
- Reporting and drawdown currency: JPY
- Position size: 0.01 lot; ¥10 per pip

## Mechanism result

After variant-local active-position suppression, 432 completed-M15 rejection trades remained.

- Net: **+¥4,450**
- PF: **1.0888259012**
- Win rate: **50.69%**
- MDD: **¥8,157**
- Minimum equity: **¥999,436** from canonical ¥1,000,000 initial capital
- Median P/L: **+¥3.50**
- Mean MAE: **-24.59 pips**
- Mean MFE: **+25.55 pips**
- Positive folds: **2/4**

Fold net:

| Fold | Net |
|---|---:|
| 2023H1 | +¥6,397 |
| 2023H2 | -¥9 |
| 2024H1 | +¥377 |
| 2024H2 | -¥2,315 |

The raw rejection population was mildly profitable, but it did not satisfy the preregistered portable-mechanism requirements: PF was below 1.10, only two folds were positive, and concentration/resampling evidence did not support a stable cross-fold edge.

## Long / Short asymmetry

| Sweep / trade | Trades | Net | PF | MDD | Median P/L | Bootstrap lower 95% | P(non-positive) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous-Day High Sweep → Short | 246 | +¥1,732 | 1.0642 | ¥5,359 | -¥12 | -¥8,894 | 38.62% |
| Previous-Day Low Sweep → Long | 186 | +¥2,718 | 1.1176 | ¥4,823 | +¥36.50 | -¥7,152 | 29.72% |

Low Sweep → Long was stronger, but it did not establish a source-native, fold-portable ex-ante discriminator. Long-only rescue or post-result Short exclusion is therefore prohibited.

## Rejection / acceptance mechanism

The post-event path separation was economically clear but mostly post-entry:

- delayed rejection: High 117 events, +¥28,808; Low 113 events, +¥30,022
- false reclaim then continuation: High 105 events, -¥20,008; Low 65 events, -¥14,518
- outside acceptance: High 54 events, -¥13,329; Low 45 events, -¥12,993

This confirms that sustained rejection and outside acceptance have sharply different outcomes. However, the leave-one-fold-out feature evaluation found no admissible predictor that identified the profitable path using only information available by the entry decision.

## Ex-ante observability

All audited features had zero lookahead violations, including completed-bar returns, reclaim depth, outside duration to decision, overshoot ratio, spread, previous-day range percentile and completed-bar volatility state. Nevertheless:

- portable mechanism: **false**
- ex-ante discriminator: **false**
- candidate catalog size: **0**
- selected candidate: **none**
- candidate freeze: **not created**

## Binding stop and downstream authorization

The first binding stop is Stop Rule 5: **portable rejection mechanismなし**.

Therefore:

- 2020–2022 historical validation: not authorized / not accessed
- Core implementation and parity: not authorized / not executed
- MT4 compile, standalone, integrated and full-equity runs: not authorized / not executed
- 2025H1 and 2025H2: not authorized / not accessed
- production authorization: **NO**
- live authorization: **NO**

## Evidence

- Scientific Run: `30375885665`
- Scientific artifact ID: `8695321156`
- Scientific artifact digest: `sha256:4eefbcc77962dc9f72fa647b386088c18f9efa196b7f70be1e970ccf9ed8964b`
- Scientific head SHA: `b94d09c0dc057f6a811cf79664cff81adf0fc922`
- Packaging defect: mutable `run.log` only; scientific result preserved
- Canonical r1 package: generated after merge by the evidence-only Infrastructure Hardening v1 workflow

## Exact next action

Close HYP-034. Do not create a candidate, exclude a side after outcomes, retune the fixed Exit, combine this study with Asian Range Sweep or HYP-032 state, or access 2020–2022/2025 for this family.
