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
```

### 2024-09 through 2024-12

```text
workflow: Run USDJPY H2 2024-09 to 2024-12 Collect and Baseline
run_id: 29569149852
head_sha: ba7dc2a448bf626d6282e69397d91e00c05ec12c
result record: docs/research_reboot/usdjpy_h2_2024_09_12_source_and_baseline_result_v1.md
```

Independent fixed-weekday audit:

```text
month     expected hours   observed   missing   hard errors   effective coverage
2024-09   504              504        0         0             100%
2024-10   552              552        0         0             100%
2024-11   504              504        0         0             100%
2024-12   528              528        0         0             100%
```

Accepted artifacts:

```text
2024-09 source artifact_id: 8404664185
2024-09 baseline artifact_id: 8423361030

2024-10 source artifact_id: 8408558801
2024-10 baseline artifact_id: 8423402213

2024-11 source artifact_id: 8421758330
2024-11 baseline artifact_id: 8423419800

2024-12 source artifact_id: 8423343357
2024-12 baseline artifact_id: 8423376366
```

The first-attempt November source artifact `8412658745` is excluded. The rerun recovered the missing 2024-11-22 day and the accepted terminal manifest contains all 504 fixed weekday hours.

All six H2 source months, July through December 2024, are accepted. No month-level A1/E3 result was used to alter either strategy.

## Entry-horizon diagnostic

### Invalid v1

Run `29582417411` completed technically but is research-invalid because it reset prior-history state at month boundaries. No result from that artifact may be used.

### Accepted v2

```text
workflow: Run USDJPY H1 Entry-Horizon Diagnostic v2
run_id: 29583719940
head_sha: e81fe4d1600a5c8d665c700d68218b6bf85299c3
artifact: usdjpy-h1-entry-horizon-diagnostic-v2-29583719940
artifact_digest: sha256:f95a0a450aa3b821dbcb20ea4f3410f345668606bf5f20a766a3e01d8a6e89e4
result record: docs/research_reboot/usdjpy_h1_entry_horizon_diagnostic_v2_result_v1.md
```

The v2 run passed the registered-hold regression for all 13 candidates, matched the authoritative H1 metrics, reported 12 unique entry definitions and confirmed `h2_data_read: false` and `promotion_decision: false`.

Research interpretation:

- A1 and E3 are not isolated six-bar peaks; each has a neighboring positive horizon region.
- The original six-bar screen nevertheless changed candidate ranking materially.
- C4, C3, E2 and B2 require separate slower-horizon hypotheses if researched later.
- No candidate is promoted from the development diagnostic.
- Any new entry-plus-exit strategy requires a new pre-registration and a later untouched validation block.

## Joint H2 evaluator

The evaluator implementation is frozen before opening the H2 candidate result.

```text
implementation lock:
  docs/research_reboot/usdjpy_joint_h2_a1_e3_implementation_lock_v1.md

config:
  configs/research/usdjpy_joint_h2_a1_e3_eval_v1.json

runner:
  tools/run_usdjpy_joint_h2_a1_e3_eval_v1.py

workflow:
  Run USDJPY Joint H2 A1 E3 Evaluation v1
```

The evaluator:

- audits all six H2 terminal manifests against fixed weekday-hour denominators;
- loads accepted aggregate-repair M15 bars;
- reproduces exact A1 and E3 H1 metrics within `1e-9` before H2 acceptance;
- uses H1 bars only as prior lookback history near the H2 boundary;
- retains only signals, entries and exits inside the H2 block;
- applies every preregistered gate independently;
- reports direction attribution, intervention sensitivity, best-two-day concentration, overlap and daily correlation;
- performs no Exit optimization or parameter change.

## Research roadmap

```text
Step 3A — independent H1 family screening:
  complete

Step 3B — retain six-bar strategy representatives:
  complete

Step 3C — joint A1+hold6 / E3+hold6 H2 pre-registration:
  complete

Step 3D — untouched H2 data collection and batch validation:
  complete

Entry-horizon development diagnostic:
  v1 invalidated
  v2 accepted and recorded

Step 4 — evaluate frozen A1+hold6 and E3+hold6 H2 results:
  evaluator implementation complete
  execution pending

Exit-policy research:
  horizon/path evidence available
  strategy selection not started
  must use controlled mechanism-based branches and a later untouched validation block

EA / Core / MT4 implementation:
  not started
```

## Next operations

1. Run `Run USDJPY Joint H2 A1 E3 Evaluation v1` with no inputs.
2. Accept the result only if all six fixed-weekday source audits and both H1 regressions pass.
3. Apply the frozen common H2 gate exactly as registered.
4. After the H2 decision, define a small mechanism-based exit research plan without reopening the current H2.
5. Pre-register any new entry-plus-exit candidate before evaluating it on a later untouched block.
6. Reproduce surviving complete strategies in Core/MT4 before EA deployment.
