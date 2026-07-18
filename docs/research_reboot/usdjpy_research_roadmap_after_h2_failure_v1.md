# USDJPY Research Roadmap After A1/E3 H2 Failure v1

## 1. Current decision

The confirmatory 2024-07 through 2024-12 H2 evaluation is complete.

```text
A1_impulse_breakout_lb3_hold6: failed
E3_trend_24h_resumption_hold6: failed
advancing candidates: none
```

A1+hold6 and E3+hold6 are closed complete strategies. They will not receive Exit rescue, direction removal, hour changes, date exclusions, threshold changes, Core migration or MT4 implementation.

The accepted H1 entry-horizon diagnostic remains development evidence only. It may support new hypotheses, but no strategy was promoted by that diagnostic.

## 2. Research principles for the next cycle

1. A strategy is the complete combination of entry, permitted time, execution rule, Exit, cost model and position rules.
2. No result from 2024-07 through 2024-12 may be used to repair A1 or E3.
3. New hypotheses must be defined from H1-only mechanism evidence before later-period candidate outcomes are opened.
4. The next confirmatory set is limited to at most three complete strategies.
5. A robust horizon region is preferred over an isolated best point.
6. No Cartesian sweep of hold, stop, target, trailing, breakeven and partial close is permitted.
7. Every data block receives a fixed weekday-hour audit, zero-terminal-error gate and exact implementation regression.
8. A candidate that fails a confirmatory block is closed. It is not repaired on that same block.
9. Core and MT4 work begins only after a complete strategy survives final untouched validation.

## 3. Data-block allocation

The chronology for the next research cycle is fixed as follows.

```text
2024-01-01 through 2024-07-01 exclusive:
  completed development evidence
  candidate mechanisms and initial fixed holds only

2024-07-01 through 2025-01-01 exclusive:
  completed A1/E3 confirmatory H2
  not reused to tune or validate the new shortlist

2025-01-01 through 2025-07-01 exclusive:
  new-strategy confirmatory validation V1

2025-07-01 through 2026-01-01 exclusive:
  Exit-policy development for V1 survivors only

2026-01-01 through 2026-07-01 exclusive:
  final untouched validation of the complete entry-plus-Exit strategy

2026-07 onward:
  broker reproduction and forward shadow observation
```

The 2025 and 2026 candidate results must not be opened before the applicable pre-registration is committed.

## 4. Stage 5A — freeze the new shortlist

### Objective

Create no more than three complete strategies from the accepted H1-only horizon evidence.

### Recommended primary shortlist

#### N1 — C4 slow Asia-range failed excursion

```text
entry mechanism: existing C4 Asia 00-06 range failed excursion
fixed hold: 16 M15 bars
rationale: first tested point in the 16-24 bar strong region where severe PF exceeded 1.0
```

The 24-bar point is not selected merely because it had the highest H1 average. Sixteen bars represents the beginning of the robust slow-reversal region and reduces dependence on the endpoint maximum.

#### N2 — C3 medium-horizon rolling failed excursion

```text
entry mechanism: existing C3 rolling 24-bar failed excursion
fixed hold: 12 M15 bars
rationale: centre of the positive 8-16 bar region
```

Twelve bars is treated as the mechanism-centred representative of a broad region, not as permission to search the same later block across 8, 12 and 16 bars.

#### N3 — E2 slow trend resumption

```text
entry mechanism: existing E2 eight-hour trend-resumption signal
fixed hold: 24 M15 bars
rationale: distinct trend-continuation mechanism and positive H1 result under severe cost
classification: higher overfit risk because shorter neighbouring horizons were much weaker
```

N3 receives the same gate as the other candidates. Its higher development risk is not compensated by a weaker validation threshold.

### Deferred candidate

```text
B2 Asia 00-07 breakout at 16-24 bars
```

B2 is deferred because its H1 entry population was only 99. It may be revisited in a separately pre-registered sparse-signal programme, but it is not added to the primary three-candidate confirmatory set.

### Required outputs before V1

- machine-readable candidate registry;
- exact entry and Exit definitions;
- allowed entry timestamps and hard no-trade rule;
- cost scenarios;
- common V1 gates;
- H1 regression assertions for every candidate;
- explicit statement that no 2025 candidate result has been opened.

## 5. Stage 5B — collect and audit 2025 H1

### Period

```text
2025-01-01T00:00:00Z through 2025-07-01T00:00:00Z exclusive
```

### Data requirements

- Dukascopy USDJPY bid/ask tick source;
- M15 signal and outcome bars;
- `spread_mean_pips` from the actual entry bar;
- base spread `max(0.5 pips, spread_mean_pips)`;
- severe cost: spread basis x3 plus 0.5 pip slippage per side;
- fixed Monday-Friday UTC-hour denominator;
- `unobserved_records: 0`;
- terminal hard errors: 0;
- aggregate-repair bars included and given timestamp priority;
- hard no-trade mask applied to the actual next-bar entry timestamp.

The generic session-baseline output remains diagnostic and may not change candidate definitions.

## 6. Stage 5C — V1 confirmatory evaluation

Each candidate is judged independently. No winner is selected merely from the highest total.

The V1 pre-registration must fix, at minimum:

- all six monthly source blocks accepted;
- at least four positive months;
- aggregate average net pips > 0;
- aggregate PF >= 1.10;
- total excluding the best two UTC entry days > 0;
- severe average net pips >= -0.5;
- severe PF >= 0.90;
- no hard no-trade violation;
- exact H1 regression passed;
- candidate-specific aggregate and minimum-month sample gates fixed from H1 populations before V1 is opened.

No retrospective event date may be removed unless it is explicitly registered before V1 execution.

### V1 decision branches

```text
no candidate passes:
  close N1-N3
  return to genuinely new independent mechanisms
  do not begin Exit research

one candidate passes:
  only that candidate enters Exit-policy development

multiple candidates pass:
  all passing candidates may enter Exit-policy development
  no candidate is eliminated only because another has higher total pips
```

## 7. Stage 6 — Exit-policy development on 2025 H2

### Eligibility

Only a strategy that passes V1 may enter this stage.

### Period

```text
2025-07-01T00:00:00Z through 2026-01-01T00:00:00Z exclusive
```

### Sequence

1. Measure post-entry path, MFE, MAE, time to MFE/MAE and profit giveback.
2. Preserve the V1 fixed hold as the baseline Exit.
3. Define mechanism-based Exit branches before comparing results.
4. Test a small branch set rather than a parameter grid.
5. Select no more than one new Exit policy per surviving entry mechanism for final validation.

### Maximum branch structure per survivor

```text
E0: validated fixed-hold baseline
E1: one mechanism-defined failure / invalidation Exit
E2: one mechanism-defined profit-preservation or trailing Exit
```

SL, TP, trailing, breakeven and partial-close combinations may not be multiplied into a Cartesian sweep. M15 OHLC MFE/MAE values are descriptive; executable stop/target research must use M1 or tick ordering where required.

The 2025 H2 block becomes Exit-development data after this stage and cannot serve as final validation.

## 8. Stage 7 — final untouched validation on 2026 H1

### Period

```text
2026-01-01T00:00:00Z through 2026-07-01T00:00:00Z exclusive
```

Before opening results, freeze:

- complete entry and Exit logic;
- cost and slippage scenarios;
- position overlap and re-entry rules;
- all promotion gates;
- regression assertions;
- any official diagnostic event dates.

The final test compares the validated fixed-hold baseline and, if one was selected, the single mechanism-based Exit variant. A strategy advances only if the complete implementation passes every final gate. A failed final candidate is closed and is not repaired on 2026 H1.

## 9. Stage 8 — research/Core parity

Only final-validation survivors enter Core.

Required parity checks:

- identical signal timestamp;
- identical next-bar entry timestamp;
- identical direction;
- identical Exit timestamp and reason;
- identical hard no-trade exclusions;
- identical spread basis and severe-cost calculation;
- identical trade count by month;
- net-pips equality within the predeclared floating-point tolerance.

Any mismatch is an implementation defect until explained and resolved. Research and Core results may not be averaged or reconciled informally.

## 10. Stage 9 — MT4/Rakuten reproduction

After Core parity:

1. Implement the strategy in MT4 without changing research logic.
2. Map UTC and broker-server timestamps, including DST handling.
3. Verify bar construction and next-bar execution semantics.
4. Reproduce trade timestamps and directions on a common test slice.
5. Apply Rakuten spread, slippage, order rejection and lot-rounding rules.
6. Compare research, Core and MT4 trade ledgers.

A strategy does not become deployable merely because the Python result passed.

## 11. Stage 10 — forward shadow and risk model

From 2026-07 onward:

- run on demo or non-executing shadow mode;
- preserve frozen entry and Exit parameters;
- log intended order, actual spread, slippage proxy and missed/rejected orders;
- define forward acceptance duration and trade-count thresholds before judging the shadow result;
- design lot sizing, maximum simultaneous exposure, daily loss limit and strategy shutdown rules only after execution behaviour is measured.

Live capital allocation occurs only after the forward gate and operational checks pass.

## 12. Work that is explicitly not next

The following are not next operations:

- optimizing A1 or E3 Exit;
- retesting all 13 candidates across many holds on 2025 data;
- lowering sample or PF gates;
- selecting long-only or short-only from H2 attribution;
- implementing an EA before final validation;
- adding other currency pairs before the USDJPY research-to-MT4 pipeline is proven end to end.

## 13. Immediate execution order

```text
1. Commit the N1-N3 candidate and V1 gate pre-registration.
2. Implement H1 regression tests for N1-N3.
3. Collect and fixed-weekday-audit 2025-01 through 2025-06.
4. Run one joint V1 evaluation without parameter changes.
5. If none pass, stop this branch and design new mechanisms.
6. If any pass, collect/audit 2025-07 through 2025-12 for controlled Exit development.
7. Freeze at most one new Exit per survivor.
8. Collect/audit and run final 2026-01 through 2026-06 validation.
9. Move only final survivors to Core, MT4 and forward shadow.
```
