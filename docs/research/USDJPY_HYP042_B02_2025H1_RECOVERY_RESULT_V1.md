# USDJPY-HYP-042 — B02 2025H1 Breakout Failure Recovery Study

**Final decision:** `B02_V2_NO_CHANGE_REQUIRED_AT_CURRENT_STAGE`

The current B02 remains unchanged. No Core or MT4 candidate implementation is authorized.

## Baseline identity

- 2023–2024 B02: 429 trades, `+¥12,722`.
- 2025H1 B02: 105 trades, `-¥6,964`, PF `0.793`.
- 2025H1 F05: 358 trades, `-¥13,844`.
- 2025H1 B02＋F05: 463 trades, `-¥20,808`, PF `0.829`.

## Failure decomposition

- `IMMEDIATE_FALSE_BREAKOUT`: 18 trades, net -9,652 JPY, gross loss 9,652 JPY, 2025 loss share 28.7%, development loss share 30.2%, difference -1.5 pp; Long/Short 8/10; F05 overlap 9.
- `SLOW_ACCEPTANCE_FAILURE`: 20 trades, net -17,521 JPY, gross loss 17,521 JPY, 2025 loss share 52.1%, development loss share 49.1%, difference +3.0 pp; Long/Short 10/10; F05 overlap 7.
- `TEMPORARY_PROFIT_GIVEBACK`: 14 trades, net -5,744 JPY, gross loss 5,744 JPY, 2025 loss share 17.1%, development loss share 18.2%, difference -1.1 pp; Long/Short 2/12; F05 overlap 6.
- `TREND_EXHAUSTION_ENTRY`: 0 trades, net +0 JPY, gross loss 0 JPY, 2025 loss share 0.0%, development loss share 0.0%, difference 0.0 pp; Long/Short 0/0; F05 overlap 0.
- `EXIT_HORIZON_MISMATCH`: 4 trades, net -725 JPY, gross loss 725 JPY, 2025 loss share 2.2%, development loss share 2.5%, difference -0.4 pp; Long/Short 2/2; F05 overlap 1.
- `SESSION_VOLATILITY_MISMATCH`: 0 trades, net +0 JPY, gross loss 0 JPY, 2025 loss share 0.0%, development loss share 0.0%, difference 0.0 pp; Long/Short 0/0; F05 overlap 0.
- `OVERLAP_CHRONOLOGY`: 0 trades, net +0 JPY, gross loss 0 JPY, 2025 loss share 0.0%, development loss share 0.0%, difference 0.0 pp; Long/Short 0/0; F05 overlap 0.
- `OTHER`: 49 trades, net +26,678 JPY, gross loss 0 JPY, 2025 loss share 0.0%, development loss share 0.0%, difference 0.0 pp; Long/Short 23/26; F05 overlap 14.

The 2025H1 B02 loss is concentrated in acceptance failure: immediate false breakouts and slow acceptance failures account for `80.8%` of gross loss. Temporary-profit giveback adds `17.1%`; late horizon mismatch is only `2.2%`. No residual loss was uniquely assigned to trend-exhaustion, session/volatility or overlap after the higher-priority path classifications.

## Finite candidate result

- `C1_BREAKOUT_ACCEPTANCE_30M`: development -2,516 JPY (delta -15,238); 2025H1 B02 -4,563 JPY (delta +2,401); modified share 50.6%; winner retention 56.9%; 2024 delta -18,379; portable=False.
- `C2_FALSE_BREAK_RANGE_REENTRY`: development +5,125 JPY (delta -7,597); 2025H1 B02 +878 JPY (delta +7,842); modified share 78.6%; winner retention 42.9%; 2024 delta -18,182; portable=False.
- `C3_PROFIT_TO_NONPROFIT_GIVEBACK`: development +11,219 JPY (delta -1,503); 2025H1 B02 +2,321 JPY (delta +9,285); modified share 73.2%; winner retention 47.1%; 2024 delta -10,963; portable=False.

`C3_PROFIT_TO_NONPROFIT_GIVEBACK` is the best 2025 result: B02 becomes `+¥2,321` with PF `1.166`, and the baseline portfolio improves to `-¥11,523` with PF `0.887`. It is not adopted because it changes 314/429 development trades, cuts winner gross profit retention to `47.1%`, and worsens 2024 B02 by `¥10,963`. This is not a narrow failure recovery; it is a broad lifecycle replacement whose benefit is concentrated in the weak 2023/2025 regimes.

## Risk and execution

- Baseline Core 2025H1 exact full-equity evidence: minimum equity `¥57,328`, maximum equity DD `¥42,737`, minimum free margin `¥22,611.58`, minimum margin level `156.0535%`, maximum concurrency `8`, stopout breach `0`.
- M15-boundary counterfactuals reduce 2025H1 DD, but none is implementation-authorized because the portability/winner-preservation contract fails before Core.
- Tester currency is JPY; 0.01 lot maps one pip to `¥10`; B02 `-696.4 pips = -¥6,964` and portfolio `-2,080.8 pips = -¥20,808` exactly.
- Integrated chronology is unchanged: matured closes → B02 evaluation → F05 evaluation → snapshot. F05 signals and economics are invariant.

## Evidence limitation

The common binding path resolution is the first executable M15 boundary. Exact 5-second, 15-second, 1-minute and 5-minute paths are not asserted across all periods because the consumed 2024H2 and 2025H1 baseline artifacts do not preserve a common exact intrabar Tick sequence. The evidence therefore reports explicit extra-exit-cost stress and next-M15-boundary delay, and makes no fabricated second-level parity claim.

## Closure

- 2020–2022 was not used and is not a binding gate.
- 2025H1 remains the validation period despite known baseline outcomes and reruns.
- 2025H2 was not used.
- HYP-039, HYP-040, HYP-041 and portfolio-integration branches/statuses were not modified.
- Baseline B02 remains authoritative. Production and live trading are not authorized.
