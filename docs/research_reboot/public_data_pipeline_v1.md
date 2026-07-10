# Public FX Data Pipeline v1

Created on: 2026-07-10 JST  
Execution target: Rakuten MT4, but public-data research is performed outside MT4.

## Position

This pipeline exists to move from source metadata to actual public bid/ask research datasets without committing large raw files to git.

It deliberately separates:

1. public market proxy data,
2. Rakuten MT4 advertised/base cost model,
3. Rakuten MT4 live execution truth.

Dukascopy BI5 data is used as a public bid/ask proxy. It is not Rakuten MT4 data.

## Files added for this stage

- `tools/download_dukascopy_bi5_ticks.py`
- `tools/resample_fx_ticks.py`
- `configs/data_sources/dukascopy_bi5_plan_v1.yaml`

Previously added and used by this stage:

- `tools/download_public_fx_data.py`
- `tools/normalize_fx_bars.py`
- `tools/build_market_profile.py`
- `configs/data_sources/fx_source_registry_v1.yaml`
- `configs/brokers/rakuten_mt4_snapshot_2026-07-10.yaml`
- `docs/research_reboot/prior_art_review_v1.md`

## Data source

Primary public-data source:

- Dukascopy Historical Data Export page: https://www.dukascopy.com/swiss/english/marketwatch/historical/
- BI5 hourly tick feed pattern: `https://datafeed.dukascopy.com/datafeed/{symbol}/{year}/{month_zero_based}/{day}/{hour}h_ticks.bi5`

The source registry and plan both record that this is a proxy source, not Rakuten execution truth.

## Initial universe

Keep the universe narrow until the data and profile pipeline is proven:

- EURUSD
- USDJPY
- GBPUSD
- AUDUSD
- USDCAD
- USDCHF

Timeframes:

- M1
- M5
- M15
- H1

## Smoke test command

Run a one-day two-symbol smoke test first:

```bash
python tools/download_dukascopy_bi5_ticks.py \
  --symbols EURUSD USDJPY \
  --start 2024-01-02T00 \
  --end 2024-01-03T00 \
  --output-root data/raw/dukascopy_bi5_smoke \
  --manifest-out data/raw/dukascopy_bi5_smoke/download_manifest.jsonl
```

Then resample the downloaded hourly tick files:

```bash
python tools/resample_fx_ticks.py \
  --input data/raw/dukascopy_bi5_smoke/EURUSD/2024/01/02/00.csv.gz \
  --input data/raw/dukascopy_bi5_smoke/EURUSD/2024/01/02/01.csv.gz \
  --input data/raw/dukascopy_bi5_smoke/USDJPY/2024/01/02/00.csv.gz \
  --input data/raw/dukascopy_bi5_smoke/USDJPY/2024/01/02/01.csv.gz \
  --output-dir data/processed/dukascopy_bi5_smoke_bars \
  --timeframes M1 M5 M15 H1
```

For full days, pass all hourly files. A shell glob or manifest-driven wrapper can be added after the smoke test succeeds.

## Pilot month command

After smoke test passes, run a one-month six-symbol pilot:

```bash
python tools/download_dukascopy_bi5_ticks.py \
  --symbols EURUSD USDJPY GBPUSD AUDUSD USDCAD USDCHF \
  --start 2024-01-01T00 \
  --end 2024-02-01T00 \
  --output-root data/raw/dukascopy_bi5_pilot_2024_01 \
  --manifest-out data/raw/dukascopy_bi5_pilot_2024_01/download_manifest.jsonl
```

The pilot output must be stored outside git and promoted as artifact/release asset only after checksums are captured.

## Market profile

After resampling, generate market profile tables:

```bash
python tools/build_market_profile.py \
  --input data/processed/dukascopy_bi5_smoke_bars/M1/EURUSD_M1.csv.gz \
  --input data/processed/dukascopy_bi5_smoke_bars/M1/USDJPY_M1.csv.gz \
  --output-dir data/profiles/dukascopy_bi5_smoke_market_profile
```

Outputs:

- `market_profile_overall.csv`
- `market_profile_hourly.csv`
- `market_profile_weekday.csv`

## Cost model

Use the base Rakuten MT4 spread table only as a floor:

| Symbol | Base spread pips |
|---|---:|
| EURUSD | 0.6 |
| USDJPY | 0.5 |
| GBPUSD | 1.2 |
| AUDUSD | 1.2 |
| USDCAD | 2.0 |
| USDCHF | 1.6 |

Required stress:

- spread x1.0
- spread x1.5
- spread x2.0
- spread x3.0
- slippage per side: 0.0 / 0.1 / 0.3 / 0.5 / 1.0 pips

Do not promote a strategy that only works under base spread.

## Strategy research gate

Do not start strategy optimization until the following exists:

1. smoke download/resample result,
2. one-month market profile,
3. hourly spread/range ranking by symbol,
4. initial exclusion of bad-liquidity windows,
5. dataset checksums.

## Rejection rules

Reject early if a candidate design depends on:

- M1 micro-scalping with TP close to base spread,
- spread values staying at advertised levels,
- rollover/maintenance windows,
- a single symbol or month without cross-period support,
- external AI/WebRequest calls inside MT4 Strategy Tester.

## Next implementation task

Add a manifest-driven wrapper that reads `download_manifest.jsonl`, selects successfully downloaded tick files, and invokes `resample_fx_ticks.py` without manually enumerating every hourly path.
