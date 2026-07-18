# USDJPY Research Roadmap — 2024 H1 Development / H2 Validation v3

## 1. Correction

The previous full-year-2024 development roadmap is superseded.

The correct allocation is:

```text
2024-01-01 through 2024-07-01 exclusive:
  development block

2024-07-01 through 2025-01-01 exclusive:
  candidate-specific unused validation block for newly frozen strategies
```

The 2024 H2 block has been opened only for the two complete strategies:

```text
A1_impulse_breakout_lb3_hold6
E3_trend_24h_resumption_hold6
```

Those two strategies failed and remain closed.

No H2 candidate result has been opened for C1-C4, B1-B3, D1-D2, E1-E2, or any new H1-developed strategy. Therefore 2024 H2 remains unused outcome data for those candidates, provided their complete definitions and gates are frozen from H1-only evidence before their H2 results are run.

Methodological wording:

```text
2024 H2 is not globally untouched at project level because A1/E3 results are known.
2024 H2 remains candidate-specific unused validation data for strategies whose H2 results have never been opened.
```

The known A1/E3 failure may not be used to tune a new strategy's direction, hours, threshold, lookback, hold or Exit.

## 2. Immediate research objective

The work completed so far is a narrow first screen, not an exhaustive strategy programme.

Completed work:

- five broad families;
- thirteen registered candidates;
- twelve unique Entry definitions;
- mostly one common six-bar Exit;
- one H1 horizon diagnostic over nine fixed horizons;
- H2 confirmation of A1+hold6 and E3+hold6 only.

The next objective is to use 2024 H1 much more fully, freeze a broader but controlled set of complete strategies, and evaluate those strategies once on 2024 H2.

## 3. Research rules

1. All new Entry, time, Exit, cost and position rules are developed using 2024 H1 only.
2. No new-candidate result from 2024 H2 may be opened before the registry, shortlist rule and H2 gates are committed.
3. 2024 H2 is evaluated once for the frozen shortlist. No candidate is repaired after its H2 result is opened.
4. A strategy is Entry + allowed time + next-bar execution + Exit + costs + overlap/re-entry rules.
5. Fixed-horizon surfaces are mapped before stop, target or trailing branches are introduced.
6. Isolated best points are rejected; broad neighbouring regions are preferred.
7. No Cartesian sweep of hold, stop, target, trailing, breakeven and partial close is permitted.
8. Multiple testing is controlled by a fixed maximum candidate universe, family caps and a maximum final shortlist.
9. Core and MT4 work begins only after H2 validation and later replication.

## 4. Stage R0 — canonical 2024 bundle and regression lock

Build one authoritative January-December 2024 data bundle from accepted artifacts.

Required resolutions:

```text
M1
M5
M15
H1
```

Required checks per month:

- fixed Monday-Friday UTC-hour expectation;
- unobserved records = 0;
- terminal hard errors = 0;
- effective coverage = 1.0;
- accepted aggregate-repair bars included with timestamp priority;
- duplicate timestamps resolved deterministically;
- actual Entry-bar `spread_mean_pips` retained;
- November uses accepted rerun artifact IDs, not the excluded first attempt.

The bundle must reproduce:

- authoritative H1 A1 and E3 results;
- authoritative H2 A1 and E3 results;
- all thirteen registered-hold H1 results from the corrected screen.

This regression lock validates the data assembly and evaluator. It does not reopen A1 or E3.

## 5. Stage R1 — expanded Entry universe on 2024 H1 only

The thirteen existing candidates remain included but are not exhaustive.

Before any expanded result is run, commit a registry with no more than sixty unique Entry definitions across the following families.

### A. Impulse and rolling-range breakout

Coarse structures only:

```text
lookback: 3, 6, 12, 24 bars
confirmation:
  close beyond prior range
  close beyond prior range plus current range > previous range
  close beyond prior range plus current range > prior-eight-bar median range
```

Maximum: 12 Entry definitions.

### B. Session and prior-range breakout

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

Maximum: 9 Entry definitions.

### C. Failed excursion and range re-entry

References:

```text
rolling 12, 24, 48, 96 bars
Asia 00-06 UTC
Asia 00-07 UTC
prior UTC day
```

Maximum: 7 Entry definitions.

### D. Compression to expansion

Structures:

```text
4 versus prior 4 bars
8 versus prior 8 bars
12 versus prior 12 bars
16 versus prior 16 bars
```

For each:

```text
close breakout only
close breakout plus range expansion
```

Maximum: 8 Entry definitions.

### E. Trend continuation and resumption

Trend windows:

```text
16, 32, 64, 96 M15 bars
```

Resumption structures:

```text
one-bar pullback and break
one fixed multi-bar pullback structure
```

Maximum: 8 Entry definitions.

### F. Session-transition reversal

At most six mechanism-defined candidates around:

```text
post-Asia transition
London transition
New York transition
```

Each must specify reference range, excursion and reversal confirmation before execution.

### G. Volatility-normalized Entry

At most six coarse ATR/range-normalized breakout or reversal definitions. Fine threshold grids are prohibited.

### Universe limit

```text
maximum unique Entry definitions: 60
```

No Entry definition may be added after the first expanded H1 result is opened.

## 6. Stage R2 — H1 fixed-horizon surface

Every Entry definition is evaluated on contiguous 2024 H1 bars using:

```text
1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
```

Required outputs per Entry and horizon:

- trade count;
- gross average and total pips;
- default net average and total pips;
- default PF;
- severe average and PF;
- six monthly results;
- two quarterly results;
- Jan-Feb, Mar-Apr and May-Jun blocks;
- long/short attribution;
- total excluding best three UTC Entry days;
- best-month concentration;
- daily net-pips distribution;
- hard no-trade violations;
- MFE, MAE and time-to-MFE/MAE over a fixed path window.

A robust horizon region requires at least three adjacent tested horizons with coherent positive behaviour, unless a mechanism-defined endpoint is preregistered before results.

## 7. Stage R3 — H1 internal stability diagnostics

These are development diagnostics, not independent validation.

Required H1 stability views:

- six monthly results;
- Q1 versus Q2;
- rolling two-month blocks;
- rolling three-month blocks;
- first half of H1 versus second half of H1;
- spread and realized-volatility regimes using backward-looking descriptors only.

Anchored diagnostics may be used, for example:

```text
rank on Jan-Feb, report Mar
rank on Jan-Mar, report Apr
rank on Jan-Apr, report May
rank on Jan-May, report Jun
```

The ranking score and family caps must be frozen before fold results are generated.

## 8. Stage R4 — H1 selection into controlled Exit research

Common minimum H1 conditions:

```text
positive gross average
positive default average
PF >= 1.10
at least 4 of 6 positive months
positive Q1 and positive Q2
positive total excluding best three UTC Entry days
severe PF >= 0.90
no hard no-trade violation
non-isolated positive horizon region
```

Sample classes:

```text
standard:
  >= 120 H1 trades
  >= 15 trades each month

medium-frequency:
  >= 60 H1 trades
  >= 8 trades each month

sparse:
  < 60 H1 trades
  diagnostic only; not promoted from this six-month development block
```

Selection caps:

```text
maximum two representatives per family
maximum eight Entry/horizon representatives overall
```

Nearby parameterizations of the same mechanism do not occupy separate shortlist slots unless their trade sets and timing are materially distinct.

## 9. Stage R5 — controlled Exit research on 2024 H1

Only R4 representatives enter Exit research.

Baseline:

```text
E0: robust fixed-horizon representative
```

Maximum additional branches per Entry mechanism:

```text
E1: one mechanism-defined failure/invalidation Exit
E2: one mechanism-defined profit-preservation or trailing Exit
E3: optional one mechanism-defined target Exit when justified by H1 path evidence
```

Maximum total Exit policies per Entry mechanism, including E0:

```text
4
```

Execution requirements:

- pure time exits may use M15;
- structural invalidation may use M5 or M1;
- stop/target/trailing ordering uses M1 or tick data when both levels can occur inside one M15 bar;
- overlap, re-entry and same-bar ambiguity rules are frozen before results;
- default and severe cost models remain unchanged.

Exit selection must improve temporal consistency, adverse-tail behaviour or concentration resistance, not only aggregate pips.

No more than one non-baseline Exit per Entry mechanism may be retained for H2.

## 10. Stage R6 — freeze the 2024 H2 validation shortlist

Before opening any new-candidate H2 result, commit:

- no more than five complete strategies;
- exact Entry definitions;
- exact allowed timestamps;
- next-bar Entry semantics;
- exact fixed-hold or selected Exit policy;
- overlap and re-entry rules;
- default and severe costs;
- H1 regression expectations;
- all H2 gates;
- an explicit list of candidate IDs whose H2 results have never been opened.

Multiplicity control:

```text
maximum H2 shortlist: 5 complete strategies
one joint H2 run
independent pass/fail decision per strategy
no winner chosen solely by highest total pips
```

## 11. Stage V1 — candidate-specific unused 2024 H2 validation

Period:

```text
2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
```

All new strategies are run once, unchanged.

The common gate must include:

- all six H2 source audits pass;
- positive aggregate average;
- PF >= 1.10;
- at least four positive months;
- positive total after excluding best two or three UTC Entry days, fixed before execution;
- severe average >= -0.5 pips/trade;
- severe PF >= 0.90;
- candidate-specific sample gates fixed from H1 frequency;
- zero hard no-trade violations;
- exact H1 regression passed.

A failed H2 strategy is closed. H2 may not be used to adjust its Entry, direction, time, hold or Exit.

## 12. Stage V2 — unchanged replication on 2025 H1

Only 2024 H2 survivors proceed unchanged to:

```text
2025-01-01 through 2025-07-01 exclusive
```

This block is a replication test, not an Exit-development block.

A strategy that fails is closed. A strategy that passes proceeds to 2025 H2 replication or final validation as preregistered before its 2025 H1 result is opened.

## 13. Stage V3 — second replication on 2025 H2

```text
2025-07-01 through 2026-01-01 exclusive
```

Only unchanged V2 survivors proceed.

A strategy must survive both 2025 halves before Core migration.

## 14. Core, MT4 and forward shadow

Only V1-V3 survivors proceed.

### Research/Core parity

Require trade-ledger agreement for:

- signal timestamp;
- next-bar Entry timestamp;
- direction;
- Exit timestamp and reason;
- exclusion rule;
- spread basis and cost;
- monthly trade counts;
- net pips within fixed tolerance.

### MT4/Rakuten reproduction

Verify server time, DST, bar construction, next-bar execution, spread, slippage, order rejection and lot rounding without changing research logic.

### Forward shadow

Run frozen logic in demo or non-executing shadow mode. Define duration, trade-count and operational gates before judging the forward result.

## 15. Immediate execution order

```text
1. Mark the incorrect full-year-2024 development roadmap as superseded.
2. Build and hash the canonical 2024 bundle.
3. Reproduce authoritative A1/E3 H1 and H2 results plus all thirteen H1 registered-hold results.
4. Commit the expanded H1 Entry registry, maximum sixty definitions.
5. Run the H1 horizon-surface and stability programme.
6. Select at most eight representatives for controlled H1 Exit research.
7. Freeze at most five complete strategies and all H2 gates.
8. Run one joint candidate-specific unused 2024 H2 validation.
9. Replicate unchanged H2 survivors on 2025 H1 and 2025 H2.
10. Move only repeatedly validated strategies to Core, MT4 and forward shadow.
```
