# USDJPY 2024 Raw Tick Archive v1

## Status

The validated 2024 USDJPY Dukascopy Bid/Ask tick dataset has been moved out of GitHub Actions retention into an immutable GitHub Release.

- Release tag: `usdjpy-2024-raw-bidask-ticks-v1`
- Release title: `USDJPY 2024 Raw Dukascopy Bid/Ask Ticks v1`
- Package workflow run: `29717760185` attempt `1`
- Package workflow head SHA: `634ab0612288d54a4b48a074e89fed3d6313d486`
- Source collection run: `29689427642` attempt `1`
- Repair data run: `29707697472` attempt `1`
- Actions annual artifact ID: `8451237093`
- Actions annual artifact SHA-256: `64e12eb8cb74dd7212f112b94ba216c790b85d196a157c25b0ce54bfff3c095c`
- Actions expiry: `2026-10-18T04:49:28Z`
- Durable Release: independent of Actions artifact expiry

## Preserved data

The Release contains 64 assets:

- 12 monthly deterministic raw-tick archives (`tar.gz`)
- 12 monthly validation manifests
- 12 source-artifact receipts
- 12 repair-artifact receipts
- 12 monthly checksum files
- annual manifest
- repair lock
- release notes
- annual `SHA256SUMS`

Each monthly raw-tick archive preserves both:

1. original hourly Dukascopy BI5 payloads;
2. deterministic decoded Bid/Ask CSV.GZ files.

## Annual validation

| Field | Result |
|---|---:|
| Accepted | true |
| Present days | 366 / 366 |
| Resolved hours | 8,784 / 8,784 |
| Downloaded hours | 6,250 |
| No-tick hours | 2,534 |
| Missing 404 hours | 0 |
| Error hours | 0 |
| Tick rows | 40,969,081 |
| Negative-spread rows | 0 |
| Source BI5 bytes | 178,738,706 |
| Decoded CSV bytes | 359,586,218 |

## Boundary

This is the canonical public Dukascopy proxy dataset. It is not evidence of quote equivalence with Rakuten Securities. It is not yet a directly consumable standard MT4 real-tick input; FXT/HST generation or a compatible tick-import conversion remains a separate stage.

Machine-readable provenance, monthly artifact IDs, sizes, and digests are recorded in [`receipt.json`](./receipt.json).
