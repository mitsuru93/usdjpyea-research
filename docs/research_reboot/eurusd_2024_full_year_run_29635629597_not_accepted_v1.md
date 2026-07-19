# EURUSD 2024 full-year source run 29635629597 — not accepted

Created: 2026-07-19 JST

## Decision

Run `29635629597`, attempt `1`, is **not accepted as the canonical EURUSD 2024 annual source bundle**.

The downloaded annual artifact passes the content-level coverage and bar-validation checks listed below. The rejection is version-lineage based: the run executed at head SHA `7ea43919a2477a77ec4276a0fbe258061b5da29b`, which predates commit `ecbebb5ce21ae4569faf4b43a6d31ac04232fea1` (`fix: make annual FX bundle byte deterministic`).

A fresh workflow dispatch from current `main` is required. Re-running failed jobs on this run is not sufficient because it preserves the old head SHA.

## Artifact identity

- workflow run ID: `29635629597`
- run attempt: `1`
- head branch: `main`
- head SHA: `7ea43919a2477a77ec4276a0fbe258061b5da29b`
- artifact ID: `8441596981`
- artifact name: `public-fx-data-EURUSD-2024-annual-29635629597-a1`
- artifact digest: `sha256:7d6e282172ec4290465b61dece886df0407f983726c4f51fb9eddd028318a685`
- artifact size: `19,261,430` bytes
- created at: `2026-07-19T11:01:45Z`
- expired: `false` at inspection time

The downloaded ZIP SHA-256 matched the GitHub artifact digest exactly.

## Checks that passed

### Annual source summary

- expected-record mode: `weekdays`
- expected records: `6288`
- observed records: `6288`
- downloaded records: `6112`
- no-tick records: `176`
- unobserved records: `0`
- hard-error records: `0`
- effective coverage: `1.0`

### Monthly source summaries

All twelve monthly summaries were present. Every month had:

- `expected_records_mode=weekdays`
- `observed_records=expected_records`
- `unobserved_records=0`
- `hard_error_records=0`
- `effective_coverage=1.0`

### Annual bars

- M1: `364717` rows
- M5: `73318` rows
- M15: `24446` rows
- H1: `6112` rows

All four files had:

- validation status `ok`
- no duplicate timestamps in independent inspection
- monotonically increasing UTC timestamps
- manifest gzip SHA-256 matching the actual file bytes

### Metadata boundary

`run_metadata.json` correctly recorded:

- source: Dukascopy public bid/ask BI5
- research status: `source_data_only`
- strategy assumptions: `null`
- broker spread assumption: `null`
- symbol: `EURUSD`
- timeframes: M1, M5, M15, H1

## Rejection reason

The annual builder used by this run predates the current deterministic-bundle implementation. The later implementation adds, among other controls:

- canonical column enforcement;
- stricter numeric, timestamp-grid, OHLC, bid/ask, spread, and tick-count validation during annual assembly;
- deterministic gzip output with zero mtime and empty embedded filename;
- separate canonical-content and gzip hashes;
- explicit duplicate-resolution audit;
- hard failure on conflicting same-priority duplicate bars.

The old artifact is therefore useful as a diagnostic result, but it does not satisfy the current canonical lineage requirement.

## Required next action

Dispatch `Run EURUSD 2024 Full-Year Public Data Collection` again from current `main`. Accept only the new annual artifact after checking its exact artifact ID, digest, creation time, run attempt, head SHA, coverage summaries, duplicate-resolution audit, deterministic hashes, and four validated bar files.

No EURUSD H1 strategy run may use this artifact as its accepted source bundle.
