# USDJPY-HYP-040 Final 2025H1 Decision v2

## Formal conclusion

`USDJPY-HYP-040 / A_EXACT_EXECUTABLE_12BAR_UNCHANGED` is closed with:

- formal deployment decision: `FAIL_RAKUTEN_2023_2024_PORTABILITY_WITH_2025H1_VALIDATION_COMPLETED`
- economic 2025H1 decision: `FAIL_ASIAN_RANGE_SWEEP_2025H1_PORTABILITY`
- candidate status: `CLOSED_PORTABILITY_FAILURE_WITH_2025H1_EVIDENCE`

The unchanged Asian Range Sweep is not an authorized third strategy, is not authorized for Common Portfolio Integration, and is not authorized for production or live trading.

## Why 2025H1 was executed

The automatic gate sequence would normally stop after the binding Rakuten 2023–2024 portability failure. The user explicitly directed the unchanged candidate to be executed through 2025H1. That direction permitted collection of validation-period economic evidence but did not waive the historical portability failure for deployment or adoption.

The first candidate-specific 2025H1 outcome access occurred at `2026-07-30T02:07:18.1978177Z`. The candidate remained `A_EXACT_EXECUTABLE_12BAR_UNCHANGED`; no retuning or post-result candidate modification occurred. 2025H2 was not accessed.

## Fixed candidate contract

- Asian range: 00:00 to before 07:00 UTC
- Signal window: 07:00 to before 20:00 UTC
- Upper sweep: Short
- Lower sweep: Long
- Entry: next observed M15 open
- Exit: open after 12 observed M15 bars
- Suppression: variant-active, same-day same-side and fold-boundary controls
- Fixed size: 0.01 lot

Research/Core parity reproduced 545 of 545 canonical HYP-030 rows with zero row-field mismatch. MetaEditor compile completed with zero errors and zero warnings. The 2025H1 path audit confirmed `12_OBSERVED_M15_BARS`, zero holding mismatch and zero unresolved trades.

## Rakuten 2023–2024 portability

| Metric | Result |
|---|---:|
| Trades | 545 |
| Net | +¥4,221 |
| Profit factor | 1.069930 |
| Positive folds | 3 / 4 |
| Exact schedule or row mismatches | 265 |
| Baseline net | +¥52,779 |
| Combined net | +¥57,000 |

Aggregate profitability did not cure the exact portability failure. The 265 mismatches show that the Rakuten executable population, price or chronology contract did not reproduce the binding Dukascopy candidate exactly. Therefore `FAIL_RAKUTEN_2023_2024_PORTABILITY` remains binding.

## 2025H1 validation results

| Variant | Trades | Net | PF | Full-equity DD |
|---|---:|---:|---:|---:|
| B02 + F05 baseline | 463 | -¥20,808 | 0.829408 | ¥42,737 |
| Asian Range Sweep standalone | 140 | -¥23 | 0.998896 | ¥5,990 |
| B02 + F05 + Asian Range Sweep | 603 | -¥20,831 | 0.854136 | ¥38,644 |
| B02 + Asian Range Sweep | 245 | -¥6,987 | 0.871746 | ¥12,132 |
| F05 + Asian Range Sweep | 498 | -¥13,867 | 0.872977 | ¥25,321 |

Standalone direction split:

- Long: -¥1,140
- Short: +¥1,117

Portfolio delta versus B02 + F05 baseline:

- net: -¥23
- PF: +0.024728
- full-equity DD: -¥4,093
- realized DD: -¥3,764
- minimum equity: +¥4,093
- minimum free margin: -¥1,350.82

The candidate reduced drawdown but did not recover portfolio loss. Standalone net was slightly negative and PF remained below 1. The combined portfolio was ¥23 worse than baseline and remained deeply negative. Accordingly the 2025H1 economic gate also failed.

## Complementarity and concentration

- Daily correlation to baseline: -0.413955
- Weekly correlation to baseline: -0.528809
- Contribution on baseline loss days: +¥4,980
- Contribution on baseline drawdown days: -¥1,872
- Event bootstrap probability of non-positive net: 0.4947
- Day bootstrap probability of non-positive net: 0.5101
- Top one winner removed net: -¥1,459
- Top five winners removed net: -¥4,910
- Top winner decile removed net: -¥6,934

The low correlation and drawdown reduction are diagnostically useful, but they do not constitute deployable alpha because the fixed candidate failed both exact historical portability and 2025H1 profitability.

## Evidence authority

- Research preregistration SHA: `4a6cb16768bbacc0c9bbeabfd5817bb26318c81a`
- Core candidate SHA: `5d6c55c0bf6273354de6e102da57e758cf7663e9`
- Core main merge SHA: `50f4b70bc3500c395ae332ed7fd16427bc968f53`
- Research/Core parity Run: `30503243876`
- MT4 five-variant Run: `30506742207`
- Final evaluation Run: `30512972565`
- Core Result Issue: `#694`
- Core PR: `#641`
- Immutable Release: `usdjpy-hyp040-asian-range-sweep-2025h1-validation-v2`
- Release archive SHA-256: `dde913ad860da5be5a6a4ae21e17e3e02f1d64333858ca8c3e432e8a18feb6e9`
- Release readback: `PASS_BYTE_IDENTICAL_RELEASE_READBACK`

## Non-interference

- HYP-030 formal decision remains `NO_PORTABLE_CANDIDATE` and was not changed.
- HYP-039 was not used, combined, modified or rejudged.
- 2025H2 was not accessed.
- Production and live authorization remain false.

## Exact next action

Close HYP-040 without retuning or reopening. Exclude it from the authorized Common Portfolio Integration strategy set. Preserve its negative-correlation and drawdown-reduction observations only as diagnostic evidence for future independently preregistered mechanisms.
