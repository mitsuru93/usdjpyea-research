# USDJPY R4 Entry/Horizon Representative Selection Preregistration v1

## Decision

R4 applies one common, frozen selection procedure to all 660 accepted R2 Entry/horizon combinations using only accepted R2 and R3 H1 outputs.

```text
maximum representatives: 8
maximum per family: 2
maximum per Entry definition: 1
minimum representatives: 0
relax gates if fewer than eight pass: prohibited
H2 access: prohibited
2025 access: prohibited
Exit optimization: prohibited
Core promotion: false
MT4 promotion: false
```

R4 selects diagnostic Entry/horizon representatives for controlled R5 Exit research. A selected representative is not a complete strategy and is not approved for Core, MT4 or capital allocation.

Authoritative configuration:

```text
configs/research/usdjpy_r4_entry_horizon_selection_v1.json
```

Authoritative evaluator:

```text
tools/run_usdjpy_r4_entry_horizon_selection_v1.py
```

## Frozen inputs

R4 accepts only:

1. accepted R2 Release `usdjpy-r2-horizon-surface-v1`;
2. accepted R3 Release `usdjpy-r3-temporal-stability-v1`;
3. the R2 normalized trade ledger and 660-row summary;
4. the complete R3 temporal, regime, direction, concentration, sample-class and neighbouring-horizon outputs.

The Release and internal-file digests are fixed in the configuration. R4 does not regenerate Entry signals or fixed-horizon returns.

## Selection philosophy

The objective is not to choose the largest H1 mean return. R4 first requires evidence that a combination remains positive after severe costs and is not dependent on one month, one or two UTC dates, one spread regime, one realized-volatility regime or one isolated horizon point.

Only combinations that pass every common eligibility gate are ranked. There is no rescue rule for a well-performing combination that fails a gate.

## Eligibility gates

### Sample sufficiency

Eligible sample classes are `standard` and `moderate`. `sparse` combinations are excluded.

```text
aggregate trades >= 60
minimum trades in each calendar month >= 5
```

This does not imply that 60 trades establish profitability. It is the minimum evidence class allowed to enter the comparative ranking.

### Aggregate economics

Every eligible combination must satisfy all of the following:

```text
average default-cost net pips > 0
average severe-cost net pips > 0
default-cost profit factor > 1
severe-cost profit factor > 1
positive default-cost months >= 4 of 6
total default-cost pips excluding the best two UTC Entry dates > 0
```

### Temporal stability

```text
Q1 and Q2 average default-cost net pips: both positive
Q1 and Q2 average severe-cost net pips: both positive
rolling two-month windows: at least 4 of 5 default-positive
rolling two-month windows: at least 3 of 5 severe-positive
rolling three-month windows: all 4 default-positive
rolling three-month windows: at least 3 of 4 severe-positive
```

The windows and period boundaries are those frozen in R3. No new window search is permitted.

### Neighbouring-horizon support

The current horizon must not be an isolated positive point.

```text
all available points in the immediate R3 neighbourhood are default-positive
at least two available neighbourhood points are severe-positive
isolated_default_positive = false
```

Endpoints use their two available points; interior horizons use their three available points. This remains a diagnostic fixed-horizon selection and does not define the R5 Exit.

### Spread and realized-volatility regimes

For the four nonempty spread quartiles:

```text
at least 3 of 4 default-positive
at least 2 of 4 severe-positive
```

For each of RV32 and RV96, warmup regime zero is ignored and the four nonwarmup quartiles must satisfy:

```text
at least 3 of 4 default-positive
at least 2 of 4 severe-positive
```

A regime with zero trades does not count as positive. The evaluator must retain the complete regime grids and report every count.

### Concentration limits

```text
largest absolute UTC-day contribution share <= 0.25
largest absolute calendar-month contribution share <= 0.50
top two UTC dates' share of positive daily pips <= 0.50
maximum absolute long/short contribution share <= 0.90
```

The direction limit diagnoses one-sided dependence without requiring both directions to be independently profitable. Directional strategies are therefore not automatically rejected, but a result almost entirely attributable to one side is excluded.

## Ranking after gates

Only fully eligible combinations receive a selection score.

R4 uses equal-weight percentile-rank aggregation. Each component is ranked among the eligible set with higher values treated as better, and the twelve percentile ranks are averaged.

Components:

1. aggregate average severe-cost net pips;
2. aggregate severe-cost profit factor;
3. minimum quarterly average severe-cost net pips;
4. minimum rolling-three-month average severe-cost net pips;
5. minimum spread-regime average default-cost net pips;
6. minimum RV32 nonwarmup-regime average default-cost net pips;
7. minimum RV96 nonwarmup-regime average default-cost net pips;
8. median anchored percentile for average severe-cost net pips;
9. median neighbouring-horizon average default-cost net pips;
10. total excluding the best two UTC dates divided by aggregate trades;
11. one minus the largest absolute month contribution share;
12. one minus the maximum absolute direction contribution share.

No component receives a larger weight. Percentile aggregation prevents a single metric's numerical scale from dominating the result.

Deterministic tie-break order:

```text
selection score descending
aggregate average severe-cost net pips descending
minimum quarterly average severe-cost net pips descending
total excluding best two UTC dates per trade descending
candidate_id ascending
horizon_bars ascending
```

## Redundancy control

Ranking alone may retain multiple expressions of the same effect. R4 therefore applies the following controls in rank order:

1. at most one horizon for each `definition_sha256`;
2. at most two representatives per family;
3. pairwise redundancy exclusion.

For pairwise redundancy, R4 constructs:

- daily default-cost PnL vectors over every UTC date from January 1 through June 30, filling inactive dates with zero;
- sets of exact Entry timestamps.

The lower-ranked combination is redundant only when both are true:

```text
Pearson correlation of daily default-cost PnL >= 0.85
Entry timestamp Jaccard similarity >= 0.50
```

If daily variance is zero, Pearson correlation is defined as zero for this rule. The higher preregistered rank is retained.

R4 proceeds down the fixed ranking until eight representatives are selected or the eligible list is exhausted. It may not lower thresholds or force family diversity to reach eight.

## Required audit outputs

```text
selection_audit_all_660.csv
eligible_ranked.csv
selected_representatives.csv
redundancy_decisions.csv
eligible_pairwise_similarity.csv.gz
family_selection_summary.csv
r4_acceptance.json
run_metadata.json
```

`selection_audit_all_660.csv` must contain every gate, the aggregate gate result and a machine-readable failure-reason list for every one of the 660 combinations.

`selected_representatives.csv` must contain no more than eight rows, no more than two rows per family and no duplicate `definition_sha256` values.

## Acceptance

R4 passes only if:

1. accepted R2 and R3 Release ZIP digests match;
2. all fixed internal-file digests match;
3. exactly 660 combinations enter the audit;
4. every gate is calculated for all 660 combinations;
5. sparse combinations are never eligible;
6. eligibility equals the conjunction of all frozen gates;
7. the ranking uses only fully eligible combinations;
8. all twelve percentile-rank components have equal weight;
9. all eligible pairwise similarities are reported;
10. the selected set contains no duplicate Entry definition;
11. no family contributes more than two representatives;
12. no retained pair violates both redundancy thresholds;
13. selected rows are a prefix of the deterministic rank after applying only the frozen constraints;
14. no gate is relaxed if fewer than eight are selected;
15. H2 rows parsed equals zero;
16. 2025 access equals false;
17. Entry definitions and horizons remain unchanged;
18. no Exit branch is evaluated;
19. Core promotion remains false;
20. MT4 promotion remains false.

## Next stage

A passing R4 freezes at most eight Entry/horizon representatives for R5 controlled Exit research on 2024 H1. R5 Exit policies and their limits must be separately preregistered before any Exit outcome is opened.
