# USDJPY Entry-Horizon Research Protocol v2

## Status

This protocol supersedes `usdjpy_entry_horizon_research_protocol_v1.md`.

Run `29582417411` is invalid for cross-candidate horizon interpretation because its runner generated signals separately inside each calendar month. The authoritative H1 screen concatenates January-June before signal generation. Resetting history at month boundaries removed valid first-trading-day entries for candidates requiring prior-session or multi-hour history.

The active confirmatory H2 remains unchanged:

```text
A1_impulse_breakout_lb3_hold6 + six-M15-bar exit
E3_trend_24h_resumption_hold6 + six-M15-bar exit
```

## Research questions

Confirmatory H2 asks whether A1+hold6 and E3+hold6 reproduce on the untouched July-December 2024 block. The entry-horizon diagnostic separately asks how all frozen H1 entry definitions behave across fixed forward horizons on the January-June development block.

The diagnostic cannot alter the active H2.

## Frozen inputs

```text
candidate registry:
  configs/research/usdjpy_h1_multi_family_candidates_v1.json

registry blob SHA:
  68d2ad24ef278283f9addf190a2aadd26504efd6

horizon config:
  configs/research/usdjpy_h1_entry_horizon_diagnostic_v2.json

runner:
  tools/run_usdjpy_h1_entry_horizon_diagnostic_v2.py
```

Signal definitions, directions, entry windows, next-bar entry semantics, spread convention and hard exclusions remain unchanged.

## Development-block semantics

January-June M15 bars are loaded per source month, deduplicated using the canonical repair priority, concatenated into one chronological development block and only then passed to each signal generator.

Signals and exits may cross internal month boundaries. This matches the authoritative H1 screen. No July bar is loaded, so positions lacking a complete forward horizon at the end of June are omitted for that horizon.

## Horizons and path diagnostics

Fixed close horizons:

```text
1, 2, 3, 4, 6, 8, 12, 16 and 24 M15 bars
```

For entries with a complete 24-bar path, report gross and cost-adjusted MFE/MAE plus bars to MFE/MAE. MFE and MAE remain descriptive because M15 OHLC does not reveal intrabar high-low ordering.

## Acceptance tests

The diagnostic is accepted only if:

1. All 13 candidates match the authoritative corrected H1 screen at each candidate's registered hold period.
2. Trade count, average net pips, total net pips, profit factor, severe average and severe profit factor all match within fixed numerical tolerance.
3. C1 and C2 map to the same entry definition.
4. Metadata reports 13 registered candidates and 12 unique entry definitions.
5. Metadata reports `h2_data_read: false` and `promotion_decision: false`.

An A1-only regression is not adequate because A1 does not require history across the affected month boundaries.

## Interpretation rules

- No single best horizon is promoted as an exit.
- Neighboring horizons and monthly stability are evaluated as a response surface.
- Duplicate entry definitions are not treated as independent evidence.
- No failed H1 candidate is inserted into the active H2.
- Any proposed entry-plus-exit strategy requires a new pre-registration and a later untouched validation block.
- SL, TP, trailing, breakeven and partial-close branches are not opened simultaneously.
- Core/MT4 reproduction remains required after research validation.
