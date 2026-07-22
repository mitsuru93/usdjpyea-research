# USDJPY post-Family-E 2024 architecture diagnosis v1

## Scope and boundary

This diagnosis uses only accepted 2024 H1/H2 evidence after the binding 2025 H1 failure of `E2_ADAPTIVE_60_90__A15_B5_C15_R0`.

It does not use 2025 H1 thresholds, trade identities or candidate-specific outcomes to select a new rule. Candidate-specific 2025 H2 remains locked.

Accepted sources:

- 2024 H1 Entry-State Atlas v2: Core artifact `8516049893`, digest `sha256:ee54d2608c38750776366c27bde03e046a44c6bebec6964f33f1f04b4f115981`
- H1 atlas CSV SHA-256: `a9f78991fbf23cb5fb0af96b6b36fc4c3f9185e499a9ca44bdd3d33fcaa40efd`
- H1 baseline event audit SHA-256: `9560d6382e2457eaec83415316fb59d4989244d49c9977ce76cbdd717f32f09a`
- 2024 H2 accepted baseline source artifact: Core artifact `8519879009`, digest `sha256:1341850d4530d9bb8ea6522aefaa796dd5ea70abc698913633cb523f55d51981`
- H2 baseline event audit SHA-256: `a5a871d7105c6e68548e804c9ab517ee6bc0b08553474b158799f47ebd32edcd`

The H1 and H2 event audits were reconstructed with one common entry-time definition. No intrabar high/low was used. The diagnostic uses M15 executable marks, signal details logged at order-open time, accepted baseline exits and fixed 0.01-lot outcomes.

## Question

Which recurring market structure can explain why an early-loss overlay generalized directionally but could not restore positive expectancy?

The candidate explanations were:

1. late entry after the directional move was already mature;
2. failure to retain price outside the breakout level;
3. reversal after a superficially valid break;
4. repeated entries that treat one directional event as multiple independent opportunities.

## Full-year exposure-state result

The strongest cross-half distinction was not calendar time. It was the role of F05 inside the directional event.

| Strategy / entry state | 2024 H1 | 2024 H2 | Interpretation |
|---|---:|---:|---|
| F05 standalone | JPY -3,811 | JPY -4,931 | Negative in both halves |
| F05 opposite overlap | JPY -851 | JPY -2,933 | Negative in both halves |
| F05 mixed overlap | JPY -1,537 | JPY -544 | Negative in both halves |
| F05 same-direction stack | JPY +19,702 | JPY +26,071 | Strongly positive in both halves |
| F05 simultaneous same-direction | JPY -260 | JPY +5,068 | Mixed, but not persistently negative |

B02 remained positive in both 2024 halves overall. Therefore the next architecture unit targets F05 admission while retaining B02 unchanged.

## Mechanism interpretation

The result does not imply that an existing same-direction position mechanically creates edge. The more plausible causal interpretation is:

- the first F05 breakout signal frequently occurs before continuation is demonstrated;
- a later same-direction F05 signal often contains new information because price has continued beyond the first signal;
- baseline accounting treats every signal as an independent trade, even when they belong to one directional event;
- taking the first signal and every subsequent signal mixes an unconfirmed probe with confirmed continuation entries;
- Family E could cut some failed probes but could not change the admission architecture.

The new research unit therefore separates **observation** from **capital deployment**.

## New architecture hypothesis

For F05, the first same-direction signal of a directional event should create a non-trading probe state. A later same-direction F05 signal may be traded only after price has advanced far enough beyond the probe signal close within a finite event age.

This mechanism is called `F_EVENT_CONFIRMATION_ADMISSION`.

It is distinct from closed families:

- not Family A: it does not block weak acceptance using wick or outside-close thresholds;
- not Family B: it does not require a currently open accepted position and does not discard blocked signals from state;
- not Family C/D/E: it does not alter exits;
- the event memory includes probe signals that were deliberately not traded.

## Why this addresses the common failure event

The architecture directly targets the recurring sequence:

1. a range break occurs;
2. the first signal is recorded but not assumed to have continuation edge;
3. price must demonstrate directional follow-through;
4. only then is an F05 entry admitted;
5. the event has a finite age and a finite trade budget;
6. an opposite F05 signal terminates the old event and starts a new probe.

This prevents a mature or reversing move from producing multiple nominally independent entries without requiring a calendar-regime label.

## 2023 fallback data policy

If no Family F specification passes the complete 2024 H1/H2 development and cross-regime gates, the next diagnostic may use 2023 as an additional development/falsification period.

Tick data is not required for that first 2023 stage because the current architecture uses:

- M15 bar-close signals;
- next-M15-bar executable entry assumptions;
- fixed spread in research;
- fixed time-cap exits;
- no intrabar stop-loss, take-profit or trailing decision.

The preferred low-download path is:

1. obtain compressed M1 OHLC data for 2023;
2. derive M15 deterministically from M1;
3. build the signal/event atlas and screen finite specifications on bars;
4. reserve tick data for a later candidate only if the candidate introduces intrabar execution, variable-spread dependence, stop/target ordering or tick-equity requirements.

M15-only data can be used for the event-confirmation logic itself, but M1 is preferred because it preserves deterministic M15 construction, gap checks and a closer MT4 Model-0 bridge at modest download cost.

## Decision

Proceed to a finite, preregistered Family F search on 2024 H1. At most one exact specification may advance to 2024 H2. No 2025 period may be accessed during this search.