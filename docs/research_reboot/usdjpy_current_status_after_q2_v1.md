# USDJPY Research Status After Q2 v1

## Verified baseline block

The verified Dukascopy monthly baseline block covers 2024-01 through 2024-06 with 100% effective coverage and zero final hard errors.

```text
2024-01: 29307131333
2024-02: 29383810487
2024-03: 29421329471
2024-04: 29455059447
2024-05: 29469227483
2024-06: 29475803893
```

## Existing family decisions

```text
M5 pullback continuation:
  closed in current form after Q2 gate failure

Unfiltered M15 breakout:
  rejected

M15 impulse-confirmed breakout:
  exact-source-confirmed H1 development candidate
```

Impulse candidate H1 result:

```text
trades: 391
positive months: 4 / 6
avg net pips: +2.016
total net pips: +788.22
profit factor: 1.281
Q1 avg net pips: +2.628
Q2 avg net pips: +1.327
severe profit factor: 0.982
event-excluded profit factor: 1.204
total excluding best two days: +251.58 pips
```

Canonical result:

```text
docs/research_reboot/usdjpy_h1_dukascopy_impulse_confirmation_result_v1.md
```

## Adopted research design

The project will not validate the impulse candidate alone. Multiple independent families are developed on the same H1 block and then tested together on one untouched H2 block.

```text
Step 3A: evaluate each family independently on 2024-01 through 2024-06
Step 3B: retain at most three representatives per family
Step 3C: pre-register all retained candidates and common H2 gates
Step 3D: evaluate all retained candidates on 2024-07 through 2024-12 in one batch
Step 4: compare surviving families
Step 5: consider family combinations only after independent validation
```

Active plan:

```text
docs/research_reboot/usdjpy_multi_family_h1_research_plan_v1.md
```

Candidate registry:

```text
configs/research/usdjpy_h1_multi_family_candidates_v1.json
```

## Families currently included

```text
A. M15 impulse-confirmed breakout
B. Session range breakout
C. Mean reversion / failed excursion
D. Compression to expansion
E. Higher-timeframe trend continuation
```

The families are not combined during H1 screening.

## Current phase

```text
Roadmap position:
Step 3A - H1 independent multi-family screening

Development data:
2024-01 through 2024-06

Untouched validation data:
2024-07 through 2024-12
not yet opened for candidate evaluation

Exit-policy optimization:
not started

EA / Core implementation:
not started
```

## Current implementation

Screening tool:

```text
tools/run_usdjpy_h1_multi_family_screen.py
```

Workflow:

```text
Run USDJPY H1 Multi-Family Screen
```

Workflow file:

```text
.github/workflows/run_usdjpy_h1_multi_family_screen.yml
```

The workflow downloads the original H1 Dukascopy M15 day artifacts, adds aggregate-repair bars from the canonical monthly baselines, evaluates only the registered candidates, and reports:

- source-bar coverage and duplicate handling;
- candidate-level and monthly results;
- Q1/Q2 attribution;
- default and severe costs;
- intervention sensitivity;
- best-two-day concentration;
- H1 retention checks;
- family ranking;
- retained candidates, capped at three per family.

## H2 status

The earlier impulse-only H2 pre-registration has been superseded before H2 execution.

```text
docs/research_reboot/usdjpy_m15_impulse_breakout_h2_prereg_v1.md
```

A new joint H2 pre-registration will be created only after the H1 multi-family artifact has been inspected and the final retained candidate list has been committed.

The July tick-pilot wrapper may remain in the repository, but its data must not be used for candidate selection or evaluation before the joint H2 pre-registration is complete.

## Immediate next action

Run:

```text
Run USDJPY H1 Multi-Family Screen
```

After the run completes, inspect its artifact and decide which candidates survive H1. Only then create the joint H2 pre-registration.
