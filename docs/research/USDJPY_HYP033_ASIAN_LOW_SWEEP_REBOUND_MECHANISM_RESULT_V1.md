# USDJPY-HYP-033 / Asian Low Sweep Post-Sweep Rebound Mechanism Study

## Final decision

`NO_EX_ANTE_OBSERVABLE_DISCRIMINATOR`

The source-native Long rebound asymmetry is real in 2023–2024, but the preregistered Entry-time discriminator does not produce a portable candidate. The study stops at binding Stop Rule 5. No candidate freeze, historical validation, Core/MT4 implementation, 2025 validation, production authorization or live authorization exists.

## Identity

- Hypothesis: `USDJPY-HYP-033`
- Family: `S_ASIAN_LOW_SWEEP_REBOUND_MECHANISM`
- Research start SHA: `a9b139e971bbaa8ed0ab64d0bef66b542eb78be5`
- Core start/end SHA: `f897b250b808207d960417b2306935dcb0655acf`
- Binding source SHA: `a4eae54d21216b059d39b84b5ade56b87d527fd6`
- Binding Run: `30375772490`
- Artifact: `8695153813`
- Artifact digest: `sha256:941d0da79889bd6e4357cc6cfb769c557f05f22c5b145c5423a0a95c3955b7c6`
- Deterministic archive SHA-256: `e119f466dff6938b30425f1a05fa08a916a53599e256e8728eb7c3d23a2b3298`
- Release tag: `usdjpy-hyp033-asian-low-sweep-rebound-mechanism-v1`
- PR: `#377`
- Binding receipt Issue: `#385`

## Source authority

- Resolved executable events: 547
- Long / Short: 241 / 306
- Asian Low / High sweep detections before suppression: 888 / 1131
- Both-side sweep events: 16
- Unresolved chronology / duplicate / no executable Entry: 0 / 0 / 0
- Common / canonical-only / raw-native-only: 507 / 38 / 40
- Side / Entry / Exit / P/L mismatches: 0 / 0 / 5 / 5

The five Exit/P&L mismatches remain in the mismatch ledger. No unfavorable mismatch row was removed.

## Long/Short mechanism result

| Metric | Long | Short |
|---|---:|---:|
| Trades | 241 | 306 |
| Net | ¥13,650 | ¥-8,542 |
| PF | 1.595524 | 0.769602 |
| MDD | ¥2,916 | ¥10,529 |
| Positive folds | 4/4 | 0/4 |
| Positive months | 21/24 | 10/24 |
| Median MAE | -15.1 pips | -16.7 pips |
| Median MFE | 18.5 pips | 13.9 pips |
| Median reclaim speed | 12.856s | 17.727s |
| Midpoint reach | 48.55% | 32.68% |
| Range re-departure | 77.18% | 86.27% |

Long profitability is not a simple H4/D1 upward-direction exposure: Long net is positive in completed H4 Down and D1 Down states and the exact diagnostic marks `not_simple_h4_d1_exposure=true`.

## Ex-ante observability

The preregistered feature was `reclaim_speed_seconds`, using a coarse threshold of 60 seconds and only information available by Entry admission. Lookahead violations were zero.

Fast Long retained positive pooled economics, but failed the binding fold, minimum-fold, bootstrap and portfolio-MDD gates:

- trades: 154
- net: ¥8,398
- PF: 1.521356
- positive folds: 3/4
- minimum fold: ¥-2,059
- event bootstrap lower 95%: ¥-183.07
- date/session bootstrap lower 95%: ¥-516.05
- additive portfolio net: ¥60,025 versus ¥51,627
- additive portfolio MDD: ¥41,199 versus ¥40,487

The slow Long group was also profitable and failed in a different fold. Reclaim speed therefore describes the mechanism but does not identify portable rebound quality.

## Candidate catalog

- `C1_SYMMETRIC_FAST_RECLAIM`: failed.
- `C2_SYMMETRIC_SHALLOW_FAST_RECLAIM`: failed.
- Long-only catalog admission: not authorized because the ex-ante discriminator and portfolio DD complementarity conditions failed.

Selected candidate: none. Candidate freeze: none.

## Downstream authorization

- 2020–2022 accessed: false
- Core/MT4 accessed: false
- 2025H1/H2 accessed: false
- production authorized: false
- live authorized: false
- retuning authorized: false

## Research value retained

The study establishes a genuine source-native Long/Short path asymmetry. The remaining research value is not another threshold adjustment of reclaim speed or a Long-only rescue. A future independent hypothesis would need a distinct Entry-time mechanism that explains post-sweep inventory absorption or failed continuation while preserving portfolio DD.
