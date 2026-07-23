# USDJPY Research Agent Instructions

These instructions apply to the entire repository.

## Repository purpose and boundaries

This repository is for research and pre-MT4 simulation work for USDJPY EA development.

- Prefer robustness over peak profit.
- Avoid lookahead bias in all research and simulations.
- Use conservative assumptions whenever same-bar execution order is ambiguous.
- Compare outcomes by month, session, path class, direction, and exposure state.
- Do not add MT4 production code (`.mq4` / `.mqh`) here.
- Do not include broker-specific live-trading logic or production secrets.

## Mandatory start-up sequence

Before any USDJPY analysis, hypothesis proposal, candidate design, parameter grid, result interpretation, MT4 workflow design, or period-access decision:

1. Read `configs/research/usdjpy_research_memory_manifest_v1.json`.
2. Read every file in its `mandatory_startup_read_order`.
3. Verify the latest Research `main` commit and the exact current candidate-registry pointer.
4. State or record a start-up read receipt containing:
   - Research commit;
   - files read and their blob/SHA identity when available;
   - current registry schema, status, and exact next action;
   - relevant hypothesis-ledger IDs;
   - declared data/time lineage;
   - periods accessed and periods not accessed.

Do not use conversation summaries, memory, issue titles, artifact names, or file names alone as the source of truth.

If the mandatory files cannot be read or disagree, stop scientific interpretation and reconcile the source-of-truth state first.

## Research-memory rule

`configs/research/usdjpy_hypothesis_ledger_v1.json` is the append-only causal research ledger.

Before proposing a new hypothesis, compare it against all ledger entries that overlap in:

- target strategy;
- entry or exit action;
- P1/P2/P3 path;
- timing;
- shock, extension, acceptance, retention, overlap, recovery, or event-state features;
- affected-trade population;
- failed robustness gate;
- period and lineage.

A new family is blocked unless the work records:

- prior hypothesis IDs reviewed;
- exact overlap with prior work;
- retained findings being used;
- falsified claims not being repeated;
- the genuinely new observable or causal distinction;
- new falsifiable predictions;
- why the proposal is not a threshold-only relabeling.

Closed exact candidates must not be repaired, retuned, combined, or reopened from H2 or 2025 evidence unless a later explicit policy supersedes that closure.

## Evidence and lineage

Use this precedence:

1. binding result JSON and exact receipt;
2. verified GitHub Release receipt and Actions identity;
3. preregistration and frozen policy;
4. human-readable report;
5. candidate registry and hypothesis-ledger summary;
6. conversation context.

Identify Actions evidence by repository, Run ID, artifact ID, digest, creation time, and corresponding Release receipt when archived.

Do not call HST bars tick data.

Do not silently rewrite the historical 2024/2025 lineage. A corrected-clock or corrected-field series must be separately named and must not be combined with historical trade counts or P/L unless the entire lineage is recomputed and explicitly adopted.

## Atomic result update

After every completed scientific test, the same Research change must update:

- result JSON;
- human-readable report;
- candidate registry;
- hypothesis ledger;
- period-access state or policy pointer;
- exact next action.

Technical incomplete attempts are logged separately and are never counted as scientific results.

Historical ledger entries are not silently edited. Use an erratum or superseding entry and preserve the original evidence.

## Protected periods

Follow the current registry and period policy exactly. At present:

- 2023 descriptive Architecture Atlas work is authorized;
- candidate generation and outcome evaluation are not authorized;
- 2024 H2 is locked;
- 2025 H1 may not be used for retuning or threshold selection;
- 2025 H2 is locked;
- live orders are not authorized.

## Archive

The canonical durable evidence path is:

Actions artifact -> digest verification -> GitHub Release asset -> Release readback verification -> committed receipt.

Google Drive is not the canonical archive for this research.
