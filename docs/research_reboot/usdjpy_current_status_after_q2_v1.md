# USDJPY Research Status After Q2 v1

## Verified H1 data block

The verified Dukascopy development block covers 2024-01 through 2024-06 with 100% effective coverage and zero final hard errors.

```text
2024-01 baseline: 29307131333
2024-02 baseline: 29383810487
2024-03 baseline: 29421329471
2024-04 baseline: 29455059447
2024-05 baseline: 29469227483
2024-06 baseline: 29475803893
```

## Closed or rejected branches

```text
M5 pullback continuation:
  closed in current form after Q2 failure

Unfiltered M15 breakout:
  rejected

Session range breakout:
  no candidate retained
  B3 failed only the predeclared aggregate sample gate: 94 < 120

Mean reversion / failed excursion:
  no candidate retained

Compression to expansion:
  no candidate retained

Higher-timeframe trend continuation:
  E1 and E2 rejected
  E3 retained
```

No failed H1 candidate may be added to H2 after the corrected screen result was opened.

## Corrected H1 multi-family result

Authoritative workflow:

```text
run_id: 29547232643
head_sha: a1a96ca0808f31b508b6ee82da345949725acc30
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
artifact_digest: sha256:b5fd40e7c37cd3c4c417b9e02547ce6d7195f0f989266e4f0e3ae0305947ec94
```

The run completed successfully and passed the A1 canonical reproduction assertion.

Canonical result record:

```text
docs/research_reboot/usdjpy_h1_multi_family_screen_v2_result_v1.md
```

The earlier run 29546116205 is invalid because it applied selected entry-hour fields to the signal bar and used a different spread field.

## Retained H2 candidates

### A1 — M15 impulse-confirmed breakout

```text
candidate_id: A1_impulse_breakout_lb3_hold6
trades: 391
positive months: 4 / 6
avg net pips: +2.015899
total net pips: +788.216501
profit factor: 1.280577
Q1 avg net pips: +2.628028
Q2 avg net pips: +1.327254
severe profit factor: 0.981540
event-excluded profit factor: 1.203591
total excluding best two days: +251.580550
```

### E3 — 96-bar trend resumption

```text
candidate_id: E3_trend_24h_resumption_hold6
trades: 361
positive months: 4 / 6
avg net pips: +1.783355
total net pips: +643.791082
profit factor: 1.305343
Q1 avg net pips: +0.816226
Q2 avg net pips: +2.724059
severe profit factor: 0.949636
event-excluded profit factor: 1.246307
total excluding best two days: +394.000132
```

Both candidates remain two-sided. Direction-only variants are not registered.

## Research roadmap position

```text
Step 3A — independent H1 family screening:
  complete

Step 3B — retain representatives:
  complete

Step 3C — joint H2 pre-registration:
  complete

Step 3D — untouched H2 data collection and batch validation:
  current

Step 4 — compare candidates that pass every H2 gate:
  not started

Exit-policy research:
  not started

EA / Core / MT4 implementation:
  not started
```

## Active H2 pre-registration

```text
docs/research_reboot/usdjpy_joint_h2_prereg_a1_e3_v1.md
```

Pre-registration commit:

```text
b89b550c87addd074ac6ab6de5438ad6f8e972ce
```

Validation block:

```text
2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
```

Both candidates are judged independently against the same predeclared gate. Candidate definitions, directions, holds, sessions, sample thresholds, intervention dates and cost scenarios may not be changed after H2 is opened.

## Immediate next action

Collect the July 2024 Dukascopy USDJPY bid/ask tick block with:

```text
Run Public FX Tick Pilot 2024-07 USDJPY
```

Workflow file:

```text
.github/workflows/run_public_fx_tick_pilot_USDJPY_2024_07.yml
```

After July reaches 100% effective coverage and zero final hard errors, preserve its source run ID. Repeat the same collection and monthly processing for August through December, then evaluate A1 and E3 together in one H2 batch. Monthly candidate results must not be used to alter either candidate while collection is in progress.