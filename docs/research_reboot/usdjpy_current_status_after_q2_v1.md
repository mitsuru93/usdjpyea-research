# USDJPY Research Status After Q2 v1

## Verified development block

The canonical Dukascopy development block is 2024-01 through 2024-06 with 100% effective coverage and zero final hard errors.

```text
2024-01 baseline: 29307131333
2024-02 baseline: 29383810487
2024-03 baseline: 29421329471
2024-04 baseline: 29455059447
2024-05 baseline: 29469227483
2024-06 baseline: 29475803893
```

## Corrected H1 multi-family screen

```text
run_id: 29547232643
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
artifact_digest: sha256:b5fd40e7c37cd3c4c417b9e02547ce6d7195f0f989266e4f0e3ae0305947ec94
result record: docs/research_reboot/usdjpy_h1_multi_family_screen_v2_result_v1.md
```

Run `29546116205` remains invalid because it used signal-bar entry-hour semantics and a non-canonical spread field.

The two H1-retained complete six-bar strategies were:

```text
A1_impulse_breakout_lb3_hold6
  H1 trades: 391
  H1 avg net pips: +2.015899
  H1 total net pips: +788.216501
  H1 PF: 1.280577

E3_trend_24h_resumption_hold6
  H1 trades: 361
  H1 avg net pips: +1.783355
  H1 total net pips: +643.791082
  H1 PF: 1.305343
```

## Verified H2 source block

All six untouched H2 months, 2024-07 through 2024-12, passed fixed Monday-Friday UTC-hour audits with:

```text
unobserved records: 0
terminal hard errors: 0
effective coverage: 100%
```

The accepted 2024-09 through 2024-12 record is:

```text
docs/research_reboot/usdjpy_h2_2024_09_12_source_and_baseline_result_v1.md
run_id: 29569149852
```

The first-attempt November aggregate artifact `8412658745` is excluded. The accepted November source and baseline artifacts are `8421758330` and `8423419800`.

## Accepted joint H2 result

```text
workflow: Run USDJPY Joint H2 A1 E3 Evaluation v1
run_id: 29628387393
head_sha: 90d18503cf9948029b5a9f73e44499e2cce73d4f
artifact_id: 8424623578
artifact: usdjpy-joint-h2-a1-e3-eval-v1-29628387393
artifact_digest: sha256:182840ea48bf9d375ce718a5c940cee064fbccb4c36b659a80e7678938664364
result record: docs/research_reboot/usdjpy_joint_h2_a1_e3_eval_run_29628387393_result_v1.md
```

All workflow steps succeeded. The six H2 source audits passed, both exact H1 regressions passed, output completeness checks passed, and no Exit optimization or parameter change occurred.

Decision:

```text
A1_impulse_breakout_lb3_hold6: FAIL
E3_trend_24h_resumption_hold6: FAIL
advancing candidates: none
```

### A1 H2

```text
trades: 408
positive months: 0 / 6
minimum monthly trades: 60
avg default net: -4.373667 pips/trade
total default net: -1784.456321 pips
PF: 0.665936
event-excluded avg: -4.273162 pips/trade
event-excluded PF: 0.671629
total excluding best two days: -2052.092362 pips
severe avg: -6.706542 pips/trade
severe PF: 0.533500
hard no-trade violations: 0
```

A1 was negative in every H2 month. Its gross average before spread was already negative at `-3.707230` pips/trade, so transaction cost was not the primary cause.

### E3 H2

```text
trades: 379
positive months: 1 / 6
minimum monthly trades: 54
avg default net: -1.876125 pips/trade
total default net: -711.051333 pips
PF: 0.842863
event-excluded avg: -1.221570 pips/trade
event-excluded PF: 0.890810
total excluding best two days: -980.360109 pips
severe avg: -4.182464 pips/trade
severe PF: 0.682792
hard no-trade violations: 0
```

E3 had one positive month, 2024-09, but failed every preregistered performance and robustness gate. Its gross average before spread was `-1.222955` pips/trade.

The candidates remained distinct:

```text
exact timestamp+direction overlap: 64
daily net-pips correlation: 0.138793
```

## Entry-horizon diagnostic

Run `29582417411` remains invalid because it reset prior-history state at month boundaries.

Accepted diagnostic:

```text
workflow: Run USDJPY H1 Entry-Horizon Diagnostic v2
run_id: 29583719940
artifact: usdjpy-h1-entry-horizon-diagnostic-v2-29583719940
artifact_digest: sha256:f95a0a450aa3b821dbcb20ea4f3410f345668606bf5f20a766a3e01d8a6e89e4
result record: docs/research_reboot/usdjpy_h1_entry_horizon_diagnostic_v2_result_v1.md
```

This diagnostic is development evidence only. It showed that C4, C3, E2 and B2 may support separately specified slower-horizon hypotheses, but it did not promote any strategy.

## Research decision

The current six-bar A1 and E3 strategies are closed.

They do not advance to:

```text
Exit optimization
Core migration
MT4 implementation
EA deployment
```

Neither candidate may be repaired with H2 information. No direction, hour, date, threshold, lookback or hold may be changed and then presented as a continuation of this H2 test.

New hypotheses may be created from H1-only mechanism evidence, including the accepted entry-horizon diagnostic, but each must be treated as a new complete strategy and must receive:

1. a fixed mechanism-based definition;
2. a pre-registration before later-period results are opened;
3. a later untouched validation block;
4. Core/MT4 reproduction only after validation.

## Research roadmap

```text
Step 3A — independent H1 family screening:
  complete

Step 3B — retain six-bar strategy representatives:
  complete

Step 3C — joint A1+hold6 / E3+hold6 H2 pre-registration:
  complete

Step 3D — untouched H2 collection and validation:
  complete

Step 4 — frozen A1+hold6 / E3+hold6 H2 evaluation:
  complete
  neither advances

Entry-horizon development diagnostic:
  v1 invalidated
  v2 accepted

New strategy-family / slower-horizon pre-registration:
  next

Exit-policy research on a validated strategy:
  not started

EA / Core / MT4 implementation:
  not started
```

## Next operations

1. Do not optimize Exit on the failed A1 or E3 strategies.
2. Define a small set of new mechanism-based complete strategies from H1-only evidence, with emphasis on robust horizon regions rather than isolated maxima.
3. Fix a later untouched validation block before opening its results.
4. Collect and audit the later validation data under the corrected fixed-weekday pipeline.
5. Advance to Exit-policy research and Core/MT4 only if a complete strategy survives that validation.
