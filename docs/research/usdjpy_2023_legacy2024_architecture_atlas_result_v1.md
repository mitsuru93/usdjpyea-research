# USDJPY 2023 legacy2024-compatible baseline and Architecture Atlas v1

Decision: **PASS — accept for cross-year diagnosis**

## Lineage

The accepted historical 2024 H1/H2 data, trade keys and P/L were not modified. Only 2023 timestamps and derived trade/Atlas fields were transformed to the historical 2024 `ServerToUtc` and US-DST hard-exclusion contract.

The previously accepted canonical-clock 2023 baseline and Atlas remain preserved as a separate lineage and are not combined with this result.

## Mandatory 2024 reproduction gate

- opened / closed: 429 / 428
- B02 / F05 opened: 98 / 331
- net: JPY 22,797
- missing accepted trade keys: 0
- unexpected trade keys: 0
- accepted 2024 H1 M15 SHA-256: `766be5ebba158e5b40f5da5d66929b4da8a25d42a8716b1e591d7c09dd87c2a3`
- accepted 2024 H1 ledger SHA-256: `0b3e7235be48c1113ce77367fda1922d27a347f480344a2ca5c4f86e995e7eb5`

## 2023 result under the historical 2024 contract

- opened / closed / period-end open: 961 / 960 / 1
- B02 / F05 closed: 230 / 730
- net: JPY -9,279
- PF: 0.954994325182
- P1 / P2 / P3 / Winner: 222 / 164 / 106 / 468
- M15 timestamps changed from true UTC: 1,543
- duplicate / non-ascending transformed timestamps: 0 / 0

## Difference from the separately preserved canonical-clock 2023 lineage

- common open trade keys: 906
- historical-2024-compatible only: 55
- canonical-clock only: 58
- net difference: JPY +625

This is a real population difference, not a display-only timestamp change.

## Output identities

- joined Atlas: `3cc1df9e39cc77efb33eba6cd3c3e98c9d5bfb18d05997c6550c4c6e19394097`
- entry features: `7c6f5a557fc3a24db42d2562769f4f5de060b6bcc778a81af167d055439135a5`
- outcomes: `b573e428fc9237eec48bfcbbc6d60a63ecc2d562e991d56820764159dfceac39`
- builder execution SHA-256: `7cb022bbe0ed59fff588f495b4dd212e66d66e5bc640ff68963db64aea25c8b8`

## Next authorization

Cross-year descriptive diagnosis on 2023, 2024 H1 and 2024 H2 is authorized. Candidate evaluation is limited to the already frozen 18-cell Family G preregistration. 2025 H1/H2 remain locked.
