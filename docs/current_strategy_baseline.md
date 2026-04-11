# Current Strategy Baseline (Research Mirror)

## Purpose
This document captures the **current EA baseline design** as a research-side reference.

> MT4 EA behavior remains the final source of truth. Any mismatch discovered during MT4 validation must be resolved in favor of MT4 behavior.

## Baseline Signal Model
- Symbol: **USDJPY**
- Timeframe: **M1**
- Core signal frame: **EMA20 envelope**
- Envelope deviation: **±0.070%**

Research interpretation notes:
- Candidate generation should be constrained to the envelope model above.
- Any additional signal nuances are **TBD / to be verified against EA**.

## Reverse vs Trend Distinction
The baseline includes two operating paths:

1. **Reverse (Rev)**
   - Present and active in baseline.
   - Default TP/SL: **TP 10 pips / SL 30 pips**.

2. **Trend**
   - Trend mode exists and is **enabled** in baseline.
   - Default TP/SL: **TP 10 pips / SL 20 pips**.

Operational details beyond this high-level split are **TBD / to be verified against EA**.

## Touch Model Distinction
- **Reverse touch logic:** uses **real touch**.
- **Trend touch logic:** uses **virtual spread clipping** for trigger judgment.

Exact implementation order, tie-breakers, and edge-case handling are **TBD / to be verified against EA**.

## TP/SL Defaults
- Reverse defaults: **TP 10 pips / SL 30 pips**
- Trend defaults: **TP 10 pips / SL 20 pips**

Any per-filter, per-session, or per-state TP/SL overrides are **TBD / to be verified against EA**.

## Session Segmentation (JST)
The baseline uses JST session buckets:
- ASIA: 03:00-08:59
- TOKYO: 09:00-15:59
- LONDON: 16:00-20:59
- NY: 21:00-02:59

Many thresholds and filters are session-aware. Exact parameter mappings by session are **TBD / to be verified against EA**.

## Source-of-Truth Policy
This repository is intentionally pre-MT4 and research-oriented:
- It should document and approximate current baseline behavior conservatively.
- It should not invent undocumented trade logic.
- If uncertain, mark items **TBD / to be verified against EA**.
