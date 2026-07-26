# USDJPY B02/F05 Research Platform Completion v1

## Status

Implementation complete for the shared, read-only research platform foundation.

## Delivered

1. Canonical trade and event model with UTC and monotonic chronology checks.
2. Deterministic evidence hashing.
3. Machine-readable experiment contracts and registry.
4. Source inventory covering accepted Releases, repository outputs and archive members.
5. Explicit no-recollection rule for Tick data unless a documented non-reconstructable field exists.
6. Read-only adapters for lifecycle summaries and archived path ledgers.
7. F05 failed-reclaim state-transition validation.
8. Common aggregation by period, strategy, side and state.
9. Numeric and categorical factor contrasts with fold-direction consistency and deterministic permutation tests.
10. Observation builder from canonical event streams.
11. Interaction analysis, matched cohorts and bootstrap intervals.
12. Dependency-free GitHub-hosted CI with no market-data download.

## Scientific boundaries

The platform produces descriptive, contrast and robustness evidence. It does not by itself establish causality, adopt candidates, alter frozen research decisions, change EA logic, unlock MT4 implementation, or access 2025 data.

## Data policy

New Tick collection remains locked by default. Existing Releases, receipts, derived bars, archives, path ledgers and evaluator outputs must be exhausted first. A new collection requires a documented required field that cannot be reconstructed from those sources.

## Operational use

Future evaluators should:

1. register the experiment and its falsification rule;
2. resolve sources through the inventory;
3. adapt source trades into canonical records;
4. build observations;
5. run grouped, factor, interaction, matched-cohort and bootstrap diagnostics as applicable;
6. write deterministic result hashes and registry links;
7. preserve Research-to-MT4 parity gates before implementation.

## Completion criteria

The platform foundation is complete when all dedicated tests and the repository Research CI succeed on the final branch commit. Scientific experiments remain separate, registered units of work rather than part of platform completion.
