# USDJPY V1 Candidate-Specific 2024 H2 Validation Preregistration v1

## Decision

V1 applies the five accepted R6 complete strategies, unchanged, to the fixed 2024 H2 validation period in one joint run.

```text
validation start: 2024-07-01T00:00:00Z
validation end exclusive: 2025-01-01T00:00:00Z
frozen strategies: 5
Entry changes: prohibited
Exit changes: prohibited
time-cap changes: prohibited
H2 ranking: prohibited
parameter sweep in H2: prohibited
2025 access: prohibited
Core / MT4 promotion in V1: prohibited
```

Authoritative configuration:

```text
configs/research/usdjpy_v1_candidate_specific_h2_validation_v1.json
```

## Frozen strategies

| Freeze rank | Strategy | Family | Time cap |
|---:|---|---|---:|
| 1 | R1H04_ramom_32_64_z125__T0_fixed_time_cap | volatility_adjusted_momentum | 32 |
| 2 | R1B02_legacy_asia_00_07_breakout__T0_fixed_time_cap | session_range_breakout | 48 |
| 3 | R1E02_legacy_trend_8h_resumption__T0_fixed_time_cap | trend_pullback_resumption | 48 |
| 4 | R1F05_donchian_96__T0_fixed_time_cap | donchian_channel_breakout | 32 |
| 5 | R1E03_trend_12h_resumption__T0_fixed_time_cap | trend_pullback_resumption | 32 |

The previously opened complete strategies `A1_impulse_breakout_lb3_hold6` and `E3_trend_24h_resumption_hold6` are not inputs and cannot appear in the V1 cohort.

## Implementation regressions before H2 outcomes

The evaluator must first regenerate the five H1 Entry ledgers from the accepted R1 definitions and require exact equality to the accepted R1 signal keys, sides and definition hashes. It must also regenerate the five H1 fixed-time trades and require exact equality to the accepted R5 T0 timestamps, prices, costs and returns.

No H2 outcome is calculated unless every H1 regression passes.

## Execution and cost contract

- signal: completed M15 bar;
- Entry: next available M15 mid open;
- hard no-trade window: applied to the actual Entry timestamp with the accepted DST-aware session configuration;
- Exit: selected fixed-time-cap bar mid close;
- Entry and Exit must remain in the same UTC calendar month, matching the accepted R2/R5 domain;
- trades remain independent; no new netting or concurrency rule;
- default cost: `max(0.5, entry spread_mean_pips)`;
- severe cost: `default cost * 3 + 1`.

## Individual gates

Each strategy passes only if all are true:

```text
trades >= 60
average default net pips > 0
average severe net pips > 0
default PF > 1
severe PF > 1
default-positive months >= 4 of 6
severe-positive months >= 3 of 6
Q3 and Q4 both default-positive
Q3 and Q4 both severe-positive
total default pips excluding best two UTC Entry dates > 0
largest absolute month contribution share <= 0.60
top two UTC Entry dates share of positive daily pips <= 0.50
maximum absolute long/short contribution share <= 0.95
```

No H1 rank or portfolio result can rescue an individual failed gate.

## Reusable H2 policy

2024 H2 is the fixed reusable validation gate. If one or more strategies pass, only those unchanged strategies may proceed to Research/Core and MT4 parity. If all fail, this exact R6 branch closes and research returns to H1 for a new versioned and preregistered hypothesis or optimization branch; that new branch may be evaluated again on the same H2.

Every H2 exposure must be logged. There is no direct H2 parameter sweep and no ranking of H2 variants within a run. Because H2 is reusable, it is not represented as the final untouched holdout after repeated exposures. The final untouched period remains 2025, opened only after strategy freeze and Research/Core/MT4 parity.

## Required outputs

```text
h1_signal_regression.csv
h1_trade_regression.csv
h2_candidate_signals.csv.gz
h2_candidate_trades.csv.gz
h2_candidate_summary.csv
h2_candidate_monthly.csv
h2_candidate_quarterly.csv
h2_daily_net_pips.csv
h2_direction_attribution.csv
h2_gate_results.csv
h2_joint_portfolio_diagnostic.csv
h2_decision.json
v1_acceptance.json
run_metadata.json
```

## Acceptance

V1 is accepted only if the exact R0/R1/R5/R6 input digests match, all H1 implementation regressions pass, the five-strategy H2 cohort is unchanged, all output grids are complete, pass/fail equals the conjunction of the frozen individual gates, no H2 ranking or optimization occurs, and 2025/Core/MT4 remain closed.
