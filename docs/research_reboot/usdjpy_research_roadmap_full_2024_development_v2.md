# USDJPY Research Roadmap — Full-Year 2024 Development v2

## 1. Status and correction

The prior roadmap that moved directly from the failed A1/E3 H2 result to a three-candidate 2025 validation set is superseded.

The completed 2024-07 through 2024-12 A1/E3 evaluation remains a valid confirmatory rejection of those two complete six-bar strategies:

```text
A1_impulse_breakout_lb3_hold6: failed
E3_trend_24h_resumption_hold6: failed
```

However, after that result was opened, the whole 2024 calendar year may be reused as development and exploratory research data for new strategies. It can no longer provide untouched confirmation for those new strategies.

The next research cycle therefore uses:

```text
2024-01-01 through 2025-01-01 exclusive:
  full development, mechanism comparison, horizon research and Exit research

2025-01-01 onward:
  untouched validation blocks for strategies frozen after the 2024 research programme
```

A1+hold6 and E3+hold6 remain closed. Reusing 2024 does not reopen or rescue them.

## 2. Why the earlier work is not a sufficient strategy search

The work completed so far consisted mainly of:

- five broad families;
- thirteen registered candidate variants;
- twelve unique Entry definitions;
- a common six-bar Exit for most candidates;
- a nine-point horizon diagnostic on those same Entry definitions;
- confirmatory H2 evaluation of only A1+hold6 and E3+hold6.

This is a valid narrow experiment, but it is not a broad EA research programme. It does not justify moving immediately to MT4 or treating the candidate space as exhausted.

The 2024 research programme must now answer three distinct questions:

1. Which Entry mechanisms show repeatable directional information?
2. Over what holding-time region does each mechanism operate?
3. Can a small mechanism-based Exit policy improve a robust fixed-hold baseline without parameter-grid overfitting?

## 3. Research principles

1. 2024 is now one development corpus. Results from any 2024 subperiod are exploratory for future strategies.
2. The strategy object is Entry + allowed time + execution + Exit + cost + position rules.
3. Entry quality is first mapped with fixed time exits before SL, TP or trailing branches are introduced.
4. Candidate families are compared by surfaces and temporal stability, not by one maximum result.
5. Long and short remain included during development unless the mechanism itself is direction-specific before results are opened.
6. No full Cartesian product of Entry, hold, SL, TP, trailing, breakeven and partial close is permitted.
7. Every reported result includes gross P&L, default cost, severe cost, monthly and quarterly attribution, day concentration and sample size.
8. 2025 results may not be opened until the final 2024 shortlist and gates are committed.
9. A 2024-developed strategy must pass later untouched validation before Core or MT4 implementation.

## 4. Stage R0 — build one canonical 2024 research bundle

### Objective

Create one authoritative January-December 2024 USDJPY dataset from the already accepted monthly source and baseline artifacts.

### Required resolutions

```text
M1
M5
M15
H1
```

M15 is the primary Entry and fixed-hold research timeframe. M1 or tick data is required when executable stop/target ordering cannot be determined from M15 OHLC.

### Required source checks

For every month:

- fixed Monday-Friday UTC-hour denominator;
- unobserved records = 0;
- terminal hard errors = 0;
- effective coverage = 1.0;
- aggregate-repair bars included with timestamp priority;
- duplicate timestamps removed deterministically;
- actual Entry-bar `spread_mean_pips` retained;
- accepted November rerun artifact IDs used, not the excluded first attempt.

### Bundle outputs

- one month/artifact manifest;
- one coverage and repair audit;
- contiguous M1/M5/M15/H1 series;
- monthly row counts and boundaries;
- deterministic hashes for every canonical output;
- regression reproduction of the authoritative A1/E3 H1 and H2 results.

A failure to reproduce those known results is an implementation defect and blocks the expanded research.

## 5. Stage R1 — expanded Entry-mechanism universe

The current thirteen candidates remain in the universe but are no longer treated as exhaustive.

The first expanded screen will contain approximately fifty fixed Entry definitions across seven mechanism families. The exact registry must be committed before the expanded full-year result is run.

### Family A — impulse and range breakout

Structured variants:

```text
lookback bars: 3, 6, 12, 24
confirmation:
  close beyond prior range only
  current range > previous range
  current range > rolling median range of prior 8 bars
```

Target count: 12 Entry definitions.

### Family B — session and prior-range breakout

References:

```text
Asia 00-06 UTC
Asia 00-07 UTC
prior UTC day
```

Entry windows:

```text
07-11 UTC
07-16 UTC
12-16 UTC
```

Use the first signal per direction per UTC day.

Target count: 9 Entry definitions.

### Family C — failed excursion and range re-entry

References:

```text
rolling 12 bars
rolling 24 bars
rolling 48 bars
rolling 96 bars
Asia 00-06 UTC
Asia 00-07 UTC
prior UTC day
```

The signal requires an excursion beyond the reference and a close back inside it.

Target count: 7 Entry definitions.

### Family D — compression to expansion

Compression/comparison structures:

```text
4 versus prior 4 bars
8 versus prior 8 bars
12 versus prior 12 bars
16 versus prior 16 bars
```

For each structure compare:

```text
close breakout only
close breakout plus range expansion
```

Target count: 8 Entry definitions.

### Family E — trend continuation and resumption

Trend windows:

```text
16, 32, 64, 96 M15 bars
```

Resumption forms:

```text
one-bar pullback and break
multi-bar pullback and break, with the exact pattern fixed in the registry
```

Target count: 8 Entry definitions.

### Family F — session-transition reversal

Mechanisms fixed before execution around:

```text
post-Asia transition
London transition
New York transition
```

These are not generic hour filters. Each definition must specify the reference range, excursion condition and reversal confirmation.

Target count: 3-6 Entry definitions.

### Family G — volatility-normalized breakout or reversal

A small ATR/range-normalized family may be included to distinguish absolute movement from regime-relative movement.

The registry must limit this family to no more than six Entry definitions. Thresholds must be coarse mechanism levels, not a fine optimization grid.

### Total search-size control

```text
maximum unique Entry definitions in R1: 60
```

Any additional family requires a separate versioned registry and may not be added after the first R1 result is opened.

## 6. Stage R2 — fixed-horizon surface across full-year 2024

Every Entry definition is evaluated using the same fixed-horizon set:

```text
1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
```

This is a horizon map, not permission to select the single highest point.

### Required outputs per Entry and horizon

- trades;
- gross average and total pips;
- default net average and total pips;
- default PF;
- severe average and PF;
- monthly metrics for all twelve months;
- quarterly metrics for all four quarters;
- long and short attribution;
- total excluding best five UTC Entry days;
- share of total from the best month and best quarter;
- daily net-pips distribution;
- exact hard no-trade violations;
- median and quantile MFE/MAE and time-to-MFE/MAE over a fixed path window.

### Horizon-region assessment

A horizon point is not considered robust merely because it is the maximum.

A candidate can proceed only when it has a positive region containing at least three adjacent tested horizons, or a mechanism-defined boundary supported by the neighbouring points.

Isolated peaks such as the former B3 six-bar result are classified as unstable.

## 7. Stage R3 — temporal stability and pseudo-out-of-sample diagnostics within 2024

Because 2024 is development data, these diagnostics do not create untouched validation. Their role is to reject fragile candidates before 2025.

### Calendar stability

Required reports:

- twelve monthly results;
- four quarterly results;
- first half versus second half;
- rolling two-month blocks;
- rolling three-month blocks.

### Anchored walk-forward diagnostic

The fixed registry is evaluated through anchored folds such as:

```text
train Jan-Apr, report May-Jun
train Jan-Jun, report Jul-Aug
train Jan-Aug, report Sep-Oct
train Jan-Oct, report Nov-Dec
```

The algorithm may rank candidates inside each training block using the frozen selection score, but the reported fold result uses the following block only.

No hyperparameter is changed after a fold result is opened.

### Regime attribution

Report candidate performance against coarse exogenous market descriptors computed without future data, including:

- realized volatility regime;
- directional versus range-bound regime;
- session;
- day of week;
- spread regime.

Regime results are diagnostic. A regime filter becomes a new strategy rule and requires its own 2025 preregistration.

## 8. Stage R4 — selection from Entry and horizon evidence

The first selection pass is family-level and stability-based.

### Minimum common requirements

Before a candidate can enter Exit research it must satisfy all of the following on 2024 development data:

```text
positive gross average
positive default average
aggregate PF >= 1.10
at least 3 of 4 positive quarters
at least 7 of 12 positive months
positive total after excluding best five UTC Entry days
severe PF >= 0.90
no hard no-trade violation
non-isolated positive horizon region
```

### Sample classes

```text
standard candidate:
  at least 240 trades in 2024
  at least 40 trades in every quarter

medium-frequency candidate:
  at least 120 trades in 2024
  at least 20 trades in every quarter

sparse candidate:
  fewer than 120 trades
  recorded separately and not promoted from a single-year screen
```

A sparse candidate may only advance through a separately designed multi-year programme.

### Family control

No more than two Entry/horizon representatives per family and no more than eight total representatives may enter R5.

Representatives should cover distinct mechanisms rather than several nearby parameterizations of the same signal.

## 9. Stage R5 — controlled Exit research on 2024

Only R4 survivors enter Exit research.

The validated object at this stage is still development-only.

### Baseline

```text
E0: the robust fixed-horizon representative selected in R4
```

### Maximum additional Exit branches per Entry mechanism

```text
E1: one mechanism-defined invalidation or failure Exit
E2: one mechanism-defined profit-preservation or trailing Exit
E3: optional one mechanism-defined target Exit only when justified by the path distribution
```

No more than four total Exit policies including E0 are evaluated per Entry mechanism.

### Execution resolution

- time exits may use M15;
- bar-dependent invalidation may use M5 or M1;
- stop/target/trailing ordering must use M1 or tick data when both levels can occur inside one M15 bar;
- costs are charged using the same default and severe framework;
- overlapping positions, re-entry and same-bar ambiguity rules must be fixed before results are produced.

### Exit-selection rule

A new Exit must improve mechanism consistency, not only aggregate pips. It must show improvement across multiple quarters or reduce adverse-tail/concentration while retaining positive expectancy.

No more than one non-baseline Exit per Entry mechanism may be retained for 2025 validation.

## 10. Stage R6 — freeze the 2025 validation shortlist

After all 2024 Entry and Exit research is complete, freeze:

- no more than five complete strategies;
- exact Entry conditions;
- exact allowed timestamps;
- exact next-bar execution semantics;
- fixed-hold or selected Exit logic;
- position overlap and re-entry rules;
- cost and severe scenarios;
- source-data requirements;
- H1/full-2024 regression assertions;
- 2025 promotion gates.

The shortlist is committed before any 2025 candidate result is opened.

No strategy advances because it has the highest 2024 total alone.

## 11. Stage V1 — untouched 2025 H1 confirmation

```text
2025-01-01 through 2025-07-01 exclusive
```

Each frozen complete strategy is judged independently.

The preregistered V1 gate will require source completeness, sample sufficiency, positive aggregate expectancy, PF, monthly breadth, severe-cost behaviour, concentration resistance, zero hard no-trade violations and full-2024 implementation regression.

A failed strategy is closed and not repaired on 2025 H1.

## 12. Stage V2 — untouched 2025 H2 replication

```text
2025-07-01 through 2026-01-01 exclusive
```

Only V1 survivors enter V2, unchanged.

V2 is replication, not Exit development. Entry, Exit and all thresholds remain frozen.

A strategy must survive both 2025 halves before Core migration.

## 13. Core, MT4 and forward operation

Only V1 and V2 survivors proceed.

### Research/Core parity

Require exact trade-ledger agreement for signal, Entry, direction, Exit, exclusion, cost and monthly trade counts within a fixed numerical tolerance.

### MT4/Rakuten reproduction

Verify broker-server time, DST mapping, bar construction, Entry timing, spread, slippage, rejection and lot rounding without changing strategy logic.

### Forward shadow

Run frozen logic in non-executing or demo mode and predefine the evaluation duration, trade count and operational acceptance gates before judging the forward result.

## 14. What is not permitted

- repairing A1 or E3 with their H2 result;
- treating 2024 full-year research as untouched validation;
- promoting a single isolated horizon maximum;
- choosing long-only or short-only after seeing attribution without defining a new strategy;
- adding new Entry definitions after the R1 result is opened;
- fine-grained parameter sweeps;
- moving to MT4 before 2025 replication.

## 15. Immediate execution order

```text
1. Mark the prior three-candidate roadmap as superseded.
2. Build and hash the canonical full-year 2024 research bundle.
3. Reproduce the known A1/E3 H1 and H2 results from that bundle.
4. Commit the expanded R1 Entry registry, maximum 60 unique Entry definitions.
5. Implement and run the full 2024 horizon-surface and temporal-stability screen.
6. Select no more than eight family-distinct representatives for controlled Exit research.
7. Run R5 Exit research on 2024 using at most four Exit policies per mechanism.
8. Freeze no more than five complete strategies.
9. Pre-register and run untouched 2025 H1 confirmation.
10. Replicate unchanged survivors on untouched 2025 H2.
11. Move only dual-validated survivors to Core, MT4 and forward shadow.
```
