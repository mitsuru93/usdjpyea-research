# EURUSD 2024 data representation boundary v1

Created: 2026-07-19 JST

## Correction

The accepted artifact `public-fx-data-EURUSD-2024-annual-29635629597-a1` is the canonical **bar bundle** for EURUSD H1 research. It is derived from Dukascopy ticks, but it does not preserve the complete 2024 tick stream. The annual package contains M1, M5, M15 and H1 bars plus a limited set of repair-hour normalized ticks; it must not be described or used as the complete MT4 tick source.

## Separate authorities

### H1 research bar authority

- config: `configs/research/eurusd_2024_source_archive_v1.json`
- release tag: `eurusd-2024-source-artifact-archive-v1`
- accepted asset: `eurusd-2024-source-artifact-id-8441596981.zip`
- use: H1 strategy research and bar-level diagnostics

### Tick conversion authority

- config: `configs/research/eurusd_2024_tick_archive_v1.json`
- release tag: `eurusd-2024-tick-data-archive-v1`
- planned contents: all retrievable 2024 hourly vendor BI5 payloads and deterministic normalized UTC Bid/Ask tick CSV.GZ files
- use: controlled conversion into MT4 FXT/HST or another explicitly selected tick-import format

## Broker boundary

The tick archive is Dukascopy public-market proxy data. It is not Rakuten MT4 broker-native tick history. Rakuten spread and execution assumptions remain separate research inputs.
