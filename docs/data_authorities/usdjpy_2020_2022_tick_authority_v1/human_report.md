# USDJPY 2020–2022 Source-Native Bid/Ask Tick Authority

- Work ID: `USDJPY-DATA-2020-2022-TICK-AUTHORITY-001`
- Decision: `PASS_2020_2022_TICK_AUTHORITY_CERTIFIED`
- Primary source: Dukascopy source-native USDJPY BI5
- Analysis period: 2020-01-01 through 2022-12-31
- Warm-up only: 2019-10-01 through 2019-12-31
- Analysis Tick count: 78,737,040
- 2020: 24,321,113
- 2021: 14,822,017
- 2022: 39,593,910
- Critical gaps requiring review: 0
- Invalid Bid/Ask or non-positive price rows: 0
- Release: `usdjpy-2020-2022-source-native-bidask-tick-authority-v1`
- Workflow run: `30513521957` attempt `1`
- Rakuten broker-native raw Tick: `RAKUTEN_RAW_TICK_NOT_AVAILABLE`

## Firewall

This data authority is analysis-only. No B02, F05, C3, HYP-039, HYP-040, HYP-041, HYP-042, or Common Portfolio candidate P/L was computed. Existing formal decisions and 2025H1 validation results are unchanged.

## Layers

The Release preserves monthly original BI5 payloads, monthly normalized Tick CSV.GZ, Bid/Ask bars for M1/M5/M15/H1/H4/D1, monthly QC packages, root manifests, SHA-256 values, and remote readback receipts. Derived bars do not replace raw Tick authority.

## Permitted next use

Preregistered regime analysis, failure decomposition, source-portability diagnostics, and long-horizon mechanism stability analysis are permitted. Candidate selection, threshold tuning, side/session/holding changes, or substitution for 2025H1 validation are prohibited.
