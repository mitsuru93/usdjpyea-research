# USDJPY 2025 Full-Year Unchanged Replication Preregistration v1

## Decision

The 2024 programme is complete for the two surviving frozen strategies:

- `R1B02_legacy_asia_00_07_breakout__T0_fixed_time_cap`
- `R1F05_donchian_96__T0_fixed_time_cap`

Research/Core/MT4 parity and the finite Phase 2 engineering gates are complete. The next historical gate is one unchanged full-year replication over:

```text
2025-01-01T00:00:00Z
through
2026-01-01T00:00:00Z exclusive
```

This document and its machine-readable configuration are committed before collecting or opening any 2025 strategy outcome.

Authoritative configuration:

```text
configs/research/usdjpy_2025_full_year_replication_v1.json
```

## Role of 2025

2025 is a capital-allocation replication gate. It is not a new development period and it is not split into mandatory H1 and H2 selection gates.

The evaluator must report monthly, quarterly and half-year attribution, but the decision is made on the continuous full-year block. No month, quarter or half-year may be used to redesign either strategy.

## Frozen strategy contract

The replication imports the accepted 2024 V1 evidence by exact identity:

```text
accepted run: 29673802426
artifact ID: 8438161821
artifact digest: sha256:19acb99e0ad286b3d2593b6f9df59a6675920eb3734d5901b70e4d8dc9a7c6b8
release tag: usdjpy-v1-candidate-specific-h2-validation-v1
```

Only the two accepted individual survivors are evaluated. Their Entry, time cap, Exit, re-entry, hard-exclusion and cost rules remain unchanged.

### B02

- session range: 00:00–07:00 UTC;
- close breakout;
- first signal per direction and UTC day;
- entry at the next available M15 mid open;
- fixed-time Exit after 48 M15 bars;
- same entry/exit UTC month required.

### F05

- Donchian lookback: 96 completed M15 bars;
- close breakout with prior-bar crossing reset;
- entry at the next available M15 mid open;
- fixed-time Exit after 32 M15 bars;
- same entry/exit UTC month required.

Default and severe costs remain:

```text
default = max(0.5 pips, entry spread mean)
severe = default * 3 + 1 pip
```

## Individual pass gates

Each strategy passes only when every condition below is true.

### Sample and aggregate economics

```text
trades >= 120
average default net pips > 0
average severe net pips > 0
default profit factor > 1
severe profit factor > 1
```

The trade minimum is twice the preregistered six-month H2 minimum because the replication block is twice as long. It is not derived from any 2025 observation.

### Calendar distribution

```text
default-positive months >= 8 of 12
severe-positive months >= 6 of 12
default-positive quarters >= 3 of 4
severe-positive quarters >= 2 of 4
```

All twelve months and all four quarters are reported. Requiring every month or every quarter to be positive is explicitly rejected as unnecessarily strict.

H1 and H2 totals are reported but are not separate mandatory gates. The quarterly requirements already prevent a strategy from passing on one isolated part of the year while avoiding an unnecessary two-stage holdout procedure.

### Concentration

```text
total default net pips excluding the best two UTC Entry dates > 0
largest absolute calendar-month contribution share <= 0.60
top two UTC Entry dates' share of positive daily pips <= 0.50
maximum absolute long/short contribution share <= 0.95
```

These match the accepted H2 concentration philosophy. No tighter threshold is introduced solely because the block is longer.

## Metrics reported but not used as pass gates

The evaluator must report:

- default and severe maximum drawdown in pips;
- drawdown duration in trades;
- rolling three-month results;
- H1 versus H2 attribution;
- entry-spread distribution;
- exact trade-ledger SHA-256.

Maximum drawdown is not a historical pass gate in this version. Translating pips into an account-level drawdown limit requires a separately frozen lot-sizing and portfolio-allocation rule. Rejecting a strategy against an arbitrary pre-allocation pip threshold would mix strategy replication with capital sizing.

## Decision handling

- B02 and F05 are judged independently.
- H2 rank is irrelevant and no 2025 ranking is permitted.
- A failed strategy is closed for live capital allocation.
- A failed strategy remains preserved as a research and engineering artifact.
- One strategy cannot rescue the other.
- An equal-weight joint portfolio is diagnostic only.
- No failed gate may be relaxed after results are opened.
- No 2025 result may be used to alter Entry, Exit, cost or time parameters.

## Data sequence

The authorized sequence is:

1. freeze this preregistration and its machine-readable lock;
2. collect immutable 2025 USDJPY raw Bid/Ask ticks;
3. validate every hourly and daily source packet;
4. build and lock one canonical 2025 M15 bundle;
5. verify the 2025 evaluator without calculating strategy outcomes;
6. run B02 and F05 once on the locked bundle;
7. publish the complete ledger, diagnostics and independent decisions.

The preregistration itself does not open 2025 strategy results and does not authorize live capital.
