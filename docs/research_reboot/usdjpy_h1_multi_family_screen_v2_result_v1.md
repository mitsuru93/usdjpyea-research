# USDJPY H1 Multi-Family Screen v2 Result

## Run

```text
workflow: Run USDJPY H1 Multi-Family Screen
run_id: 29547232643
head_sha: a1a96ca0808f31b508b6ee82da345949725acc30
artifact: usdjpy-h1-multi-family-screen-v2-29547232643
artifact_digest: sha256:b5fd40e7c37cd3c4c417b9e02547ce6d7195f0f989266e4f0e3ae0305947ec94
```

All workflow steps completed successfully. The A1 canonical reproduction assertion also passed:

```text
trades: 391
total_net_pips: 788.2165005892261
avg_net_pips: 2.0158989784890693
profit_factor: 1.2805773608918685
```

The corrected v2 artifact is the authoritative H1 multi-family screening result. Run 29546116205 remains invalid and must not be used for research decisions.

## Data coverage

| Month | M15 rows | First bar | Last bar |
|---|---:|---|---|
| 2024-01 | 2,080 | 2024-01-02 00:00 UTC | 2024-01-31 23:45 UTC |
| 2024-02 | 1,984 | 2024-02-01 00:00 UTC | 2024-02-29 23:45 UTC |
| 2024-03 | 1,964 | 2024-03-01 00:00 UTC | 2024-03-29 20:45 UTC |
| 2024-04 | 2,064 | 2024-04-01 00:00 UTC | 2024-04-30 23:45 UTC |
| 2024-05 | 2,148 | 2024-05-01 00:00 UTC | 2024-05-31 20:45 UTC |
| 2024-06 | 1,872 | 2024-06-03 00:00 UTC | 2024-06-28 20:45 UTC |

Aggregate-repair bars from the canonical monthly baselines were included. No duplicate M15 timestamps remained after loading.

## H1 retention result

Two candidates passed every predeclared H1 retention condition.

### A1 — M15 impulse-confirmed breakout

```text
candidate_id: A1_impulse_breakout_lb3_hold6
trades: 391
positive_months: 4 / 6
minimum_monthly_trades: 55
avg_net_pips: +2.015899
total_net_pips: +788.216501
profit_factor: 1.280577
Q1_avg_net_pips: +2.628028
Q2_avg_net_pips: +1.327254
severe_avg_net_pips: -0.153070
severe_profit_factor: 0.981540
event_excluded_avg_net_pips: +1.458025
event_excluded_profit_factor: 1.203591
total_excluding_best_two_days: +251.580550
```

Monthly default-cost averages:

| Month | Trades | Avg net pips | PF |
|---|---:|---:|---:|
| 2024-01 | 73 | +5.479 | 1.510 |
| 2024-02 | 79 | +3.373 | 1.489 |
| 2024-03 | 55 | -2.227 | 0.622 |
| 2024-04 | 63 | +3.955 | 1.795 |
| 2024-05 | 66 | +0.535 | 1.080 |
| 2024-06 | 55 | -0.732 | 0.900 |

Direction attribution is diagnostic only:

```text
long: 216 trades, +3.734 pips/trade, +806.629 total
short: 175 trades, -0.105 pips/trade, -18.412 total
```

The H2 candidate remains two-sided.

### E3 — 96-bar trend resumption

```text
candidate_id: E3_trend_24h_resumption_hold6
trades: 361
positive_months: 4 / 6
minimum_monthly_trades: 49
avg_net_pips: +1.783355
total_net_pips: +643.791082
profit_factor: 1.305343
Q1_avg_net_pips: +0.816226
Q2_avg_net_pips: +2.724059
severe_avg_net_pips: -0.351598
severe_profit_factor: 0.949636
event_excluded_avg_net_pips: +1.449472
event_excluded_profit_factor: 1.246307
total_excluding_best_two_days: +394.000132
```

Monthly default-cost averages:

| Month | Trades | Avg net pips | PF |
|---|---:|---:|---:|
| 2024-01 | 63 | +4.940 | 1.677 |
| 2024-02 | 49 | -0.464 | 0.920 |
| 2024-03 | 66 | -2.170 | 0.736 |
| 2024-04 | 56 | +3.455 | 1.808 |
| 2024-05 | 65 | +1.579 | 1.341 |
| 2024-06 | 62 | +3.264 | 1.715 |

Direction attribution is diagnostic only:

```text
long: 223 trades, +3.991 pips/trade, +889.942 total
short: 138 trades, -1.784 pips/trade, -246.151 total
```

The H2 candidate remains two-sided.

A1 and E3 share 61 identical entry-timestamp/direction rows, equal to 15.6% of A1 trades and 16.9% of E3 trades. Their H1 daily net-pips correlation is 0.361. They are not treated as duplicates.

## Candidate excluded only by sample-size gate

### B3 — prior UTC-day high/low breakout

B3 met every performance and robustness condition but did not reach the predeclared aggregate sample requirement.

```text
trades: 94
required: 120
minimum_monthly_trades: 12
avg_net_pips: +2.377876
profit_factor: 1.336151
positive_months: 4 / 6
Q1_avg_net_pips: +3.371019
Q2_avg_net_pips: +1.296455
severe_avg_net_pips: +0.212353
severe_profit_factor: 1.025971
event_excluded_profit_factor: 1.337945
total_excluding_best_two_days: +122.332704
```

B3 is not promoted. Lowering the 120-trade condition after opening the H1 result is prohibited. It may be recorded as a diagnostic near-miss but is excluded from the joint H2 candidate set.

## Other family decisions

```text
Session range breakout:
  B1 rejected
  B2 rejected
  B3 excluded by aggregate sample gate

Mean reversion / failed excursion:
  C1 rejected
  C2 rejected
  C3 rejected
  C4 rejected

Compression to expansion:
  D1 rejected
  D2 rejected

Higher-timeframe trend continuation:
  E1 rejected
  E2 rejected
  E3 promoted
```

C4 produced positive aggregate default-cost results but failed Q1 and severe-stress requirements. C3 failed Q2, concentration and severe-stress requirements. Neither is promoted.

## Step decision

```text
Step 3A: complete
Step 3B: complete

Retained candidates:
  A1_impulse_breakout_lb3_hold6
  E3_trend_24h_resumption_hold6

Next:
  Step 3C — commit one joint H2 pre-registration and common gate
```

No 2024-07 through 2024-12 candidate result may be opened until that joint pre-registration is committed.