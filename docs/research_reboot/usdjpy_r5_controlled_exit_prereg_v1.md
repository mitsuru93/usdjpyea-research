# USDJPY R5 Controlled Exit Research Preregistration v1

## Decision

R5 applies exactly four common Exit policies to each of the eight frozen R4 Entry/horizon representatives on canonical 2024 H1.

```text
representatives: 8
policies: 4
representative/policy combinations: 32
Entry rows per policy: 2,982
total policy trade rows: 11,928
candidate-specific Exit parameters: prohibited
parameter sweep: prohibited
R5 selection or promotion: prohibited
H2 access: prohibited
2025 access: prohibited
Core promotion: false
MT4 promotion: false
```

R5 is a controlled mechanism comparison. It does not choose the final complete strategies. R6 selection and H2 gates must be separately preregistered after R5 is accepted.

Authoritative configuration:

```text
configs/research/usdjpy_r5_controlled_exit_v1.json
```

Authoritative evaluator:

```text
tools/run_usdjpy_r5_controlled_exit_v1.py
```

## Frozen representatives

| Rank | Candidate | Family | Time cap | Entry rows |
|---:|---|---|---:|---:|
| 1 | R1H04_ramom_32_64_z125 | volatility_adjusted_momentum | 32 | 146 |
| 2 | R1B02_legacy_asia_00_07_breakout | session_range_breakout | 48 | 97 |
| 3 | R1E02_legacy_trend_8h_resumption | trend_pullback_resumption | 48 | 366 |
| 4 | R1A04_impulse_lb24_med16_x125 | impulse_breakout | 48 | 739 |
| 5 | R1F05_donchian_96 | donchian_channel_breakout | 32 | 343 |
| 6 | R1E03_trend_12h_resumption | trend_pullback_resumption | 32 | 722 |
| 7 | R1H05_ramom_48_96_z125 | volatility_adjusted_momentum | 12 | 125 |
| 8 | R1F04_donchian_64 | donchian_channel_breakout | 24 | 444 |

The time caps are the R4-selected diagnostic horizons. They are retained as maximum holding limits for all R5 policies. R5 may exit earlier but may not extend a trade beyond its selected cap.

## Frozen Entry cohort

R5 reads the normalized R2 trade ledger and extracts only the eight exact R4 candidate/horizon pairs.

For all four policies:

- the Entry timestamp is unchanged;
- the side is unchanged;
- the Entry price is unchanged;
- the selected time-cap timestamp is unchanged;
- the default and severe cost fields are unchanged;
- no Entry is added, deleted or filtered;
- signal overlap, concurrency and netting are not changed.

The expected common Entry cohort is 2,982 rows. Each policy must contain exactly those 2,982 Entry keys, giving 11,928 policy-trade rows.

## ATR14 definition

ATR is calculated from canonical M15 midpoint OHLC bars.

True range is:

```text
max(
  mid_high - mid_low,
  abs(mid_high - previous mid_close),
  abs(mid_low - previous mid_close)
)
```

For the first canonical bar, true range is `mid_high - mid_low`.

Wilder ATR14 is initialized with the simple mean of the first fourteen true ranges. Subsequent values use:

```text
ATR[t] = (13 × ATR[t-1] + TR[t]) / 14
```

Static Entry distances use the ATR known at the completed signal bar, immediately before the actual next-bar Entry. A preflight based only on frozen inputs found ATR14 available for all 2,982 selected Entry rows; no Entry may therefore be removed for ATR warmup.

## Four fixed policies

### T0 — fixed time cap

```text
policy_id: T0_fixed_time_cap
Exit: selected time-cap bar midpoint close
```

T0 is the exact R2 baseline. It must reproduce all eight selected R2 ledgers by Entry timestamp, Exit timestamp, side, gross pips, default cost/net and severe cost/net.

### S1 — static two-ATR protective stop

```text
policy_id: S1_static_stop_2atr
long stop: Entry midpoint - 2.0 × Entry ATR14
short stop: Entry midpoint + 2.0 × Entry ATR14
profit target: none
maximum hold: selected time cap
```

This policy isolates the effect of a fixed volatility-scaled loss boundary without introducing a profit cap.

### B1 — fixed asymmetric ATR bracket

```text
policy_id: B1_bracket_1p5_3atr
long stop: Entry midpoint - 1.5 × Entry ATR14
long target: Entry midpoint + 3.0 × Entry ATR14
short stop: Entry midpoint + 1.5 × Entry ATR14
short target: Entry midpoint - 3.0 × Entry ATR14
maximum hold: selected time cap
```

The bracket fixes reward distance at twice the stop distance. The multipliers are mechanism probes selected before outcomes, not estimates of optimal USDJPY parameters.

### C1 — monotone three-ATR Chandelier trailing stop

```text
policy_id: C1_chandelier_3atr
initial long stop: Entry midpoint - 3.0 × signal-bar ATR14
initial short stop: Entry midpoint + 3.0 × signal-bar ATR14
maximum hold: selected time cap
```

For each later bar, the stop applied to that bar must be known before its open:

```text
long candidate stop:
  highest midpoint high through the prior completed bar
  minus 3.0 × ATR14 of the prior completed bar

short candidate stop:
  lowest midpoint low through the prior completed bar
  plus 3.0 × ATR14 of the prior completed bar
```

The operational stop is constrained never to loosen:

```text
long stop = max(previous stop, candidate stop)
short stop = min(previous stop, candidate stop)
```

The current bar high, low and ATR may update the stop only for the next bar. This prevents look-ahead.

The Chandelier mechanism is a volatility-scaled trailing stop attached to favorable price extremes. Its inclusion does not assert that the three-ATR parameter is optimal for USDJPY.

## Intrabar and gap semantics

R5 uses M15 midpoint open, high, low and close.

For each bar, a stop gap is checked at the midpoint open before high/low tests. A gap through a stop fills at the worse midpoint open rather than at the stop level.

A gap beyond a profit target fills at the target level; favorable gap improvement is not credited.

If both bracket stop and target lie within the same M15 bar, the stop is assumed to occur first. This adverse-first convention is deliberately conservative because intrabar ordering is unknown.

If no earlier Exit occurs, the trade exits at the selected time-cap bar midpoint close.

## Cost semantics

Gross PnL is calculated from midpoint Entry and Exit prices.

For each Entry row, R5 subtracts the exact R2 default and severe round-trip cost fields. No Exit-policy-specific spread model is introduced. Holding the cost model fixed isolates differences caused by Exit path logic rather than by a second cost-model change.

This does not establish that live stop or target fills will incur the same realized spread. Research/Core and MT4 execution parity remains a later gate.

## Reporting

Required complete grids:

```text
exit_summary.csv: 8 × 4 = 32 rows
exit_monthly.csv: 8 × 4 × 6 = 192 rows
exit_direction.csv: 8 × 4 × 2 = 64 rows
exit_reason.csv: 8 × 4 × 3 = 96 rows
baseline_regression.csv: 8 rows
```

Exit-reason categories are:

```text
time_cap
stop
target
```

`stop` includes static, bracket and Chandelier stops; the policy identifier preserves the mechanism.

Per-policy reporting includes at least:

- trades;
- win rate;
- average and total gross, default-net and severe-net pips;
- default and severe profit factor;
- median, 5th percentile and 95th percentile default-net pips;
- positive months and minimum monthly trades;
- average and median bars held;
- Exit-reason counts and shares;
- total excluding the best one and best two UTC Entry dates.

## Acceptance

R5 passes only if:

1. R0, R2 and R4 Release ZIP digests match;
2. canonical M15, R2 trade-ledger and R4 selected-representative digests match;
3. exactly eight frozen representatives are present;
4. the extracted R2 cohort contains exactly 2,982 rows;
5. each representative matches its preregistered Entry-row count;
6. ATR14 is available at every selected signal bar;
7. all four policies use identical Entry keys;
8. the policy ledger contains exactly 11,928 rows;
9. T0 reproduces all eight R2 selected ledgers exactly by Entry and Exit timestamp and within absolute tolerance `1e-9` for prices, costs and PnL;
10. all Exit timestamps are no later than the selected time cap;
11. all policy exits remain in the R2 same-UTC-month domain;
12. stop gaps use the worse midpoint open;
13. favorable target gaps are not credited;
14. same-bar bracket ambiguity uses adverse-first ordering;
15. Chandelier stops use only prior completed data and never loosen;
16. default and severe costs exactly equal the corresponding R2 Entry-row costs;
17. all 32 summary, 192 monthly, 64 direction and 96 reason rows are present;
18. the normalized gzip ledger is byte deterministic;
19. no policy is added, deleted or modified after results;
20. R5 emits no strategy selection or promotion;
21. H2 rows parsed equals zero;
22. 2025 access equals false;
23. Core promotion remains false;
24. MT4 promotion remains false.

## Interpretation boundary

R5 compares Exit mechanisms on the H1 development block. The best mean return, best profit factor or best Exit for one representative is not automatically selected.

R6 must separately preregister:

- common complete-strategy eligibility gates;
- treatment of candidate-specific versus common Exit policies;
- temporal and concentration requirements;
- maximum one complete strategy per underlying Entry definition;
- maximum five complete strategies overall;
- the candidate-specific unused H2 validation gates.

No H2, 2025, Core or MT4 work may begin before R6 is frozen and accepted.

## Methodological sources

Kaminski and Lo, “When Do Stop-Loss Rules Stop Losses?”, *Journal of Financial Markets* 18 (2014), 234–254, DOI `10.1016/j.finmar.2013.07.001`, provides the general motivation for treating stop-loss rules as strategy-dependent mechanisms rather than assuming that stops universally improve results.

The Chandelier Exit is the established ATR-from-favorable-extreme trailing-stop construction associated with Charles Le Beau and later popularized by Alexander Elder. R5 uses a preregistered, no-look-ahead implementation and does not infer optimality from its conventional parameterization.
