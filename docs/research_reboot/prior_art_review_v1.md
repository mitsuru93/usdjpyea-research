# Prior Art Review v1: MT4, AI, and FX Strategy Research

Collected on: 2026-07-10 JST  
Scope: zero-base FX/MT4 research for Rakuten MT4 execution, not a justification for any existing USDJPY-only design.

## Position

AI/ML is allowed in this project only when it improves a clearly defined research or decision layer under strict validation. It is not accepted as a shortcut to profitable trading.

The default architecture remains:

1. public-data research outside MT4,
2. deterministic strategy and feature generation,
3. walk-forward / purged validation,
4. cost and execution stress testing,
5. MT4 implementation only after the strategy is explainable and reproducible.

## MT4 as research platform vs execution platform

MT4/MQL4 can execute deterministic Expert Advisors, read/write files, and emit CSV logs, but it is a weak environment for heavy research or online AI integration.

Relevant MQL4 constraints:

- File operations are sandboxed under `MQL4\Files` or `Tester\Files`; `FILE_COMMON` can use the shared terminal folder, but arbitrary filesystem access is not available.
- `WebRequest()` requires manually whitelisted URLs, is synchronous, and cannot run in Strategy Tester.
- Strategy Tester has execution restrictions that make external-service-dependent research designs unsuitable for reproducible backtesting.
- Order execution must handle `OrderSend()` errors such as invalid price, requote, and invalid stops.

Design implication:

- Do not put data acquisition, model training, or external API dependency inside MT4.
- MT4 should receive versioned parameters/artifacts and emit logs.
- Python/GitHub Actions should own download, normalization, model training, and robustness analysis.

## Prior art and how it affects this project

### 1. FX heuristic optimization and reproducibility

Ivanov and Yan (2021), *Constraint-Based Inference of Heuristics for Foreign Exchange Trade Model Optimization*, argue that indicator-function values can be non-reproducible and can reduce trade opportunities compared with price-action templates. Their work emphasizes dataset-agnostic heuristic templates, parameter search across instruments/granularities, and reproducibility.

Project implication:

- Avoid indicator soup.
- Treat every feature as a versioned formula.
- Prefer small, auditable feature blocks before moving to ML.

### 2. Genetic programming on intraday FX

Cirillo, Lloyd, and Nordin (2014), *Evolving intraday foreign exchange trading strategies utilizing multiple instruments price series*, used 5-minute OHLC data from AUDUSD, EURUSD, GBPUSD, and USDJPY, and evaluated in-sample/out-of-sample results for USDJPY. They explicitly compared selection based on training-only fitness versus validation-aware criteria.

Project implication:

- Multi-instrument inputs are worth testing, but only with strict OOS validation.
- Strategy selection must not be based on training-set PnL alone.
- M5 is a serious starting timeframe; it is less spread-fragile than M1.

### 3. Rule-based feature optimization for FX robo-trading

Zhang and Khushi (2020), *GA-MSSR: Genetic Algorithm Maximizing Sharpe and Sterling Ratio Method for RoboTrading*, optimized trading-rule features on intraday data of six major currency pairs and used Sharpe/Sterling ratio objectives to reduce variance and drawdown.

Project implication:

- Objective functions must include drawdown/risk, not just net profit.
- Optimization is allowed only after market profile and baseline cost stress are available.
- Risk-adjusted objectives should be part of ranking.

### 4. Deep/reinforcement learning in trading

Pricope (2021), *Deep Reinforcement Learning in Quantitative Algorithmic Trading: A Review*, notes that many DRL trading studies remain proof-of-concept, often rely on unrealistic settings, lack real-time platform testing, and do not consistently achieve meaningful profitability.

Project implication:

- Do not start with DRL.
- ML should initially be used for no-trade classification, regime classification, candidate ranking, or shadow prediction.
- Live/forward validation is mandatory before any ML-derived rule affects real orders.

### 5. Meta-policy / regime-aware policy selection

Niu, Li, and Li (2022), *MetaTrader: An Reinforcement Learning Approach Integrating Diverse Policies for Portfolio Optimization*, proposes a two-stage RL system that learns diverse policies and then a meta-policy to select among them by market condition.

This is not MetaQuotes MT4; it is an academic method named MetaTrader.

Project implication:

- The useful idea is policy selection by regime, not immediate RL implementation.
- This supports a regime-first multi-candidate / single-decision design.

### 6. Backtest overfitting and validation design

Carr and Lopez de Prado (2014), *Determining Optimal Trading Rules without Backtesting*, warns that calibrating a trading rule via historical simulations contributes to backtest overfitting.

Project implication:

- Use walk-forward, embargo/purging where labels overlap, and parameter-neighborhood checks.
- Reject one-point parameter winners.
- Report distributions of outcomes across months/sessions/regimes, not only aggregate PnL.

## Accepted research stance

Allowed:

- deterministic feature engineering,
- regime-first architecture,
- public-data screening with spread/slippage stress,
- ML as shadow prediction or secondary scoring,
- later ML promotion only after OOS and MT4-forward evidence.

Rejected for now:

- MT4-hosted model training,
- WebRequest-dependent live AI decisions,
- black-box entry models without reason codes,
- high-frequency short-TP strategies that require ideal spreads,
- parameter searches ranked only by total net profit,
- direct adoption of any paper result without reproducing it on our broker-cost model.

## Initial design consequence

The first strategy research architecture should be:

```text
Market profile
  -> regime labels
  -> candidate engines
       mean_reversion
       breakout_expansion
       pullback_continuation
       session_structure
  -> single decision layer
       long / short / no_trade
  -> cost stress
  -> walk-forward validation
  -> MT4 deterministic implementation
```

This is more appropriate than a single RSI/MA/indicator-cross EA and more testable than a first-pass black-box AI EA.
