# B02/F05 2023–2024 Winner–Loser Factor Analysis v1

## 1. Objective

This report performs factor diagnosis before hypothesis formation. It compares winning and losing baseline trades for B02 and F05 across four development/falsification folds:

- 2023 H1
- 2023 H2
- 2024 H1
- 2024 H2

No 2025 trade identity or result was used to choose a factor, threshold, side, or mechanism. Historical 2024 is unchanged. The 2023 data were transformed into the historical-2024 clock contract and exactly reconciled to the accepted cross-year baseline.

## 2. Source and lineage reconciliation

- Research main: `9072214a5110dc5f41935063cb2af3878072f5b6`
- 2023 accepted historical-2024-compatible baseline:
  - opened 961, closed 960
  - B02 closed 230, net JPY -12,459
  - F05 closed 730, net JPY +3,180
  - portfolio net JPY -9,279
  - shifted M15 bars 1,543, duplicates 0
- 2024 H1:
  - B02 97, net JPY +9,554
  - F05 331, net JPY +13,243
- 2024 H2:
  - B02 102, complete-marked net JPY +15,627
  - F05 392, complete-marked net JPY +22,482

The common analysis population contains 1,882 trades. The one open 2024 H2 F05 position is included using the accepted period-end mark of JPY -249.

## 3. Common feature contract

Only values observable at entry or earlier were used for entry-factor analysis:

- side-aligned M15 open movement over 15m, 30m, 1h, and 4h;
- prior 1h movement and 1h acceleration;
- open-path length, range, efficiency, and aligned-step fraction over 1h and 4h;
- 4h range position and recent-path expansion;
- reference-range width;
- signal-close outside distance;
- next-M15-open executable outside distance and retention from signal close;
- direction, UTC hour, session;
- pre-existing same/opposite exposure, simultaneous peers, and stack ordinal.

For cross-fold comparability, these are based on M15 executable open marks. The accepted 2024 H2 source does not expose the full signal-bar OHLC feature set available in the 2024 H1 Atlas. Therefore H1-only wick/body/ATR fields are not used for four-fold claims.

Outcome-path diagnostics use M15-open executable marks at 15m, 30m, 60m, 120m, and 240m, plus MFE, MAE, and path class. These are diagnostic outcomes, not entry information.

## 4. Strategy and fold results

| Strategy   | Fold   |   Trades |   Wins |   Win rate |    Net JPY |    PF |   Avg win JPY |   Avg loss JPY |
|:-----------|:-------|---------:|-------:|-----------:|-----------:|------:|--------------:|---------------:|
| B02        | 2023H1 |      121 |     61 |      0.504 | -14381.000 | 0.651 |       439.410 |       -686.417 |
| B02        | 2023H2 |      109 |     57 |      0.523 |   1922.000 | 1.082 |       443.316 |       -448.981 |
| B02        | 2024H1 |       97 |     57 |      0.588 |   9554.000 | 1.732 |       396.737 |       -326.500 |
| B02        | 2024H2 |      102 |     64 |      0.627 |  15627.000 | 1.707 |       589.625 |       -581.816 |
| F05        | 2023H1 |      367 |    170 |      0.463 | -11671.000 | 0.860 |       422.300 |       -423.665 |
| F05        | 2023H2 |      363 |    179 |      0.493 |  14851.000 | 1.255 |       407.994 |       -317.923 |
| F05        | 2024H1 |      331 |    178 |      0.538 |  13243.000 | 1.280 |       340.371 |       -313.530 |
| F05        | 2024H2 |      392 |    200 |      0.510 |  22482.000 | 1.261 |       543.420 |       -448.969 |

The annual 2023 deficit is not homogeneous. Both strategies fail in 2023 H1 and recover in 2023 H2:

- B02: 2023 H1 JPY -14,381, then 2023 H2 JPY +1,922.
- F05: 2023 H1 JPY -11,671, then 2023 H2 JPY +14,851.

Thus the 2023 annual B02/F05 summary masks a first-half regime failure shared by both mechanisms.

## 5. Winner versus loser pre-entry continuous features

Positive rank-biserial Δ means winners tend to have a higher feature value. A material portable factor was predeclared here as the same direction in all four folds with `|Δ| >= 0.10` in every fold.

| Strategy   | Feature                          |   Winner median |   Loser median |   Rank-biserial Δ |   BH q |
|:-----------|:---------------------------------|----------------:|---------------:|------------------:|-------:|
| B02        | 4h side-aligned open move (pips) |          29.400 |         30.000 |             0.039 |  0.648 |
| B02        | 1h acceleration (pips)           |          15.400 |         14.550 |             0.070 |  0.539 |
| B02        | 1h open-path length (pips)       |          29.100 |         26.250 |             0.086 |  0.395 |
| B02        | 1h path efficiency               |           0.789 |          0.779 |             0.010 |  0.901 |
| B02        | Signal close outside (pips)      |           4.700 |          3.300 |             0.119 |  0.304 |
| B02        | Entry executable outside (pips)  |           5.100 |          3.450 |             0.118 |  0.304 |
| B02        | Same-direction stack ordinal     |           1.000 |          1.000 |             0.083 |  0.395 |
| F05        | 4h side-aligned open move (pips) |          43.500 |         44.400 |            -0.015 |  0.818 |
| F05        | 1h acceleration (pips)           |          14.000 |         11.700 |             0.069 |  0.493 |
| F05        | 1h open-path length (pips)       |          30.800 |         29.950 |             0.026 |  0.793 |
| F05        | 1h path efficiency               |           0.834 |          0.808 |             0.035 |  0.793 |
| F05        | Signal close outside (pips)      |           4.400 |          4.400 |             0.020 |  0.793 |
| F05        | Entry executable outside (pips)  |           4.800 |          4.700 |             0.020 |  0.793 |
| F05        | Same-direction stack ordinal     |           3.000 |          3.000 |             0.022 |  0.793 |

### Cross-fold stability

| Strategy   | Feature                          |   Winner-higher folds |   Winner-lower folds |   Pooled Δ |   Pooled q | Material same-sign all 4   |
|:-----------|:---------------------------------|----------------------:|---------------------:|-----------:|-----------:|:---------------------------|
| B02        | 1h open-path length (pips)       |                     3 |                    1 |      0.086 |      0.395 | False                      |
| B02        | Signal close outside (pips)      |                     3 |                    1 |      0.119 |      0.304 | False                      |
| B02        | Entry executable outside (pips)  |                     3 |                    1 |      0.118 |      0.304 | False                      |
| B02        | 1h acceleration (pips)           |                     3 |                    1 |      0.070 |      0.539 | False                      |
| B02        | Same-direction stack ordinal     |                     3 |                    1 |      0.083 |      0.395 | False                      |
| B02        | 1h path efficiency               |                     3 |                    1 |      0.010 |      0.901 | False                      |
| B02        | 4h side-aligned open move (pips) |                     2 |                    2 |      0.039 |      0.648 | False                      |
| F05        | 1h acceleration (pips)           |                     4 |                    0 |      0.069 |      0.493 | False                      |
| F05        | 1h path efficiency               |                     4 |                    0 |      0.035 |      0.793 | False                      |
| F05        | Entry executable outside (pips)  |                     4 |                    0 |      0.020 |      0.793 | False                      |
| F05        | Signal close outside (pips)      |                     4 |                    0 |      0.020 |      0.793 | False                      |
| F05        | 1h open-path length (pips)       |                     3 |                    1 |      0.026 |      0.793 | False                      |
| F05        | 4h side-aligned open move (pips) |                     3 |                    1 |     -0.015 |      0.818 | False                      |
| F05        | Same-direction stack ordinal     |                     2 |                    2 |      0.022 |      0.793 | False                      |

### Finding

- B02: zero pre-entry continuous features are material and same-sign in all four folds.
- F05: zero pre-entry continuous features are material and same-sign in all four folds.
- B02 signal-close/executable breakout distance shows a modest pooled difference, but the sign reverses in 2024 H2.
- F05 winner and loser medians are nearly identical for signal outside distance, executable outside distance, 4h aligned movement, and stack ordinal.
- BH-adjusted q-values do not support a portable univariate separator.

The current local M15/4h geometry does not explain winner versus loser status in a period-invariant way.

## 6. Multivariate held-out-fold discrimination

A regularized logistic model was trained on three folds and tested on the untouched fourth fold. Numeric features were standardized and categorical entry-state features one-hot encoded. This is descriptive generalization, not candidate selection.

| Strategy   | Held-out fold   |   Train N |   Test N |   AUC |   Brier |
|:-----------|:----------------|----------:|---------:|------:|--------:|
| B02        | 2023H1          |       308 |      121 | 0.619 |   0.242 |
| B02        | 2023H2          |       320 |      109 | 0.445 |   0.277 |
| B02        | 2024H1          |       332 |       97 | 0.570 |   0.248 |
| B02        | 2024H2          |       327 |      102 | 0.504 |   0.255 |
| F05        | 2023H1          |      1086 |      367 | 0.468 |   0.258 |
| F05        | 2023H2          |      1090 |      363 | 0.515 |   0.254 |
| F05        | 2024H1          |      1122 |      331 | 0.474 |   0.255 |
| F05        | 2024H2          |      1061 |      392 | 0.526 |   0.250 |

### Finding

- B02 held-out AUC ranges from 0.445 to 0.619.
- F05 held-out AUC ranges from 0.468 to 0.526.
- F05 is effectively indistinguishable from chance using the current entry-feature set.
- B02 shows one moderately informative fold, but the learned relationship reverses or collapses elsewhere.

This rejects the idea that another static threshold or combination of the already-measured M15-local features is the principal missing mechanism.

## 7. Direction decomposition

| Strategy   | Fold   | Side   |   Trades |   Wins |    Net JPY |    PF |
|:-----------|:-------|:-------|---------:|-------:|-----------:|------:|
| B02        | 2023H1 | long   |       66 |     38 |   -360.000 | 0.980 |
| B02        | 2023H1 | short  |       55 |     23 | -14021.000 | 0.388 |
| B02        | 2023H2 | long   |       63 |     35 |   -496.000 | 0.960 |
| B02        | 2023H2 | short  |       46 |     22 |   2418.000 | 1.218 |
| B02        | 2024H1 | long   |       65 |     43 |  10839.000 | 2.826 |
| B02        | 2024H1 | short  |       32 |     14 |  -1285.000 | 0.820 |
| B02        | 2024H2 | long   |       58 |     38 |   8355.000 | 1.694 |
| B02        | 2024H2 | short  |       44 |     26 |   7272.000 | 1.722 |
| B02        | POOLED | long   |      252 |    154 |  18338.000 | 1.378 |
| B02        | POOLED | short  |      177 |     85 |  -5616.000 | 0.890 |
| F05        | 2023H1 | long   |      239 |    116 |   -143.000 | 0.997 |
| F05        | 2023H1 | short  |      128 |     54 | -11528.000 | 0.674 |
| F05        | 2023H2 | long   |      207 |     97 |  -5268.000 | 0.848 |
| F05        | 2023H2 | short  |      156 |     82 |  20119.000 | 1.857 |
| F05        | 2024H1 | long   |      251 |    145 |  19917.000 | 1.726 |
| F05        | 2024H1 | short  |       80 |     33 |  -6674.000 | 0.664 |
| F05        | 2024H2 | long   |      217 |    110 |  10485.000 | 1.266 |
| F05        | 2024H2 | short  |      175 |     90 |  11997.000 | 1.256 |
| F05        | POOLED | long   |      914 |    468 |  24991.000 | 1.167 |
| F05        | POOLED | short  |      539 |    259 |  13914.000 | 1.111 |

### Finding

Direction is not a causal invariant.

- Both B02 and F05 short trades are deeply negative in 2023 H1, strongly positive in 2023 H2, mixed in 2024 H1, and positive in 2024 H2.
- Long-side contributions also change sign.

A permanent long/short block would encode one period rather than explain the mechanism.

## 8. F05 exposure-state decomposition

| Fold   | Exposure state              |   Trades |    Net JPY |    PF |
|:-------|:----------------------------|---------:|-----------:|------:|
| 2023H1 | mixed_overlap               |       46 |   5904.000 | 2.384 |
| 2023H1 | opposite_overlap            |       25 |   3551.000 | 1.811 |
| 2023H1 | same_direction_stack        |      224 | -16494.000 | 0.704 |
| 2023H1 | simultaneous_same_direction |       13 |     25.000 | 1.009 |
| 2023H1 | standalone                  |       59 |  -4657.000 | 0.712 |
| 2023H2 | mixed_overlap               |       28 |  -1468.000 | 0.686 |
| 2023H2 | opposite_overlap            |       18 |   1570.000 | 1.439 |
| 2023H2 | same_direction_stack        |      247 |   9599.000 | 1.244 |
| 2023H2 | simultaneous_same_direction |       17 |   1430.000 | 1.552 |
| 2023H2 | standalone                  |       53 |   3720.000 | 1.469 |
| 2024H1 | mixed_overlap               |       10 |  -1537.000 | 0.254 |
| 2024H1 | opposite_overlap            |       14 |   -851.000 | 0.681 |
| 2024H1 | same_direction_stack        |      234 |  19702.000 | 1.705 |
| 2024H1 | simultaneous_same_direction |       10 |   -260.000 | 0.783 |
| 2024H1 | standalone                  |       63 |  -3811.000 | 0.717 |
| 2024H2 | mixed_overlap               |       12 |   -544.000 | 0.751 |
| 2024H2 | opposite_overlap            |       12 |  -3182.000 | 0.479 |
| 2024H2 | same_direction_stack        |      287 |  26071.000 | 1.468 |
| 2024H2 | simultaneous_same_direction |       17 |   5068.000 | 5.346 |
| 2024H2 | standalone                  |       64 |  -4931.000 | 0.765 |
| POOLED | mixed_overlap               |       96 |   2355.000 | 1.179 |
| POOLED | opposite_overlap            |       69 |   1088.000 | 1.065 |
| POOLED | same_direction_stack        |      992 |  38878.000 | 1.217 |
| POOLED | simultaneous_same_direction |       57 |   6263.000 | 1.795 |
| POOLED | standalone                  |      239 |  -9679.000 | 0.835 |

### Finding

The 2024-only interpretation that “same-direction stack creates edge” does not survive 2023 H1:

- F05 same-direction stack: JPY -16,494 in 2023 H1, then +9,599, +19,702, and +26,071.
- F05 standalone is negative in three folds but positive in 2023 H2.

Open exposure therefore does not mechanically create expectancy. It is a proxy for an unobserved market state that sometimes represents continuation and sometimes represents crowded failure.

## 9. Post-entry trajectory separation

Each cell shows median pips for winner / loser.

| Strategy   | Fold   | 15m W/L       | 60m W/L      | 120m W/L      | 240m W/L       | MFE W/L       | MAE W/L         |
|:-----------|:-------|:--------------|:-------------|:--------------|:---------------|:--------------|:----------------|
| B02        | 2023H1 | -0.85 / -0.05 | 2.70 / -6.70 | 5.50 / -10.50 | 12.30 / -22.95 | 61.20 / 9.00  | -17.70 / -74.10 |
| B02        | 2023H2 | -0.30 / -0.45 | 1.50 / -2.10 | 4.70 / -6.35  | 13.10 / -10.75 | 51.10 / 10.10 | -8.20 / -52.80  |
| B02        | 2024H1 | -0.70 / 0.40  | 0.50 / -1.90 | 3.80 / -4.25  | 4.60 / -8.75   | 41.00 / 8.85  | -10.60 / -42.05 |
| B02        | 2024H2 | 0.00 / -3.55  | 5.30 / -6.80 | 8.35 / -13.45 | 17.25 / -36.30 | 67.15 / 14.10 | -12.30 / -70.60 |
| F05        | 2023H1 | 2.30 / -3.70  | 3.45 / -6.80 | 9.80 / -11.20 | 17.40 / -19.70 | 45.15 / 7.80  | -10.65 / -45.30 |
| F05        | 2023H2 | 1.00 / -0.50  | 3.00 / -2.85 | 5.80 / -6.15  | 16.80 / -11.60 | 44.90 / 7.65  | -7.20 / -33.30  |
| F05        | 2024H1 | 0.75 / -2.20  | 4.85 / -4.50 | 5.85 / -8.20  | 10.20 / -12.70 | 32.50 / 4.80  | -7.15 / -31.50  |
| F05        | 2024H2 | 0.60 / -2.10  | 5.65 / -3.60 | 13.00 / -9.55 | 24.50 / -15.60 | 55.60 / 11.80 | -11.25 / -48.60 |

### Finding

The portable information appears after the setup signal:

- B02 has weak and unstable separation at 15–30m, but winner/loser medians separate consistently by 60m and widen at 120–240m.
- F05 separates as early as 15m in all four folds, then widens monotonically.
- Winners have materially larger MFE and shallower MAE in every fold.

This indicates that the missing distinction is not breakout magnitude at entry. It is whether price subsequently establishes and maintains a directional state.

This finding must not be converted directly into another P/L checkpoint threshold. Families D/E/H already tested checkpoint-style exit logic. The causal requirement is an independently observable price-structure transition, not “close because the trade is down X pips.”

## 10. Monthly and date concentration

| Strategy   | Fold   |   Positive months |   Negative months | Best month       | Worst month      |
|:-----------|:-------|------------------:|------------------:|:-----------------|:-----------------|
| B02        | 2023H1 |                 1 |                 5 | 2023-05 (+101)   | 2023-03 (-5003)  |
| B02        | 2023H2 |                 5 |                 1 | 2023-11 (+1004)  | 2023-12 (-1424)  |
| B02        | 2024H1 |                 6 |                 0 | 2024-01 (+3190)  | 2024-03 (+419)   |
| B02        | 2024H2 |                 6 |                 0 | 2024-12 (+5567)  | 2024-07 (+709)   |
| F05        | 2023H1 |                 3 |                 3 | 2023-05 (+5457)  | 2023-01 (-9748)  |
| F05        | 2023H2 |                 3 |                 3 | 2023-12 (+18808) | 2023-09 (-6095)  |
| F05        | 2024H1 |                 5 |                 1 | 2024-04 (+5871)  | 2024-01 (-4597)  |
| F05        | 2024H2 |                 5 |                 1 | 2024-08 (+13396) | 2024-09 (-13444) |

| Strategy   | Fold   |   Top-2 positive-date share |   Net ex best 2 positive dates |
|:-----------|:-------|----------------------------:|-------------------------------:|
| B02        | 2023H1 |                       0.155 |                     -17722.000 |
| B02        | 2023H2 |                       0.166 |                      -2025.000 |
| B02        | 2024H1 |                       0.148 |                       6231.000 |
| B02        | 2024H2 |                       0.122 |                      11232.000 |
| F05        | 2023H1 |                       0.227 |                     -23842.000 |
| F05        | 2023H2 |                       0.288 |                      -2486.000 |
| F05        | 2024H1 |                       0.217 |                       1875.000 |
| F05        | 2024H2 |                       0.180 |                       7722.000 |

### Finding

- The common failure in 2023 H1 is broad rather than one isolated date: B02 remains JPY -17,722 and F05 JPY -23,842 after removing their two best positive dates.
- F05 2023 H2 profit is concentrated in November–December; removing the two best dates leaves JPY -2,486.
- F05 2024 H1 is also relatively concentrated; removing the two best dates leaves JPY +1,875.
- B02 2024 H1/H2 and F05 2024 H2 remain positive after removing their two best dates.
- Month identity is not portable: F05 January is negative in 2023 H1 and 2024 H1, but the major negative month shifts to September in 2024 H2. Calendar month is therefore a diagnosis dimension, not a causal trading rule.

Full monthly and daily tables are included in the analysis bundle.

## 11. Loss-path decomposition

| Strategy   | Fold   |   P1 giveback share |   P2 minor-favorable share |   P3 never-profitable share |
|:-----------|:-------|--------------------:|---------------------------:|----------------------------:|
| B02        | 2023H1 |               0.406 |                      0.311 |                       0.283 |
| B02        | 2023H2 |               0.479 |                      0.258 |                       0.263 |
| B02        | 2024H1 |               0.348 |                      0.547 |                       0.105 |
| B02        | 2024H2 |               0.392 |                      0.367 |                       0.241 |
| F05        | 2023H1 |               0.384 |                      0.237 |                       0.379 |
| F05        | 2023H2 |               0.456 |                      0.304 |                       0.240 |
| F05        | 2024H1 |               0.342 |                      0.314 |                       0.343 |
| F05        | 2024H2 |               0.460 |                      0.191 |                       0.349 |

Definitions:

- P1: reached at least +10 pips MFE, then finished negative.
- P2: had minor favorable excursion below +10 pips, then finished negative.
- P3: never became profitable on the executable M15-open path.

### Finding

No single loss mode explains all folds:

- B02 gross losses contain both P1 givebacks and P2/P3 failed admissions.
- F05 also repeatedly contains both givebacks and immediate/low-MFE failures.
- 2024 H1 B02 is unusually P2-heavy, while other folds have larger P1/P3 shares.

An entry filter alone cannot address P1. An exit overlay alone cannot repair P2/P3. A coherent architecture needs both state-defined admission and state-defined termination.

## 12. Factor diagnosis

### 12.1 Rejected causal explanations

1. **Large breakout distance creates the edge** — rejected by sign reversal and weak effect.
2. **Strong recent 4h aligned movement creates the edge** — rejected by small, unstable winner–loser differences.
3. **A fixed trade direction creates the edge** — rejected by fold-specific sign changes.
4. **Same-direction stacking creates the edge** — rejected by the 2023 H1 stack loss.
5. **One loss class is the sole defect** — rejected because P1, P2, and P3 are all economically material.
6. **Another multivariate combination of the same local features is likely to solve it** — not supported by held-out-fold AUC.

### 12.2 Retained causal observations

1. The decisive separation appears in **state realization after the M15 setup**, not in local setup magnitude.
2. B02 and F05 share the 2023 H1 failure, despite different signal definitions.
3. Direction and exposure labels behave as regime proxies rather than stable causes.
4. Winner/loser trajectory separation becomes stronger with completed higher-timeframe elapsed structure.
5. Both admission failure and giveback require a paired entry/termination architecture.

## 13. Hypotheses derived after factor diagnosis

### H1 — Native higher-timeframe transition completion is the missing state variable

**Claim:** B02 and F05 M15 events are setup observations, not primary deployable signals. Capital should be deployed only when a completed native H1/H4 price-state transition confirms the same direction. Termination should occur on a completed opposite state transition.

**Why this follows from the data:**

- measured M15-local entry features do not generalize;
- outcome trajectories begin to separate over completed 1h–4h structure;
- fixed side and exposure labels reverse across folds;
- both P2/P3 admission failures and P1 givebacks recur.

**Falsifiable predictions before outcome access:**

- HTF-confirmed entries reduce P2+P3 frequency and loss share in every fold;
- state-reversal termination reduces P1 giveback loss without erasing the majority of winner gross profit;
- long and short use the same directional logic;
- no side-specific, year-specific, or session-specific exception is required;
- if the result depends on an outcome-derived threshold, the hypothesis is rejected.

### H2 — Exposure state is a proxy, not a deployable rule

**Claim:** Same-direction stack is profitable only when it coincides with a latent continuation state. Once native HTF state is included, stack/standalone labels should add little incremental explanatory value.

**Prediction:** Conditional on the HTF transition state, exposure-state coefficient/effect should shrink materially and should not be required by the protocol.

### H3 — B02 and F05 require the same market-state ledger but different setup roles

**Claim:**

- B02 session-range break identifies a possible transition from overnight balance.
- F05 Donchian break identifies a possible continuation/expansion event.
- Both are subordinate setup observations.
- The primary deployable event is the common native HTF transition, not a strategy-specific M15 threshold.

This is not “apply the same Boolean filter to B02 and F05.” The setup semantics remain different, while the causal state confirmation and termination contract are shared.

### H4 — Path-class predictions are binding causal tests

A candidate must not pass merely because aggregate net improves.

- Entry mechanism must reduce P2/P3 across all four folds.
- Termination mechanism must reduce P1 giveback.
- Exposure-state dependence must diminish.
- Direction symmetry must hold.
- Improvement must retain monthly/date breadth.

Failure of those mechanism predictions rejects the causal interpretation even if one aggregate is positive.

## 14. Distinction from closed work

- Not Family A: no M15 wick/outside-close threshold.
- Not Family F: no “second F05 signal” as confirmation.
- Not Families G/H: no checkpoint reacceptance overlay on an already-open baseline trade.
- Not Family I: no static 4h movement cutoff.
- Not RQ-020B: no static 5-day/20-day router.
- Not RQ-020E/RQ-021: no reuse or repair of the 660 M15-entry × fixed-horizon surface.

The distinct information is that both the **primary entry** and **termination** are defined by completed native H1/H4 state transitions.

## 15. Research boundary and next analysis task

This report is descriptive factor diagnosis using already-opened 2023/2024 baseline outcomes. It does not authorize candidate outcome evaluation.

The next pre-outcome task is:

1. define deterministic native H1/H4 bars from the accepted M15 lineage;
2. freeze a finite, direction-symmetric state-transition definition without opening its outcomes;
3. audit duplication against all closed families;
4. pre-register the path-class predictions above;
5. only after explicit registry authorization, evaluate unchanged across 2023H1, 2023H2, 2024H1, and 2024H2.

## 16. Reproducibility identities

- `b02f05_2023_2024_common_factor_dataset_v1.csv`: `ab57a58b65aceeee2d9f51182e97e3de712458d12a4832497ed1857c3c8d6b80`
- `usdjpy_2023_legacy2024_historical_baseline_ledger_rebuilt.csv`: `a6e60f982eef8e470c5fb0c1040dd85179928382347bff1f05f01d3a96f94d8f`
- `usdjpy_2023_legacy2024_m15_rebuilt.csv.gz`: `b42a967200363d727c0c1faa50be3d281a12d5d42d886cb33d999b9126aa6adf`
