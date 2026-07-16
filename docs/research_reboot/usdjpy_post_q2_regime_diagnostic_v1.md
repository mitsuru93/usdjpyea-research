# USDJPY Post-Q2 Regime Diagnostic v1

## Purpose

The Q1-retained M5 pullback family and the M15 breakout watchlist family both failed their pre-registered Q2 monthly-replication gate.

The next step is attribution, not retuning.

This diagnostic must answer why Q1 and Q2 differ before a new strategy family or regime condition is proposed.

## Fixed candidates

No parameter search is allowed in this phase.

### Candidate A

```text
name: m5_pullback_strict
timeframe: M5
session: UTC 13-16
family: pullback_continuation
pullback_min_pips: 2
trend_lookback_bars: 12
trend_min_pips: 10
hold_bars: 6
```

### Candidate B

```text
name: m15_breakout_lb3
timeframe: M15
session: UTC 13-16
family: breakout_close_followthrough
lookback_bars: 3
hold_bars: 6
```

## Canonical sample

```text
2024-01 through 2024-06
```

Canonical baseline run IDs:

```text
2024-01: 29307131333
2024-02: 29383810487
2024-03: 29421329471
2024-04: 29455059447
2024-05: 29469227483
2024-06: 29475803893
```

## Required outputs

The fixed-family diagnostic tool must produce:

1. Monthly results.
2. Daily results.
3. Long/short results.
4. Official-intervention sensitivity.
5. Configuration metadata proving that parameters were not changed.

Tool:

```text
tools/analyze_usdjpy_h1_fixed_family_diagnostics.py
```

Official-event registry:

```text
configs/market_events/usdjpy_official_interventions_2024.csv
```

## Intervention interpretation

Official Ministry of Finance operation dates are retrospective labels.

They must not be promoted directly into a live no-trade rule because:

1. Confirmation is published after the event.
2. The official operation date is not an exact UTC interval.
3. The second 2024 intervention shock appears around the following UTC/JST calendar date in market data.

Intervention labels are used only to measure event dependence.

## Diagnostic questions

### D1: Monthly replication

For each fixed candidate:

- How many positive months are there?
- Is performance concentrated in Q1 or Q2?
- Does H1 aggregate performance conceal a regime break?

### D2: Direction dependence

For each month:

- Long total and average net pips.
- Short total and average net pips.
- Whether failure is one-sided or bilateral.

A direction filter must not be proposed solely because one observed month had an asymmetric failure.

### D3: Daily concentration

For each month:

- Positive and negative active days.
- Best and worst day.
- Result excluding the best day.
- Result excluding the worst day.
- Top-one-day and top-two-day share of total positive contribution.

### D4: Intervention sensitivity

For M15 breakout in particular:

- Result including all dates.
- Result excluding exact MOF operation dates.
- Result excluding the dates associated with the observed UTC market shocks.

If the result changes sign, the family is event-dependent and cannot be treated as a normal-regime edge.

### D5: Market-state attribution

A second-stage diagnostic may join source M5/M15 bars and calculate descriptive fields:

- prior-session realized range;
- primary-session realized range;
- directional efficiency ratio;
- spread/range ratio;
- pre-entry trend magnitude;
- prior-bar and prior-hour shock size.

This stage is descriptive only. Threshold selection is prohibited in the H1 sample.

## Promotion rule for a new hypothesis

A new family or explicit regime condition may be proposed only after the diagnostics identify a mechanism that:

1. appears in multiple months;
2. is not explained by one intervention episode or one extreme day;
3. is defined without selecting a profitable threshold from H1;
4. can be tested on an untouched later period;
5. preserves the DST-aware hard no-trade window.

## Untouched test period

The H1 2024 data are now diagnostic/development data.

The next promoted hypothesis must be tested on a later untouched block. The test block must be selected and recorded before its results are opened.

No exit-policy optimization or EA implementation begins before a new entry/regime hypothesis passes its own out-of-sample gate.
