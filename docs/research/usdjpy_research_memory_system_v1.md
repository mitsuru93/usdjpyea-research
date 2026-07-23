# USDJPY Research Memory System v1

## Why this exists

The main research risk is not merely losing a file. It is losing the causal sequence:

1. what was observed;
2. what mechanism was inferred;
3. what the mechanism predicted before results were seen;
4. what exact specification was executed;
5. which gate rejected it;
6. which part of the idea was falsified;
7. which finding remained useful;
8. which follow-up would duplicate closed work.

A list of candidate names and final P/L cannot answer those questions. It can cause a later thread to repeat a failed mechanism, omit a contrary H2 result, reopen a closed threshold, or overlook a useful partial finding.

This system makes that causal sequence a mandatory repository input.

## Canonical components

| Component | Role |
|---|---|
| `AGENTS.md` | Repository-wide instructions for AI/Codex work |
| `configs/research/usdjpy_research_memory_manifest_v1.json` | Start-up read order and current canonical pointers |
| `configs/research/usdjpy_hypothesis_ledger_v1.json` | Append-only hypothesis, failure, and retained-finding ledger |
| `configs/research/usdjpy_validation_operating_contract_v4.json` | Memory-gated research and execution contract |
| `configs/research/usdjpy_research_candidate_registry_v24.json` | Current state, permissions, and exact next action |
| `tools/validate_usdjpy_research_memory_v1.py` | Structural consistency validator |
| `.github/workflows/validate_usdjpy_research_memory_v1.yml` | CI enforcement |

## What a future thread must do

A new thread must not begin by asking only “what is the next candidate?” It must:

1. inspect the latest Research `main`;
2. read the manifest and every mandatory file in order;
3. report the current registry status and exact next action;
4. identify the prior hypothesis-ledger entries relevant to the requested analysis;
5. declare the lineage being used;
6. confirm which protected periods remain closed.

The start-up receipt is evidence that the thread did not rely on a stale summary.

## Hypothesis-ledger structure

Each entry separates:

- **origin analysis** — the empirical observation that motivated the idea;
- **causal hypothesis** — the proposed explanation;
- **target failure mode** — the exact path or architecture problem;
- **pre-result predictions** — what should occur if the explanation is correct;
- **tests** — periods, execution type, Run/artifact identity, and results;
- **decision** — the formal closure or current state;
- **falsified or unsupported claims** — what the evidence rejected;
- **retained findings** — what remains useful despite failure;
- **prohibited reuse** — what later work must not repeat;
- **successor questions** — the remaining research gap.

This prevents a positive headline delta from erasing a failed robustness gate.

## Current causal lineage

### Broad and shock-conditioned admission

- `USDJPY-HYP-001` SC70/C240: H1 improvement, H2 large deterioration, 2025 H1 loss compression only.
- `USDJPY-HYP-002` S1: narrower F05 shock filter; improved H1 and 2025 diagnostic, reversed in H2.
- `USDJPY-HYP-004` S3: recurring positive headline deltas, but exact specification failed date-removal robustness.

Retained finding: some extended or shock-conditioned F05 entries are poor.

Rejected shortcut: a static exact threshold reliably separates them from continuation winners.

### Protection exits

- `USDJPY-HYP-003` S2: DD reduction, but B02 damage and concentration.
- `USDJPY-HYP-007` Family C/MFE20: aggregate H1/H2 improvement, but parameter non-identifiability and H2 concentration.
- `USDJPY-HYP-008` Family D: P3 protection worked, but later-recovery winners reversed H2.
- `USDJPY-HYP-009` Family E: state-adaptive exit generalized as loss compression but failed the 2025 H1 viability gate.

Retained finding: early exit can save genuine F05 losses.

Rejected shortcut: exit timing alone restores portfolio expectancy.

### Admission architecture

- `USDJPY-HYP-005` Family A: one-bar non-shock acceptance features produced no eligible H1 cell.
- `USDJPY-HYP-006` Family B: static overlap/ordinal filters produced no eligible H1 cell.
- `USDJPY-HYP-010` Family F: event-probe/confirmation grid produced a high headline PF but failed month/date robustness.

Retained finding: F05 exposure/event state matters.

Rejected shortcut: the tested static acceptance, overlap, or event thresholds are robust admission rules.

### Current open question

`USDJPY-RQ-011` is descriptive, not a candidate:

- 2023 baseline parity and Architecture Atlas are accepted;
- reconstruct and audit the historical 2024 H1 M15 UTC and trade-key fields;
- compare retained findings across years only after the field contract is reconciled;
- do not generate candidate signals or select parameters yet.

## Duplicate-research audit

Every new mechanism proposal must explicitly map itself to the ledger.

A valid novelty statement answers:

1. Which prior IDs target the same strategy and path?
2. Which prior features or actions overlap?
3. Which prior failed gate would also threaten this proposal?
4. Which retained finding is being used?
5. What new observable exists that prior work did not contain?
6. What result would falsify the new explanation?
7. Why is this not the same mechanism with a different threshold?

Failure to answer these questions blocks preregistration.

## Updating after a test

A completed test must produce one atomic Research update containing:

- result JSON;
- report;
- registry update;
- ledger update;
- period-access update;
- next action.

Negative results stay in the ledger. A technical failure is recorded separately from a scientific failure.

## Corrections

Do not silently repair historical evidence.

Use:

- an erratum entry;
- a superseding ledger entry;
- a new registry version;
- explicit old and corrected values;
- evidence explaining why the interpretation does or does not change.

## Durable evidence

The durable path is GitHub Release, not Google Drive:

1. download the exact Actions artifact;
2. verify its digest;
3. publish the Release asset;
4. download the Release asset;
5. verify byte identity;
6. commit the receipt.

The complete 2025 H1 evidence is archived under Release tag `usdjpy-2025h1-evidence-archive-v1`.
