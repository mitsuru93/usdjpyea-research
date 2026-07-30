# USDJPY Current Memory — HYP-040 Closure

## Binding state

`USDJPY-HYP-040 / A_EXACT_EXECUTABLE_12BAR_UNCHANGED` is complete and closed.

- Formal decision: `FAIL_RAKUTEN_2023_2024_PORTABILITY_WITH_2025H1_VALIDATION_COMPLETED`
- Economic 2025H1 decision: `FAIL_ASIAN_RANGE_SWEEP_2025H1_PORTABILITY`
- Candidate status: `CLOSED_PORTABILITY_FAILURE_WITH_2025H1_EVIDENCE`
- Common Portfolio authorization: false
- Production/live authorization: false

## Numbers to retain

- Rakuten 2023–2024: 545 trades, +¥4,221, PF 1.069930, 3/4 positive folds, 265 exact mismatches.
- 2025H1 standalone: 140 trades, -¥23, PF 0.998896.
- 2025H1 B02+F05 baseline: -¥20,808, PF 0.829408, full-equity DD ¥42,737.
- 2025H1 combined: -¥20,831, PF 0.854136, full-equity DD ¥38,644.
- Combined versus baseline: net -¥23; full-equity DD -¥4,093.
- Daily correlation to baseline: -0.413955; weekly: -0.528809.

## Interpretation

The candidate showed useful negative correlation and reduced drawdown, but this did not translate into deployable alpha. Historical exact portability failed, standalone 2025H1 was slightly negative, and the combined portfolio was ¥23 worse than baseline. HYP-040 must not be rescued, retuned or reopened under the same identity.

## Non-interference

HYP-030 remains `NO_PORTABLE_CANDIDATE`. HYP-039 was not modified or combined. 2025H2 remains unaccessed.

## Evidence

- Core main merge: `50f4b70bc3500c395ae332ed7fd16427bc968f53`
- Core Result Issue: `#694`
- Release: `usdjpy-hyp040-asian-range-sweep-2025h1-validation-v2`
- Archive SHA-256: `dde913ad860da5be5a6a4ae21e17e3e02f1d64333858ca8c3e432e8a18feb6e9`

## Exact next action

Exclude HYP-040 from the authorized Common Portfolio constituent set. Retain the evidence only for read-only comparison and mechanism design in separately preregistered future research.
