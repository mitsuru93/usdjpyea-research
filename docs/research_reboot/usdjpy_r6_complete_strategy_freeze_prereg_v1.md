# USDJPY R6 Complete-Strategy Freeze and H2 Gate Preregistration v1

## Decision

R6 applies one common procedure to all thirty-two accepted R5 Entry/Exit combinations, freezes at most five complete H1 strategies, and simultaneously freezes the candidate-specific unused 2024 H2 validation gates.

```text
R5 combinations audited: 32
maximum frozen complete strategies: 5
maximum per family: 2
maximum per Entry definition: 1
minimum frozen strategies: 0
relaxation if fewer than five pass: prohibited
H2 rows parsed in R6: 0
2025 access: prohibited
Core promotion: false
MT4 promotion: false
```

A frozen R6 strategy is eligible only for the single joint V1 H2 validation. It is not approved for Core, MT4 or capital allocation.

Authoritative configuration:

```text
configs/research/usdjpy_r6_complete_strategy_freeze_v1.json
```

Authoritative evaluator:

```text
tools/run_usdjpy_r6_complete_strategy_freeze_v1.py
```

## Frozen inputs

R6 accepts only:

1. accepted R4 Release `usdjpy-r4-entry-horizon-selection-v1`;
2. accepted R5 Release `usdjpy-r5-controlled-exit-v1`;
3. the R5 normalized Exit ledger, complete 32-row summary, monthly output and acceptance metadata.

R6 does not regenerate Entry signals, modify any R4 representative or recalculate an alternative R5 Exit parameter.

## Common H1 eligibility gates

Every Entry/Exit combination must pass every gate below. A strong average return cannot rescue a failed stability or concentration gate.

### Sample and aggregate economics

```text
aggregate trades >= 60
minimum trades in each H1 month >= 5
average default-cost net pips > 0
average severe-cost net pips > 0
default-cost profit factor > 1
severe-cost profit factor > 1
default-positive months >= 4 of 6
severe-positive months >= 3 of 6
total default-cost pips excluding the best two UTC Entry dates > 0
```

### Temporal stability

Using the exact R5 trade ledger and Entry-month assignment:

```text
Q1 and Q2: both default-positive
Q1 and Q2: both severe-positive
rolling two-month blocks: at least 4 of 5 default-positive
rolling two-month blocks: at least 3 of 5 severe-positive
rolling three-month blocks: all 4 default-positive
rolling three-month blocks: at least 3 of 4 severe-positive
```

The fixed blocks are January–February through May–June and January–March through April–June. No alternative window search is permitted.

### Concentration

```text
largest absolute UTC Entry-date contribution share <= 0.25
largest absolute calendar-month contribution share <= 0.50
top two UTC dates' share of positive daily pips <= 0.50
maximum absolute long/short contribution share <= 0.90
```

The first three concentration fields use default-cost net pips. Direction contribution share is the larger absolute long or short total divided by the sum of the absolute long and short totals. A zero denominator is assigned zero.

### Execution evidence

R6 requires the accepted R5 evidence that:

- all four policies use exact common Entry sets;
- all Exit timestamps are no later than their R4 time caps;
- R2 default and severe cost fields are unchanged;
- same-bar bracket ambiguity is adverse-first;
- Chandelier values use prior completed data only and stops never loosen.

These are implementation gates, not ranking components.

## Ranking after eligibility

Only fully eligible combinations receive a ranking score.

R6 uses the equal-weight mean of ten ascending percentile ranks:

1. aggregate average severe-cost net pips;
2. aggregate severe-cost profit factor;
3. minimum quarterly average severe-cost net pips;
4. minimum rolling-three-month average severe-cost net pips;
5. number of severe-positive months;
6. total excluding the best two UTC dates divided by trades;
7. one minus largest absolute UTC-day share;
8. one minus largest absolute month share;
9. one minus top-two-positive-days share;
10. one minus direction absolute-contribution share.

No component receives a larger weight.

Tie-break order:

```text
selection score descending
aggregate average severe-cost net pips descending
minimum quarterly average severe-cost net pips descending
total excluding best two UTC dates per trade descending
candidate_id ascending
policy_id ascending
```

R5's descriptive finding that the fixed time cap led average return for all eight representatives does not bypass this procedure.

## Complete-strategy redundancy

R6 traverses the deterministic ranking and applies:

1. at most one Exit policy for each `definition_sha256`;
2. at most two strategies from one family;
3. pairwise redundancy exclusion.

For pairwise redundancy, R6 calculates:

- daily severe-cost net PnL over every UTC date from January 1 through June 30, filling inactive dates with zero;
- exact Entry-timestamp sets.

The lower-ranked strategy is redundant only when both are true:

```text
daily severe-cost PnL Pearson correlation >= 0.85
Entry-timestamp Jaccard similarity >= 0.50
```

A zero-variance daily vector receives correlation zero. Ranking continues until five strategies are frozen or the eligible list is exhausted. No gate may be relaxed to reach five.

## Frozen H2 validation gates

R6 itself does not parse H2. It emits a complete machine-readable H2 plan for the frozen strategies.

### Validation domain

```text
start: 2024-07-01T00:00:00Z
end exclusive: 2025-01-01T00:00:00Z
execution: one joint run
strategy count: at most five
Entry and Exit parameters: unchanged
```

Only candidate-specific unused H2 outcomes may be opened. Previously opened complete strategies `A1_impulse_breakout_lb3_hold6` and `E3_trend_24h_resumption_hold6` are forbidden. R6 must assert that no frozen strategy is either forbidden complete strategy.

### Individual H2 gates

Each frozen strategy passes or fails independently:

```text
trades >= 60
average default-cost net pips > 0
average severe-cost net pips > 0
default-cost profit factor > 1
severe-cost profit factor > 1
default-positive months >= 4 of 6
severe-positive months >= 3 of 6
Q3 and Q4 both default-positive
Q3 and Q4 both severe-positive
total default-cost pips excluding the best two UTC Entry dates > 0
largest absolute month contribution share <= 0.60
top two UTC dates' share of positive daily pips <= 0.50
maximum absolute long/short contribution share <= 0.95
```

H2 ranking is prohibited. An H1 rank does not compensate for a failed H2 gate.

### H2 decision handling

- no strategy parameter may be changed after H2 is opened;
- no failed strategy may be rescued under a modified rule;
- each failed strategy is closed;
- at least one individual strategy must pass before Research/Core and MT4 parity begins;
- if none pass, this branch stops without using 2025 to redesign it;
- an equal-weight joint-portfolio diagnostic is reported but is not an individual pass gate.

## Required outputs

```text
complete_strategy_audit_all_32.csv
eligible_complete_strategies.csv
frozen_complete_strategies.csv
redundancy_decisions.csv
eligible_pairwise_similarity.csv.gz
family_freeze_summary.csv
h2_validation_plan.json
r6_acceptance.json
run_metadata.json
```

The 32-row audit must expose every gate and machine-readable failure reasons.

## Acceptance

R6 passes only if:

1. accepted R4 and R5 Release ZIP digests match;
2. R4 selected-representative, R5 Exit-ledger, summary and acceptance digests match;
3. exactly thirty-two complete combinations enter the audit;
4. all common gates are calculated for all thirty-two;
5. eligibility equals the conjunction of the frozen gates;
6. only eligible combinations receive ranking scores;
7. all ten percentile-rank components have equal weight;
8. all eligible pairwise similarities are reported;
9. at most five strategies are frozen;
10. no frozen strategies share an Entry definition;
11. no family contributes more than two;
12. no retained pair violates both redundancy thresholds;
13. no eligibility threshold is relaxed;
14. the H2 plan contains exactly the frozen strategies and unchanged Entry/Exit specifications;
15. no frozen strategy is a previously opened forbidden complete strategy;
16. H2 rows parsed equals zero;
17. 2025 access equals false;
18. R4 representatives are unchanged;
19. R5 policies and parameters are unchanged;
20. Core and MT4 promotion remain false.

## Next stage

A passing R6 authorizes one joint V1 run over candidate-specific unused 2024 H2 only. It does not itself authorize implementation or 2025 replication.
