# USDJPY 2023 fast M1 acquisition contract v1

## Decision

The initial 2023 research stage will use **one-minute bid OHLC bars, not tick data**.

The dataset covers the half-open UTC interval from `2023-01-01T00:00:00Z` through immediately before `2024-01-01T00:00:00Z`. M15 bars will be constructed deterministically from M1.

## Why M1 is the appropriate level

The current architecture questions are evaluated at completed M15 bars. They do not require the order of prices inside a minute. M1 therefore preserves the information needed to:

- reproduce M15 OHLC exactly from a documented source;
- detect missing minute intervals;
- distinguish complete from incomplete M15 bars;
- bridge later to MT4 Model 0 more closely than an M15-only download;
- avoid the much larger transfer and processing cost of full ticks.

M15-only data would be usable for the event logic itself, but it would remove the independent M15-construction and minute-gap audit. Therefore M1 is the selected compromise.

## Frozen source

- Market data origin: Dukascopy public historical data API
- Acquisition client: `dukascopy-node@1.49.0`
- Instrument: `usdjpy`
- Timeframe: `m1`
- Price side: bid
- Timezone: UTC
- No ask series and no tick series

`dukascopy-node` is a third-party open-source client and is not affiliated with Dukascopy Bank SA. The exact npm version and distribution integrity must be captured in the run evidence.

## Normalization

Every retained M1 row will have:

`timestamp_utc, open, high, low, close, volume`

Rows must be strictly increasing and unique. Invalid OHLC relationships, non-finite values or duplicate timestamps fail the acquisition. No missing minute is forward-filled.

M15 aggregation uses UTC quarter-hour buckets:

- open = first M1 open;
- high = maximum M1 high;
- low = minimum M1 low;
- close = last M1 close;
- volume = sum of M1 volume;
- source M1 count is retained for every M15 bar.

A bar with fewer than 15 source minutes is retained and flagged rather than manufactured.

## Acquisition-only boundary

This stage may download, normalize, hash and audit the 2023 bars. It may not generate B02/F05 signals, evaluate a candidate, select thresholds, access 2024 H2 for Family F, access any 2025 period or place orders.

After the data artifact passes, the next step is a 2023 architecture atlas. A new finite candidate family must be preregistered separately.

## When tick data would become necessary

Tick data will be added only if a later candidate depends materially on intrabar stop/target ordering, intrabar trailing, variable spread, slippage/execution sequencing, or tick-level equity and margin behavior. None of those is part of the current diagnostic stage.
