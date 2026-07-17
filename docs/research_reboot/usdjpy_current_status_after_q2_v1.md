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

Run `29546116205` is invalid because it used signal-bar entry-hour semantics and a non-canonical spread field.

## Active confirmatory H2

The active candidates are complete entry-plus-six-bar strategies, not exit-independent winning entries.

```text
A1_impulse_breakout_lb3_hold6
  trades: 391
  avg net pips: +2.015899
  total net pips: +788.216501
  PF: 1.280577

E3_trend_24h_resumption_hold6
  trades: 361
  avg net pips: +1.783355
  total net pips: +643.791082
  PF: 1.305343
```

Active pre-registration:

```text
docs/research_reboot/usdjpy_joint_h2_prereg_a1_e3_v1.md
commit: b89b550c87addd074ac6ab6de5438ad6f8e972ce
validation block: 2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
```

Candidate definitions, directions, six-bar holds, sessions, gates, intervention dates and cost scenarios remain frozen. PR #59 was closed without merge.

## Verified H2 source and baseline blocks

### 2024-07

```text
source run_id: 29544395435
source artifact: public-fx-data-pilot-2024-07-USDJPY-aggregate-29544395435
source digest: sha256:0698a05fc17d15cd9e3c405cb1367a02e6a10230ab69bbb29bceb61b62f34672
effective coverage: 100%
hard errors: 0

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
effective coverage: 100%
hard errors: 0

baseline run_id: 29567447264
baseline artifact: fx-session-baseline-2024-08-USDJPY-29567447264
baseline digest: sha256:e5dd5f183b4a414c2b25bb4f6e46f627c07660358533d9a097dec01a2968b7c6
aggregate repair records: 0
```

No month-level A1/E3 result is used to alter either strategy.

## 2024-09 through 2024-12 collection

```text
workflow: Run USDJPY H2 2024-09 to 2024-12 Collect and Baseline
run_id: 29569149852
```

The workflow processes the four source months sequentially with four concurrent day jobs per month, then creates four monthly baseline artifacts in parallel.

## Entry-horizon diagnostic

### Invalid v1

Run `29582417411` completed technically but is research-invalid.

```text
invalid record:
  docs/research_reboot/usdjpy_h1_entry_horizon_run_29582417411_invalid_v1.md

reason:
  the v1 runner generated signals separately for each month and reset prior-history state at month boundaries
```

No result from the invalid artifact may be used.

### Accepted v2

```text
workflow: Run USDJPY H1 Entry-Horizon Diagnostic v2
run_id: 29583719940
head_sha: e81fe4d1600a5c8d665c700d68218b6bf85299c3
artifact: usdjpy-h1-entry-horizon-diagnostic-v2-29583719940
artifact_digest: sha256:f95a0a450aa3b821dbcb20ea4f3410f345668606bf5f20a766a3e01d8a6e89e4
result record: docs/research_reboot/usdjpy_h1_entry_horizon_diagnostic_v2_result_v1.md
```

The v2 run is accepted. It passed the registered-hold regression for all 13 candidates, matched the authoritative H1 metrics, reported 12 unique entry definitions and confirmed `h2_data_read: false` and `promotion_decision: false`.

Primary horizon findings:

```text
A1:
  positive from 1 through 16 bars except no tested negative point inside that range
  highest tested average at 6 bars: +2.016 pips
  24 bars: -0.233 pips

E3:
  negative at 1-3 bars
  positive at 4-24 bars
  strongest region at 6-12 bars
  highest tested average at 6 bars: +1.783 pips

C4:
  strengthens from 6 through 24 bars
  16 bars: +2.932 pips, severe PF 1.079
  24 bars: +4.198 pips, severe PF 1.170

C3:
  broad positive region at 8-16 bars
  highest tested average at 12 bars: +1.606 pips
  negative again at 24 bars

E2:
  weak at shorter horizons
  24 bars: +3.607 pips, 5 positive months, severe PF 1.109

B2:
  16 and 24 bars become positive and cost-stress positive
  remains sample-limited with 99 H1 entries

B3:
  positive only at 6 bars and negative at neighboring tested horizons
  remains below the 120-trade gate
```

Research interpretation:

- A1 and E3 are not merely isolated six-bar peaks; each has a neighboring positive horizon region.
- The original six-bar screen nevertheless changed candidate ranking materially.
- C4, C3, E2 and B2 require separate slower-horizon hypotheses if researched later.
- No candidate is promoted from the development diagnostic.
- Any new entry-plus-exit strategy requires a new pre-registration and a later untouched validation block.

## Research roadmap

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
  v1 invalidated
  v2 accepted and recorded

Step 4 — evaluate frozen A1+hold6 and E3+hold6 H2 results:
  not started

Exit-policy research:
  horizon/path evidence available
  strategy selection not started
  must use controlled mechanism-based branches and a later untouched validation block

EA / Core / MT4 implementation:
  not started
```

## Next operations

1. Finish and verify run `29569149852` without inspecting month-level candidate results.
2. Evaluate A1+hold6 and E3+hold6 on the full H2 block under the frozen gate.
3. Use the accepted horizon surface to define a small mechanism-based exit research plan.
4. Pre-register any new entry-plus-exit candidates before evaluating them on a later untouched block.
5. Reproduce surviving complete strategies in Core/MT4 before EA deployment.
