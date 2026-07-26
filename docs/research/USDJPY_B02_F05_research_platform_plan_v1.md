# USDJPY B02/F05 Research Platform Plan v1

## Objective

Improve four measurable capabilities:

1. research speed;
2. research accuracy;
3. factor-analysis accuracy;
4. hypothesis accuracy.

This work extends the existing Research/Core separation. It does not replace MT4 final validation, existing frozen contracts, candidate decisions, or period policy.

## Immediate implementation rule

Do not start a new tick collection as part of platform construction. Existing Release assets and frozen datasets must be inventoried and reused first. A new collection requires a documented missing field, proof that it cannot be reconstructed from accepted assets, estimated runtime/storage, and explicit authorization. The known collection cost is approximately 20 hours.

## Confirmed current-state findings

- B02/F05 research already has frozen data/gate contracts and machine-readable outputs.
- The accepted 2024 source includes approximately 40.97 million ticks and derived M1/M5/M15/M30/H1/H4 bars.
- The lifecycle evaluator is materialized from six Python fragments and guarded by a source SHA. This preserves provenance but makes extension and unit-level reuse difficult.
- Many hypothesis-specific evaluators and result documents exist. The platform must wrap and migrate them incrementally rather than rewrite prior research.

## Target architecture

```text
accepted release assets
  -> source manifest and integrity audit
  -> canonical trade identities
  -> canonical ordered event streams
  -> reusable feature/state extractors
  -> factor-analysis modules
  -> machine-readable experiment contracts
  -> fold/strategy/direction robustness reports
  -> MT4 trade-level parity for promoted candidates
```

## Phase 1 — contracts and compatibility layer

Status: started on `research/b02-f05-foundation-v1`.

Deliverables:

- `tools/research_platform/event_model_v1.py`
  - canonical trade identity;
  - ordered event record;
  - UTC, strategy, direction, period, MFE/MAE validation;
  - deterministic record digest.
- `tools/research_platform/experiment_contract_v1.py`
  - hypothesis/mechanism/endpoint/falsification fields;
  - dataset and code lineage;
  - deterministic contract digest.
- contract tests on a GitHub-hosted runner.

This phase intentionally consumes no market data and triggers no tick collection.

## Phase 2 — source inventory and adapters

Build a read-only manifest from existing Releases, repository receipts, and frozen contracts. For each source record:

- release tag and asset name;
- asset digest and size;
- time coverage;
- resolution and Bid/Ask availability;
- timezone convention;
- accepted population compatibility;
- fields required by state-transition analysis;
- reconstruction status.

Then add adapters for the existing stage-1 path ledger and lifecycle outputs. Existing evaluators remain authoritative until adapter parity is demonstrated trade by trade.

## Phase 3 — state-transition extraction

Extract reusable events instead of encoding each hypothesis in a new evaluator. Initial event vocabulary:

- `ENTRY`;
- `INITIAL_FAVORABLE` / `INITIAL_ADVERSE`;
- `BREAKOUT_ATTEMPT`;
- `BREAKOUT_ESTABLISHED`;
- `RANGE_REENTRY`;
- `PROFIT_ARMED`;
- `PEAK_FORMED`;
- `MOMENTUM_DECAY`;
- `REACCELERATION`;
- `TERMINATION_SIGNAL`;
- `TP` / `SL` / actual exit.

Every event must retain elapsed time, signed excursion, MFE, MAE and a typed payload. Definitions are versioned; hypotheses consume events but do not redefine them silently.

## Phase 4 — factor-analysis accuracy

Common modules will provide:

- matched-cohort comparisons;
- fold-specific and pooled effect sizes;
- bootstrap confidence intervals;
- minimum-population warnings;
- month, strategy, side, session and regime decomposition;
- interaction screening;
- competing explanations and falsification checks;
- leakage and post-outcome feature checks.

Predictive feature importance is treated as hypothesis discovery evidence, not causal proof.

## Phase 5 — hypothesis accuracy and speed

A hypothesis becomes executable only through an experiment contract containing:

- observed failure state;
- proposed market mechanism;
- manipulable variables;
- expected intermediate-state change;
- primary endpoint;
- adverse trade-off;
- falsification rule;
- dataset/code/event-schema lineage.

Parameter sweeps and condition changes use configuration, shared extractors and cached event tables. Hypothesis-specific scripts should become thin entry points rather than independent data-processing pipelines.

## Phase 6 — parity and promotion

Promoted candidates receive:

- canonical-event replay;
- Python baseline result;
- trade-ID-level comparison to MT4;
- mismatch classification for entry, price path, spread, exit ordering and timing;
- stress tests and deterministic result packaging.

MT4 remains the final execution-parity authority. Research runners perform discovery and broad analysis.

## Platform metrics

Baseline and subsequent versions will record:

- manual steps per experiment;
- new code lines needed per hypothesis;
- cold and cached runtime;
- reproducibility pass rate;
- source-integrity failure rate;
- event-extraction parity rate;
- Python/MT4 trade match rate;
- fold direction consistency;
- hypothesis intermediate-state prediction accuracy;
- number of hypotheses rejected by automated falsification before MT4 use.

## Migration constraints

- No retroactive alteration of frozen research evidence.
- No replacement of accepted data based solely on newer upload timestamps.
- No new tick collection without a proved data gap and authorization.
- No direct write to Core during discovery-platform implementation.
- New platform outputs must coexist with existing hypothesis-specific results until parity is established.
