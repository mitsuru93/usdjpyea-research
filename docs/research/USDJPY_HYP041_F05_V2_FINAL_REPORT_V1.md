# USDJPY-HYP-041 — F05 2025H1 Loss Recovery and Portable Architecture Study

## Final decision

`FAIL_F05_V2_PORTABLE_RECOVERY`

No finite F05 v2 candidate preserved material 2023–2024 F05 economics while materially improving both 2025H1 F05 and the B02＋F05 portfolio. No candidate was selected for Core／MT4 implementation.

## Goal and baseline

The EA-wide objective remains to preserve the established 2023–2024 B02／F05 economics and pass the 2025H1 validation period.

| Scope | Result |
|---|---:|
| 2023–2024 F05 | 1,451 trades, +¥39,151, PF 1.1424 |
| 2025H1 F05 | 358 trades, -¥13,844, PF 0.8433 |
| 2025H1 B02 | -¥6,964 |
| 2025H1 B02＋F05 | 463 trades, -¥20,808, PF 0.8294 |
| 2025H1 authority maximum Tick-equity DD | 約¥42,737 |

The baseline identity matched the frozen authority. JPY currency mismatch, same-timestamp chronology mismatch and B02 trade changes were all zero.

## Failure decomposition

A common-schema ledger was reconstructed for 1,809 F05 trades across 2023H1–2025H1. The 2025H1 F05 gross loss of ¥88,333 was attributed by the frozen mutually-exclusive diagnostic schema as follows.

| Bucket | Trades | Gross loss | Share | B02 overlap trades |
|---|---:|---:|---:|---:|
| Market-state misfit | 183 | -¥81,504 | 92.3% | 106 |
| Chronology／same-timestamp interaction | 9 | -¥6,829 | 7.7% | 6 |
| Entry immediately adverse | 0 | ¥0 | 0.0% | 0 |
| Temporary profit then loss | 0 | ¥0 | 0.0% | 0 |
| Edge decay during extended hold | 0 | ¥0 | 0.0% | 0 |
| Same-session consecutive loss | 0 | ¥0 | 0.0% | 0 |
| Other | 0 | ¥0 | 0.0% | 0 |

These labels are deterministic loss attribution under the diagnostic schema. They are not, by themselves, proof that a bucket label defines a portable causal permission rule. The candidate results confirm that distinction: the broad market-state label could compress 2025H1 risk only by eliminating the historical F05 strategy.

## Frozen finite candidate catalog

### C1 — Chronology-aware Loss Persistence Permission

Contract: process accepted F05 closes before entries at identical timestamps, then block a later F05 Entry only after an accepted same-side realized loss in the same UTC date and session. The rule was Long／Short symmetric and did not reuse the exact HYP-027 threshold.

Result:

- 2023–2024 F05: +¥39,151; retention 100%
- 2025H1 F05: -¥13,844; delta ¥0
- 2025H1 portfolio: -¥20,808; delta ¥0
- blocked trades: 0

Decision: `REJECT_NO_2025H1_IMPROVEMENT`.

### C2 — Market-State Risk Compression

Contract: block F05 Entry only when completed-bar `market_state=MISALIGNED` and Entry-time `extension_atr>=1.50`; re-evaluate independently at each signal. This was one fixed rule, not an H4／D1 grid and not exact S3 reuse.

Result:

- 2023–2024 F05: ¥0
- historical F05 blocked: 1,451／1,451
- historical net retention: 0%
- 2025H1 F05: +¥178; delta +¥14,022
- 2025H1 portfolio: -¥6,786; delta +¥14,022
- 2025H1 F05 blocked: 357 trades

Decision: `REJECT_DESTROYS_2023_2024_F05_ECONOMICS`.

C2 demonstrates that state information can compress the known 2025H1 loss, consistent with HYP-029 mechanism evidence. It does not produce a portable F05 v2 architecture because the fixed rule classifies essentially the entire historical F05 population as ineligible.

### C3 — Continuation-Failure／Giveback Lifecycle

Contract: use completed M15 lifecycle observations and Entry-time ATR. Exit a first-bar continuation failure when current P/L is negative and MFE is below 0.25 Entry ATR; exit an ATR-qualified giveback after MFE reaches at least 1.0 Entry ATR and current P/L falls to at most 0.25 Entry ATR. No fixed SL／TP／hold grid or future information was used.

Result:

- 2023–2024 F05: +¥6,032, PF 1.0446
- historical net retention: 15.4%
- historical modified trades: 1,028／1,451
- 2025H1 F05: -¥13,629, PF 0.6959; delta +¥215
- 2025H1 portfolio: -¥20,593, PF 0.7375; delta +¥215
- 2025H1 modified trades: 261／358
- spread +0.5 pip proxy: historical net -¥1,223
- spread +1.0 pip proxy: historical net -¥8,478

Decision: `REJECT_LOW_HISTORICAL_RETENTION_AND_IMMATERIAL_2025H1_RECOVERY`.

### Combined candidate

`C4_C1_PLUS_C3` was not authorized. The preregistered 2023–2024 complementarity requirements were not met, so no combined 2025H1 result was generated.

## Outcome visibility and reruns

- The 2025H1 baseline was known before the study.
- C1／C2／C3 contracts were frozen before their first candidate outcomes.
- Each candidate version had one valid 2025H1 replay.
- Candidate-specific valid replay count: 3 total.
- Candidate retuning after 2025H1: false.
- Schema side mapping and Q1／Q2 aggregation defects were detected and corrected before first candidate execution; invalid candidate replay count remained zero.
- 2025H2 was not accessed.

## Core／MT4 disposition

The Research selection gate returned `NO_PORTABLE_F05_V2_CANDIDATE_FOR_CORE`. Therefore:

- selected candidate: none
- shared F05 v2 production module: not created
- candidate MT4 compile: not applicable
- Research／Core candidate parity: not applicable
- Core／MT4 candidate parity: not applicable
- candidate full-equity and margin replay: not authorized

This is not a technical no-result. The scientific result is complete: the finite candidate catalog failed before a candidate qualified for Core／MT4 implementation. The Core repository preserves the diagnostic and Research evidence at merge commit `4c82040c62d90cec4dfbeeb68d48123fead1de62` without activating production or live behavior.

## Residual loss

The numerically best 2025H1 portfolio result was C2 at -¥6,786, requiring another ¥6,786 to reach zero. It cannot be adopted because it removes all historical F05 trades and retains 0% of the 2023–2024 F05 net.

Among candidates that left a nonzero historical F05 strategy, C3 produced the best modified architecture but left the 2025H1 portfolio at -¥20,593, requiring ¥20,593 to reach zero while retaining only 15.4% of historical F05 net.

## Formal interpretation

HYP-027, HYP-029 and HYP-032 remain closed with their original decisions. Their mechanism evidence remains valid, but the finite HYP-041 translations did not yield a portable F05 v2 candidate.

HYP-039, HYP-040, B02 v2 and the common portfolio integration branch were not changed. Production and live trading remain unauthorized.

## Exact next action

Treat the F05 dimension as `F05_BASELINE_UNCHANGED` in the common portfolio integration framework. Import the HYP-041 formal FAIL, candidate-level residual-loss evidence and no-change disposition. Compare available HYP-039, HYP-040, baseline B02 and HYP-042 C3 reserve combinations without reopening or retuning HYP-041.
