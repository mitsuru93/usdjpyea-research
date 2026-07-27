# USDJPY Market-State Router S3 — Pre-2025 Final Audit v1

## Corrected decision

**`PASS_PRE2025_ALL_GATES_ELIGIBLE_FOR_SEPARATE_2025_PREREGISTRATION`**

The fixed `S3_H4_ALIGNED` router has passed research portability, exact implementation freeze, H4 state parity, row-level trade-permission parity, controlled Core/MT4 order-path integration, accounting reconciliation, pre-2025 economic attribution and bounded native full-equity drawdown.

The prior audit status, `PASS_HISTORICAL_ECONOMIC_ATTRIBUTION_HOLD_2025_GATE_FOR_EQUITY_DD_AUTHORITY`, is superseded. Its apparent $71.74 equity-DD deterioration came from initializing both running peaks with one snapshot dated **2021-06-04**, 578 days before the 2023–2024 research observations. The separately preregistered reconciliation reset the peak inside the declared study window and showed material DD improvement.

This audit permits a **separate, outcome-free preregistration** of the unchanged one-shot 2025 gate. It does not itself access 2025, dispatch that gate, or authorize production/live orders.

## Frozen candidate

- Candidate: `S3_H4_ALIGNED`
- Completed exact-slot H4 Bid bars
- Recursive EMA(6,24)
- Latest completed H4 state available at entry information time
- Allow entry only when H4 state equals the trade side
- Neutral state blocks both directions
- No B02/F05 semantic change
- No strategy, side, session or period exception
- No parameter change or result-guided repair

## Research result

The canonical 2023H1–2024H2 population contains 1,882 B02/F05 trades. The router blocks 671 and allows 1,211. The frozen research counterfactual improves net P/L by **¥22,687**, with all four half-year folds positive and the weakest fold still positive at **¥931**.

## Core and MT4 parity

The implementation chain passed:

- 3,055 H4 state rows with zero state, timestamp or EMA parity mismatch
- 1,882 canonical reference trades with zero permission mismatch
- Native controlled population: 1,898 candidate rows; 676 blocked; 1,222 allowed
- 1,222 candidate orders opened and 1,222 closed
- Zero order-send failures and zero order-close failures

The 1,882 Research population and 1,898 native MT4 population are deliberately not treated as identical. The immutable economic-attribution package records 9 Research-only rows, 25 native-only rows and 34 nonmatching trade IDs in the population-delta ledger.

## Accounting repair and economic attribution

The tester account currency is **USD**, not JPY. The previous evaluator defect came from labelling account balance/equity values as JPY and comparing those values directly with quote-currency JPY price P/L. The final audit separates account-currency economics from quote-currency price P/L and reconciles every population to zero unexplained balance residual.

### Native MT4 population

| Metric | Baseline | S3 candidate | Change |
|---|---:|---:|---:|
| Trades | 1,898 | 1,222 | -676 |
| Net account P/L | $317.00 | $496.78 | **+$179.78** |
| Gross quote-currency P/L | ¥51,408 | ¥76,391 | **+¥24,983** |
| Profit factor | 1.121774 | 1.311332 | **+0.189558** |
| Closed-trade MDD | $296.11 | $195.06 | **-$101.05 (-34.13%)** |

### Binding 1,882-row population

| Metric | Baseline | S3 candidate | Change |
|---|---:|---:|---:|
| Trades | 1,882 | 1,211 | -671 |
| Net account P/L | $294.56 | $467.24 | **+$172.68** |
| Gross quote-currency P/L | ¥48,203 | ¥72,081 | **+¥23,878** |
| Profit factor | 1.113796 | 1.294391 | **+0.180596** |
| Closed-trade MDD | $296.11 | $195.06 | **-$101.05** |

Commission and swap are zero in these tester outputs. The maximum absolute per-ticket price-conversion residual is below $0.005, and all four accounting populations have zero unexplained final-balance residual.

## Bounded native full-equity DD reconciliation

### Why the earlier comparison was invalid for the historical gate

The economic-attribution evaluator reproduced the following unbounded values:

| Metric | Baseline | S3 candidate | Change |
|---|---:|---:|---:|
| Unbounded equity DD | $615.74 | $687.48 | +$71.74 |
| Running-peak timestamp | 2021-06-04 | 2021-06-04 | — |

Each population contained exactly one pre-2023 equity snapshot. The next observations begin in January 2023. Using the 2021 snapshot as the running peak therefore mixed an unrelated pre-period balance anchor into the 2023–2024 risk window. These values remain reproducibility diagnostics, not gate authority.

### Canonical 2023–2024 bounded result

The preregistered calculation used `[2023-01-01, 2025-01-01)` UTC and initialized each running peak at the first valid in-window snapshot. Both populations had 49,163 in-window snapshots, a median interval of 900 seconds and zero duplicate timestamps.

| Metric | Baseline | S3 candidate | Change |
|---|---:|---:|---:|
| Peak equity | $10,013.13 | $10,011.00 | — |
| Trough equity | $9,701.26 | $9,809.30 | — |
| Bounded full-equity DD | $311.87 | $201.70 | **-$110.17 (-35.33%)** |
| DD percentage of peak | 3.115% | 2.015% | **-1.100 pp** |
| Balance-path contribution | $278.67 | $188.91 | -$89.76 |
| Floating-P/L contribution | $33.20 | $12.79 | -$20.41 |
| Trough margin | $80 | $40 | -$40 |
| Trough free margin | $9,621.26 | $9,769.30 | +$148.04 |

The DD identity residual is zero in both runs. The candidate’s improvement is not an artefact of ignoring floating P/L: both the realized balance-path contribution and the floating-P/L contribution are smaller.

### Half-year breadth

| Fold | Baseline DD | Candidate DD | Change |
|---|---:|---:|---:|
| 2023H1 | $256.03 | $198.06 | **-$57.97 (-22.64%)** |
| 2023H2 | $182.36 | $131.75 | **-$50.61 (-27.75%)** |
| 2024H1 | $67.17 | $57.86 | **-$9.31 (-13.86%)** |
| 2024H2 | $124.62 | $96.59 | **-$28.03 (-22.49%)** |

The candidate is non-worse in **4/4** half-year folds.

## Canonical drawdown authority

For historical and future gates, the primary risk metric is:

> Native full MT4 equity-curve peak-to-trough maximum drawdown in the effective account currency, including intratrade floating P/L, with the running peak initialized at the first valid snapshot inside the declared evaluation window.

Closed-trade MDD remains a secondary diagnostic. Pre-period snapshots may be retained for reproducibility but may not initialize the gate-window running peak.

## Gate matrix

| Gate | Result |
|---|---|
| Research portability | PASS |
| Candidate freeze | PASS |
| H4 state parity | PASS |
| Trade permission parity | PASS |
| Controlled order-path integration | PASS |
| Accounting reconciliation | PASS |
| Historical net improvement | PASS |
| Historical PF improvement | PASS |
| Closed-trade MDD improvement | PASS — diagnostic |
| Bounded native full-equity MDD non-worse | **PASS** |
| Half-year equity-DD breadth | **PASS — 4/4** |
| 2025 gate eligibility | **PASS — separate preregistration allowed** |
| 2025 gate authorization in this audit | **NO** |
| Production/live authorization | **NO** |

## Evidence authority

### Research

- Impact Atlas Phase 1: PR #286
- Market-State Routing Phase 2: PR #293
- Candidate/reference freeze: PR #297
- Exact implementation contract/reference v2: PR #316
- Initial pre-2025 audit and identified blocker: PR #326
- DD protocol and pre-outcome schema amendments: PRs #327–#329
- Result JSON: `configs/research/usdjpy_market_state_router_native_equity_dd_reconciliation_result_v1.json`

### Core

- H4 parity Run `30237882923`; Issues #314/#315
- Reference trade identity Run `30238772493`; Issue #325
- Preimplementation audit Run `30239760337`; Issue #328
- Controlled order-path Run `30241915781`; Issues #332/#333
- Economic-attribution Run `30256893465`; Issue #368
- Final economic Release readback Run `30259786568`; Issue #376
- Bounded equity-DD reconciliation Run `30261603069`; Issue #395; PR #387

Economic-attribution Release:

- Tag: `usdjpy-market-state-router-s3-economic-attribution-v1`
- Target Core SHA: `2deb131bdda3dd13d0b5b69d0c80967235fb3e66`
- Archive: `usdjpy-s3-economic-attribution-30256893465.zip`
- SHA-256: `40cdd1f8c6e7984e500a79ce430e697c3c33d31c6c4d8daa30e6ad6a5bb7062b`

DD-reconciliation Release:

- Tag: `usdjpy-s3-native-equity-dd-reconciliation-v1`
- Target Core SHA: `b3cc4faa4c83e6a3c00df0fec8262b7d9290f7e1`
- Archive: `usdjpy-s3-native-equity-dd-30261603069-1.zip`
- SHA-256: `8896d464935eccaba551847de3a332d5d744f3d1e42d1e0d7b7851af9a83fa72`

## Next action

Create a **separate outcome-free one-shot 2025 gate protocol** for the unchanged `S3_H4_ALIGNED` candidate. That protocol must freeze period roles, population identity, Baseline/candidate implementation, accounting currency, cost treatment, net/PF/DD gates, half-year breadth, execution errors, margin/stopout checks and the treatment of any population mismatch before reading 2025 outcomes.

No EMA retuning, exception grid, B02/F05 change or post-2025 repair is permitted.
