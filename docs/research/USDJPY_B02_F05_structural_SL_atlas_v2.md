# USDJPY B02/F05 comprehensive structural-stop atlas v2

## Status

`ATLAS_COMPLETE_NO_ROBUST_FAMILY`

This report records the direct user-requested expansion of the B02/F05 structural-stop research. The atlas did not reuse Notion as a task selector and did not reopen HYP-023, HYP-024 or HYP-025.

The result does **not** invalidate the separately validated `F05_FAILED_RECLAIM_BASIC_V1`. That exact candidate passed its frozen Research historical portfolio and raw-tick gates in Run `30104463746`. Atlas v2 searched for additional structural families and broader transfer rules.

## Canonical execution

- Research execution commit: `37833fe29cb5cfa13bcfb1e6896e0dcb584aa926`
- GitHub Actions Run: `30106687299`, attempt 1
- Artifact: `8602116809`
- Artifact digest: `sha256:167064e9a599a83171cb6cc825609911cf7b804d0b9adec6a5750eab06b32369`
- Release: `usdjpy-b02-f05-structural-sl-atlas-v2`
- Artifact `result_v2.json` SHA-256: `fb8ac1ed5eea8e75123f0114cd1f084dc64e1152b02bac96cfa8ad86268b0a1f`
- Independent local reproduction: semantic JSON exact after removing only Run identity fields

## Population and search scale

- Trades: 1,882
- Baseline final-loss trades: 916
- B02: 429 trades / 190 losers
- F05: 1,453 trades / 726 losers
- Deterministic candidates: 303
- Structural families: 12
- Deterministic event-counterfactual rows: 354,304
- Checkpoint feature snapshots: 9,410
- M5 trajectory-shape rows: 9,397
- Deterministic nested-CV rows: 144
- Supervised nested-CV rows: 240
- Unsupervised nested-CV rows: 72

The deterministic families covered breakout/entry re-entry persistence, failed-reclaim sequences, repeated crossing/chop, normalized MFE giveback, stagnation giveback, rolling-channel failure, adverse runs, CUSUM reversal, rolling-slope deterioration, persistent underwater time, adverse volatility shock and pre-entry range invalidation.

The statistical layers included leave-one-fold-out selection, date-level Wilcoxon tests with Benjamini-Hochberg correction, +1/+2-pip exit stress, 1/2/5-minute execution delays, best-date removal, fold/direction/strategy/month breadth, four supervised model classes and KMeans trajectory clustering.

## Binding result

No additional candidate or method passed the frozen discovery gates:

- exact deterministic candidates: `0`
- nested-CV deterministic families: `0`
- nested-CV supervised models: `0`
- nested-CV trajectory clusters: `0`
- shared B02/F05 structural stop: rejected
- new B02 rule: none
- new F05 family: none
- candidate frozen: false
- implementation authorized: false

## Gate attrition

### ALL scope

Out of 303 candidates:

- total delta positive: 16
- +1-pip severe delta positive: 8
- 2-minute delayed delta positive: 13
- all-fold default nonnegative: 0
- all-fold severe nonnegative: 0
- both directions nonnegative: 3
- best-date-removed positive: 5
- winner-damage gate: 2
- month-breadth gate: 7
- BH-adjusted date q <= 0.10: 0

### B02 scope

Out of 303 candidates:

- total delta positive: 68
- +1-pip severe delta positive: 44
- all-fold default nonnegative: 2, but one had zero triggers and the other had only two triggers
- both directions nonnegative: 21
- winner-damage gate: 7
- month-breadth gate: 16
- BH-adjusted date q <= 0.10: 0

No B02 candidate combined adequate support, all-fold stability, winner retention, temporal breadth and corrected significance.

### F05 scope

Out of 303 candidates:

- total delta positive: 8
- +1-pip severe delta positive: 5
- all-fold default nonnegative: 1
- all-fold severe nonnegative: 0
- both directions nonnegative: 2
- winner-damage gate: 1
- month-breadth gate: 3
- BH-adjusted date q <= 0.10: 0

## Principal near-miss: F05 repeated-crossing/chop

Definition:

- M5
- 30-minute rolling window
- at least four breakout-level crossings
- current displacement no greater than 0.25 pre-entry normalized range units

Observed full-sample overlay:

- triggers: 256
- loser triggers: 175
- winner triggers: 81
- loser benefit: +4,227.4 pips
- winner damage: -2,921.5 pips
- total delta: +1,305.9 pips
- +1-pip severe delta: +1,049.9 pips
- +2-pip severe delta: +793.9 pips
- 2-minute delayed delta: +1,330.4 pips
- 5-minute delayed delta: +1,239.5 pips
- fold totals: 2023H1 +899.5 / 2023H2 +135.3 / 2024H1 +216.0 / 2024H2 +55.1
- fold severe totals: 2023H1 +833.5 / 2023H2 +67.3 / 2024H1 +155.0 / 2024H2 -5.9
- Long +1,051.2 / Short +254.7
- positive active months: 14 / 24
- best-date-removed delta: +1,115.4
- raw date p-value: 0.0140
- BH-adjusted q-value: 0.5208
- median trigger time: 147.5 minutes

Nested leave-one-fold-out selection chose this candidate for three holdouts:

- 2023H2: +135.3 default / +67.3 severe
- 2024H1: +216.0 / +155.0
- 2024H2: +55.1 / -5.9
- 2023H1 holdout: no candidate in the family passed the three-fold training gate

It was rejected for five independent reasons:

1. 2024H2 severe-cost fold became negative.
2. Winner damage exceeded 60% of loser benefit.
3. Positive-month ratio was 14/24, below 60%.
4. BH-adjusted date evidence was not significant.
5. No connected neighboring parameter cell passed the preliminary gates.

The aggregate number is therefore not sufficient evidence for an implementable rule.

## Supervised model results

Models used only information available at the checkpoint and selected probability thresholds using the three training folds.

### F05 near-misses

- 15-minute L2 logistic:
  - selected in 2/4 folds
  - 21 holdout triggers
  - +387.5 pips default / +366.5 severe
  - minimum holdout fold -22.9 pips
  - winner damage -271.0 pips

- 60-minute L2 logistic:
  - selected in 3/4 folds
  - 32 holdout triggers
  - +113.8 pips default / +81.8 severe
  - minimum holdout fold -3.7 pips
  - winner damage -363.4 pips

Neither generalized across all folds.

### B02 model instability

The largest pooled B02 model result was the 5-minute histogram gradient booster:

- selected in 4/4 training procedures
- 164 holdout triggers
- pooled +718.4 pips / +554.4 severe
- minimum holdout fold -843.1 pips
- winner damage -3,784.5 pips

This is a strong example of pooled performance masking fold reversal. No B02 model passed.

## Unsupervised trajectory clustering

KMeans trajectory clusters produced no all-fold survivor.

The only selected F05 clusters were harmful in their holdout folds:

- 30-minute, k=3: one selected fold, 69 triggers, -1,010.8 pips
- 60-minute, k=5: one selected fold, 38 triggers, -354.9 pips

Unsupervised shape similarity did not isolate a portable terminal-loss state.

## Descriptive trajectory evidence

The full path still contains strong winner/loser information, but it is mostly a late outcome descriptor rather than a portable online stopping rule.

### B02 medians

- underwater fraction: winners 0.1697 / losers 0.8809, rank-biserial -0.9064
- peak-MFE time: winners 490m / losers 101m, rank-biserial 0.7720
- final MFE: winners 62.9 / losers 17.0 pips, rank-biserial 0.7359
- final MAE: winners -19.0 / losers -65.15 pips, rank-biserial 0.7541
- breakout crossings: winners 6 / losers 12

### F05 medians

- underwater fraction: winners 0.1399 / losers 0.8713, rank-biserial -0.8392
- peak-MFE time: winners 392m / losers 60m, rank-biserial 0.7414
- final MFE: winners 50.3 / losers 12.7 pips, rank-biserial 0.7263
- final MAE: winners -14.6 / losers -46.85 pips, rank-biserial 0.7067
- breakout crossings: winners 6 / losers 10

By contrast, first positive time and first breakout re-entry time did not separate winners and losers materially. The useful information accumulates over the path, but attempts to turn it into fixed deterministic, supervised or clustered stopping policies did not generalize.

## Interpretation

Three conclusions are supported:

1. **B02 and F05 should not share one generic structural stop.**
2. **Broad path deterioration is real but too heterogeneous for a single frozen stop family.**
3. **The separately validated F05 strict failed-reclaim sequence remains exceptional because it uses a narrow event ordering and full portfolio/raw-tick validation rather than broad path classification.**

The atlas also shows why aggregate loss savings are misleading: several candidates and models produced large pooled gains while failing one fold, damaging winners, concentrating in months/dates or collapsing under severe costs.

## Scientific boundaries

This atlas evaluated counterfactual exits on the accepted trade population. It did not perform a full accepted-signal re-admission/margin replay for new candidates, because no candidate passed discovery. It also did not perform raw-tick event-order audits, MT4 parity or 2025 access for new candidates.

- fixed-pip stop evaluated: false
- full admission portfolio replay for new candidates: false
- raw-tick audit for new candidates: false
- MT4 accessed by atlas: false
- 2025 H1/H2 accessed: false
- candidate frozen: false
- implementation authorized: false

## Evidence files

The immutable Release and artifact contain:

- `result_v2.json`
- `deterministic_event_ledger_v2.csv.gz`
- `deterministic_candidate_metrics_v2.csv`
- `deterministic_nested_cv_v2.csv`
- `supervised_nested_cv_v2.csv`
- `unsupervised_nested_cv_v2.csv`
- `trajectory_diagnostics_v2.csv`
- protocol, evaluator, log and package manifests
