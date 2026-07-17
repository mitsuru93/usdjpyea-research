# USDJPY Multi-Family H1 Research Plan v1

## Decision

The project will not open the 2024-07 through 2024-12 validation block until all H1 development families have been evaluated and the surviving candidates have been pre-registered together.

Development period:

```text
2024-01-01 through 2024-06-30
```

Later untouched validation period:

```text
2024-07-01 through 2024-12-31
```

## Research sequence

```text
Step 3A: evaluate each family independently on H1
Step 3B: retain at most three representatives per family
Step 3C: pre-register all retained candidates and one common H2 gate
Step 3D: run all retained candidates on H2 in one batch
Step 4: compare surviving families
Step 5: consider cross-family combinations only after independent evidence exists
```

## Rules

1. Family definitions are evaluated independently.
2. No cross-family combination is permitted during H1 family screening.
3. Each family may retain zero to three candidates.
4. H1 is development evidence and cannot establish an EA.
5. H2 must not be opened until the candidate list and gates are committed.
6. The same Dukascopy bid/ask source-bar pipeline and cost convention are used across families.
7. The DST-aware hard no-trade configuration remains authoritative.
8. The low-liquidity New York 16:00-19:00 local window remains excluded.
9. No candidate may be rescued after H2 by changing its direction, threshold, hold, session, or exclusion dates.
10. Exit-policy optimization and Core/MT4 implementation remain blocked until a family passes H2.

## H1 families

### A. M15 impulse-confirmed breakout

Existing exact-source-confirmed candidate:

```text
close breaks the previous three completed M15 bars
and
signal-bar range > previous completed M15-bar range
entry: next M15 open
entry hours: UTC 13-16
hold: 6 M15 bars
```

This candidate is carried into the common comparison unchanged.

### B. Session range breakout

Mechanism:

A completed, widely observed session range may attract stop and momentum flow when price closes beyond it.

Development variants:

```text
B1: Asia UTC 00:00-06:00 range; first close breakout during UTC 07:00-12:00
B2: Asia UTC 00:00-07:00 range; first close breakout during UTC 07:00-12:00
B3: prior UTC day high/low; first close breakout during UTC 07:00-16:00
```

Entry is the next M15 open. Hold is six M15 bars. Only the first eligible breakout per direction per UTC day is retained.

### C. Mean reversion / failed excursion

Mechanism:

An intrabar excursion beyond a recent reference range that fails to close outside may indicate rejection rather than continuation.

Development variants:

```text
C1: breach previous 12-bar high/low and close back inside
C2: breach previous 24-bar high/low and close back inside
C3: breach Asia UTC 00:00-06:00 range and close back inside during UTC 07:00-16:00
```

Entry is the next M15 open in the reversal direction. Holds of three and six M15 bars are reported separately; they are treated as explicit candidates, not optimized exits.

### D. Compression to expansion

Mechanism:

A short-range contraction may store order imbalance that is released when price closes beyond the compressed range with immediate range expansion.

Development variants:

```text
D1: previous 4-bar range < preceding 4-bar range
D2: previous 8-bar range < preceding 8-bar range
```

The signal bar must close beyond the compressed range and have a larger range than the previous completed bar. Entry is the next M15 open and hold is six M15 bars.

### E. Higher-timeframe trend continuation

Mechanism:

A one-bar pullback may resume when a local M15 reversal agrees with the completed higher-timeframe direction.

Development variants:

```text
E1: prior 4-hour direction + one-bar pullback/resumption
E2: prior 8-hour direction + one-bar pullback/resumption
E3: prior 24-hour direction + one-bar pullback/resumption
```

Long definition: higher-timeframe return positive, previous M15 bar bearish, signal close above previous high.
Short definition: higher-timeframe return negative, previous M15 bar bullish, signal close below previous low.
Entry is the next M15 open and hold is six M15 bars.

## H1 reporting requirements

Every candidate must report:

- monthly trades, average net pips, total net pips and profit factor;
- Q1 and Q2 averages;
- long and short attribution;
- default and severe-cost results;
- official intervention-event sensitivity;
- result excluding the best two UTC days;
- minimum monthly trade count;
- source-bar coverage and duplicate handling.

## H1 retention screen

H1 retention does not mean validation. A candidate is eligible for joint pre-registration only when it meets all of the following development screens:

1. Positive aggregate default-cost average net pips.
2. Default-cost profit factor at least 1.10.
3. Positive average net pips in both Q1 and Q2.
4. At least four positive months out of six.
5. Positive aggregate total after excluding the best two UTC days.
6. Positive average after excluding 2024-04-29, 2024-05-01 and 2024-05-02.
7. Severe-stress profit factor at least 0.90.
8. At least 120 H1 trades in aggregate and at least 12 trades in every active calendar month.

If more than three candidates in one family pass, representatives are selected by robustness order:

```text
positive-month count
then event-excluded PF
then severe PF
then result excluding best two days
```

No new threshold may be introduced during representative selection.

## Immediate action

Run the H1 multi-family screening workflow on the original January-June Dukascopy M15 bars, including aggregate-repair bars from the canonical monthly baselines.

The output of that workflow will determine which candidates, if any, join the existing impulse-breakout candidate in the common H2 pre-registration.
