# USDJPY-HYP-039 — Unchanged Short Pullback 2025H1 Portfolio Recovery Qualification

## Purpose

Qualify the exact unchanged HYP-037 Short-only rule as a new independent deployment candidate and measure how far it recovers the fixed 2025H1 B02/F05 portfolio baseline of **JPY -20,808**.

This does not reopen or revise either closed decision:

- HYP-037: `FAIL_2023_2024_RESEARCH_CANDIDATE_GATE_NO_RETUNING`
- HYP-038: `MECHANISM_CONFIRMED_NO_DEPLOYABLE_LOSS_DECOUPLING_RULE`

No HYP-038 filter or lifecycle rule is permitted.

## Frozen candidate

`C1_SHORT_DUKASCOPY_NATIVE_16BAR_UNCHANGED`

- Short only
- Dukascopy source-native Bid M15 bars
- EMA20 / EMA96
- ATR20
- 0.25 ATR pullback tolerance
- prior-bar trend strength at or below -1
- current bar High reaches EMA20 minus tolerance, Close below EMA20, bearish Close
- first executable Bid at or after the next observed M15 boundary
- first executable Ask at or after 16 observed M15 bars
- same-variant active suppression: reject signal index `i` when `i <= prior accepted i + 17`
- fold crossing prohibited during 2023–2024 comparison
- 0.01 lot, 1 pip = JPY 10
- no SL, no TP, no session exclusion

The machine-readable authority is `configs/research/usdjpy_hyp039_candidate_contract_v1.json`.

## Period firewall

- 2020–2022: analysis only; not required.
- 2023–2024: Research/Core/MT4 and Rakuten portability; no retuning.
- 2025H1: candidate-specific external evaluation after freeze, parity, compile and Rakuten portability.
- 2025H2: reserved for the final B02 v2 + F05 v2 + third-strategy integrated gate.

After the first 2025H1 outcome is opened, further 2025H1 runs may be development or diagnostic runs, but no changed version may describe 2025H1 as unseen validation.

## Binding decision

The binding portfolio is `B02 + F05 + Short Pullback`.

- `PASS_SHORT_PULLBACK_2025H1_PORTFOLIO_RECOVERY`
- `PASS_SHORT_PULLBACK_PORTABILITY_PARTIAL_2025H1_RECOVERY`
- `FAIL_SHORT_PULLBACK_2025H1_PORTABILITY`
- `FAIL_CORE_MT4_PORTABILITY`

Concentration is mandatory diagnostic evidence but is not an automatic failure by itself when cost-adjusted standalone P/L is positive, the portfolio improves, full-equity DD does not worsen and margin remains valid.

## Authorization

Core and MT4 research implementation are authorized. Production and live trading are not authorized.
