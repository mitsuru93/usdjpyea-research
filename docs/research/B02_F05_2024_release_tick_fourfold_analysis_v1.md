# B02/F05 2024 Release Tick four-fold analysis v1

## 1. Correction
The prior statement that accepted 2024 M1/M5 data were unavailable was incorrect. The Research release `usdjpy-2024-mt4-tick-import-v1` contains the full 2024 Dukascopy Bid/Ask tick stream as twelve monthly UTC CSV.GZ assets. The package contains 40,969,081 ticks with real Bid/Ask and variable spread.

The release package ZIP SHA-256 is `002493b24e508de6db3807315793d44d756f76d9fee058d9b546f0a8c07d40b2`. All inner assets passed the package `SHA256SUMS` check.

## 2. Exact reconstruction
- Tick rows: 40,969,081
- Reconstructed M1 rows: 373,383
- M1 output SHA-256: `7e43afb066f5594f8e0b9fde408a08513433b05d9c1d39c294874d271af879b2`
- 2024 B02/F05 baseline trades joined: 922/922 at the exact Entry minute.
- Accepted Entry Bid versus Release first Bid: exact for all 922 trades.
- 2024 H1 accepted M15 OHLC: 11,884/11,884 bars exact in Open, High, Low and Close.
- 2024 H2 accepted portfolio-snapshot opens: 12,209 matched timestamps, all exact. The remaining 41 accepted snapshots did not have a corresponding tick-generated M15 row, but no tested Entry window was lost.
- Median source spread at Entry: 0.5 pips in 2024 H1 and 0.6 pips in 2024 H2.

Therefore the release ticks reconstruct the accepted 2024 market series rather than an unrelated substitute series. The source remains Dukascopy and must not be called Rakuten quote history.

## 3. Population and definitions
The accepted baseline labels were retained:
- P3: never profitable, final loss.
- P2: minor favorable excursion below +10 pips, final loss.
- P1: reached at least +10 pips, final loss.
- WINNER: final P/L positive.

Immediate windows: 1, 3, 5, 10, 15 and 30 minutes after Entry. The common four-fold features use the same formulas in 2023H1, 2023H2, 2024H1 and 2024H2. No 2025 data were accessed.

## 4. Immediate P3 result
| 分 | B02 AUC平均 | B02 最低fold | F05 AUC平均 | F05 最低fold |
|---:|---:|---:|---:|---:|
| 1 | 0.418 | 0.319 | 0.576 | 0.499 |
| 3 | 0.577 | 0.466 | 0.668 | 0.597 |
| 5 | 0.650 | 0.537 | 0.703 | 0.650 |
| 10 | 0.748 | 0.699 | 0.783 | 0.752 |
| 15 | 0.779 | 0.742 | 0.832 | 0.805 |
| 30 | 0.864 | 0.832 | 0.886 | 0.863 |

The 2023 finding is confirmed in 2024.
- F05 begins to separate at 3 minutes and is materially clearer by the first completed M5.
- B02 does not have a stable five-minute separator; robust separation begins around 10 minutes.
- By 15 and 30 minutes both strategies are strongly separated, but those later checkpoints are increasingly descriptive of an already-failed trade.

### Representative four-fold-stable features
| Strategy | Contrast | 分 | 特徴 | Positive median | Negative median | Δ | pooled q |
|---|---|---:|---|---:|---:|---:|---:|
| B02 | P3_vs_EVER | 10 | `body_dir_pips` | -0.1000 | -4.7000 | 0.524 | 3.11e-06 |
| B02 | P3_vs_EVER | 10 | `window_close_location_dir` | 0.5240 | 0.1637 | 0.455 | 2.85e-05 |
| B02 | P3_vs_EVER | 10 | `breakout_retention_fraction` | 1.0000 | 0.8000 | 0.321 | 0.00106 |
| F05 | P3_vs_EVER | 3 | `body_dir_pips` | 0.3000 | -2.1500 | 0.351 | 2.9e-13 |
| F05 | P3_vs_EVER | 5 | `m5_last_body_dir_pips` | 0.5000 | -2.8500 | 0.413 | 3.18e-18 |
| F05 | P3_vs_EVER | 5 | `window_close_location_dir` | 0.5385 | 0.2550 | 0.349 | 1.95e-13 |
| F05 | WINNER_vs_P2 | 1 | `mfe_pips` | 1.0000 | 0.5000 | 0.213 | 1.34e-05 |
| F05 | WINNER_vs_P2 | 5 | `range_pips` | 8.1000 | 5.8000 | 0.236 | 3.61e-07 |
| F05 | WINNER_vs_P2 | 15 | `path_length_pips` | 26.9000 | 19.5000 | 0.261 | 9.59e-09 |

The portable mechanism is not a pre-Entry oscillator state. It is failure to establish and retain the breakout after execution:
- weak or negative direction-aligned body,
- close in the wrong side of the short window,
- fewer favorable M1 steps,
- more adverse steps,
- reduced breakout retention,
- greater adverse excursion.

## 5. P2 result
| 分 | B02 AUC平均 | B02 最低fold | F05 AUC平均 | F05 最低fold |
|---:|---:|---:|---:|---:|
| 1 | 0.521 | 0.478 | 0.615 | 0.594 |
| 3 | 0.526 | 0.464 | 0.626 | 0.613 |
| 5 | 0.559 | 0.526 | 0.627 | 0.604 |
| 10 | 0.547 | 0.427 | 0.629 | 0.604 |
| 15 | 0.599 | 0.566 | 0.627 | 0.589 |
| 30 | 0.664 | 0.598 | 0.698 | 0.661 |

- F05 P2 differs from Winner from the first minute through range/MFE expansion. At 3-5 minutes the signal is already portable across all four folds.
- B02 P2 remains weak through 15 minutes and becomes only moderately distinguishable at 30 minutes.
- For F05, the central deficiency is insufficient early participation and expansion, not merely a low oscillator reading.

## 6. P1 result
| 分 | B02 AUC平均 | B02 最低fold | F05 AUC平均 | F05 最低fold |
|---:|---:|---:|---:|---:|
| 1 | 0.470 | 0.382 | 0.529 | 0.490 |
| 3 | 0.480 | 0.435 | 0.472 | 0.447 |
| 5 | 0.554 | 0.511 | 0.449 | 0.411 |
| 10 | 0.608 | 0.577 | 0.502 | 0.468 |
| 15 | 0.617 | 0.564 | 0.473 | 0.436 |
| 30 | 0.570 | 0.496 | 0.527 | 0.495 |

P1 remains indistinguishable from Winner in the immediate window. F05 has no four-fold portable immediate feature. B02 has only one weak ten-minute efficiency feature and the multivariate performance remains modest. A first-M5 abort must not be treated as a P1 solution.

## 7. Native M30/H1/H4 Entry features
| Task | M30 mean/min | H1 mean/min | H4 mean/min | Combined mean/min |
|---|---:|---:|---:|---:|
| B02_P3_vs_EVER | 0.510/0.477 | 0.567/0.520 | 0.551/0.505 | 0.547/0.498 |
| F05_P3_vs_EVER | 0.536/0.500 | 0.479/0.427 | 0.521/0.492 | 0.531/0.494 |
| B02_WINNER_vs_P2 | 0.447/0.269 | 0.445/0.274 | 0.455/0.307 | 0.442/0.238 |
| F05_WINNER_vs_P2 | 0.481/0.451 | 0.542/0.507 | 0.508/0.448 | 0.472/0.445 |
| B02_WINNER_vs_P1 | 0.636/0.557 | 0.597/0.540 | 0.515/0.428 | 0.577/0.544 |
| F05_WINNER_vs_P1 | 0.538/0.507 | 0.542/0.492 | 0.522/0.493 | 0.532/0.499 |

Full 2024 H2 OHLC does not rescue static higher-timeframe Entry selection:
- F05 has no portable M30/H1/H4 Entry factor for P3, P2 or P1.
- B02 P3 has one H1 MACD-histogram-change feature and one H4 range/ATR feature with consistent sign, but pooled BH q-values are 0.582 and 0.210 and model AUC remains weak.
- Static M30/H1/H4 state is therefore not an adequate Entry separator.

## 8. Native M30/H1/H4 Exit-state features
| Task | M30 mean/min | H1 mean/min | H4 mean/min | Combined mean/min |
|---|---:|---:|---:|---:|
| B02_P2_vs_WINNER_0m | 0.459/0.352 | 0.487/0.337 | 0.404/0.234 | 0.474/0.266 |
| B02_P2_vs_WINNER_15m | 0.685/0.589 | 0.596/0.418 | 0.415/0.259 | 0.671/0.545 |
| B02_P2_vs_WINNER_30m | 0.772/0.698 | 0.651/0.559 | 0.441/0.286 | 0.694/0.592 |
| F05_P2_vs_WINNER_0m | 0.612/0.578 | 0.562/0.542 | 0.505/0.474 | 0.587/0.565 |
| F05_P2_vs_WINNER_15m | 0.699/0.663 | 0.587/0.558 | 0.518/0.475 | 0.662/0.632 |
| F05_P2_vs_WINNER_30m | 0.777/0.728 | 0.685/0.638 | 0.535/0.498 | 0.752/0.710 |
| B02_P1_vs_WINNER_0m | 0.606/0.568 | 0.533/0.426 | 0.552/0.479 | 0.600/0.540 |
| B02_P1_vs_WINNER_30m | 0.639/0.582 | 0.619/0.539 | 0.519/0.455 | 0.621/0.540 |
| B02_P1_vs_WINNER_60m | 0.712/0.675 | 0.697/0.604 | 0.533/0.453 | 0.703/0.636 |
| F05_P1_vs_WINNER_0m | 0.521/0.477 | 0.545/0.494 | 0.516/0.495 | 0.545/0.488 |
| F05_P1_vs_WINNER_30m | 0.588/0.555 | 0.581/0.572 | 0.508/0.499 | 0.579/0.562 |
| F05_P1_vs_WINNER_60m | 0.679/0.615 | 0.644/0.589 | 0.499/0.485 | 0.648/0.610 |

This is the second new result enabled by the Release ticks.
- F05 P2 is already different at the event landmark: Winner M30 range median 23.0 pips versus P2 14.75, and M30 directional body 13.8 versus 7.1.
- At +15 minutes, F05 P2 M30 AUC is 0.699 with minimum fold 0.663; at +30 minutes it is 0.777/0.728.
- B02 P2 becomes clearer later: M30 AUC 0.685/0.589 at +15 minutes and 0.772/0.698 at +30 minutes.
- P1 remains close to Winner at +10 arrival and the first 15 minutes. M30/H1 state decay becomes material from about +30 minutes and especially +60 minutes.

Representative Exit-state changes are direction-aligned M30/H1 body and momentum, M30/H1 range expansion, MACD-histogram change, Bollinger position, close location, Stochastic/RSI and counter-wick structure. These are completed-bar state observations, not permission to select thresholds from the displayed medians.

## 9. Revised architecture diagnosis
The evidence now supports three distinct lifecycle phases:
1. Setup: existing B02/F05 M15 signal.
2. Establishment: completed first-M5/second-M5 breakout retention and directional structure. This is where P3 and, for F05, P2 begin to separate.
3. Continuation/termination: completed M30/H1 state decay after a previously established move. This is where P1 becomes distinguishable.

Timing differs by strategy:
- F05 establishment: approximately 3-5 minutes.
- B02 establishment: approximately 10 minutes.
- F05 P2 decay: visible immediately and clearer by M30.
- B02 P2 decay: later, around 15-30 minutes.
- P1 giveback decay: generally 30-60 minutes after the +10-pip landmark.

## 10. Scientific boundaries
- These are descriptive outcome-conditioned features, not a frozen candidate.
- Do not select rules such as “body below X pips”, “retention below Y%”, “RSI below Z” from this report.
- A validation family must define finite completed-bar state transitions before opening outcomes.
- Long/short logic must remain symmetric.
- 2025 H1/H2 were not accessed.
- MT4/TDS may use the Release CSVs, but the source remains Dukascopy.

## 11. Reproducibility
Source release tag: `usdjpy-2024-mt4-tick-import-v1`
Source Actions artifact: `8458310265`
Source package SHA-256: `002493b24e508de6db3807315793d44d756f76d9fee058d9b546f0a8c07d40b2`
Reconstructed M1 SHA-256: `7e43afb066f5594f8e0b9fde408a08513433b05d9c1d39c294874d271af879b2`
