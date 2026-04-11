# Feature Set v1 (Decision-Time Snapshot)

This document defines the compact research-side feature set attached to each simulator v1 candidate row.

## Design intent

- Pre-MT4 research support only.
- Candidate rows remain **labels/signals**, not confirmed MT4/live executions.
- Every feature is computed using information available **at or before signal bar close**.
- No forward bars are used in any feature formula (anti-lookahead rule).
- USDJPY pip size is fixed to `0.01`.

## Anti-lookahead rule

For a signal timestamp `t`:
- Features use values from bars `<= t` only.
- Outcome evaluation still starts from `t+1` bar (existing simulator v1 rule).
- No future window/shift is used in feature computation.

## Feature definitions

| Feature | Meaning | Signed/Absolute | Unit |
|---|---|---|---|
| `close` | Signal bar close price. | Absolute | Price |
| `ema20` | EMA(20) on close (pandas `ewm`, `adjust=False`). | Absolute | Price |
| `dist_from_ema_pips` | `close - ema20` converted to pips. | Signed | Pips |
| `envelope_upper` | Upper envelope from v1 (`ema20 * (1 + 0.00070)`). | Absolute | Price |
| `envelope_lower` | Lower envelope from v1 (`ema20 * (1 - 0.00070)`). | Absolute | Price |
| `touch_upper` | Whether bar high reached upper envelope. | Boolean | Flag |
| `touch_lower` | Whether bar low reached lower envelope. | Boolean | Flag |
| `pre10_change_pips` | `close(t) - close(t-10)` in pips. | Signed | Pips |
| `pre30_change_pips` | `close(t) - close(t-30)` in pips. | Signed | Pips |
| `pre60_change_pips` | `close(t) - close(t-60)` in pips. | Signed | Pips |
| `net10_change_pips` | Net sum of one-bar close changes over the prior 10 fully closed bars (`t-10 ... t-1`). | Signed | Pips |
| `rsi14` | RSI(14), Wilder smoothing approximation using pandas EWMA alpha `1/14`. | Bounded oscillator | Index (0-100) |
| `atr5_pips` | ATR(5) using true range mean, in pips. | Absolute | Pips |
| `atr14_pips` | ATR(14) using true range mean, in pips. | Absolute | Pips |
| `atr_ratio_5_14` | Short/long ATR ratio (`atr5_pips / atr14_pips`). | Relative | Ratio |
| `macd_line` | MACD line (`EMA12 - EMA26`) on close. | Signed | Price delta |
| `macd_signal` | Signal line (`EMA9` of MACD line). | Signed | Price delta |
| `macd_hist` | `macd_line - macd_signal`. | Signed | Price delta |
| `bb_width` | Bollinger band width (20, 2σ): `upper - lower`. | Absolute | Price |
| `bb_width_ratio_to_close` | `bb_width / close`. | Relative | Ratio |
| `month` | JST-derived year-month label for reporting. | Categorical | String |
| `session` | JST session bucket (ASIA/TOKYO/LONDON/NY). | Categorical | String |
| `input_timezone_mode` | Explicit raw timeline mode used for conversion (`UTC` or `JST`). | Categorical | String |

## Why this is research-side (not MT4 truth)

These features are intentionally compact, explicit, and auditable so candidates can be screened and filtered quickly before MT4 validation.

They do **not** attempt to replicate:
- broker execution/fill behavior,
- live EA locks or gating semantics,
- full MT4 indicator/runtime parity.

MT4 remains the final source of truth for production behavior.
