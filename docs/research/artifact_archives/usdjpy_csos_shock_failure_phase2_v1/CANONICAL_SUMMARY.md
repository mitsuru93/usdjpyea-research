# USDJPY CSOS Shock Failure Phase 2 v1 — Canonical Summary

## Decision

`PASS_PORTABLE_RESEARCH_CANDIDATE`

Frozen candidate: `B_EXECUTABLE_T0_8BAR`. This is a research candidate only. Core implementation, MT4, 2025H1/H2, live operation and B02/F05 integration remain unauthorized.

## Authorities

- Research main inspected at start: `2a245a36a97282cbf840e0e9f2ea26f18239cadc`
- Core main inspected at start: `6ded071b3ba83cc13ff5aabb664017c80e421f9b`
- CSOS PR #295 head: `74c9dc6869c805e3ec3fe1db87e5744ef62729b6`
- CSOS evaluator: `11643bd5c9d04dec1d8df34e681b6516cc39264b`
- CSOS canonical result: `88b88cd01bb84fafdf2e097401222d4f9dac1c6d`
- Corrected CSOS Release: `usdjpy-csos-opportunity-atlas-v1-r1`
- Phase 2 PR run: `30205540213`
- Phase 2 artifact: `8632971871`, `sha256:8e969013266e6289a8571d8939b8a51a964be8c87f40107ca1b6e1992a9ed27d`

## Event and chronology audit

- CSOS events reproduced: 114/114
- Duplicate IDs / duplicate shock starts / overlapping duplicate intervals / same-shock double counts: 0 / 0 / 0 / 0
- Timezone mismatches / bar-close leakage: 0 / 0
- Chronology: 58 exact, 53 bounded 2023 cross-source, 3 unresolved (2.63%).
- Excluding all 3 unresolved events leaves 111 trades, +¥12,207, PF 2.372. Spread +1 pip leaves +¥11,097; severe stress leaves +¥9,033, PF 1.916. Candidate selection remains B and LOFO remains 3/4 positive.

## Selected candidate observed-spread performance

- Trades: 114
- Net: +¥12,502
- PF: 2.381
- Win rate: 62.28%
- MDD: ¥1,555
- Positive folds: 3/4
- Positive months: 17/24
- Long: +¥7,288, PF 2.572
- Short: +¥5,214, PF 2.180

## Stress and portability

- Spread +1 pip: +¥11,362, PF 2.197
- Severe: +¥9,689, PF 1.964
- Remove top 3 events: +¥6,600, PF 1.729
- Remove top decile wins: +¥2,604, PF 1.288
- LOFO rule-selected held-out results: B +¥2,776; C -¥313; C +¥423; B +¥8,235 = 3/4 positive.

## Complementarity and portfolio

- Correlation: B02 +0.052; F05 -0.126
- B02/F05 negative-day contribution: +¥9,462
- Time overlap: 86.84%; existing baseline drawdown at entry: 97.37%
- Additive fixed-lot portfolio: +¥64,129; MDD ¥38,213 versus baseline ¥40,455 (-5.54%).
- Peak concurrent positions estimate: 7; incremental margin estimate at 25x: ¥6,455.

## Boundaries

No 2025 data were accessed. B02/F05 logic was not changed. Core and MT4 were not accessed. Production was not authorized.
