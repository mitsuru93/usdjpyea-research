# AGENTS Guidance

## Repository Purpose
This repository is for **research only** and focuses on pre-MT4 simulation work for USDJPY EA development.

## Core Principles
- Prefer robustness over peak profit.
- Avoid lookahead bias in all research and simulations.
- Use conservative assumptions whenever same-bar execution order is ambiguous.
- Compare outcomes by month, session, and RV/TR bucket.

## Boundaries
- Do not add MT4 production code (`.mq4` / `.mqh`) in this repository.
- Do not include broker-specific live-trading logic or production secrets.
