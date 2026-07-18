# USDJPY H2 Batch Run 29569149852 Failure and Recovery v1

## Run

```text
workflow: Run USDJPY H2 2024-09 to 2024-12 Collect and Baseline
run_id: 29569149852
head_sha: ba7dc2a448bf626d6282e69397d91e00c05ec12c
```

## First-attempt failure

The first attempt failed before December collection and monthly baseline generation.

The November collection lacked the complete day artifact for:

```text
chunk: d16
date: 2024-11-22 UTC
missing hours: 24
```

The first November aggregate initial manifest contained 20 weekday chunks and 480 unique hourly records instead of the fixed November expectation of 21 weekdays and 504 hourly records.

The old aggregate summary used:

```text
expected_records_mode: observed
expected_records: 480
observed_records: 480
effective_coverage: 1.0
```

That was not a valid 100% November coverage statement because the missing day was removed from the denominator. The d16 matrix failure prevented December from starting.

Invalid first-attempt aggregate:

```text
artifact_id: 8412658745
artifact: public-fx-data-pilot-2024-11-USDJPY-aggregate-29569149852
digest: sha256:8629b80f7196fe0fade05c0e31e2b1242e7b704edcb4229bc1bf74b0900e547e
```

This artifact remains excluded.

## Recovery execution

GitHub Actions `re-run failed jobs` was requested for run `29569149852`.

The missing day completed on the rerun:

```text
artifact_id: 8421751697
artifact: public-fx-data-pilot-2024-11-USDJPY-d16-29569149852
digest: sha256:9f34820a3a01c9ee48928c5a205738224bde5a270364f40d7bad3f3b4cf2c1bc
```

The d16 manifest contains all 24 UTC hours:

```text
downloaded: 22
no_ticks: 2
hard errors: 0
effective coverage: 1.0
bar validation: ok
M1 rows: 1320
M5 rows: 264
M15 rows: 88
H1 rows: 22
```

The two no-tick hours are `2024-11-22T22:00:00Z` and `2024-11-22T23:00:00Z`.

## Recovered November aggregate

The rerun produced a new aggregate artifact:

```text
artifact_id: 8421758330
artifact: public-fx-data-pilot-2024-11-USDJPY-aggregate-29569149852
digest: sha256:5c4f3e17100a63ff0f370d4810fb8f4ebca22ceb5192120ebfb8d58a788b12f4
```

The current rerun still uses the old workflow file from head SHA `ba7dc2a...`, so its JSON label remains `expected_records_mode: observed`. Acceptance does not rely on that label. The terminal manifest was independently compared with the fixed Monday-Friday UTC expectation.

Independent fixed-denominator audit:

```text
November weekdays: 21
fixed expected hours: 504
unique terminal manifest hours: 504
missing expected hours: 0
extra hours: 0
downloaded: 493
no_ticks: 11
hard errors: 0
effective expected: 493
effective coverage: 1.0
validation files: 84 = 21 days × 4 timeframes
validation status: ok
```

The recovered aggregate includes all 24 records for 2024-11-22. The final statuses for that date are 22 downloaded and two no-tick records.

The 11 no-tick records follow Friday market-close hours and are explicitly represented in the manifest; they are not unobserved gaps.

## Recovered November baseline

```text
artifact_id: 8423419800
artifact: fx-session-baseline-2024-11-USDJPY-29569149852
digest: sha256:d83599f9080ed603fd5fc36cd0742a6281c26af4672bdf8e5216fcaf39779507
```

The baseline artifact contains:

```text
21 weekday day-bar sets
42 day input files: M5 and M15
8 repaired source hours represented by two consolidated repair bar files
44 total input files
source unique hours: 504
source hard errors after repair: 0
session experiment summary: present
trade output: present
hard no-trade filtering: enabled
base spread: 0.5 pips
cost mode: max_base_public
```

The eight aggregate-repair hours replace terminal day-manifest errors. They are not additional trading dates.

## Decision

The November source and monthly baseline from the rerun are accepted.

```text
accepted source aggregate artifact_id: 8421758330
accepted baseline artifact_id: 8423419800
excluded source aggregate artifact_id: 8412658745
```

The first-attempt November artifact must never be selected by name alone because the rerun created a second artifact with the same display name. Artifact ID and digest are authoritative.

The active A1+hold6 / E3+hold6 pre-registration is unchanged. No candidate result was opened during recovery.

## Permanent correction for future runs

Two changes were added on `main` after this run's frozen head SHA:

1. `tools/summarize_download_manifest.py`
   - adds `expected_records_mode: weekdays`;
   - computes a fixed Monday-Friday UTC-hour denominator;
   - reports `unobserved_records` explicitly.

2. `.github/workflows/reusable_public_fx_tick_symbol_pilot_monthly_v2.yml`
   - increases the daily job timeout from 60 to 90 minutes;
   - treats day-job failure as recoverable input to the aggregate stage;
   - synthesizes error records for absent weekday hours;
   - sends those gaps through aggregate repair;
   - accepts a month only after fixed weekday coverage reaches 100% with zero terminal hard errors.

Relevant commits:

```text
754b566470657b7a4a01f6675080d33b64e877c1
f122618c88db900b22bb5b69b8c5fbab2ffc5ea2
```
