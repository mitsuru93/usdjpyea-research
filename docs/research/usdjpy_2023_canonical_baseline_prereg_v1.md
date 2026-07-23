# USDJPY 2023 Canonical Baseline Preregistration v1

## Purpose

Reconstruct the unchanged B02/F05 baseline on the accepted 2023 Rakuten MT4 Bid-bar history and require exact Research/Rakuten-MT4 parity before any architecture-atlas analysis.

This is baseline reconstruction, not candidate evaluation. No 2024 H2 or 2025 data is accessed.

## Frozen preparation evidence

- Core preparation Run: `29997167048`
- Job: `89173483747`
- Runner: `onamae-mt4-01`
- Head SHA: `75ae68113b10f23e3bfb74e653601166b9e640ae`
- Receipt: `mitsuru93/usdjpyea-core#184`
- Artifact ID: `8559483151`
- Artifact SHA-256: `22d66bf76c60362b78e9badff2113bc196b80e3657f5083ae470d1d62df70c01`
- Drive file ID: `1rFrQN3Awa-AoCdFVBdQ8gSp0MwxDk-H-`

The preparation Run independently reproduced the accepted normalized M1/M15 hashes from the accepted source artifact before generating MT4 history.

## Frozen MT4 history

| File | Records | Bytes | SHA-256 |
|---|---:|---:|---|
| USDJPY1.hst | 371,128 | 22,267,828 | `f6711747dad368f7f108f8088b8e6aa09f9c86ce9347468dd32e1c6816456e06` |
| USDJPY15.hst | 24,825 | 1,489,648 | `c82c88307289b698cf2c71ae13050d9ad006b412d35f6a36a4e358c046e65571` |

HST format is v401 with record order:

`time, open, high, low, close, tick_volume, spread, real_volume`

Timestamps are the canonical Europe/EET-EEST MT4 server-local clock encoded as epoch values. M1→M15 OHLC and volume aggregation is exact.

## Frozen baseline identity

- Canonical source commit: `cbdfcb36602f2138431ebe6618489b289e24d96d`
- Canonical source SHA-256: `207652c3dda2aa6802f909b5cc86fa5aab68652d38ed10b3f74b7907ce6968ec`
- Canonical source blob: `2f837118b772550eee8995fae2f8c55d408f9540`
- Expected trade ledger SHA-256: `33d08d580d584f533bc5f9dda510184fb86c668608f76f8e9b7c014924c5f1b8`

No B02/F05 entry, exit, sizing, spread, session or hard-exclusion rule was changed.

## Frozen expected result

| Metric | Expected |
|---|---:|
| Opened | 964 |
| B02 opened | 232 |
| F05 opened | 732 |
| Closed | 963 |
| Period-end open | 1 |
| Realized net JPY | -9,904 |
| Gross profit JPY | 197,579 |
| Gross loss JPY | 207,483 |
| Profit factor | 0.9522659687781649 |
| Wins | 469 |
| Losses | 493 |
| Flat | 1 |

The sole period-end open trade must be:

`F05|2023-12-29T16:30:00Z|-1`

with entry UTC `2023-12-29T16:45:00Z`.

## Binding Rakuten MT4 run contract

- Symbol: USDJPY
- Period: M15
- Model: 0
- Spread: 5 points
- Test interval: `2023.01.01` through `2024.01.01`
- B02/F05 fixed lots: 0.01 each
- Virtual JPY initial balance: 100,000
- Virtual leverage: 25
- Virtual stop-out level: 100%
- Runner: interactive Rakuten MT4 runner

## Pass gates

All of the following are required:

1. exact M1 and M15 HST hashes;
2. MetaEditor compilation success;
3. exact 964/232/732/963/1 counts;
4. exact opened trade-key set;
5. exact gross pips for all 963 closed trades;
6. net JPY equal to -9,904;
7. PF equal to 0.9522659687781649;
8. exact period-end open trade key;
9. zero OrderSend and OrderClose failures.

The period-end floating value is reported and reconciled against the frozen open trade and final Bid/Ask, but it is not a tuning or selection input.

A failed gate stops the process at baseline parity diagnosis. The result may not be used to modify the baseline logic.
