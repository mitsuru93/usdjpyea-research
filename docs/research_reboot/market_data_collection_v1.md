# Market Data Collection v1

Collected on: 2026-07-10 JST  
Execution target: Rakuten MT4  
Research stance: zero-base market and strategy selection; legacy USDJPY assets are reference material only.

## Commitments for this reboot

- Do not choose a pair because legacy USDJPY assets exist.
- Do not treat advertised spread as execution truth.
- Do not optimize strategy rules before market profile and cost profile are built.
- Reject strategies that only survive under raw/mid-price assumptions.
- Treat Rakuten MT4 as the final execution environment, but do public-data research outside MT4 first.

## Sources collected

### Public historical market data sources

1. Dukascopy Historical Data Export
   - URL: https://www.dukascopy.com/swiss/english/marketwatch/historical/
   - Role: primary public tick/bid-ask proxy source.
   - Use: build M1/M5/M15 datasets for EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, USDCHF.
   - Limitation: Dukascopy quotes are not Rakuten MT4 quotes.

2. HistData.com Free Forex Historical Data
   - URL: https://www.histdata.com/download-free-forex-data/
   - Role: secondary crosscheck source.
   - Observed formats: MT4/MT5 M1, Generic ASCII M1/Tick, NinjaTrader 1-second last/bid/ask.
   - Observed site update timestamp: 2026-06-28 22:55:26.
   - Limitation: web download flow and licensing/automation constraints must be checked before CI ingestion.

### Rakuten MT4 broker-condition sources

1. Rakuten MT4 top
   - URL: https://www.rakuten-sec.co.jp/web/fx/mt4/
   - Captured items: MT4/EA support positioning, domestic server environment claim, MT4 time conversion.

2. Rakuten MT4 trading rules
   - URL: https://www.rakuten-sec.co.jp/web/fx/mt4/rule.html
   - Captured items: 24 FX pairs, 1,000-unit trade unit, lot mapping, fee-free trading, order types, point size, order caveats.

3. Rakuten MT4 trading hours
   - URL: https://www.rakuten-sec.co.jp/web/fx/mt4/session.html
   - Captured items: principally 24h trading, daily maintenance, summer-time shift.

4. Rakuten MT4 swap/spread page
   - URL: https://www.rakuten-sec.co.jp/web/fx/mt4/commission.html
   - Captured items: advertised spread table as of publication date 2026-07-06, spread caveats.

5. Rakuten spread performance PDF
   - URL: https://www.rakuten-sec.co.jp/web/company/disclosure/pdf/fx_spread.pdf
   - Captured items: spread presentation ratio, max spread, quote/contract suspension time for recent period.

## Files added

- `configs/data_sources/fx_source_registry_v1.yaml`
- `configs/brokers/rakuten_mt4_snapshot_2026-07-10.yaml`

## Immediate data interpretation

The current collected sources justify starting public historical research immediately, but they do not justify final acceptance of any short-TP or high-frequency strategy.

Reason:

- Rakuten explicitly states that spreads vary with market conditions and advertised values are not guaranteed execution spreads.
- Recent Rakuten MT4 spread-performance data show advertised spread presentation ratios around 96% for major non-JPY USD pairs, but max spreads can be much larger than the advertised values.
- Public bid/ask data from Dukascopy or HistData can be used for market-structure screening, not for final Rakuten execution truth.

## Initial universe

Keep the initial research universe narrow:

- EURUSD
- USDJPY
- GBPUSD
- AUDUSD
- USDCAD
- USDCHF

Do not add crosses, exotics, XAUUSD, CFDs, crypto, or high-volatility products until the base pipeline is validated.

## Dataset build target

Preferred normalized M1 schema:

```text
timestamp_utc
symbol
bid_open
bid_high
bid_low
bid_close
ask_open
ask_high
ask_low
ask_close
mid_open
mid_high
mid_low
mid_close
spread_open_pips
spread_high_pips
spread_low_pips
spread_close_pips
spread_mean_pips
source
source_build_id
```

Derived bars:

- M5
- M15
- H1

## Cost model

Use layers:

1. Raw/mid price only — structure discovery only.
2. Public bid/ask spread — public proxy cost.
3. Rakuten advertised spread — minimum broker cost floor, not execution truth.
4. Spread stress — x1.5, x2.0, x3.0.
5. Slippage stress — 0.1, 0.3, 0.5, 1.0 pips per side.
6. Bad-liquidity no-trade windows — rollover, maintenance, major news, holidays, shocks.

## Acceptance posture

A strategy candidate cannot be promoted if it:

- loses profitability under spread x1.5 or x2.0 stress,
- relies on very small TP relative to spread,
- concentrates PnL in a single month/session,
- depends on rollover/early-morning spread anomalies,
- cannot be implemented deterministically in MT4,
- requires WebRequest or external services in Strategy Tester,
- has no Rakuten MT4 forward-log validation path.

## Next implementation step

Create a downloader/resampler outside MT4. The downloader should:

1. Pull public data for the six-symbol universe.
2. Normalize to UTC.
3. Generate bid/ask/mid OHLC.
4. Compute spread distributions.
5. Write dataset checksums.
6. Register finished datasets in `configs/datasets/dataset_registry.yaml` only after checksums are known.

Raw bulk data should not be committed directly to git. Use release assets or workflow artifacts, consistent with the existing dataset registry pattern.
