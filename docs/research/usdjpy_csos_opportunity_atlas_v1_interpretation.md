# USDJPY CSOS Opportunity Atlas v1 — Objective-Specific Interpretation

Status: `POST_ANALYSIS_INTERPRETATION_NO_RULE_CHANGE_NO_EA_AUTHORIZATION`

This note interprets the frozen Opportunity Atlas against the CSOS objective: identify return sources that B02/F05 do not cover. It does not alter any signal definition, threshold, holding horizon, score, rank, source data, or receipt. The preregistered Atlas and its automatic rankings remain authoritative.

## Frozen automatic results

The weighted family ranking is:

1. D — Shock Failure
2. F — Liquidity Sweep
3. J — Pullback Continuation
4. C — Shock Continuation
5. E — Session Transition

The artifact's portable-positive heuristic selected D, J and E because those families were positive in at least three of four folds. That heuristic measures portability of positive standalone contribution; it is not identical to the narrower CSOS requirement of helping specifically when B02/F05 are weak.

## CSOS-objective research sequence

### 1. D — Shock Failure

Primary third-strategy research candidate.

- 114 opportunities over two years; 57.0 per year.
- Net contribution: +¥12,847 normalized fixed-lot estimate.
- Profit factor: 2.437.
- Positive folds: 3/4.
- Contribution on B02/F05-negative days: +¥9,644.
- Reduction of negative-day losses: +¥7,302.
- Theoretical maximum-drawdown improvement: +¥2,635.
- Daily P/L correlation: +0.068 to B02 and -0.064 to F05.
- Both long and short sides were positive; all sufficiently populated sessions were positive.
- Simultaneous holding with at least one baseline strategy was 86.8%. Therefore, its independence is return-pattern independence, not temporal or capital-usage independence.

Interpretation: D is the only family that combines positive standalone economics, positive weak-market contribution, low B02/F05 P/L correlation, bilateral directionality and three-fold portability. It is the strongest answer to “what should become the third strategy?” at Opportunity Atlas stage.

### 2. F — Liquidity Sweep

Strongest pure weak-market complement, with Asian Range Sweep prioritized inside the family.

Family aggregate:

- 934 non-overlapping family opportunities; 467.0 per year.
- Net contribution: +¥7,708.
- Contribution on B02/F05-negative days: +¥30,621.
- Expected weak-market coverage: 23.0%.
- Reduction of negative-day losses: +¥12,146.
- Theoretical maximum-drawdown improvement: +¥8,203.
- Daily P/L correlation: -0.252 to B02 and -0.246 to F05.
- Positive folds: 2/4 at family-aggregation level.

Variant evidence:

- `F_ASIAN_RANGE_SWEEP`: +¥8,708, PF 1.147, positive in 4/4 folds, +¥19,512 on baseline-negative days.
- `F_PREVIOUS_DAY_SWEEP`: +¥2,763, PF 1.044, positive in 3/4 folds, +¥18,919 on baseline-negative days.

Interpretation: the family aggregation loses portability because two distinct reference-level mechanisms are combined under deterministic first-signal priority. The next study should preserve Asian Range Sweep and Previous-Day Sweep as separate mechanisms rather than optimize or blend them prematurely.

### 3. G — Trend Exhaustion

Mechanism-refinement priority, not a strategy candidate in its present definition.

- Net contribution: -¥9,439; PF 0.937; positive folds 1/4.
- Contribution on B02/F05-negative days: +¥49,122.
- Expected weak-market coverage: 25.7%, the highest family-level coverage in the Atlas.
- Reduction of negative-day losses: +¥26,479.
- Daily P/L correlation: -0.350 to B02 and -0.563 to F05.
- Winner damage risk: 23.1%.

Interpretation: G locates a large missed return source, but the frozen broad proxy destroys too much of B02/F05's profitable regime. It should be researched to isolate the actual exhaustion event from ordinary counter-trend fading. It is not authorized for implementation or parameter search.

## Why J is not the second complementary strategy despite high profit

J — Pullback Continuation produced the largest family net contribution (+¥20,752) and was positive in 4/4 folds. However:

- contribution on B02/F05-negative days was -¥39,589;
- daily P/L correlation was +0.341 to B02 and +0.450 to F05;
- negative-day loss reduction was -¥59,733.

J is a plausible independent return-source study, but the fixed proxy mainly adds exposure to the same favorable trend regimes rather than repairing the markets B02/F05 miss. It ranks highly for standalone economics, not for strict complementarity.

## Scientific conclusion

At Opportunity Atlas stage, the third strategy to develop next is **D — Shock Failure**.

The next three CSOS research programs should be:

1. Shock Failure event-definition and execution-validity study.
2. Liquidity Sweep split study, beginning with Asian Range Sweep and retaining Previous-Day Sweep separately.
3. Trend Exhaustion mechanism-refinement study focused on reducing winner damage without using 2025 or performing broad parameter optimization.

This is research prioritization only. No EA, Core change, MT4 run, production authorization, or 2025-period access is implied.
