# USDJPY H2 Batch Run 29569149852 Failure and Recovery v1

## Run

```text
workflow: Run USDJPY H2 2024-09 to 2024-12 Collect and Baseline
run_id: 29569149852
head_sha: ba7dc2a448bf626d6282e69397d91e00c05ec12c
```

The first attempt failed before December collection and monthly baseline generation.

## Root cause

The November collection lacked the complete day artifact for:

```text
chunk: d16
date: 2024-11-22 UTC
missing hours: 24
```

The November aggregate initial manifest contained 20 weekday chunks and 480 unique hourly records instead of the fixed November expectation of 21 weekdays and 504 hourly records.

The aggregate repair recovered terminal error records that existed in available manifests, but it could not retry a day whose manifest artifact was entirely absent.

A second defect masked this omission inside the aggregate summary:

```text
expected_records_mode: observed
expected_records: 480
observed_records: 480
effective_coverage: 1.0
```

This result was not a valid 100% November coverage statement because the missing day had been removed from the denominator. The called workflow still failed because the d16 matrix job failed, which prevented the December dependency from starting.

## Evidence from the November aggregate artifact

```text
artifact: public-fx-data-pilot-2024-11-USDJPY-aggregate-29569149852
artifact_id: 8412658745
artifact_digest: sha256:8629b80f7196fe0fade05c0e31e2b1242e7b704edcb4229bc1bf74b0900e547e

reported expected_records: 480
reported successful_records: 471
reported no_ticks: 9
reported hard_error_records: 0
reported effective_coverage: 1.0
actual fixed weekday expectation: 504
unobserved hours: 24
```

No November source block or later baseline is accepted from this first attempt until the missing weekday is collected or repaired and a fixed weekday coverage gate passes.

## Immediate recovery

GitHub Actions `re-run failed jobs` was requested for run `29569149852`. GitHub restarted the failed workflow attempt and its dependent job graph.

The active A1+hold6 / E3+hold6 pre-registration is unchanged. No candidate result was opened.

## Permanent correction

Two changes were added on `main`:

1. `tools/summarize_download_manifest.py`
   - adds `expected_records_mode: weekdays`;
   - computes a fixed Monday-Friday UTC-hour denominator;
   - reports `unobserved_records` explicitly.

2. `.github/workflows/reusable_public_fx_tick_symbol_pilot_monthly_v2.yml`
   - increases the daily job timeout from 60 to 90 minutes;
   - treats day-job failure as recoverable input to the aggregate stage;
   - synthesizes `error` records for every absent weekday hour;
   - passes those synthetic gaps to aggregate repair;
   - accepts the month only after the fixed weekday coverage gate reaches 100% with zero terminal hard errors.

Relevant commits:

```text
754b566470657b7a4a01f6675080d33b64e877c1
f122618c88db900b22bb5b69b8c5fbab2ffc5ea2
```

## Acceptance requirement

November is accepted only when all of the following hold:

```text
expected_records_mode: weekdays
expected_records: 504
observed_records: 504
unobserved_records: 0
hard_error_records: 0
effective_coverage: 1.0
validation status: ok
```

December and all four monthly baselines must then complete before the H2 A1/E3 batch is evaluated.
