# USDJPY B02/F05 Entry Establishment Phase 2 — result v1

Updated: 2026-07-26

## Status

`PHASE2_DIAGNOSIS_COMPLETE_NO_CANDIDATE_AUTHORIZATION`

The preregistered prospective Entry-establishment study completed on the canonical 2023H1, 2023H2, 2024H1 and 2024H2 population. No 2025 outcome, MT4 execution, candidate authorization, EA implementation or production authorization was used.

## Population and lineage

- canonical trades: 1,882
- canonical state rows: 68,955
- Research execution SHA: `20c415c3cbab81f27c59b53951fcefe6f729fbc6`
- Core authority SHA: `aca45ab891d9a6da272b5111a99142d99e874929`
- Phase 2 run: `30201494372`
- artifact ID: `8631779176`
- artifact digest: `sha256:c8ad3b2d2864db32015d5b7c68034a09b00ec0b16cfeee354e30387d2b7eb6f1`
- artifact expiry: 2026-10-24

## Primary result

The preregistered leave-one-fold-out portability gate failed.

| Held-out fold | Selected on remaining folds | Held-out net delta |
|---|---|---:|
| 2023H1 | `DC_m15_votes_lt_2` | ¥79 |
| 2023H2 | `DC_m30_votes_lt_2` | -¥1,427 |
| 2024H1 | `DC_m15_votes_lt_2` | -¥167 |
| 2024H2 | `AF_m30_mae_ge_10_mfe_lt_2` | -¥21,750 |

Only 1 of 4 held-out folds was positive. The preregistered portability requirement was therefore not met.

## Descriptive best rule

The full-sample descriptive best was `DC_m15_votes_lt_2`:

- family: directional confirmation
- checkpoint: 15 minutes
- triggered trades: 15
- losers affected: 11
- winners affected: 4
- gross loss avoided: ¥3,852
- winner damage: ¥1,184
- net delta: ¥2,668
- loser capture rate: 1.20%
- winner hit rate: 0.41%

Fold results:

| Fold | Triggered | Net delta |
|---|---:|---:|
| 2023H1 | 6 | ¥79 |
| 2023H2 | 3 | ¥1,233 |
| 2024H1 | 3 | -¥167 |
| 2024H2 | 3 | ¥1,523 |

This rule is not authorized. Its total improvement is small relative to the Phase 1 admission-side upper bound, it affects only 15 trades, and its LOFO selection is not stable.

## Interpretation

The broad proposition that Entry-establishment quality is important remains descriptively valid, but the current small decision-time rule family does not convert it into a portable intervention. Simple early MFE/MAE thresholds, directional-vote thresholds and signal-expiration definitions either damage too many eventual winners or fail to reproduce when a fold is held out.

The particularly large 2024H2 failure of the training-selected adverse-first rule shows that aggregate historical optimization can select a rule whose apparent loser benefit is dominated by regime-specific winner damage.

## Decision

- Phase 2 portable candidate: **none**
- candidate authorization: **not granted**
- MT4 implementation: **not authorized**
- 2025H1 gate test: **not authorized from this Phase 2 result**
- production authorization: **not granted**

The next Impact Atlas priority should move to **Market-state strategy routing**, while preserving Entry-establishment as a future enriched-data research topic rather than extending the same local threshold grid.

## Evidence package

The artifact contains:

- `candidate_fold_metrics.csv`
- `candidate_overall_ranking.csv`
- `lofo_selection_results.csv`
- `execution_receipt.json`
- `result_report.md`
- preregistration and input materialization receipts
- deterministic package SHA-256 list
