# USDJPY 2023 Architecture Atlas Preregistration v1

## Purpose

Build a descriptive Atlas for the 963 closed trades that passed exact Research/Rakuten-MT4 parity in the 2023 canonical baseline.

The Atlas is not a candidate search. It must not create entry rules, rank thresholds, access 2024 H2 or use any 2025 evidence.

## Exact source set

- Binding MT4 Run: `29998477805`
- Binding artifact ID: `8560057457`
- Binding artifact SHA-256:
  `bf2cd6e94ba4a15f764e784f4a82b8d07edd3070ab198bbf9bc27112e931f63b`
- MT4 audit SHA-256:
  `a7349269db2072e24e694847e0c5517a90d10edd387aedb8baffa788caf008ff`
- Preparation artifact ID: `8559483151`
- Preparation artifact SHA-256:
  `22d66bf76c60362b78e9badff2113bc196b80e3657f5083ae470d1d62df70c01`
- Expected trade ledger SHA-256:
  `33d08d580d584f533bc5f9dda510184fb86c668608f76f8e9b7c014924c5f1b8`
- Normalized M15 SHA-256:
  `4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78`

The sole period-end open F05 trade is excluded because no frozen realized close outcome exists inside 2023.

## Atlas structure

The entry-feature table contains only information known at or before the executable entry. It covers:

1. explicit breakout geometry;
2. signal-bar acceptance;
3. ATR and pre-entry path;
4. active portfolio and overlap state;
5. calendar/session context;
6. whether the entry falls in an M15 bucket built from fewer than 15 source M1 bars.

Outcome/path columns are stored separately and joined only by the exact canonical trade key:

`strategy, signal_utc, entry_utc, side`

Outcome fields include realized P/L, executable-bar MFE/MAE, elapsed time to extremes, fixed forward marks, giveback and the four frozen path classes.

## Frozen path classes

- `WINNER`: final gross pips are nonnegative;
- `P1_GIVEBACK_TO_LOSS`: losing trade with at least 10 pips MFE;
- `P2_MINOR_FAVORABLE_THEN_LOSS`: losing trade with positive but less than 10 pips MFE;
- `P3_NEVER_PROFITABLE`: losing trade whose MFE never became positive.

## Reconciliation gates

- 963 closed trades;
- B02 closed: 232;
- F05 closed: 731;
- realized net: JPY -9,904;
- zero missing, unexpected or duplicate keys;
- zero gross-pips mismatches;
- zero future-derived columns in the entry-feature table;
- zero hard-excluded entry violations;
- zero use of the known regressed Deinit timestamp rows.

## Permitted outputs

Descriptive summaries may be produced by:

- strategy;
- entry exposure state;
- path class;
- month;
- incomplete-source-bar exposure.

No threshold screen, candidate ranking or rule selection is permitted in this build.

## Next decision

After the Atlas passes, inspect which loss architecture recurs within 2023. Candidate formulation remains blocked until the corresponding 2024 H1 UTC-derived session and trade-key fields are rebuilt under the same canonical clock.
