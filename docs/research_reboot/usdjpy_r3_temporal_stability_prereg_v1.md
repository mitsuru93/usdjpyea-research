# USDJPY R3 Temporal-Stability Preregistration v1

## Decision

R3 applies one fixed diagnostic framework to all 660 accepted R2 Entry/horizon combinations. It does not select a representative, change an Entry definition, change a horizon, or define an operational Exit.

```text
candidate/horizon combinations: 660
Entry definitions: 60
fixed horizons: 11
research block: 2024-01-01 through 2024-07-01 exclusive
candidate selection: prohibited
H2 access: prohibited
2025 access: prohibited
Core promotion: false
MT4 promotion: false
```

Authoritative configuration:

```text
configs/research/usdjpy_r3_temporal_stability_v1.json
```

Authoritative evaluator:

```text
tools/run_usdjpy_r3_temporal_stability_v1.py
```

## Inputs

R3 accepts only:

1. accepted R2 Release `usdjpy-r2-horizon-surface-v1`;
2. its deterministic trade ledger `candidate_horizon_trades.csv.gz`;
3. its 660-row `candidate_horizon_summary.csv`;
4. canonical M15 bars from Release `usdjpy-r0-canonical-2024-v1`;
5. the fixed market-session configuration.

Input digests are frozen in the R3 configuration. R3 does not regenerate R1 signals or R2 returns.

## Fixed temporal diagnostics

Every combination is reported over the following complete grids:

### Calendar months

```text
2024-01, 2024-02, 2024-03, 2024-04, 2024-05, 2024-06
rows: 660 × 6 = 3,960
```

### Quarters

```text
2024-Q1: January-March
2024-Q2: April-June
rows: 660 × 2 = 1,320
```

### Rolling two-month blocks

```text
Jan-Feb, Feb-Mar, Mar-Apr, Apr-May, May-Jun
rows: 660 × 5 = 3,300
```

### Rolling three-month blocks

```text
Jan-Mar, Feb-Apr, Mar-May, Apr-Jun
rows: 660 × 4 = 2,640
```

### Anchored development blocks

```text
Jan-Feb, Jan-Mar, Jan-Apr, Jan-May, Jan-Jun
rows: 660 × 5 = 3,300
```

For each anchored block, R3 reports descending minimum ranks and percentiles for:

- average default-cost net pips;
- default-cost profit factor;
- average severe-cost net pips;
- severe-cost profit factor.

Anchored ranks are diagnostics. They do not constitute a selection rule.

## Fixed regime diagnostics

### Spread regimes

Spread quartile boundaries are calculated from all eligible canonical H1 M15 Entry bars outside the project-wide hard no-trade window.

```text
regimes: quartiles 1-4
rows: 660 × 4 = 2,640
```

### Realized-volatility regimes

Realized volatility is the population standard deviation (`ddof=0`) of M15 close-to-close returns in pips.

```text
windows: 32 and 96 M15 bars
value assigned to Entry: rolling value ending on the completed signal bar
quartile source: eligible canonical H1 Entry bars
```

The canonical bundle begins on January 2, 2024. Consequently, initial Entries can lack a full 32- or 96-bar history. These Entries are not deleted. They are assigned to fixed regime `0 = warmup unavailable`.

```text
regimes per RV window: 0, 1, 2, 3, 4
rows per RV window: 660 × 5 = 3,300
```

The quartile edges are outputs of the fixed algorithm, not parameters selected from candidate performance.

## Direction and concentration diagnostics

R3 reports a complete long/short attribution grid:

```text
rows: 660 × 2 = 1,320
```

For every Entry/horizon combination, concentration reporting includes:

- active Entry dates;
- highest and highest-two UTC Entry-date contribution;
- share of positive daily pips contributed by the best one and two days;
- largest absolute daily contribution share;
- largest absolute monthly contribution share;
- long-trade share;
- maximum absolute long/short contribution share.

These fields diagnose whether aggregate performance depends on a narrow date, month or direction.

## Neighbouring-horizon diagnostics

For each of the eleven ordered horizons, R3 uses the immediately adjacent grid points where available. Endpoints therefore have two-point neighbourhoods and interior horizons have three-point neighbourhoods.

R3 reports:

- number of default-positive horizons in the neighbourhood;
- number of severe-positive horizons in the neighbourhood;
- minimum and median neighbouring average default return;
- minimum neighbouring average severe return;
- whether all available neighbouring points are default-positive;
- whether all available neighbouring points are severe-positive;
- whether the current positive point is isolated;
- whether the current point is a local diagnostic maximum.

A local maximum is not selected as an Exit. Neighbouring support remains descriptive until the R4 selection requirements are separately frozen.

## Sample classes

R3 assigns every combination to one fixed sample class:

```text
standard:
  aggregate trades >= 120
  minimum monthly trades >= 12

moderate:
  aggregate trades >= 60
  minimum monthly trades >= 5

sparse:
  all remaining combinations
```

A sparse classification does not automatically delete a candidate in R3. It identifies the evidentiary class that R4 must account for.

## Required metrics

Each applicable temporal or regime block reports:

- trades;
- win rate;
- average and total default-cost net pips;
- default-cost profit factor;
- average and total severe-cost net pips;
- severe-cost profit factor;
- median default-cost net pips;
- 5th and 95th percentile default-cost net pips.

## Required outputs

```text
temporal_monthly.csv                 3,960 rows
temporal_quarterly.csv               1,320 rows
rolling_2month.csv                   3,300 rows
rolling_3month.csv                   2,640 rows
anchored_ranking.csv                 3,300 rows
spread_regime.csv                    2,640 rows
rv32_regime.csv                      3,300 rows
rv96_regime.csv                      3,300 rows
direction_attribution.csv            1,320 rows
horizon_neighborhood.csv               660 rows
concentration.csv                      660 rows
sample_classes.csv                     660 rows
entry_regime_map.csv.gz       one row per unique Entry timestamp
regime_edges.json
r3_acceptance.json
run_metadata.json
```

All grids retain all 660 R2 combinations, including zero-trade cells within a time or regime block.

## Research firewall

R3 may not:

- add, remove or modify an Entry definition;
- add, remove or modify a horizon;
- introduce an Exit branch;
- use H2 information;
- access any 2025 artifact;
- emit a shortlist or promotion decision;
- promote a candidate to Core or MT4.

R3 is internal H1 development analysis. Its output can inform only the separately preregistered R4 representative-selection rules.

## Acceptance

R3 passes only if:

1. R2 Release and internal trade/summary digests match;
2. R0 Release and canonical M15 digest match;
3. all 383,078 R2 trade rows are loaded;
4. all 660 candidate/horizon combinations remain present;
5. all required temporal grids have their exact row counts;
6. spread, RV32 and RV96 regime grids have their exact row counts;
7. direction, neighbourhood, concentration and sample-class outputs each have their exact row counts;
8. the Entry regime map has unique Entry timestamps;
9. every R2 trade has spread, RV32 and RV96 regime labels;
10. RV32 and RV96 warmup regime `0` is present;
11. the Entry-regime gzip output is byte deterministic;
12. H2 rows parsed equals zero;
13. 2025 access equals false;
14. no selection or promotion decision is emitted;
15. Core and MT4 promotion remain false.

## Next stage

A passing R3 unblocks design of the R4 common selection requirements. It does not itself select any of the maximum-eight Entry/horizon representatives.
