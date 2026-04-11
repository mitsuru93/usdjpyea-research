# USDJPY EA Research (Pre-MT4)

This repository is dedicated to **pre-MT4 research and simulation** for a USDJPY Expert Advisor (EA).

It is intended for:
- feature engineering and signal research
- simulation under conservative assumptions
- robustness testing across regimes and market conditions
- candidate strategy screening before MT4 validation

## Scope

This repo contains research artifacts only.

Included:
- lightweight research modules (`research/`)
- configuration placeholders (`configs/`)
- baseline documentation (`docs/`)
- experiment templates and research-side config skeletons
- basic CI checks for Python source integrity

Excluded:
- MT4 production code (`.mq4`, `.mqh`)
- broker-specific implementation details
- live-trading operational setup
- secrets and production credentials

## Repository Layout

- `research/data_sample/` — placeholder for small, sanitized sample data
- `research/features/` — feature engineering package
- `research/simulator/` — simulation logic package
- `research/scoring/` — scoring and candidate evaluation package
- `research/experiments/` — experiment outputs/tracking placeholders
- `research/reports/` — report placeholders
- `docs/` — current baseline and simulator-scope documentation
- `configs/strategy/` — strategy configuration skeletons
- `configs/experiments/` — experiment templates
- `tools/` — utility scripts and supporting tooling notes

## Development Notes

- Keep assumptions conservative when execution order is ambiguous.
- Avoid lookahead bias in all research and simulations.
- Prefer robust behavior over peak in-sample performance.
- Compare performance by month, session, and volatility/trend buckets.


## Simulator v1 (Conservative Candidate Engine)

A first practical simulator layer is available for pre-MT4 screening:
- Generates Rev/Trend candidates from EMA20 envelope touch events.
- Evaluates outcomes with conservative assumptions (same-bar ambiguity => SL first).
- Produces summaries by overall, month, session, and family.

Important: simulator v1 is **not** full MT4 parity and does not replace MT4 validation.

## CI

A minimal GitHub Actions workflow validates Python syntax by compiling `research/` and `tools/`.
