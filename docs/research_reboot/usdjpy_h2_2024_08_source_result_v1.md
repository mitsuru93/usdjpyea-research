# USDJPY H2 2024-08 Source and Baseline Result v1

## Source run

```text
workflow: Run Public FX Tick Pilot 2024-08 USDJPY
run_id: 29556953388
head_sha: 5bbe9cfdafe1b568ede328b9321af0a1bece0c5b
aggregate artifact: public-fx-data-pilot-2024-08-USDJPY-aggregate-29556953388
artifact digest: sha256:a1769e23ffa5a1c5bacd1e45bbf86c58ee159a4021eb2a1c3ebe7bb331c79230
```

All collection, resampling, validation, summary and artifact-upload jobs completed successfully.

## Source quality

```text
expected hourly records: 528
downloaded: 513
no_ticks soft-missing: 15
hard errors: 0
calendar coverage: 97.1591%
effective coverage: 100%
bar validation status: ok
validated bar files: 88
aggregate repair records: 0
```

The 15 `no_ticks` observations are soft-missing records. They do not reduce effective coverage under the fixed source-quality rule.

The August source block passes the H2 source gate of 100% effective coverage and zero hard errors.

## Monthly baseline run

```text
workflow: Run FX Session Baseline Monthly
run_id: 29567447264
head_sha: 137e103b1f6aaf6c3435593e548408d9e7f5282c
artifact: fx-session-baseline-2024-08-USDJPY-29567447264
artifact digest: sha256:e5dd5f183b4a414c2b25bb4f6e46f627c07660358533d9a097dec01a2968b7c6
```

All workflow steps completed successfully, including source download, aggregate repair, coverage gate, resampling, session-baseline generation and artifact upload.

## Monthly quality gate

```text
expected hourly records: 528
downloaded: 513
no_ticks soft-missing: 15
hard errors: 0
effective coverage: 100%
aggregate repair records: 0
base spread: 0.5 pips
cost spread mode: max_base_public
hard no-trade windows: enabled
M5 and M15 source files: present
```

The August monthly baseline is accepted for the final joint H2 evaluation.

This monthly run does not make an A1 or E3 promotion decision. Candidate evaluation remains deferred until all six H2 months, 2024-07 through 2024-12, have been collected and processed.

## Next step

Collect the September 2024 Dukascopy USDJPY bid/ask tick block with:

```text
workflow: Run Public FX Tick Pilot 2024-09 USDJPY
start_utc_hour: 2024-09-01T00
end_utc_hour: 2024-10-01T00
min_coverage: 1.0
max_hard_errors: 0
```
