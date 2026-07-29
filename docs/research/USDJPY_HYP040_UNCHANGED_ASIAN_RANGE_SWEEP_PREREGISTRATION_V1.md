# USDJPY-HYP-040 — Unchanged Asian Range Sweep 2025H1 Portfolio Recovery Qualification

## Status

`ACTIVE_FROZEN_PRE_2025H1_QUALIFICATION`

This is an independent EA-wide deployment qualification of the unchanged `USDJPY-HYP-030 / A_EXACT_EXECUTABLE_12BAR` mechanism. It does not reopen HYP-030 and does not modify its formal `NO_PORTABLE_CANDIDATE` decision. HYP-039 remains a separate active study and is excluded from every binding HYP-040 portfolio comparison.

## Frozen candidate

`A_EXACT_EXECUTABLE_12BAR_UNCHANGED`

- completed M15 Bid bars;
- exactly 28 Asian-range bars from `00:00 <= t < 07:00 UTC`;
- signal window `07:00 <= t < 20:00 UTC`;
- upper sweep and close back below Asian High opens Short;
- lower sweep and close back above Asian Low opens Long;
- decision at signal-bar completion;
- first executable Tick Entry: Long Ask / Short Bid;
- first executable Tick Exit after exactly 12 M15 bars: Long Bid / Short Ask;
- variant-local active suppression, same-day/same-side suppression, original duplicate and fold handling;
- 0.01 lot and JPY accounting.

The machine-readable authority is `configs/research/usdjpy_hyp040_candidate_contract_v1.json`; its pre-2025H1 freeze is recorded in `usdjpy_hyp040_candidate_freeze_receipt_v1.json`.

## Period firewall

- 2020–2022: optional historical reference / analysis; not a binding prerequisite.
- 2023–2024: Research reproduction, Core implementation, parity, Rakuten portability and margin/concurrency preflight.
- 2025H1: validation period. First candidate-specific access is `UNSEEN_AT_FIRST_VALIDATION`; subsequent unchanged-version executions remain validation-period reruns or post-result revalidation.
- 2025H2: not automatically substituted or consumed.

## Canonical HYP-030 evidence retained

- 545 trades;
- standalone `+¥7,432`, PF `1.1264`, 4/4 positive folds and 18/24 positive months;
- B02/F05 negative-day contribution `+¥18,055` and drawdown-day contribution `+¥8,799`;
- portfolio net `¥51,627 → ¥59,059` and daily PF `1.194 → 1.229`;
- portfolio MDD `¥40,487 → ¥40,548`, the formal HYP-030 gate failure of `¥61`.

The ¥61 historical MDD deterioration is retained as risk evidence; it is not treated as proof that the unchanged strategy lacks alpha or as a pre-2025H1 disqualification.

## Binding 2025H1 comparison

`B02 + F05` versus `B02 + F05 + unchanged Asian Range Sweep`.

Standalone, `B02 + Sweep`, and `F05 + Sweep` are diagnostics. HYP-039 is not included. Decisions are the preregistered full recovery, risk-tradeoff recovery, partial recovery, portability failure, Rakuten historical portability failure, or technical no-result classifications.

Production and live trading are not authorized.
