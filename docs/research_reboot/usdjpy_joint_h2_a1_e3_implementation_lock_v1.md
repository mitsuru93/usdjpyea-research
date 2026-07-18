# USDJPY Joint H2 A1/E3 Implementation Lock v1

## Status

This document fixes evaluator semantics before any A1/E3 result from the 2024-07 through 2024-12 block is opened.

It does not change the candidate definitions or promotion gate in:

```text
docs/research_reboot/usdjpy_joint_h2_prereg_a1_e3_v1.md
```

The frozen machine-readable configuration is:

```text
configs/research/usdjpy_joint_h2_a1_e3_eval_v1.json
```

## Contiguous-history semantics

A1 and E3 signals are generated on one chronological M15 sequence consisting of the accepted 2024-01 through 2024-12 bars.

The 2024-01 through 2024-06 bars are used only as pre-H2 history when generating signals near the 2024-07-01 boundary. They do not contribute H2 trades or H2 P&L.

A retained H2 trade must satisfy both:

```text
entry timestamp >= 2024-07-01T00:00:00Z
exit timestamp < 2025-01-01T00:00:00Z
```

This prevents artificial loss of the first A1 lookback and the first 96-bar E3 trend window while keeping every scored entry and exit inside the preregistered H2 block.

## Data semantics

For every month:

- source day M15 bars are loaded;
- accepted monthly baseline aggregate-repair M15 bars are added;
- duplicate timestamps are resolved with aggregate-repair bars taking priority;
- `spread_mean_pips` from the actual entry bar is used;
- spread basis is `max(0.5 pips, spread_mean_pips)`;
- the hard no-trade mask is applied to the actual next-bar entry timestamp.

The accepted H2 baseline artifacts are fixed in the evaluator configuration. November must use baseline artifact ID `8423419800`; the first-attempt November aggregate artifact ID `8412658745` remains excluded.

## H1 regression

Before H2 results are accepted, the evaluator must reproduce the exact authoritative H1 metrics for both candidates within absolute tolerance `1e-9`.

The exact expected values are stored in the evaluator configuration and originate from artifact ID `8394436272` from run `29547232643`.

Failure of any H1 regression metric invalidates the evaluator run before H2 interpretation.

## H2 outputs

The evaluator must produce:

- candidate aggregate default and severe metrics;
- all six monthly metrics, including zero-trade months if any;
- event-excluded metrics for 2024-07-11 and 2024-07-12;
- total net pips after excluding each candidate's best two UTC entry days;
- long/short attribution;
- hard no-trade violation count;
- exact A1/E3 entry timestamp-and-direction overlap;
- daily net-pips correlation;
- descriptive combined trade-day exposure;
- one pass/fail record for every preregistered gate.

Each candidate is judged independently. H2 totals may not be used to modify a candidate or choose new parameters.

## Decision rules

```text
both pass: both advance
one passes: only that candidate advances
neither passes: neither is repaired with H2 information
```

No Exit optimization, direction removal, hour change, date removal, gate reduction or candidate combination is permitted during this evaluator run.
