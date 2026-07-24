# USDJPY B02/F05 all-loss structural stop analysis v1

## Status

`DESCRIPTIVE_COMPLETE_NO_CANDIDATE_FROZEN`

This document records the direct user-requested analysis of structural stop points across the complete B02/F05 trade population for 2023H1, 2023H2, 2024H1 and 2024H2. Fixed-pip stops were excluded. Notion was not used to select the task. No new MT4 execution or 2025 data access occurred.

## Canonical execution identity

- Research evaluation commit: `b1bb2d4fd12d6dc7722f30a6da8ad18c7a387309`
- GitHub Actions run: `30101951761`, attempt `1`
- Evidence artifact: `8599982482`
- Artifact digest: `sha256:203e0bcba871d40e7f3f3863a963fdc24f3f3a782f9cf16206cbdb7ad08bbcd7`
- Result Release: `usdjpy-b02-f05-all-loss-structural-sl-v4`
- Source authority Release: `f05-failed-reclaim-historical-authorities-v1`
- Result JSON SHA-256: `c6b9b1436cb8cdae4d46fe8859d961955cc6d41254f756e050f0b8077b1fd4e9`

The exact source archives and extracted files were SHA-verified before the evaluator was run.

## Population

| Fold | B02 | F05 | Total |
|---|---:|---:|---:|
| 2023H1 | 121 | 367 | 488 |
| 2023H2 | 109 | 363 | 472 |
| 2024H1 | 97 | 331 | 428 |
| 2024H2 | 102 | 392 | 494 |
| **Total** | **429** | **1,453** | **1,882** |

Baseline final-loss trades: **916** — B02 **190**, F05 **726**.

The frozen evaluator produced 1,616 event-counterfactual rows from seven online event definitions.

## Binding conclusions

### 1. A shared B02/F05 structural stop is rejected

The same event has materially different effects across the two strategies. A rule that is beneficial for F05 can damage B02, and pooled totals conceal direction and fold failures. The shared architecture is therefore:

`REJECT_SHARED_STOP_ARCHITECTURE`

### 2. F05 strict failed reclaim is informative but not confirmatory

`SHARED_FAILED_RECLAIM_STRICT_NO_PROFIT_V1`, evaluated within F05:

- triggers: **15**
- baseline losers affected: **11 / 726** (**1.52%**)
- baseline winners affected: **4**
- total delta: **+200.6 pips**
- loser benefit: **+285.5 pips**
- winner damage: **-84.9 pips**
- fold deltas:
  - 2023H1 **+69.3**
  - 2023H2 **+14.1**
  - 2024H1 **+110.7**
  - 2024H2 **+6.5**
- direction totals:
  - Long **+65.2**
  - Short **+135.4**
- one observed fold-direction cell is negative
- removing the best date leaves **+134.4 pips**
- median trigger time: **15 minutes**

This is a real descriptive signal: aggregate delta is positive in all four folds and for both direction totals. It is not frozen as a candidate because it is sparse, damages four baseline winners, and still has one negative fold-direction cell. Its status is:

`PROMISING_EXPLORATORY_MECHANISM_NOT_CONFIRMATORY`

The same strict failed-reclaim event is not transferable to B02:

- triggers: **2**
- total delta: **-16.9 pips**
- one loser improved by **+8.5 pips**
- one winner was damaged by **-25.4 pips**

### 3. No robust B02 structural stop was found in the frozen family

The three B02-specific M15 events did not provide a portable rule:

| Event | Triggers | Total delta | Winner damage | Key failure |
|---|---:|---:|---:|---|
| First M15 re-entry without profit | 22 | -281.0 | -576.2 | six negative fold-direction cells |
| M15 failed reclaim without profit | 4 | -106.0 | -131.1 | negative 2024 results |
| M15 no reclaim for 120 minutes | 3 | +84.3 | 0.0 | only three trades; best-date removal becomes -20.6 |

The B02 conclusion is:

`NO_ROBUST_STRUCTURAL_STOP_FOUND`

### 4. Early M5 re-entry is not a shared stop

The pooled early-M5 event appears positive at **+250.3 pips**, but this is not stable:

- B02: **-149.2**
- F05: **+399.5**
- Long: **-296.8**
- Short: **+547.1**
- winner damage: **-973.0**
- seven negative fold-strategy-direction cells

The positive pooled total is therefore not evidence for a common rule.

### 5. The 120-minute no-reclaim event is too sparse and direction-dependent

The pooled result is **+124.9 pips**, but only 15 trades trigger, the median trigger is 125 minutes, Long is **-16.3**, and two cells are negative. This is not a robust stop architecture.

### 6. Generic profit-armed range failure is overbroad

`REJECTED_AS_OVERBROAD`

`PROFIT_ARMED_M5_RANGE_FAILURE_V1` triggers 1,481 trades:

- loser benefit: **+26,707.9 pips**
- winner damage: **-28,760.1 pips**
- total delta: **-2,052.2 pips**
- B02: **-462.0**
- F05: **-1,590.2**
- Long: **-1,191.9**
- Short: **-860.3**

It detects deterioration in many losing trades, but truncates winners even more. It is rejected as an executable termination rule.

## Interpretation

The evidence does not support one universal structural stop for B02 and F05. The strategies require separate termination architectures.

For F05, strict failed reclaim is the only mechanism in this frozen family that retains positive aggregate delta in every fold and in both direction totals. It should remain a descriptive research lead, not an implementation candidate.

For B02, none of the tested re-entry/reclaim events is sufficiently broad and stable. The positive three-trade M15 no-reclaim result is concentration, not a reusable rule.

## Decision boundary

- candidate frozen: **false**
- implementation authorized: **false**
- MT4 authorized: **false**
- 2025H1/H2 authorized or accessed: **false**
- fixed-pip stop evaluated: **false**
- further threshold expansion in this run: **not performed**

No HYP-023 or HYP-024 research was reopened or used as the task authority.
