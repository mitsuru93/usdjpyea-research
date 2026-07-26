# USDJPY Impact Atlas Program v1

Updated: 2026-07-26

## Objective

Redirect B02/F05 improvement research from local structural-stop optimization toward the largest economically addressable sources of portfolio underperformance.

The program must determine where improvement capacity actually resides before authorizing new trading rules.

## Binding research question

Which observable market-state, entry-establishment, portfolio-exposure, and profit-lifecycle mechanisms explain the largest avoidable loss contribution while preserving existing winner economics across 2023H1, 2023H2, 2024H1, and 2024H2?

2025H1/H2 are not candidate-selection periods. They remain external gates. Failed-reclaim evaluation for 2025 remains pending accepted raw Bid/Ask Tick acquisition and unchanged-candidate retest.

## Program hierarchy

1. Market-state and strategy permission
2. Entry establishment and admission
3. Portfolio exposure and loss clustering
4. Profit lifecycle and winner retention
5. New complementary strategy families
6. Local structural exit overlays

Local SL work is retained as a supporting program, not the primary improvement program.

## Impact Atlas unit of analysis

The atlas must support both trade-level and portfolio-event-level observations.

Required dimensions:

- strategy: B02 / F05;
- fold: 2023H1 / 2023H2 / 2024H1 / 2024H2;
- side;
- session and UTC hour;
- entry-establishment state;
- native H1/H4 market state;
- portfolio exposure state;
- loss-path state;
- profit-lifecycle state;
- shock / intervention / announcement context where source evidence exists;
- month and date breadth.

## Required impact measures

For every diagnosed mechanism or cohort:

- gross loss contribution;
- trade count and active-date count;
- avoidable-loss upper bound;
- winner population exposed to the same rule;
- winner-damage upper bound;
- net addressable impact;
- fold portability;
- direction symmetry;
- temporal breadth;
- implementation observability;
- complementarity to existing B02/F05 exposure.

No candidate may be prioritized solely by pooled profit improvement.

## Initial hypothesis programs

### A. Market-state strategy routing

B02 and F05 are setup observations whose deployability depends on a completed market-state transition. Candidate state ledgers must be deterministic, direction-symmetric, and based only on information available at the decision time.

### B. Entry establishment

Separate setup detection from deployable entry. Diagnose immediate follow-through, delayed establishment, failed establishment, false breakout, and non-expansion states.

### C. Portfolio exposure

Measure loss clustering caused by simultaneous B02/F05 positions, same-direction risk, entry clusters, and correlated adverse periods. Static stack count alone is not a sufficient causal rule.

### D. Profit lifecycle

Separate establishment, profitable expansion, maturity, exhaustion, and giveback. Evaluate winner retention before proposing profit locks or termination policies.

### E. Complementary strategy families

Only after the atlas identifies uncovered states, research independent mechanisms such as false-breakout reversal, balance mean reversion, session transition, and shock continuation/stabilization.

## Phase plan

### Phase 0 — source and lineage lock

- inventory accepted trade ledgers, path ledgers, M1/M5/M15 bars, raw Tick releases, receipts, and hashes;
- reconcile 2023 and 2024 clock contracts;
- declare fields unavailable in any fold;
- prohibit silent substitution.

### Phase 1 — descriptive Impact Atlas

Produce loss-contribution and winner-exposure tables without selecting trading thresholds.

### Phase 2 — program ranking

Rank research programs by addressable impact, coverage, portability, winner damage, causal clarity, implementability, and complementarity.

### Phase 3 — finite preregistered mechanism tests

Select at most three programs and at most four mechanism families per program. Freeze definitions before outcome evaluation.

### Phase 4 — component evaluation

Evaluate router, establishment, exposure control, and profit lifecycle separately.

### Phase 5 — staged integration

Integrate only individually supported components in the following order:

baseline -> market-state permission -> entry establishment -> exposure control -> profit lifecycle -> local exit overlay.

### Phase 6 — external gates

Apply the frozen integrated candidate to 2025H1 only after required 2025 source data are accepted. H2 handling follows the project period policy in force at execution time.

## Scientific boundaries

- Do not optimize directly on 2025H1/H2.
- Do not treat M1/HST zero detections as raw-Tick evidence.
- Do not reopen broad generic structural-SL searches without materially new state information.
- Do not combine multiple components before their independent contribution is established.
- Do not infer causality from calendar labels, side labels, or pooled model importance alone.
- Do not use Notion as the task selector; GitHub contracts and registries are authoritative.

## First executable deliverable

`USDJPY_IMPACT_ATLAS_V1` must produce:

1. canonical observation inventory;
2. trade-level loss-contribution table;
3. portfolio-event loss-cluster table;
4. entry-establishment cohort table;
5. market-state cohort table;
6. profit-lifecycle cohort table;
7. research-program priority table;
8. explicit missing-data and non-identifiability report.

No trading candidate is authorized by Phase 1.