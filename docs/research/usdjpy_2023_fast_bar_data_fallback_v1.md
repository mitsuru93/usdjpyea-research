# USDJPY 2023 fast bar-data fallback v1

## Activation condition

This fallback is inactive unless Family F has no exact specification that passes both preregistered 2024 H1 development gates and 2024 H2 cross-regime gates.

## Data choice

The initial 2023 research stage does not require tick data.

Preferred acquisition:

- compressed M1 OHLC bars for USDJPY covering 2023;
- deterministic M15 aggregation from M1;
- fixed-spread research assumptions matching the current B02/F05 architecture;
- file identity, source, timezone conversion and gap inventory frozen before outcome evaluation.

M15-only bars are usable for the current event-confirmation hypothesis because all decisions occur on completed M15 bars. M1 is preferred because it allows deterministic M15 construction, identification of missing intervals and a closer later bridge to MT4 Model 0 without the download cost of ticks.

## Tick-data boundary

Tick data becomes necessary only if a later candidate materially depends on one or more of:

- intrabar stop-loss or take-profit ordering;
- trailing-stop decisions inside the M15 bar;
- variable spread at entry or exit;
- tick-level slippage or execution sequence;
- tick-equity drawdown, minimum margin or stop-out behavior as a development variable.

Tick data is not required to decide whether the event-confirmation admission mechanism has bar-level edge.

## Intended 2023 role

2023 would be an additional development/falsification period, not a substitute for the existing binding sequence. A new candidate must still be frozen before any renewed 2025 H1 candidate execution, and 2025 H2 remains locked until an unchanged candidate passes 2025 H1.