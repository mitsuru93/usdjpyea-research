# USDJPY Entry-Horizon Research Protocol v1

## Decision

The current primary H2 is retained unchanged as a confirmatory test of two complete fixed-exit strategies:

```text
A1_impulse_breakout_lb3_hold6 + six-M15-bar exit
E3_trend_24h_resumption_hold6 + six-M15-bar exit
```

Neither candidate is described as an exit-independent winning entry. The January-June screen selected complete entry-plus-six-bar strategies.

A separate development diagnostic will evaluate the forward path of all 13 registered candidates without altering the active H2 candidate set.

The registry contains 12 unique entry definitions. `C1_failed_12bar_hold3` and `C2_failed_12bar_hold6` share the same entry signal and differ only in their originally registered hold period. They remain separately traceable, but they are not treated as two independent pieces of entry evidence.

## Separation of research questions

### Confirmatory H2 question

```text
Do A1+hold6 and E3+hold6 reproduce on the untouched 2024-07 through 2024-12 block under the pre-registered common gate?
```

The answer to this question must not be changed by the horizon diagnostic.

### Development diagnostic question

```text
For each of the 12 frozen unique entry definitions represented by the 13 registered candidates, how does default-cost and severe-cost performance evolve across multiple fixed M15 horizons, and what does the first 24 bars of MFE/MAE show about the entry's price path?
```

This question uses only 2024-01 through 2024-06.

## Frozen inputs

```text
candidate registry:
  configs/research/usdjpy_h1_multi_family_candidates_v1.json

registry blob SHA:
  68d2ad24ef278283f9addf190a2aadd26504efd6

horizon config:
  configs/research/usdjpy_h1_entry_horizon_diagnostic_v1.json

bars:
  canonical January-June Dukascopy M15 bid/ask-derived bars
  including canonical aggregate-repair bars

session exclusions:
  configs/market_sessions/fx_market_sessions_v1.json
```

Signal definitions, directions, entry windows, next-bar entry semantics and hard exclusions remain unchanged.

## Horizons

The fixed close horizons are:

```text
1, 2, 3, 4, 6, 8, 12, 16 and 24 M15 bars
```

The six-bar result must reproduce the corrected H1 screen for A1 before the diagnostic is accepted.

Month boundaries are not crossed. This preserves the canonical H1 screen's month-by-month input semantics and makes the six-bar regression exact. Horizon-specific sample counts near month-end are reported.

## Price-path diagnostics

For entries with a complete 24-bar path, report:

- gross MFE in pips;
- gross MAE in pips;
- default-cost-adjusted MFE and MAE;
- severe-cost-adjusted MFE and MAE;
- bars to MFE;
- bars to MAE.

MFE and MAE are descriptive. They do not represent executable outcomes because the order of an intrabar high and low is not known from M15 OHLC bars.

## Cost convention

Default cost:

```text
max(0.5 pip, entry-bar spread_mean_pips)
```

Severe cost:

```text
3 × max(0.5 pip, entry-bar spread_mean_pips)
+ 0.5 pip slippage per side
```

## Required reporting

For every registered candidate and horizon:

- trades;
- win rate;
- average and total default net pips;
- default profit factor;
- average and total severe net pips;
- severe profit factor;
- monthly trade count and monthly metrics;
- positive-month count.

The artifact must include an `entry_definition_id` map so duplicate registered candidates are not double-counted when interpreting entry evidence.

Across the horizon surface:

- number of positive horizons;
- longest consecutive positive run on the fixed ordered horizon grid;
- minimum, maximum and six-bar average net pips;
- the horizon with the highest average, marked diagnostic only;
- path-level MFE/MAE summaries.

## Interpretation rules

1. The largest result at one horizon is not selected as an exit.
2. An isolated positive point surrounded by negative neighboring horizons is treated as instability, not robustness.
3. Duplicate registered candidates with the same `entry_definition_id` are one entry definition for evidentiary purposes.
4. No candidate enters the active H2 because of this analysis.
5. No H2 gate, entry definition, direction, hour window or event exclusion may be changed.
6. The active H2 result remains A1+hold6 and E3+hold6 only.
7. New entry-plus-exit candidates may be proposed only after the full horizon surface is reviewed.
8. Proposed exit families must be small and mechanism-based, rather than a full Cartesian sweep of hold, SL, TP and trailing parameters.
9. Every proposed entry-plus-exit strategy requires a new pre-registration and a later untouched validation block.
10. Research results do not establish MT4 equivalence. Core/MT4 remains the final source of truth.

## Exit-research sequence after this diagnostic

```text
1. Review forward-return and MFE/MAE surfaces.
2. Define a small number of mechanism-based exit families.
3. Freeze parameter grids and selection rules before running them.
4. Develop exits on a designated development block.
5. Validate the selected complete strategies on a later untouched block.
6. Reproduce the selected strategies in Core/MT4.
```

SL, TP, trailing, breakeven and partial-close branches are not opened simultaneously. Time horizon is examined first; other exit families are introduced in later controlled stages.
