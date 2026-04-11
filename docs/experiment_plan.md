# Pre-MT4 Experiment Roadmap

This roadmap defines practical, staged research work before full MT4-equivalence simulation.

## 1) Baseline Replication
Objective: replicate the high-level baseline skeleton without inventing undocumented details.

- Implement baseline signal envelope (EMA20 ±0.070%) candidate detection.
- Implement rev/trend candidate paths and TP/SL defaults.
- Implement session tagging (JST buckets).
- Keep unknown mechanics explicitly marked as **TBD / to be verified against EA**.

Exit condition:
- Reproducible baseline run pipeline exists with transparent assumptions.

## 2) Feature Extraction Foundation
Objective: prepare analysis-grade feature snapshots at decision time.

- Capture signal context (envelope distance, slope surrogates, volatility context).
- Capture session and month identifiers.
- Capture filter-state flags (where known) with `unknown` placeholders where needed.

Exit condition:
- Feature table supports monthly/session stratification and future filter ablations.

## 3) Conservative Execution Assumptions
Objective: avoid optimistic bias before MT4 validation.

- Use conservative same-bar ordering assumptions when TP/SL hit order is ambiguous.
- Apply explicit touch model split:
  - Rev: real touch
  - Trend: virtual spread clipping touch judgment
- Log all assumptions in run metadata.

Exit condition:
- Execution assumptions are explicit, deterministic, and bias-aware.

## 4) Monthly Robustness Checks
Objective: ensure behavior is not dominated by narrow time slices.

- Report monthly metrics (PnL, PF, win rate, DD proxies, trade count).
- Apply minimum-activity and minimum-consistency checks.
- Flag unstable months/regimes for investigation.

Exit condition:
- Baseline passes minimum robustness thresholds (thresholds are **TBD / to be verified against EA**).

## 5) Session-wise Checks
Objective: assess dependence on session-specific market microstructure.

- Report metrics by session (ASIA/TOKYO/LONDON/NY).
- Compare contribution concentration and drawdown concentration by session.
- Validate whether session-specific thresholds appear beneficial or brittle.

Exit condition:
- No unacceptable fragility concentrated in a single session (exact criteria TBD).

## 6) Filter Ablation Order
Objective: isolate incremental value and side effects of filter families.

Recommended order (coarse-to-specific):
1. Core environment/context blocks (e.g., BB/ATR trend environment, M5 slope)
2. Safety/ban mechanisms (e.g., extreme/overheat, Shock families)
3. Directional families (RevZoneC, TrendDistFilter, TrendBoost)
4. Microstructure/session vetoes (TokyoTRPre60Veto, BBWChopVetoRev)
5. Override/force and chase variants (RVBWTRForce, DeepChase, DeepChaseV2)

Notes:
- Toggle one family at a time versus baseline.
- Keep all other assumptions fixed.
- Unknown interactions are **TBD / to be verified against EA**.

## 7) Promotion Criteria (Research -> Core Candidate)
A research artifact can be promoted to a core candidate only when:

- Baseline assumptions are documented and reproducible.
- Performance survives monthly and session splits.
- Ablation evidence shows non-fragile contribution.
- No known lookahead or optimistic fill bias.
- Remaining unknowns are explicitly listed for MT4 verification.

Final promotion is pending MT4 confirmation because MT4 remains the source of truth.
