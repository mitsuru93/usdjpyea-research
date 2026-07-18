# USDJPY Joint H2 A1/E3 Evaluation Result v1

## Run

```text
workflow: Run USDJPY Joint H2 A1 E3 Evaluation v1
run_id: 29628387393
head_sha: 90d18503cf9948029b5a9f73e44499e2cce73d4f
artifact_id: 8424623578
artifact: usdjpy-joint-h2-a1-e3-eval-v1-29628387393
artifact_digest: sha256:182840ea48bf9d375ce718a5c940cee064fbccb4c36b659a80e7678938664364
```

All workflow steps completed successfully.

## Acceptance checks

- Frozen evaluator configuration validated.
- All six H2 source months passed the fixed weekday-hour audit.
- Every month had `unobserved_records: 0`, `hard_error_records: 0`, and `effective_coverage: 1.0`.
- The authoritative H1 results for A1 and E3 were reproduced within absolute tolerance `1e-9`.
- No parameter change or Exit optimization occurred after H2 was opened.
- The evaluator produced all required candidate, monthly, gate, direction, daily, overlap and metadata outputs.

## Decision

```text
A1_impulse_breakout_lb3_hold6: FAIL
E3_trend_24h_resumption_hold6: FAIL
advancing_candidates: none
decision: neither_advances
```

Neither candidate may be repaired using H2 information.

## A1 result

```text
trades: 408
positive months: 0 / 6
minimum monthly trades: 60
average default net: -4.373667 pips/trade
total default net: -1784.456321 pips
profit factor: 0.665936
average gross before spread: -3.707230 pips/trade
average default cost: 0.666437 pips/trade

event-excluded trades: 407
event-excluded average: -4.273162 pips/trade
event-excluded PF: 0.671629

total excluding best two UTC days: -2052.092362 pips
severe average: -6.706542 pips/trade
severe PF: 0.533500
hard no-trade violations: 0
```

Monthly default-cost averages:

| Month | Trades | Avg net pips | PF |
|---|---:|---:|---:|
| 2024-07 | 68 | -1.079578 | 0.893322 |
| 2024-08 | 66 | -5.543834 | 0.672388 |
| 2024-09 | 60 | -6.782497 | 0.543371 |
| 2024-10 | 65 | -3.294563 | 0.679388 |
| 2024-11 | 73 | -3.923098 | 0.720543 |
| 2024-12 | 76 | -5.758808 | 0.540614 |

Direction attribution:

```text
long: 213 trades, -1.749087 pips/trade, PF 0.840451
short: 195 trades, -7.240517 pips/trade, PF 0.530401
```

A1 failed eight performance gates:

```text
positive_months
aggregate_avg
aggregate_pf
event_excluded_avg
event_excluded_pf
ex_best_two
severe_avg
severe_pf
```

It passed source coverage, aggregate and monthly sample, hard no-trade and H1 regression gates.

## E3 result

```text
trades: 379
positive months: 1 / 6
minimum monthly trades: 54
average default net: -1.876125 pips/trade
total default net: -711.051333 pips
profit factor: 0.842863
average gross before spread: -1.222955 pips/trade
average default cost: 0.653170 pips/trade

event-excluded trades: 374
event-excluded average: -1.221570 pips/trade
event-excluded PF: 0.890810

total excluding best two UTC days: -980.360109 pips
severe average: -4.182464 pips/trade
severe PF: 0.682792
hard no-trade violations: 0
```

Monthly default-cost averages:

| Month | Trades | Avg net pips | PF |
|---|---:|---:|---:|
| 2024-07 | 65 | -1.374496 | 0.889433 |
| 2024-08 | 64 | -6.818006 | 0.635461 |
| 2024-09 | 65 | +0.439986 | 1.040580 |
| 2024-10 | 54 | -1.126839 | 0.874075 |
| 2024-11 | 64 | -0.360288 | 0.964273 |
| 2024-12 | 67 | -1.941016 | 0.810593 |

Direction attribution:

```text
long: 201 trades, -2.273841 pips/trade, PF 0.805717
short: 178 trades, -1.427019 pips/trade, PF 0.883084
```

E3 failed the same eight performance gates as A1 and passed the same five structural/sample gates.

## Additional audit

The failure is not caused by transaction costs alone:

```text
A1 gross average before spread: -3.707230 pips/trade
E3 gross average before spread: -1.222955 pips/trade
```

Removing the official 2024-07-11 and 2024-07-12 intervention dates does not restore either candidate. Removing each candidate's best two UTC days also leaves aggregate loss.

The candidates remain distinct:

```text
exact entry timestamp+direction overlap: 64
overlap share of A1: 15.69%
overlap share of E3: 16.89%
daily net-pips correlation: 0.138793
shared trade days: 119
union trade days: 131
```

## Research interpretation

The H1 result did not replicate in the untouched 2024-07 through 2024-12 block. A1 deteriorated across every H2 month. E3 was less negative but produced only one positive month and failed all robustness/performance gates.

The current six-bar A1 and E3 strategies are closed and do not advance to Exit optimization, Core migration or MT4 implementation.

The accepted H1 entry-horizon diagnostic remains development evidence only. New slower-horizon or different-mechanism hypotheses may be specified from H1-only evidence, but they must be treated as new strategies, pre-registered, and tested on a later untouched block. H2 results may not be used to tune or rescue A1 or E3.
