# USDJPY Research Status After Q2 v1

## Verified development data block

The canonical Dukascopy development block covers 2024-01 through 2024-06 with 100% effective coverage and zero final hard errors.

```text
2024-01 baseline: 29307131333
2024-02 baseline: 29383810487
2024-03 baseline: 29421329471
2024-04 baseline: 29455059447
2024-05 baseline: 29469227483
2024-06 baseline: 29475803893
```

## Corrected H1 multi-family screen

Authoritative run:

```text
run_id: 29547232643
head_sha: a1a96ca0808f31b508b6ee82da345949725acc30
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
artifact_digest: sha256:b5fd40e7c37cd3c4c417b9e02547ce6d7195f0f989266e4f0e3ae0305947ec94
```

The run passed the A1 canonical reproduction assertion.

```text
docs/research_reboot/usdjpy_h1_multi_family_screen_v2_result_v1.md
```

Run `29546116205` is invalid because it applied selected entry-hour fields to the signal bar and used a non-canonical spread field.

## Active confirmatory H2 candidates

### A1 — M15 impulse breakout plus six-bar exit

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

### E3 — 96-bar trend resumption plus six-bar exit

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

These are complete entry-plus-six-bar strategies. They are not described as exit-independent winning entries. Both remain two-sided.

## Active H2 pre-registration

```text
docs/research_reboot/usdjpy_joint_h2_prereg_a1_e3_v1.md
commit: b89b550c87addd074ac6ab6de5438ad6f8e972ce
validation block: 2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
```

Candidate definitions, directions, six-bar holds, sessions, sample gates, intervention dates and cost scenarios remain frozen. PR #59, which proposed replacing this with an all-13-candidate H2 and lower sample gates, was closed without merge.

## Verified H2 source and monthly processing

### 2024-07

```text
source run_id: 29544395435
source artifact: public-fx-data-pilot-2024-07-USDJPY-aggregate-29544395435
source digest: sha256:0698a05fc17d15cd9e3c405cb1367a02e6a10230ab69bbb29bceb61b62f34672
source effective coverage: 100%
source hard errors: 0

baseline run_id: 29556241138
baseline artifact: fx-session-baseline-2024-07-USDJPY-29556241138
baseline digest: sha256:e7dfc13f5186f29f0d9e83bf5554e30f615821638d4fde11fe0be353d1e6d6d2
aggregate repair records: 0
```

### 2024-08

```text
source run_id: 29556953388
source artifact: public-fx-data-pilot-2024-08-USDJPY-aggregate-29556953388
source digest: sha256:a1769e23ffa5a1c5bacd1e45bbf86c58ee159a4021eb2a1c3ebe7bb331c79230
source effective coverage: 100%
source hard errors: 0

baseline run_id: 29567447264
baseline artifact: fx-session-baseline-2024-08-USDJPY-29567447264
baseline digest: sha256:e5dd5f183b4a414c2b25bb4f6e46f627c07660358533d9a097dec01a2968b7c6
aggregate repair records: 0
```

No month-level A1/E3 result is used to alter either strategy.

## 2024-09 through 2024-12 collection

A combined collection and baseline workflow is active:

```text
workflow: Run USDJPY H2 2024-09 to 2024-12 Collect and Baseline
run_id: 29569149852
```

Execution order:

```text
September tick collection: four concurrent day jobs
then October: four concurrent day jobs
then November: four concurrent day jobs
then December: four concurrent day jobs
then four monthly baseline jobs in parallel
```

The four months are not collected simultaneously, preventing a 16-job Dukascopy request burst.

## Entry-horizon diagnostic protocol

The H1 screen used a six-bar exit for nearly every family. Therefore it selected complete strategies adapted to that common horizon, not entry rules independently of exit.

A separate January-June development diagnostic is now frozen:

```text
protocol:
  docs/research_reboot/usdjpy_entry_horizon_research_protocol_v1.md

config:
  configs/research/usdjpy_h1_entry_horizon_diagnostic_v1.json

runner:
  tools/run_usdjpy_h1_entry_horizon_diagnostic_v1.py

workflow:
  Run USDJPY H1 Entry-Horizon Diagnostic
```

Scope:

```text
13 registered candidates
12 unique entry definitions
C1 and C2 share one entry definition and differ only in registered hold period
fixed horizons: 1, 2, 3, 4, 6, 8, 12, 16, 24 M15 bars
path diagnostics: 24-bar MFE and MAE
H2 data read: prohibited
active H2 changes: prohibited
promotion decision: prohibited
```

The workflow must reproduce the canonical A1 six-bar result before its artifact is accepted.

## Research roadmap position

```text
Step 3A — independent H1 family screening:
  complete

Step 3B — retain six-bar strategy representatives:
  complete

Step 3C — joint A1+hold6 / E3+hold6 H2 pre-registration:
  complete

Step 3D — untouched H2 data collection and batch validation:
  current

Entry-horizon development diagnostic:
  protocol and implementation complete; execution pending

Step 4 — evaluate the frozen A1+hold6 and E3+hold6 H2 results:
  not started

Exit-policy research:
  not started
  must begin with horizon/path evidence and controlled mechanism-based branches

EA / Core / MT4 implementation:
  not started
```

## Next operations

1. Allow run `29569149852` to finish and verify every September-December source and baseline gate.
2. Run `Run USDJPY H1 Entry-Horizon Diagnostic` on the frozen January-June data.
3. Review the complete horizon surface without changing the active H2.
4. Open A1/E3 H2 results only as the pre-registered six-bar confirmatory test.
5. Define any later exit families in a new pre-registration and reserve a later untouched validation block.
