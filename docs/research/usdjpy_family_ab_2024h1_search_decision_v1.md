# USDJPY Family A/B — 2024 H1 finite-search decision v1

## Decision

The preregistered Family A and Family B grids are closed at the 2024 H1 research stage.

- evaluated exact specifications: `74`;
- research-eligible specifications: `0`;
- research finalists: `0`;
- direct MT4 candidate implementation: not executed;
- 2024 H2 accessed: no;
- 2025 H1 candidate-specific access: no.

No threshold is repaired or extended from these results.

## Frozen evidence

- Research preregistration commit: `011d337931802822125ce1c0634e9e43a4c3ff67`;
- preregistration Git blob: `067bbcf40584985ce0344ec50056308bd5381c3e`;
- Core evaluator commit: `43947d223c1f3f116ced6de866402a951936615e`;
- evaluator Git blob: `085c7412a60c938ff776668f6dc647f71b9e4dd6`;
- Core Run ID: `29885440528`;
- artifact ID: `8516341842`;
- artifact digest: `sha256:670cabd09ea2355dbb21672913950aa1eb9e33695e6439d4e0f2f6d9f069abd3`;
- result SHA-256: `709aa6d4079ff12f6f8d9bbb2f42239680cef3f8e059d736490477d5653f1353`.

The accepted baseline was reproduced at 428 closed trades, JPY 22,797, PF 1.377415, B02 JPY 9,554 and F05 JPY 13,243.

## Mechanism decisions

| Mechanism | Grid size | Eligible | Decision |
|---|---:|---:|---|
| A1 weak outside close + counter-wick | 20 | 0 | close grid |
| A2 next-bar retention failure | 16 | 0 | close grid |
| A3 recent same-side failed break | 16 | 0 | close grid |
| B1 stale same-direction weak add-on | 9 | 0 | close grid |
| B2 high-ordinal weak add-on | 9 | 0 | close grid |
| B3 opposite/mixed weak entry | 4 | 0 | close grid |

## Closest non-eligible specifications

### B1 stale same-direction weak add-on

`B1_STALE_SAME_DIRECTION_WEAK_ADDON__D_pips_5__M_min_minutes_480`

- affected F05 trades: 25;
- candidate net: JPY 24,295;
- delta: JPY +1,498;
- PF: 1.423037;
- Q1 delta: JPY +923;
- Q2 delta: JPY +575;
- ex-best-two entry-date delta: JPY +326;
- leave-one-month-out minimum delta: JPY +758;
- positive / negative effect months: 3 / 3.

It failed the frozen maximum of one negative effect month. The result is not repaired by changing 480 minutes or five pips.

### B3 opposite/mixed weak entry

`B3_OPPOSITE_OR_MIXED_WEAK_ENTRY__D_pips_5`

- affected F05 trades: 13;
- candidate net: JPY 23,581;
- delta: JPY +784;
- PF: 1.405123;
- Q1 delta: JPY +570;
- Q2 delta: JPY +214;
- positive / negative effect months: 4 / 1;
- leave-one-month-out minimum delta: JPY +409;
- ex-best-two entry-date delta: JPY -591.

It failed the frozen ex-best-two-date gate and top-two positive-date concentration gate.

### Family A

The best aggregate Family A deltas did not survive both quarters, month distribution and date-concentration gates. Recent same-side failed-break suppression was directionally harmful across the grid.

## Interpretation

The explicit breakout-acceptance and conditional-overlap Entry filters tested here do not provide a distributed 2024 H1 advantage under the frozen gates. B1 indicates that stale weak add-ons remain diagnostically relevant, but the effect changes sign across too many months to justify MT4 implementation or H2 exposure.

The next independent phase is Family C structural Exit research. It must use a new preregistration and may not reuse H2 or 2025 evidence to choose thresholds.

## Research handling

- Family A v1 grid: `CLOSED_H1_NO_ELIGIBLE_SPECIFICATION`;
- Family B v1 grid: `CLOSED_H1_NO_ELIGIBLE_SPECIFICATION`;
- exact specifications exposed to H2: zero;
- exact specifications exposed to 2025 H1: zero;
- live-order authorization: none.
