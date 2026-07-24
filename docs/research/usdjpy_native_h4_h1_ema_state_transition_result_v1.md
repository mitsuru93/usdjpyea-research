# USDJPY HYP-023 Native H4/H1 Exact Six-Cell Result v1

## Decision

`USDJPY-HYP-023` is **CLOSED_NO_ELIGIBLE_FAMILY_REGION**.

The exact preregistered six cells were evaluated unchanged on 2023H1, 2023H2, 2024H1 and 2024H2. No cell passed the frozen core gates in every fold, no full cell existed, no Manhattan-adjacent core component existed, and no finalist was selected. MT4 and 2025 remain locked.

## Canonical discrepancy repaired by this package

Research main `d7324cca2644a37b9185c379c1ab3cc49aaccc2f` contains a postmortem that classifies the first exact HYP-023 execution as `SCIENTIFIC_RESULT_COMPLETE_FAIL`, while registry v40 and the hypothesis program still state that the evaluation is awaiting execution. The original result files were not merged. This package is a deterministic technical recovery using the identical input, protocol and source SHAs. It is not a second scientific search or a retune.

## Identity

- Protocol SHA-256: `969d1892d0ee6bbe99c90df997ffbbfbfa6a3ad1915d67c906b43b07a3479c37`
- Evaluator SHA-256: `ce5b21d02875eaee583f427bb560d17f34b3afa79c4a646a9d5fe5f0ff97ce1e`
- Data module SHA-256: `6787d316c774831d9ea27d2b36f078128ff27e079c6a9c83c234fc6f38b8e013`
- Simulation module SHA-256: `16026504f607e3841f086ade1840537ea07c44630485d9e586c64a9b2533e0e2`
- 2023 M15 SHA-256: `4c10ab3244996d73d0955850675231a533f918da09a41ac642c9a3e287b7ac78`
- 2024 M15 SHA-256: `1566b9d0497f3a2aa156868144d31b89721fca48329feaf82035826ada7ee25c`
- 2024 source mutated: no
- 2025 accessed: no
- MT4 accessed: no

## Population

- Candidate cells: 6
- Candidate-fold evaluations: 24
- Executed positions: 841
- Signals/events: 1,930
- Boundary liquidations: 4

## Cell-level result

- `N_H4F3S12_H1F4S16` — 2023H1: severe -401.2, PF 0.811, min-quarter -384.8, core=False; 2023H2: severe +678.2, PF 1.606, min-quarter -58.5, core=False; 2024H1: severe +219.3, PF 1.180, min-quarter -78.9, core=False; 2024H2: severe +459.0, PF 1.298, min-quarter +55.4, core=True
- `N_H4F3S12_H1F8S32` — 2023H1: severe -1250.0, PF 0.551, min-quarter -804.1, core=False; 2023H2: severe +1269.3, PF 1.907, min-quarter +565.9, core=True; 2024H1: severe -90.0, PF 0.947, min-quarter -221.2, core=False; 2024H2: severe +1196.2, PF 1.543, min-quarter +447.8, core=True
- `N_H4F6S24_H1F4S16` — 2023H1: severe +201.0, PF 1.227, min-quarter +80.6, core=True; 2023H2: severe -83.3, PF 0.886, min-quarter -97.1, core=False; 2024H1: severe +252.4, PF 1.452, min-quarter -16.6, core=False; 2024H2: severe -227.4, PF 0.718, min-quarter -271.3, core=False
- `N_H4F6S24_H1F8S32` — 2023H1: severe -472.0, PF 0.655, min-quarter -312.1, core=False; 2023H2: severe +688.7, PF 1.705, min-quarter -13.0, core=False; 2024H1: severe +245.6, PF 1.337, min-quarter +118.7, core=True; 2024H2: severe +140.5, PF 1.105, min-quarter -51.4, core=False
- `N_H4F12S48_H1F4S16` — 2023H1: severe +55.5, PF 1.152, min-quarter -132.0, core=False; 2023H2: severe -179.9, PF 0.621, min-quarter -114.9, core=False; 2024H1: severe -215.7, PF 0.276, min-quarter -117.7, core=False; 2024H2: severe -186.7, PF 0.607, min-quarter -254.0, core=False
- `N_H4F12S48_H1F8S32` — 2023H1: severe -305.7, PF 0.550, min-quarter -203.8, core=False; 2023H2: severe +105.7, PF 1.184, min-quarter -63.4, core=False; 2024H1: severe -276.2, PF 0.550, min-quarter -186.0, core=False; 2024H2: severe +95.4, PF 1.135, min-quarter -306.4, core=False

Four cells have positive pooled severe net, but each has at least one negative half-year and at least one negative three-month sub-block. Pooled positivity therefore cannot override the frozen fold and family-region gates.

## Exit mechanism diagnostic

- `BOUNDARY_LIQUIDATION`: 4 trades, default -43.2 pips, severe -51.2 pips
- `H1_OPPOSITE_STATE`: 727 trades, default +9171.5 pips, severe +7612.9 pips
- `H4_OPPOSITE_TRANSITION`: 110 trades, default -5409.3 pips, severe -5643.2 pips

The H1 opposite-state exits are positive in aggregate, while H4 opposite-transition exits are negative in aggregate. This is diagnostic only. The protocol is closed; no exit precedence, EMA period, confirmation window or threshold may be repaired from this result.

## Gate result

- Support: all cells had at least 10 trades in every fold.
- Four-fold core cells: 0.
- Four-fold full cells: 0.
- Core adjacency components: 0.
- Eligible family-region candidates: 0.
- Finalist: none.

The binding failures are half-year severe/default performance, event-only performance in losing folds, negative three-month sub-blocks, and breadth/date-removal failures. Exact failed gates are in `usdjpy_native_h4_h1_gate_failures_v1.csv`.

## Mechanism boundary

The frozen GitHub protocol is a primary native-H4 signal architecture and explicitly has no M15 parent signal. Therefore the older B02/F05 setup-observation predictions—P1/P2/P3 reduction and stack/standalone incremental effect—are not defined for this evaluator and must not be reported as confirmed. This discrepancy between the earlier analysis task and the canonical HYP-023 protocol is preserved in `usdjpy_native_h4_h1_required_output_audit_v1.json`.

## Scientific decision

Close `N_NATIVE_H4_H1_EMA_STATE_TRANSITION` and `USDJPY-HYP-023` before MT4 parity or any 2025 access. Prohibit:

- parameter expansion;
- H1/H4 alignment, period, confirmation or exit repair;
- fixed-time fallback;
- side/year/session exception;
- selection of one positive pooled cell;
- combination with R1K03 or closed Families A–I;
- MT4 or 2025 execution for this family.

## Exact next action

No scientific execution is authorized. The analysis thread may formulate at most one genuinely distinct successor research question, after canonical duplicate audit and explicit registry authorization. Until then, this execution thread stops without accessing additional market outcomes.
