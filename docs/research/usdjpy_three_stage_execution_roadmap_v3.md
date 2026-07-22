# USDJPY Three-Stage Execution Roadmap v3

## Current state

- Current candidate: none.
- `F05_MFE20_BOR1_EXIT_v1`: `CLOSED_FAIL_H2`.
- 2025 H1 candidate-specific execution: locked.
- Next stage: return to 2024 H1 mechanism diagnosis.
- Operating contract: `configs/research/usdjpy_validation_operating_contract_v3.json`.

## Objective

The objective is not to find a rule that improves one development period. The objective is to produce one unchanged exact specification that passes:

1. 2024 H1 mechanism diagnosis, finite development and exact Rakuten MT4 parity;
2. unchanged 2024 H2 binding validation;
3. unchanged 2025 H1 Rakuten MT4 binding stress validation.

A candidate is not retained merely because it reduces losses or improves aggregate H1/H2 net profit.

## Stage A — rebuild the H1 research question

Before proposing another grid, produce one mechanism-specific H1 diagnostic report.

Required analyses:

- B02 and F05 loss contribution;
- P1 giveback-to-loss, P2 minor-favourable-then-loss and P3 never-profitable attribution;
- winners that the proposed mechanism would damage;
- month, quarter, session, direction and exposure-state distribution;
- trigger frequency and effect distribution;
- explicit distinction from S1, S2, S3, Family A, Family B and the closed Family C finalist;
- mechanism-to-2025-H1-gate thesis.

The final item does not authorize candidate-specific 2025 H1 execution. It records why the mechanism could plausibly survive the already-known adverse-regime requirements.

## Stage B — preregister one finite family

The preregistration must freeze:

- mechanism definition;
- finite grid or deterministic generator;
- candidate count;
- selection and tie rules;
- parameter-equivalence handling;
- H1 screening metrics;
- maximum number of finalists;
- prohibited reinterpretations.

No result-driven expansion of the grid is permitted.

## Stage C — H1 research screening

Every candidate must report both gate values and gate margins.

Required outputs include:

- affected trade keys;
- affected count by month, quarter, direction and strategy;
- positive and negative effect counts;
- benefit, harm and benefit/harm ratio;
- mean, median, quantiles and maximum absolute effect;
- Q1 and Q2 deltas;
- ex-best-two delta;
- leave-one-month-out minimum;
- positive-date concentration;
- parameter-equivalence classes.

A candidate that passes only by a narrow margin is labelled `FRAGILE_H1_PASS_REQUIRES_REVIEW`; it is not automatically promoted.

## Stage D — finalist comparison

Before MT4 implementation, compare:

- every H1-eligible cell;
- every observationally equivalent parameter cell;
- relevant closed candidates;
- target loss paths and winner sacrifice;
- robustness margins;
- expected H2 confirmation;
- expected 2025 H1 confirmation.

The comparison must explain the candidate in plain terms before execution.

## Stage E — reusable MT4 preflight

The MT4 workflow must complete a non-binding preflight before any H2 access.

Preflight must verify:

- actual Windows interactive runner source materialization;
- MetaEditor compilation;
- fixed preset generation;
- H1 or synthetic fixture execution;
- complete audit schema including period-end open positions;
- explicit prior-artifact retrieval by repository, Run ID, artifact ID and digest;
- evaluator execution;
- receipt and artifact creation.

A binding candidate run must not be used as workflow debugging.

Separate watcher or audit workflows are not part of the research process and are prohibited for routine run discovery.

## Stage F — exact H1 Rakuten MT4 parity

The research result and MT4 output must match on:

- entry-key relation;
- changed trade keys;
- changed close times;
- changed P/L;
- all unaffected trades;
- non-target strategy;
- direct tick-equity DD;
- minimum tick equity;
- zero order failures.

Only exact parity allows H2 packaging.

## Stage G — package the complete route through 2025 H1 before H2

Before H2 dispatch, freeze both the H2 package and the inert 2025 H1 package.

The package must contain:

- exact candidate identity;
- builder, evaluator, workflow and generated MQ4 identities;
- H2 gates;
- accepted 2025 H1 baseline identity;
- 2025 H1 Rakuten MT4 workflow plan;
- 2025 H1 evaluator and gates;
- H2 PASS unlock action;
- H2 FAIL closure action.

The 2025 H1 workflow remains inert and may not read candidate-specific 2025 evidence before H2 PASS.

## Stage H — one unchanged H2 Rakuten MT4 validation

One exact specification receives one binding H2 decision.

- PASS: unlock the already-prepared 2025 H1 package.
- FAIL: close the exact specification and update the registry in the same Research PR.

No H2 threshold repair, gate change or combination is permitted.

## Stage I — unchanged 2025 H1 Rakuten MT4 stress validation

2025 H1 must be run with Rakuten MT4 Strategy Tester, not replaced by Python research output.

All fixed gates must pass, including:

- candidate net positive and above baseline;
- PF at least 1.00 and at least baseline;
- DD below baseline;
- minimum equity above baseline;
- January-March and April-June both nonnegative;
- both half-period deltas positive;
- at least four positive-effect months;
- at most one negative-effect month;
- ex-best-two delta positive;
- target strategy positive;
- non-target strategy unchanged or nonnegative;
- benefit greater than harm.

A candidate that only reduces a 2025 H1 loss but remains negative fails.

## Stage J — atomic close or pass record

The same Research PR must include:

- binding result JSON;
- human-readable result report;
- registry update;
- period access update;
- next action.

There must be no state where Actions has completed but the Research main registry still describes an earlier stage.

## Immediate next action

Do not create another candidate yet. First produce the next 2024 H1 mechanism-diagnosis report under Stage A. Only after that report is reviewed may a new finite family be preregistered.
