# USDJPY EA Research

Public repository for pre-MT4 research and simulation.

## Purpose
This repository is used to evaluate trading ideas before they are implemented and validated in MT4.

## Scope
- Python-based simulation
- Feature engineering
- Robustness testing
- Experiment configs
- Scoring and comparison logic
- Sample data and reproducible research utilities

## Out of Scope
- Private MT4 production code
- Broker-specific settings
- Final production thresholds
- Full private datasets
- Live trading or account-related information

## Goals
- Reject weak ideas before MT4 testing
- Prefer robustness over peak backtest profit
- Compare candidates by month, session, and strategy bucket
- Reduce wasted MT4 testing time

## Repository Structure
- `research/data_sample/` : small public sample datasets
- `research/features/` : feature generation code
- `research/simulator/` : pre-MT4 simulation logic
- `research/scoring/` : evaluation and ranking logic
- `research/experiments/` : experiment definitions
- `research/reports/` : generated summaries and reports
- `configs/strategy/` : strategy-related configs
- `configs/experiments/` : experiment configs
- `tools/` : helper scripts

## Workflow
1. Define a hypothesis.
2. Simulate it under conservative assumptions.
3. Score it by robustness, not only total profit.
4. Promote only strong candidates to the private core repository for MT4 validation.

## Principles
- No lookahead bias
- Conservative handling when execution order is ambiguous
- Reproducible outputs
- Clear comparison across periods and conditions

## Status
Initial repository setup for the USDJPY EA pre-MT4 research workflow.
