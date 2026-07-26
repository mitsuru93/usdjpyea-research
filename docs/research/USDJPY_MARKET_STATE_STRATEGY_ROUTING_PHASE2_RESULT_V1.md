# USDJPY B02/F05 Market-State Strategy Routing Phase 2 — result v1

Updated: 2026-07-26

## Decision

`PASS_PORTABLE_MARKET_STATE_ROUTER_RESEARCH_CANDIDATE_ONLY`

The preregistered native completed-H4 permission overlay passed the historical leave-one-fold-out portability gate on the canonical 1,882-trade B02/F05 population. This is a Research candidate result only. It does not authorize MT4 implementation, 2025 access, candidate promotion or production use.

## Distinction from closed HYP-023

`USDJPY-HYP-023` tested a primary native-H4 entry architecture and remains closed. This study did not regenerate Entry signals. Every canonical B02/F05 Entry and realized outcome was preserved; completed H1/H4 state was joined as information available at Entry and used only as a permission overlay.

## Source authority

- canonical B02/F05 trade ledger SHA-256: `98c9c8cf57c62c23a94aa38efa6ee257e823dd0b68c413615197a48be00b08ca`
- canonical population: 1,882 trades
- 2023 native-state M15 SHA-256: `4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78`
- 2024 native-state M15 SHA-256: `1566b9d0497f3a2aa156868144d31b89721fca48329feaf82035826ada7ee25c`
- periods: 2023H1, 2023H2, 2024H1, 2024H2
- 2025 accessed: no
- MT4 accessed: no

## Frozen candidate class

The selected rule was:

`S3_H4_ALIGNED`

Definition:

- construct completed exact-slot H4 bars under the accepted historical MT4-server-time contract;
- calculate H4 fast EMA 6 and slow EMA 24 using `pandas ewm(adjust=false)`;
- at the B02/F05 Entry timestamp, use only the most recent completed H4 state;
- permit the Entry only when the H4 state equals the trade direction;
- otherwise block the trade.

`S4_H4_ALIGNED` is outcome- and trade-key-equivalent because H1 parameters are unused by an H4-only permission rule. The deterministic lexicographic representative is S3. This is one equivalence class, not two independent confirmations.

## Descriptive pooled effect

| Metric | Result |
|---|---:|
| Baseline trades | 1,882 |
| Blocked trades | 671 |
| Loser benefit | ¥146,177 |
| Winner damage | ¥123,490 |
| Net delta | **+¥22,687** |
| Positive folds | 4 / 4 |
| Minimum fold net | **+¥931** |

The overlay removes substantial losing exposure, but it also suppresses substantial winner profit. The gross loser benefit must not be reported without the ¥123,490 winner damage.

## Leave-one-fold-out result

The same equivalence-class representative was selected independently from each three-fold training set.

| Held-out fold | Selected rule | Total net delta | Blocked | B02 delta | F05 delta |
|---|---|---:|---:|---:|---:|
| 2023H1 | S3_H4_ALIGNED | +¥7,232 | 197 | +¥5,040 | +¥2,192 |
| 2023H2 | S3_H4_ALIGNED | +¥931 | 177 | +¥1,386 | -¥455 |
| 2024H1 | S3_H4_ALIGNED | +¥2,816 | 120 | +¥69 | +¥2,747 |
| 2024H2 | S3_H4_ALIGNED | +¥11,708 | 177 | +¥709 | +¥10,999 |

Gate summary:

- total held-out net positive: 4 / 4 folds;
- B02 held-out net non-negative: 4 / 4 folds;
- F05 held-out net non-negative: 3 / 4 folds;
- held-out support: at least 120 blocked trades in every fold;
- preregistered portability gate: passed.

The weakest cell is F05 in 2023H2 at -¥455. This is retained and no fold, strategy, side or session exception is authorized.

## Interpretation

The result supports the narrower proposition that B02/F05 performance is conditional on the direction of the most recently completed native H4 EMA 6/24 state. It does not establish that every blocked trade is causally invalid, nor that the historical pooled +¥22,687 will be realized in 2025H1.

Because 35.7% of all trades are blocked and winner damage is large, direct EA implementation from this diagnostic would be premature. The next step is an exact candidate freeze and Research-to-MT4 parity study. The definition, time conversion, exact-slot aggregation, EMA initialization, completed-information timing and Entry permission identity must be reproduced before any 2025 access.

## Authorization boundary

- historical Research candidate: yes;
- exact finalist representative: `S3_H4_ALIGNED` equivalence class;
- Core/MT4 implementation authorization: no;
- 2025H1 evaluation authorization: no;
- production authorization: no.

## Execution evidence

- PR: `#293`
- successful Market-State Phase 2 run: `30202764106`
- successful Research CI run: `30202764117`
- Actions artifact ID: `8632158661`
- artifact digest: `sha256:b2b13c8d50f9a29c49c122b8963e9f07687dac3db7e2fafc50dd34691e113a2c`
- artifact expiry: 2026-10-24

## Next exact action

`MARKET_STATE_ROUTER_CANDIDATE_FREEZE_AND_PARITY_V1`

Freeze the S3/S4 H4-only equivalence class to representative `S3_H4_ALIGNED`, create a row-level Research reference ledger, and prove Core/MT4 parity without reading any 2025 outcome. Only successful parity may open a separately preregistered 2025H1 gate evaluation.
