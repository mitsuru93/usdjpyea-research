# USDJPY M15 Breakout 24h Alignment H2 Pre-registration v1

## Status

This document is the pre-registration record for the next untouched-period test.

It was created before reviewing candidate results for 2024-07 through 2024-12.

## Development and test periods

```text
development / diagnostic period: 2024-01-01 through 2024-06-30
test period:                     2024-07-01 through 2024-12-31
```

The H2 period must not be used to modify the candidate definition or the gates below.

## Dataset and role

Primary screening dataset:

```text
usdjpy_m1_2024_01_02_to_2026_02_18_public_main
```

Registry:

```text
configs/datasets/dataset_registry.yaml
```

The dataset is a pre-MT4 research dataset. The DT column is interpreted as MT4 server time using the EET/EEST clock (`Europe/Helsinki`) and converted to UTC before resampling.

Because this M1 dataset does not contain a usable historical spread series, the H2 screening cost basis is fixed to the Rakuten USDJPY base round-trip spread of 0.5 pips.

Passing this screen would lead only to a later Dukascopy tick-data validation. It would not lead directly to EA implementation.

## Fixed candidate

```text
name: m15_breakout_24h_aligned
symbol: USDJPY
timeframe: M15
entry session: UTC 13, 14, 15 or 16
breakout lookback: 3 completed M15 bars
hold: 6 M15 bars
entry: next M15 bar open after the signal
exit: close of the sixth held M15 bar
```

### Breakout rule

At completed signal bar `t`:

```text
long breakout:
  close[t] > max(high[t-1], high[t-2], high[t-3])

short breakout:
  close[t] < min(low[t-1], low[t-2], low[t-3])
```

### Prior-24-hour alignment rule

The prior 24-hour direction uses the 96 completed M15 bars ending at signal bar `t`:

```text
prior_24h_return = close[t] - open[t-95]
```

Eligibility:

```text
long breakout is eligible only when prior_24h_return > 0
short breakout is eligible only when prior_24h_return < 0
prior_24h_return == 0 produces no trade
```

No alternative lookback, threshold or alignment formula may be selected from H2 results.

## Hard no-trade rule

The project-wide DST-aware hard no-trade configuration remains authoritative:

```text
configs/market_sessions/fx_market_sessions_v1.json
```

No trade may be retained when its entry falls within an applicable hard no-trade window.

## Cost scenarios

Default:

```text
spread multiplier: 1.0
base spread: 0.5 pips
slippage: 0.0 pips per side
total cost: 0.5 pips
```

Severe:

```text
spread multiplier: 3.0
base spread: 0.5 pips
slippage: 0.5 pips per side
total cost: 2.5 pips
```

## Official intervention sensitivity

The Ministry of Finance official USD-selling / JPY-buying operation dates in H2 2024 are:

```text
2024-07-11
2024-07-12
```

These dates are retrospective diagnostic labels and are not live entry filters.

The result must be reported both including all dates and excluding both official dates.

## Pre-registered promotion gate

The candidate passes the public-M1 H2 screen only if all conditions below hold.

1. At least four of the six H2 calendar months have positive default-cost average net pips.
2. H2 aggregate default-cost average net pips is positive.
3. H2 aggregate default-cost profit factor is at least 1.10.
4. After excluding 2024-07-11 and 2024-07-12, aggregate default-cost average net pips remains positive and profit factor is at least 1.05.
5. After excluding the best two UTC trading days, aggregate default-cost total net pips remains positive.
6. H2 contains at least 180 retained trades in aggregate and at least 15 retained trades in each calendar month.
7. Severe-stress aggregate average net pips is no worse than -0.5 pips per trade and severe-stress profit factor is at least 0.90.
8. No retained entry violates the DST-aware hard no-trade configuration.

Failure of any condition means the candidate does not advance.

## Prohibited responses to failure

The following are not allowed after seeing H2 results:

- changing the 24-hour lookback;
- selecting a nonzero return threshold;
- changing breakout lookback from 3;
- changing hold from 6;
- deleting a losing month;
- excluding non-official event dates;
- converting the rule to long-only or short-only;
- optimizing an exit;
- treating H2 as a new development sample and immediately retesting another variant on it.

## Advancement path

If all H2 gates pass:

```text
public M1 screen
→ Dukascopy bid/ask tick validation for the same H2 period
→ separate pre-registered robustness gate
→ only then consider exit-policy research
```

If the H2 screen fails, the current M15 breakout line of research is closed in its present form.
