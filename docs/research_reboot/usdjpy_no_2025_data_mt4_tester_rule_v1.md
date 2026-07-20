# USDJPY No-2025-Data / MT4-Tester Rule v1

## Binding rule

USDJPY research and implementation validation must not collect, download, aggregate, inspect, or evaluate any 2025 market data.

The fixed 2024 H2 block remains reusable validation data. It is not treated as consumed or unavailable after prior runs.

## Authorized next work

After Research/Core/MT4 signal parity, further implementation validation must use only:

- the already installed USDJPY 2024 MT4 history;
- MT4 Strategy Tester on the dedicated Rakuten self-hosted runner;
- the frozen B02 and F05 strategy definitions;
- existing 2024 H2 diagnostic and parity artifacts.

No additional historical market-data download is authorized for this work.

## Prohibited work

The following are prohibited unless the user explicitly changes this rule:

- collection or download of 2025 ticks, bars, or broker history;
- creation of a 2025 canonical bundle;
- calculation of 2025 signals, trades, metrics, rankings, or gates;
- treating 2024 H2 as consumed;
- replacing the reusable 2024 H2 validation process with a 2025 holdout.

## Date-boundary clarification

An MT4 Tester end boundary of `2025.01.01` may be used solely as the exclusive boundary needed to include all bars dated through 2024-12-31. The tested history must contain no 2025 market-data row, and the workflow must verify this condition.

## Current authorized finite gate

Run the production-candidate execution path in MT4 Strategy Tester over the existing 2024 H2 history and verify:

- production signal parity remains unchanged;
- tester orders are opened and closed through the production runtime;
- duplicate suppression remains effective;
- fixed-time exits match the frozen contract;
- no live terminal or live order is started;
- no 2025 market-data row is read.
