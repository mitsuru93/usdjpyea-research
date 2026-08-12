# USDJPY Research Agent Instructions

These instructions apply to the entire repository.

## Repository purpose and boundaries

This repository is for research and pre-MT4 simulation work for USDJPY EA development.

- Prefer robustness over peak profit.
- Avoid lookahead bias in all research and simulations.
- Use conservative assumptions whenever same-bar execution order is ambiguous.
- Compare outcomes by month, half-year fold, session, path class, direction and exposure state.
- Do not add MT4 production code (`.mq4` / `.mqh`) here.
- Do not include broker-specific live-trading logic or production secrets.

## AI source discovery

For repository architecture, current Research state, period authority, data lineage, result evidence, or execution-safeguard questions:

1. Read `ai-source-index.json` before repository-wide search.
2. Treat it as routing metadata only. It never overrides the Research memory manifest, candidate registry, period policy, operating contract, binding result/receipt, or fresh GitHub evidence.
3. Use the indexed entry to reach the canonical source set first. Repository-wide grep/version-history exploration is fallback only when indexed sources are missing, contradictory, or insufficient.
4. Do not infer the active registry/result/receipt from the highest filename version. Resolve moving pointers from `configs/research/usdjpy_research_memory_manifest_v1.json` and the current registry.
5. The routing index does not relax or replace the mandatory start-up sequence below.

## Mandatory start-up sequence

Before any USDJPY analysis, hypothesis proposal, candidate design, parameter grid, result interpretation, MT4 workflow design or period-access decision:

1. Read `configs/research/usdjpy_research_memory_manifest_v1.json`.
2. Read every file in its `mandatory_startup_read_order`.
3. Verify the latest Research `main` commit and exact current candidate-registry pointer.
4. State or record a start-up read receipt containing Research commit, file identities, registry status/next action, relevant ledger IDs, declared lineage and periods accessed/not accessed.

Do not use conversation summaries, issue titles, artifact names or file names alone as the source of truth. If mandatory files cannot be read or disagree, stop scientific interpretation and reconcile the canonical state first.

## Research-memory and novelty rule

`configs/research/usdjpy_hypothesis_ledger_v1.json` and the active addendum are the append-only causal memory.

Before proposing a new hypothesis, compare target strategy, action, path, timing, state features, affected population, failed gate, period, lineage and algebraically equivalent payoff. A new family is blocked unless it records prior IDs, exact overlap, retained findings, falsified claims not repeated, new causal information, falsifiable predictions, why it is not threshold relabeling, and whether the outcome is algebraically derivable from opened development results.

Closed exact candidates must not be repaired, retuned, combined or reopened from 2025 evidence.

## Mandatory execution safeguards

Read `docs/operations/usdjpy_research_execution_recurrence_prevention_v1.md` and apply it before long-running work.

- Freeze authority direction before transforming data.
- Commit evaluator source before accessing outcomes.
- Run technical feasibility and one-row preflight before a full grid.
- Apply an impact-sufficiency gate before opening a family.
- Generate output hashes programmatically.
- Do not call a deterministic payoff transformation blind when source outcomes are known.
- Package one scientific stage atomically rather than using serial micro-PRs.
- Leave a machine-readable `NOT_CANONICAL` WIP receipt if interrupted.

## Evidence and lineage

Use this precedence:

1. binding result JSON and exact receipt;
2. verified GitHub Release receipt and Actions identity;
3. preregistration and frozen policy;
4. human-readable report;
5. registry and ledger summary;
6. conversation context.

Identify Actions evidence by repository, Run ID, artifact ID, digest, creation time and Release receipt. Do not call HST bars tick data. Do not silently rewrite historical 2024/2025. The accepted 2023 legacy-2024 builder must be source-reproducible before new 2023 candidate interpretation.

## Atomic result update

After every completed scientific test, the same Research change must update result JSON, report, registry, ledger, period state and exact next action. Technical incomplete attempts are separate and never scientific results. Historical entries are corrected by erratum or superseding entry.

After merge, Notion Current State and the active task must be updated and fetched back. The stage is not complete until Notion readback matches GitHub.

## Period roles

Follow the current registry and period policy exactly.

- 2023 H1/H2 and 2024 H1/H2 are development, mechanism-analysis and falsification folds.
- Candidate analysis is allowed only when explicitly authorized by the current registry and a fixed protocol.
- 2025 H1 is locked until one exact specification, Research-to-MT4 parity and workflow preflight are complete.
- Known 2025 results may define the gate but may not choose a mechanism, feature, threshold, side or weight.
- 2025 H2 is locked until an unchanged 2025 H1 pass.
- Live orders are not authorized.

## Archive

The canonical durable evidence path is:

Actions artifact -> digest verification -> GitHub Release asset -> Release readback verification -> committed receipt.

Google Drive is not the canonical archive for this research.
