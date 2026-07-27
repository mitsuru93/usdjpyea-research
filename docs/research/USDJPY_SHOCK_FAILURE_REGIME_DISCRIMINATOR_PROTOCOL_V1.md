# USDJPY-HYP-028 — Shock Failure Regime Discriminator Protocol v1

## Hypothesis

At the completed Shock Failure decision boundary, a small, auditable set of impulse, failure-quality, continuation-pressure and completed higher-timeframe features may distinguish `F_CONTINUATION_RESUMPTION` from `H_SUSTAINED_REVERSAL` without changing `B_EXECUTABLE_T0_8BAR`.

## Scientific boundary

- Development and selection use only 2023H1, 2023H2, 2024H1 and 2024H2.
- 2025H1/H2 remain consumed postmortem evidence and are not input to the selection evaluator.
- The old candidate is not retuned. A passing result creates a new candidate ID and authorizes only an implementation-contract stage.
- `D_PROFIT_THEN_GIVEBACK` is measured but no exit rule is optimized in this study.

## Lifecycle audit

The exact Raw Tick path is reconstructed for all 114 frozen Phase 2 opportunities. Canonical labels are reproduced with the r2 postmortem classifier. The historical approximate labels are preserved and any difference is emitted into a separate ledger rather than overwritten.

## Candidate catalog

The finite catalog is frozen before outcomes:

1. `RD_LOGIT_10F_V1`: ten-feature explanatory logistic score.
2. `RD_TREE_D2_V1`: depth-two implementation-oriented tree using the same ten features.
3. `RD_RANK6_V1`: six-feature monotonic score with training-only orientation.

Every model uses Leave-One-Fold-Out predictions. Thresholds come from the fixed preregistered grid and are selected only inside training folds.

## Decision

A portable candidate exists only if every preregistered breadth, retention, rejection, stress, stability, concentration, timestamp and implementation gate passes. Otherwise the required result is `NO_PORTABLE_CANDIDATE`.
