# USDJPY RQ-021 Architecture Failure Taxonomy Result v1

## Decision

`RQ-021` is complete. The closed `RQ-020E` surface was decomposed using only already-opened outputs. No cell was retuned, no horizon was added, and no new market outcome, MT4 run or 2025 evidence was accessed.

The current M15-local Entry plus unconditional fixed-time exit architecture is closed. One genuinely distinct successor question is justified: **native H1/H4 state-transition signals paired with state-conditional event termination**. This opens `RQ-022` as a research question only; no family or candidate is preregistered.

## Failure distribution

| Folds passing | Default cells | Severe-cost cells | Breadth cells |
|---:|---:|---:|---:|
| 0 | 130 | 449 | 389 |
| 1 | 213 | 135 | 208 |
| 2 | 193 | 56 | 60 |
| 3 | 110 | 19 | 3 |
| 4 | 14 | 1 | 0 |

All 660 cells had adequate support. The collapse from 14 default four-fold cells to one severe-cost four-fold cell shows that transaction-cost fragility is architecture-wide rather than confined to one family.

The weakest severe-cost fold was:

- 2024 H2: 248 cells
- 2024 H1: 162 cells
- 2023 H1: 140 cells
- 2023 H2: 110 cells

No single year or half explains the closure. The sign and magnitude failures are distributed across all four development folds.

## Family attribution

| Family | Default 4-fold | Severe 4-fold | Median severe-pass folds | Median minimum-fold severe net |
|---|---:|---:|---:|---:|
| session_handoff | 3 | 1 | 1.0 | -240.7 |
| ema_trend_cross | 3 | 0 | 0.0 | -1,202.1 |
| trend_pullback_resumption | 3 | 0 | 0.0 | -1,611.6 |
| session_range_breakout | 2 | 0 | 1.0 | -662.2 |
| failed_excursion_reversion | 2 | 0 | 0.0 | -2,593.5 |
| volatility_adjusted_momentum | 1 | 0 | 0.0 | -1,269.2 |
| all other six families | 0 | 0 | 0.0 | below -1,946.8 |

`session_handoff` is the least-failed family, but its evidence consists of one isolated `R1K03 × 24 bars` core cell. It has no full-gate cell, no contiguous horizon neighbourhood and no family region. It cannot be selected or locally repaired.

## Horizon attribution

No horizon produces a family-level neighbourhood. The longer horizons contain more default-only near-passes, but their median worst-fold severe result deteriorates:

| Horizon (M15 bars) | Default 4-fold | Severe 4-fold | Median minimum-fold severe net |
|---:|---:|---:|---:|
| 1 | 0 | 0 | -1,498.0 |
| 6 | 1 | 0 | -1,935.3 |
| 16 | 1 | 0 | -2,302.2 |
| 24 | 3 | 1 | -2,721.5 |
| 32 | 4 | 0 | -2,876.6 |
| 48 | 2 | 0 | -3,182.5 |

This rejects the interpretation that the architecture merely needs a longer fixed hold. Isolated continuation effects improve at long horizons, while the broader surface becomes more fragile.

## Direction attribution

- Dominant severe-cost side changes at least once in **562 / 660** cells.
- It changes two or more times in **349 / 660** cells.
- Only 98 cells retain the same dominant side across all four folds.
- Three cells have long-side severe net positive in all four folds.
- One cell has short-side severe net positive in all four folds.
- No cell has both directions severe-positive in all four folds.

Static direction attached to an M15 signal is therefore strongly regime-dependent. The sole core cell illustrates the same problem: long dominates in 2023 H2 and 2024 H1, whereas short dominates in 2024 H2.

## Ledger duplicate audit

The following dimensions are already closed and cannot be renamed:

- Families A/I and HYP-001–006: shock, extension, acceptance and admission filters.
- Family B/E/F: exposure state, confirmation and state-adaptive routing applied to existing B02/F05 signals.
- Families C/D/G/H: post-entry checkpoint, invalidation and recovery exits.
- `RQ-019`: local B02 band partitioning.
- `RQ-020B`: static 5-day/20-day direction, efficiency, volatility and range-position states.
- `RQ-020E`: every frozen M15 Entry × fixed-time horizon cell.

The remaining information gap is not another filter or threshold. R1 uses M15-local patterns or session references as the primary signal; R2 terminates positions after an unconditional M15 bar count. Even the old “higher-timeframe trend continuation” used an M15 pullback/resumption trigger and a fixed six-M15-bar hold. It did not define the signal and termination on completed native H1/H4 structure.

## One successor question

`USDJPY-RQ-022`:

> Can a native H1/H4 state-transition architecture, with entry and termination events defined on completed higher-timeframe structure rather than an M15 pattern plus fixed horizon, produce a broad family region across all four development folds?

This is not yet a candidate. The next permitted work is only source/data feasibility, literature and ledger duplicate audit, and a finite protocol frozen before outcomes. Parameter search, family preregistration, MT4 and 2025 remain locked.
