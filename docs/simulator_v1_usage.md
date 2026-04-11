# Simulator v1 Usage (Pre-MT4 Candidate Engine)

## What simulator v1 is

Simulator v1 is a **candidate labeling/screening engine** for pre-MT4 research.
It takes envelope touch events and creates conservative Rev/Trend candidate outcomes.

## What simulator v1 is not

Simulator v1 is intentionally limited:
- It is **not** a full MT4 backtester.
- It does **not** reproduce broker/live execution behavior.
- It does **not** implement final trend-environment gating.
- It does **not** implement full position-lock semantics.

MT4 validation remains the final source of truth before any production decisions.

## Baseline assumptions in v1

- Symbol/timeframe baseline: `USDJPY / M1`
- Envelope baseline: `EMA20` with deviation `±0.070%`
- Sessions (JST):
  - `ASIA`: 03:00-08:59
  - `TOKYO`: 09:00-15:59
  - `LONDON`: 16:00-20:59
  - `NY`: 21:00-02:59 (crosses midnight)
- Candidate mapping:
  - upper touch -> Rev SELL + Trend BUY
  - lower touch -> Rev BUY + Trend SELL
- TP/SL defaults:
  - Rev: TP 10 pips / SL 30 pips
  - Trend: TP 10 pips / SL 20 pips
- Conservative same-bar rule:
  - If TP and SL are both reachable in one bar and order is ambiguous, count **SL first**.
- Anti-lookahead convention:
  - Candidate evaluation starts on the **next bar** after the signal bar.

## Timeline handling (explicit)

Raw input `datetime` is treated as the source timeline and is not overwritten.
JST session labels are derived explicitly using `--input-timezone-mode`:

- `UTC` (default): `jst_datetime = datetime + 9h`
- `JST`: `jst_datetime = datetime` (raw already JST)

This keeps timeline assumptions auditable for MT4 comparisons.

## Entry price meaning

`entry_price` in `candidates.csv` is a **signal reference price** (touch-bar close).
It is not a true broker fill price and should not be interpreted as MT4 execution parity.

## Input expectations

Input is a simple OHLC CSV containing at least datetime/open/high/low/close.

The loader auto-detects common aliases (example: `timestamp` for datetime).
If schema is ambiguous or missing required fields, it fails with a clear error.

## Outputs

The pipeline writes:
- `candidates.csv`
- `summary_overall.csv`
- `summary_by_month.csv`
- `summary_by_session.csv`
- `summary_by_family.csv`
- `run_metadata.yaml`

`run_metadata.yaml` records assumptions and known limits for auditability.

## How to run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run simulator v1 (raw timeline interpreted as UTC):

```bash
python tools/run_candidate_sim.py \
  --input-csv path/to/usdjpy_m1.csv \
  --output-dir research/reports/my_run_v1 \
  --input-timezone-mode UTC
```

If your input is already JST:

```bash
python tools/run_candidate_sim.py \
  --input-csv path/to/usdjpy_m1.csv \
  --output-dir research/reports/my_run_v1 \
  --input-timezone-mode JST
```

Optional:

```bash
python tools/run_candidate_sim.py \
  --input-csv path/to/usdjpy_m1.csv \
  --output-dir research/reports/my_run_v1 \
  --max-holding-bars 30
```

Run smoke test:

```bash
python tools/smoke_test_research.py
```
