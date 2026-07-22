# USDJPY F05_MFE20_BOR1_EXIT_v1 — Validation Quality Postmortem v1

## Decision

The exact specification `F05_MFE20_BOR1_EXIT_v1` is closed after binding 2024 H2 FAIL. The candidate must not be repaired, retuned, combined or executed on candidate-specific 2025 H1 evidence.

This postmortem also records that the validation process itself was below the required quality. The principal failure was not the final H2 decision. The principal failure was promoting a fragile and incompletely interpreted H1 result while constructing the MT4 execution path ad hoc.

## Evidence reviewed

- accepted 2024 H1 baseline Run `29787357305`, artifact `8479048161`;
- Entry-State Atlas v2 Run `29884556860`, artifact `8516049893`;
- Family C H1 research Run `29886163522`, artifact `8516578659`;
- H1 Rakuten MT4 Run `29893008498`, artifact `8518973150`;
- H1 evaluator repair Run `29893833236`, artifact `8519210754`;
- binding H2 Rakuten MT4 Run `29895387329`, artifact `8519879009`;
- binding H2 evaluator decision Run `29896667418`, artifact `8520231535`.

## What was actually tested

The candidate kept the complete B02/F05 entry set unchanged and altered only F05 exits. After an open F05 position had previously reached 20 pips of marked MFE, it was closed at the current M15 open when the latest completed M15 close was at least 1 pip back inside the entry-specific breakout level. Normal time-cap exits were processed first, then the structural exit, then new entries.

## H1 result and hidden fragility

The Family C preregistration evaluated 48 finite structural-exit specifications. Three were research-eligible, all inside the same C2 mechanism.

| Specification | Changed positions | H1 delta JPY | Ex-best-two delta JPY | Leave-one-month-out minimum JPY |
|---|---:|---:|---:|---:|
| MFE20 / one close / 1 pip inside | 24 | 3,322 | 398 | 1,114 |
| MFE20 / one close / 2 pips inside | 24 | 3,322 | 398 | 1,114 |
| MFE20 / one close / 3 pips inside | 23 | 2,998 | 126 | 576 |

The 1-pip and 2-pip specifications produced identical affected positions, outcomes and aggregate metrics. Therefore H1 did not identify 1 pip as a distinct threshold. The selected 1-pip label was a tie-break result, not an empirically distinguished rule.

Additional H1 fragility:

- only JPY 398 of the JPY 3,322 improvement remained after removing the two strongest entry dates;
- April contributed JPY 2,208 of the total H1 improvement;
- benefit was JPY 5,472 and harm was JPY 2,150;
- 14 changed trades improved and 10 worsened;
- the median changed-trade effect was only about JPY 50.5;
- the candidate passed the Boolean gates, but the pass margins were narrow.

The process treated this as an ordinary finalist instead of a fragile H1 pass requiring a separate mechanism review and comparison report.

## H2 result

The candidate completed the unchanged 2024 H2 Rakuten MT4 test.

| Metric | Baseline | Candidate | Delta |
|---|---:|---:|---:|
| Opened | 494 | 494 | 0 |
| Closed | 493 | 493 | 0 |
| Closed net JPY | 38,358 | 41,676 | +3,318 |
| Complete marked net JPY | 38,109 | 41,427 | +3,318 |
| Closed PF | 1.354963 | 1.430822 | improvement |
| Tick-equity DD JPY | 19,603 | 15,063 | -4,540 |
| Minimum tick equity JPY | 95,271 | 95,271 | 0 |
| Changed F05 positions | — | 76 | — |

The mechanism activation rate changed materially:

- 2024 H1: 24 of 331 closed F05 positions, about 7.3%;
- 2024 H2: 76 of 392 opened F05 positions, about 19.4%.

The benefit/harm profile also weakened:

- H1 benefit/harm ratio: approximately 2.54;
- H2 benefit/harm ratio: approximately 1.26;
- H1 improved/worsened changed trades: 14 / 10;
- H2 improved/worsened changed trades: 39 / 37.

Binding H2 failed because:

1. negative-effect months were three, above the maximum of one;
2. the net delta after removing the two strongest positive entry dates was JPY -1,944.

The aggregate improvement therefore did not establish stable generalization.

## Root causes

### 1. Candidate-specific H1 analysis was skipped

Entry-State Atlas v2 was built correctly, but it was used mainly as an input table. Before the Family C grid, no dedicated report established:

- which P1/P2/P3 loss paths the proposed exit was intended to fix;
- how many winners would be cut early;
- the expected benefit/harm mechanism by path class;
- whether the rule addressed a recurring loss structure rather than a profitable-date subset;
- how the mechanism differed economically from prior exit candidates;
- how the mechanism was expected to satisfy the eventual 2025 H1 gates.

The finite grid was preregistered, but the causal and portfolio interpretation preceding the grid was incomplete.

### 2. Parameter identifiability was not checked

The selected 1-pip threshold was observationally equivalent to 2 pips on H1. A threshold-specific candidate should not have been frozen until equivalent parameter cells were collapsed into one equivalence class or a non-outcome-based canonical rule was declared.

### 3. Boolean H1 gates were mistaken for a strong H1 result

The H1 evaluator answered whether each minimum condition was positive, but did not classify the margin above the gate. An ex-best-two delta of JPY 398 and a leave-one-month-out minimum of JPY 1,114 were accepted without a separate fragility review.

### 4. Past-candidate comparison was not repeated

Earlier work produced an explicit H1 comparison between S3 and the degraded-shock exit, including mechanism interpretation, exact MT4 metrics, concentration, leave-one-month-out results and selection rationale. No equivalent comparison was produced for the Family C finalist against:

- the other two eligible C2 cells;
- closed S1-S3 mechanisms;
- the known baseline loss paths;
- the already-completed Family A and Family B results.

### 5. The path to 2025 H1 was only a gate list

The policy correctly required H2 PASS before 2025 H1, but the candidate package did not contain a pre-H2 `2025 H1 readiness thesis` explaining, without candidate-specific 2025 execution, how the mechanism was expected to achieve:

- positive total net;
- PF at least 1.00 and at least baseline;
- lower DD and higher minimum equity;
- nonnegative January-March and April-June results;
- four positive effect months and at most one negative month;
- positive target-strategy delta without harming the other strategy.

Consequently, H1 candidate selection was not organized around the complete three-stage objective.

### 6. MT4 execution infrastructure was built ad hoc

The candidate required a long repair chain across H1 and H2. Failures included:

- workflow dispatch assumptions incompatible with protected main;
- Git/check-out assumptions on the interactive Windows runner;
- source materialization defects;
- missing source Run ID for prior-artifact download;
- read-only audit workflow formatting failures;
- period-end audit rows missing canonical timestamps;
- artifact extraction-path assumptions.

Multiple auxiliary watcher/audit PRs were added solely to discover run state. This increased elapsed time without increasing research quality.

### 7. The research registry was not updated atomically

At the time of this postmortem, candidate registry v2 still described Family C as `PREREGISTRATION_PENDING`, although Family C H1, exact MT4 parity and binding H2 had already completed. The formal H2 closure record was also not yet present on main. This fragmented the source of truth across Actions artifacts, GitHub issues, unmerged work and conversation context.

## Binding recurrence-prevention actions

The following controls apply to every new USDJPY successor candidate.

1. No candidate grid before a mechanism-specific H1 diagnostic report is committed.
2. No threshold-specific finalist when adjacent parameter cells are outcome-equivalent; equivalence classes must be collapsed or canonically resolved before selection.
3. Every H1 finalist requires a robustness-margin report, not only Boolean gate results.
4. Every H1 finalist requires an explicit comparison against all eligible cells and relevant prior candidates before MT4 implementation.
5. A pre-H2 2025 H1 readiness package must exist, while 2025 H1 candidate execution remains locked until H2 PASS.
6. H1 and H2 use a preflighted reusable MT4 workflow. Candidate-specific binding runs must not be the first full execution of newly assembled workflow logic.
7. Artifact retrieval must bind repository, Run ID, artifact ID, digest and expected internal paths before a binding run.
8. Audit schema must make every event independently keyable; period-end events must include strategy, signal UTC, entry UTC and side at source.
9. Separate read-only watcher workflows are prohibited. Run state is read through the Actions API or the primary workflow receipt.
10. Candidate registry, result record and next-state decision must be updated in the same Research PR immediately after every binding decision.
11. 2025 H1, when unlocked, must be executed by Rakuten MT4 Strategy Tester. Python-only substitution is prohibited.

## Current handling

- `F05_MFE20_BOR1_EXIT_v1`: `CLOSED_FAIL_H2`;
- exact specification exposure ordinal: 1;
- candidate-specific 2025 H1 execution: not performed and not authorized;
- repair or retuning from H2 evidence: prohibited;
- next work: return to 2024 H1 diagnosis under a new family/candidate ID and the v3 operating contract.
