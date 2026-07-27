# USDJPY-HYP-028 — Shock Failure Regime Discriminator Study Result v1

## Decision

**`NO_PORTABLE_CANDIDATE`**

The study confirmed that `F_CONTINUATION_RESUMPTION` and `H_SUSTAINED_REVERSAL` are economically distinct lifecycle mechanisms in the 2023H1–2024H2 development population. It did **not** show that the frozen entry-decision-time feature catalog can distinguish them portably.

No candidate is frozen. No Core implementation contract, Core source change, MT4 economic evaluation, production authorization, live-order authorization or external-gate reservation follows from this result.

## Scientific boundary

- New independent hypothesis: `USDJPY-HYP-028`.
- Family: `S_SHOCK_FAILURE_REGIME_DISCRIMINATION`.
- Parent fixed candidate: `B_EXECUTABLE_T0_8BAR`, unchanged and still `REJECTED_FOR_PRODUCTION_AND_PORTABLE_CORE_ADOPTION`.
- Development, feature selection, model selection, threshold selection and candidate selection: `2023H1`, `2023H2`, `2024H1`, `2024H2` only.
- `2025H1/H2`: consumed postmortem comparison evidence only. The selection evaluator had no 2025 input. The workflow downloaded the 2025 Release only after `final_decision.json` existed.
- `D_PROFIT_THEN_GIVEBACK` was measured as a secondary class. No exit rule was optimized and no entry/exit hybrid candidate was created.

## Evidence authority

- Research PR: `#323`.
- Canonical PR Run: `30258797448`.
- Artifact ID: `8650040013`.
- Artifact digest: `sha256:25be1e2b42f5f95870c8f0d3d24591f422e5b66cada601744c3ef691323e81ff`.
- Artifact created at: `2026-07-27T10:39:18Z`.
- PR head containing the canonical comparison fix: `577c68d87969abd53bebde51bfde52d8d077b86f`.
- Planned immutable Release: `usdjpy-shock-failure-regime-discriminator-v1`.
- Start Research main: `34b2dcb47d735c3e78036c0bcd0d5ed45cd9e6fa`.
- Read-only Core main: `151d84b0dca3fe92a59663f56fd458727de2dbe0`.

The artifact `SHA256SUMS` readback passed. Evidence includes the hypothesis protocol, preregistration, source manifest, reconstructed lifecycle ledger, feature ledger, timestamp audit, leakage audit, class distributions, fold metrics, univariate results, LOFO predictions, candidate metrics, threshold stability, stress tests, event concentration, source parity, machine-readable final decision and human-readable report.

## Lifecycle definition and reproducibility audit

The same post-entry path taxonomy used by the r2 postmortem was applied to all 114 frozen Phase 2 opportunities:

- `D_PROFIT_THEN_GIVEBACK`: the trade becomes meaningfully profitable but the fixed lifecycle gives the profit back before exit.
- `F_CONTINUATION_RESUMPTION`: after the apparent failure and entry, price resumes the original shock direction strongly enough to invalidate the reversal thesis and produce the main loss mechanism.
- `H_SUSTAINED_REVERSAL`: after the apparent failure and entry, the move away from the original shock direction persists and creates the main winner class.

The reconstruction used exact Bid/Ask Raw Tick paths, the frozen shock and failure directions, executable entry chronology and the fixed 8-bar / 120-minute lifecycle. It preserved the historical approximate labels and emitted a separate difference ledger instead of overwriting them.

Audit result:

- Opportunities reconstructed: `114/114`.
- Lookahead violations: `0`.
- Historical approximation differences: `3`.
  - One 2023H2 event changed from approximate `H` to exact `B_DELAYED_REVERSAL`.
  - One 2024H1 event changed from approximate `A` to exact `C_INSUFFICIENT_REVERSAL`.
  - One 2024H2 event changed from approximate `A` to exact `E_TIMEOUT_TRUNCATION`.
- Duplicate and event identity contracts remained inherited from the frozen Phase 2 authority.
- The exact labels were used only as outcomes for analysis, never as predictors.

## Development-period mechanism

Across 2023H1–2024H2:

| Lifecycle class | Events | Share | Net JPY |
|---|---:|---:|---:|
| `B_DELAYED_REVERSAL` | 1 | 0.88% | +117 |
| `C_INSUFFICIENT_REVERSAL` | 1 | 0.88% | -184 |
| `D_PROFIT_THEN_GIVEBACK` | 29 | 25.44% | +1,141 |
| `E_TIMEOUT_TRUNCATION` | 1 | 0.88% | -318 |
| `F_CONTINUATION_RESUMPTION` | 37 | 32.46% | **-8,171** |
| `H_SUSTAINED_REVERSAL` | 45 | 39.47% | **+19,917** |

The core postmortem mechanism therefore existed before 2025. `F` was the main loss class and `H` the main profit class.

### Fold breakdown

| Fold | `F` events / net | `H` events / net | `D` events / net | Other |
|---|---:|---:|---:|---:|
| 2023H1 | 7 / -1,746 | 9 / +4,349 | 5 / +173 | — |
| 2023H2 | 15 / -2,866 | 10 / +2,168 | 9 / -81 | `B`: 1 / +117 |
| 2024H1 | 8 / -921 | 12 / +2,626 | 9 / +632 | `C`: 1 / -184 |
| 2024H2 | 7 / -2,638 | 14 / +10,774 | 6 / +417 | `E`: 1 / -318 |

The weak 2023H2 fold had the same central failure mechanism later observed in 2025: continuation resumption was more frequent and more negative than sustained reversal was positive.

### Side breadth

- Long `F`: 23 events / `-4,239`; Long `H`: 31 / `+10,710`.
- Short `F`: 14 / `-3,932`; Short `H`: 14 / `+9,207`.

Both mechanisms existed on both sides. The development data did not support a 2025-derived Short prohibition.

### Session breadth

- London: `F` 5 / `-610`; `H` 5 / `+1,294`.
- London/NY overlap: `F` 18 / `-3,201`; `H` 20 / `+8,519`.
- New York: `F` 6 / `-1,190`; `H` 6 / `+1,262`.
- Tokyo: `F` 6 / `-1,574`; `H` 13 / `+8,289`.
- Transition: `F` 2 / `-1,596`; `H` 1 / `+553`.

Both mechanisms were distributed across sessions. The development data did not support a 2025-derived London prohibition.

## Consumed 2025 comparison

Only after selection was frozen, the r2 postmortem lifecycle was read and explicitly restricted to `2025H1/H2`, totaling 47 MT4 events:

| Lifecycle class | Events | Share | Net JPY |
|---|---:|---:|---:|
| `D_PROFIT_THEN_GIVEBACK` | 12 | 25.53% | -89 |
| `F_CONTINUATION_RESUMPTION` | 21 | 44.68% | -5,975 |
| `H_SUSTAINED_REVERSAL` | 14 | 29.79% | +4,787 |

This confirms mechanism continuity, but it is not candidate validation and is not a clean holdout.

## Feature timestamp contract and leakage audit

Every predictor was frozen to information available no later than `entry_decision_utc`:

- M15 shock and failure bars had to be completed.
- M1/M5 inputs, where derivable, had to end no later than the decision timestamp.
- H1/H4 predictors used only completed higher-timeframe bars; the current incomplete bar was forbidden.
- Raw Tick predictor windows used timestamps strictly before the decision boundary.
- The executable entry tick remained execution/lifecycle evidence and was not used as a model predictor.
- Post-entry MFE, MAE, realized P/L, time-to-event fields and lifecycle labels were outcomes only.
- Oracle labels as predictors: `false`.
- Post-entry MFE/MAE/P&L as predictors: `false`.
- 2025 loaded by selection evaluator: `false`.
- Timestamp/leakage audit: `PASS`.

## Feature separation

### Most informative feature

`shock_duration_bars` was the only materially separated single feature:

- `H` median: `2` bars.
- `F` median: `1` bar.
- AUC: `0.6345`.
- Permutation p-value: `0.0240`.
- Fold direction consistency: `1.00`.

Longer shocks were more often followed by sustained reversal than one-bar impulses. This was a real descriptive association, but it was not strong enough to support a portable permission rule.

### Weak secondary features

- Failure-window entry-direction tick imbalance: absolute AUC `0.574`, p `0.267`.
- H4 EMA20 slope signed to shock direction: AUC `0.566`, p `0.289`.
- H1 EMA20 slope signed to shock direction: AUC `0.562`, p `0.333`.
- Retracement ratio: AUC `0.545`, p `0.505`.

### Ineffective or near-chance features

- ATR-normalized shock ratio: AUC `0.534`, p `0.621`.
- Shock-window directional tick imbalance: AUC `0.508`, p `0.904`.
- Failure-window acceleration: AUC `0.508`, p `0.888`.
- Failure-body ratio: AUC `0.505`, p `0.932`.
- Failure close relative to shock origin: AUC `0.504`, p `0.946`.

The tested continuation-pressure and higher-timeframe summaries did not provide fold-portable separation.

## Frozen candidate catalog

The finite catalog was committed before outcomes:

1. `RD_LOGIT_10F_V1`: balanced L2 logistic state score.
2. `RD_TREE_D2_V1`: depth-two permission tree.
3. `RD_RANK6_V1`: equal-weight monotonic rank score.

Thresholds came only from the preregistered grid `0.35–0.65`. Outer-fold predictions were Leave-One-Fold-Out; held-out folds did not select their own model or threshold.

The unfiltered fixed candidate baseline was:

- 114 trades.
- Net `+12,502 JPY`.
- PF `2.381`.
- MDD `1,555 JPY`.

A discriminator therefore had to improve the existing positive development economics, not merely produce a positive accepted subset.

## Candidate results

### `RD_TREE_D2_V1` — best diagnostic, rejected

- Threshold: `0.35`.
- Accepted / rejected: `69 / 45`.
- Accepted net: `+10,521 JPY`.
- PF: `3.401`.
- MDD: `1,232 JPY`.
- Recovery factor: `8.54`.
- Net benefit versus unfiltered baseline: **`-1,981 JPY`**.
- Loser benefit: `+4,673 JPY`.
- Winner damage: `-6,654 JPY`.
- `H` count retention: `60.0%`.
- `H` profit retention: `67.93%`, below the 70% gate.
- `F` count rejection: `45.95%`.
- `F` loss rejection: `48.81%`.
- Nonnegative-benefit folds: `2/4`.
- Minimum fold benefit: `-2,895 JPY`.
- OOF AUC: `0.5153`.
- Split/model stability: `0.25`.

LOFO results:

| Held-out fold | Accepted trades | Accepted net | Net benefit |
|---|---:|---:|---:|
| 2023H1 | 12 | +3,001 | +225 |
| 2023H2 | 23 | +562 | +1,224 |
| 2024H1 | 9 | +973 | -1,180 |
| 2024H2 | 14 | +5,340 | -2,895 |

The filter helped the two 2023 folds but destroyed too much 2024 winner profit. In 2024H1 it retained only 25.29% of sustained-reversal profit; in 2024H2, 61.54%.

Side net benefit:

- Long: `-429 JPY`.
- Short: `-1,552 JPY`.

Session net benefit:

- London: `-116 JPY`.
- London/NY overlap: `-1,345 JPY`.
- New York: `+428 JPY`.
- Tokyo: `-948 JPY`.
- Transition: `0 JPY`.

The all-development diagnostic tree used shock duration, failure close relative to shock origin and failure-body ratio, but its top split changed materially across LOFO fits. It is not a candidate rule.

### `RD_RANK6_V1` — rejected

- Threshold: `0.45`.
- Accepted trades: `78`.
- Net: `+9,670 JPY`.
- PF: `2.642`.
- MDD: `1,488 JPY`.
- Net benefit: **`-2,832 JPY`**.
- `H` profit retention: `71.35%`.
- `F` loss rejection: `35.01%`.
- Nonnegative-benefit folds: `1/4`.
- Minimum fold benefit: `-2,301 JPY`.
- OOF AUC: `0.5526`.
- Score stability: `0.958`.

The score was mechanically stable but not economically portable.

### `RD_LOGIT_10F_V1` — rejected

- Threshold: `0.40`.
- Accepted trades: `68`.
- Net: `+9,262 JPY`.
- PF: `2.645`.
- MDD: `1,176 JPY`.
- Net benefit: **`-3,240 JPY`**.
- `H` profit retention: `70.14%`.
- `F` loss rejection: `37.43%`.
- Nonnegative-benefit folds: `1/4`.
- Minimum fold benefit: `-1,503 JPY`.
- OOF AUC: `0.5465`.
- Model stability: `0.825`.

It met the narrow H-retention threshold but failed fold breadth, economic benefit and predictive separation.

## Threshold stability

For the best diagnostic tree, every fixed threshold had negative net benefit:

| Threshold | Accepted net | Net benefit | Nonnegative folds | Minimum fold benefit |
|---:|---:|---:|---:|---:|
| 0.35 | +10,521 | -1,981 | 2 | -2,895 |
| 0.40 | +10,521 | -1,981 | 2 | -2,895 |
| 0.45 | +7,781 | -4,721 | 2 | -5,635 |
| 0.50 | +7,781 | -4,721 | 2 | -5,635 |
| 0.55 | +7,283 | -5,219 | 2 | — |
| 0.60 | +4,790 | -7,712 | 1 | — |
| 0.65 | +3,241 | -9,261 | 1 | — |

There was no favorable threshold neighborhood. Selecting a different nearby cut would not repair the result.

## Stress and concentration

The best diagnostic accepted subset remained positive under implementation stresses:

- Spread +1 pip: `+9,831 JPY`.
- Spread +2 pips: `+9,141 JPY`.
- Execution delay +5 seconds: `+10,999 JPY`.
- Execution delay +15 seconds: `+11,331 JPY`.
- Top 1 event removed: `+7,422 JPY`.
- Top 3 removed: `+5,091 JPY`.
- Top 5 removed: `+3,816 JPY`.

These results do not rescue the candidate. The correct counterfactual is the already-positive unfiltered candidate. The filter's net benefit remained negative because winner damage exceeded avoided losses.

Bootstrap and permutation diagnostics reinforced the rejection:

- Net-benefit bootstrap 95% interval: `[-7,232.3, +2,544.0] JPY`.
- Probability of positive net benefit: `0.2122`.
- Predictive permutation p-value: `0.3968`.

## Why entry-time discrimination failed

The lifecycle classes are real, but the tested summaries do not encode enough stable state information at the original decision boundary:

1. Shock duration showed a modest, repeatable association, but not enough discrimination by itself.
2. Tick-pressure, retracement and higher-timeframe slope effects were small and changed in importance across folds.
3. The shallow tree improved pooled PF by rejecting losing trades, but it rejected even more winner profit.
4. The strongest damage appeared in the strong 2024 folds, so a pooled or 2023-focused interpretation would be misleading.
5. OOF AUCs of `0.515–0.553` were effectively near chance for a portable classifier.
6. Neither side nor session breadth supported an exception architecture.

## Formal rejection reasons

Every candidate failed at least the following:

- Three-of-four nonnegative fold-benefit gate.
- Minimum-fold benefit gate.
- Side breadth/economic gate.
- Threshold-neighborhood gate.
- OOF AUC gate.

The diagnostic tree additionally failed sustained-reversal retention and model-stability gates.

## Authorization and next step

- Portable candidate: **none**.
- Candidate ID/rule to implement: **none**.
- Core implementation contract: **not authorized**.
- Research/Core parity: **not authorized**.
- MT4 economic evaluation: **not authorized**.
- 2025 clean holdout: **prohibited**.
- Production/live orders: **not authorized**.
- Next external gate period: **not reserved**, because no candidate was frozen.

A successor Shock Failure study must be a materially different hypothesis and representation, such as an ordered state-transition or event-sequence model with a new preregistration. It must not be a nearby threshold, feature-subset, side or session repair of this closed catalog. A 2026-or-later period may be reserved only after a successor candidate is fully frozen before any access and the necessary data are complete and immutable.
