# EURUSD 2024 full-year source run 29635629597 — accepted

Created: 2026-07-19 JST

## Decision

Run `29635629597`, attempt `1`, is accepted as the canonical EURUSD 2024 annual source bundle.

The project acceptance criterion is the verified data content. The downloaded annual artifact passed annual coverage, all twelve monthly coverage checks, four-timeframe bar validation, timestamp-order checks, duplicate checks, and file-hash checks. No additional full-year collection is required.

This decision supersedes the deleted rejection record and operationally satisfies the source-data gate in `configs/research/eurusd_h1_prior_literature_candidates_v1.json`. The original pre-registration file remains unchanged as a historical pre-result specification; current source acceptance is recorded in `configs/research/eurusd_2024_source_archive_v1.json`.

## Canonical artifact identity

- workflow run ID: `29635629597`
- run attempt: `1`
- head branch: `main`
- head SHA: `7ea43919a2477a77ec4276a0fbe258061b5da29b`
- artifact ID: `8441596981`
- artifact name: `public-fx-data-EURUSD-2024-annual-29635629597-a1`
- artifact digest: `sha256:7d6e282172ec4290465b61dece886df0407f983726c4f51fb9eddd028318a685`
- artifact size: `19,261,430` bytes
- created at: `2026-07-19T11:01:45Z`
- downloaded ZIP digest matched the GitHub artifact digest

## Accepted coverage

### Annual

- `expected_records_mode=weekdays`
- expected records: `6288`
- observed records: `6288`
- downloaded records: `6112`
- no-tick records: `176`
- `unobserved_records=0`
- `hard_error_records=0`
- `effective_coverage=1.0`

### Monthly

All twelve monthly summaries were present. Every month had:

- `observed_records=expected_records`
- `unobserved_records=0`
- `hard_error_records=0`
- `effective_coverage=1.0`

## Accepted bars

- M1: `364717` rows, validation `ok`
- M5: `73318` rows, validation `ok`
- M15: `24446` rows, validation `ok`
- H1: `6112` rows, validation `ok`

Independent inspection also confirmed:

- no duplicate timestamps;
- monotonically increasing UTC timestamps;
- manifest gzip SHA-256 matching the actual files;
- source metadata identifies Dukascopy public bid/ask BI5;
- `research_status=source_data_only`;
- strategy assumptions and broker-spread assumptions are null in the source artifact.

## Operational effect

- This artifact is the EURUSD 2024 source-data canonical bundle.
- The EURUSD H1 source-data gate is passed.
- EURUSD H1 strategy implementation and screening may proceed against this artifact.
- Do not rerun the full-year collection merely to obtain a newer builder lineage.
- Do not replace this source without an explicit project decision.
- Do not mix this artifact, its candidates, or its results with USDJPY research.
