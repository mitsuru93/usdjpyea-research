# USDJPY Market-State Router S3 — Pre-2025 Final Audit v1

## Decision

**`PASS_HISTORICAL_ECONOMIC_ATTRIBUTION_HOLD_2025_GATE_FOR_EQUITY_DD_AUTHORITY`**

The fixed `S3_H4_ALIGNED` router has passed research portability, exact implementation freeze, H4 state parity, row-level trade-permission parity, controlled Core/MT4 order-path integration, accounting reconciliation and pre-2025 economic attribution.

It is **not** authorized for the 2025 gate, production or live orders. The reason is not a failure of profitability or accounting. The unresolved blocker is the drawdown authority: realized closed-trade drawdown improves, while the native full MT4 equity path worsens.

No 2025H1 or 2025H2 evidence was accessed in this audit.

## Frozen candidate

- Candidate: `S3_H4_ALIGNED`
- Completed exact-slot H4 Bid bars
- Recursive EMA(6,24)
- Use the latest completed H4 state available at entry information time
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
| Full-equity MDD | $615.74 | $687.48 | **+$71.74 (+11.65%)** |

### Binding 1,882-row population

| Metric | Baseline | S3 candidate | Change |
|---|---:|---:|---:|
| Trades | 1,882 | 1,211 | -671 |
| Net account P/L | $294.56 | $467.24 | **+$172.68** |
| Gross quote-currency P/L | ¥48,203 | ¥72,081 | **+¥23,878** |
| Profit factor | 1.113796 | 1.294391 | **+0.180596** |
| Closed-trade MDD | $296.11 | $195.06 | **-$101.05** |

Commission and swap are zero in these tester outputs. The maximum absolute per-ticket price-conversion residual is below $0.005, and all four accounting populations have zero unexplained final-balance residual.

## Drawdown authority conflict

Two different statements are simultaneously true:

1. The candidate removes enough losing closed trades to reduce realized closed-trade drawdown from $296.11 to $195.06.
2. The candidate changes the sequence and overlap of retained positions such that native peak-to-trough MT4 equity drawdown increases from $615.74 to $687.48.

For a gate that also evaluates free margin and stopout exposure, full equity is the relevant risk path. Closed-trade balance drawdown remains useful, but it cannot be the primary gate metric because it excludes intratrade floating P/L.

Therefore this audit freezes the future canonical MDD metric, before any 2025 access, as:

> Native full MT4 equity-curve peak-to-trough maximum drawdown in the effective account currency, including intratrade floating P/L, under fixed Baseline versus fixed Baseline plus `S3_H4_ALIGNED` runs.

The filtered binding reports both show $360 equity DD, but those values are retained only as diagnostics. A population-filtered report cannot supersede the native order/equity path for margin-risk authorization.

Under the newly explicit native full-equity authority, the historical non-worse DD gate fails. This does not invalidate the router’s historical economic edge. It prevents premature escalation to the one-shot 2025 gate.

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
| Native full-equity MDD non-worse | **FAIL** |
| 2025 gate authorization | **HOLD** |
| Production/live authorization | **NO** |

## Evidence authority

### Research

- Impact Atlas Phase 1: PR #286
- Market-State Routing Phase 2: PR #293
- Candidate/reference freeze: PR #297
- Exact implementation contract/reference v2: PR #316

### Core

- H4 parity Run `30237882923`; Issues #314/#315
- Reference trade identity Run `30238772493`; Issue #325
- Preimplementation audit Run `30239760337`; Issue #328
- Controlled order-path Run `30241915781`; Issues #332/#333
- Economic-attribution Run `30256893465`; Issue #368
- Release diagnostic readback: Issue #371
- Final extraction-free Release content readback Run `30259786568`; Issue #376

Immutable Release:

- Tag: `usdjpy-market-state-router-s3-economic-attribution-v1`
- Target Core SHA: `2deb131bdda3dd13d0b5b69d0c80967235fb3e66`
- Archive: `usdjpy-s3-economic-attribution-30256893465.zip`
- SHA-256: `40cdd1f8c6e7984e500a79ce430e697c3c33d31c6c4d8daa30e6ad6a5bb7062b`
- Seven required evaluation files independently read back

## Next action

Run one **pre-2025 native full-equity DD reconciliation** under a separately preregistered, outcome-free protocol. It must explain the $71.74 equity-DD deterioration using existing 2023H1–2024H2 order and equity paths without changing the S3 rule and without accessing 2025.

The study may classify whether the deterioration comes from retained-position overlap, exposure timing, forced-close handling, warm-up/start-equity history, or another ledger-reconcilable mechanism. It may not tune EMA spans, add exceptions, modify B02/F05, or use 2025 outcomes.

Only after that reconciliation establishes an explicit escalation rule may a separate decision authorize or reject the fixed one-shot 2025 gate.
