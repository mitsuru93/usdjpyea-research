# USDJPY H2 2024-08 Source Result v1

## Run

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

This run did not evaluate A1 or E3 and does not alter the joint H2 pre-registration.

## Next processing step

Run `Run FX Session Baseline Monthly` with:

```text
source_run_id: 29556953388
symbol: USDJPY
pilot_tag: pilot-2024-08-USDJPY
month_tag: 2024-08
base_spread_pips: auto
start_utc_hour: 2024-08-01T00
end_utc_hour: 2024-09-01T00
```

The monthly baseline must retain 100% effective coverage and zero final hard errors. Preserve its run ID and artifact for the final July-through-December joint H2 evaluation.
