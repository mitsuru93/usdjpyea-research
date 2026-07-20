# USDJPY 2025-Data / MT4-Tester Authorization History v2

## Current binding rule

The user explicitly changed the prior no-2025-data rule on 2026-07-21 and authorized one specific check:

```text
Run B02 and F05 in MT4 Strategy Tester on 2025 H1.
Do not collect or download Tick data.
```

The authorized interval is:

```text
2025-01-01T00:00:00Z inclusive
through 2025-07-01T00:00:00Z exclusive
```

The authorization is limited to the frozen B02/F05 rules and existing cached Rakuten MT4 history. It does not authorize Dukascopy collection, a new canonical 2025 bundle, strategy retuning, parameter optimization, new candidate selection, or 2025 H2 testing.

## Completed authorized check

The authorized MT4 test was completed in Core:

```text
Repository:    mitsuru93/usdjpyea-core
Run ID:       29783855056
Head SHA:     973d0c31bec66a6cf9cca913835b4d7cc6013dca
Artifact ID:  8477893216
Digest:       sha256:0867bb4d8bfb0be9f96e61dd1e9c73aadd56b2b217b514532596e644dc95a72a
```

Data boundary:

- pre-existing `RakutenSecurities-Live` M1 and M15 HST cache only;
- no external market-data download;
- no Tick-data collection;
- source HST hashes unchanged after the test;
- MT4 Model 0 generated tester prices from the cached broker M1 history.

The fixed 0.01-lot-per-strategy result was JPY -20,808 from an initial virtual JPY 100,000, with combined PF 0.829 and maximum tick-equity drawdown JPY 42,737 / 42.71%.

## Rule history

Before the explicit 2026-07-21 change, the binding rule prohibited all inspection or evaluation of 2025 market data and required implementation validation to use reusable 2024 H2 only. That earlier prohibition is no longer authoritative for the completed one-off 2025 H1 MT4 check described above.

The following earlier principles remain binding:

- 2024 H2 remains reusable and is not treated as consumed.
- No new historical Tick-data collection is authorized by this exception.
- A 2025 result must not be used to repair or tune B02/F05 unless the user separately authorizes a new research phase.
- No live terminal or live order is authorized by the historical tester check.
