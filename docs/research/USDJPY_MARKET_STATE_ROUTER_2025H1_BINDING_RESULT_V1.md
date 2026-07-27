# USDJPY S3_H4_ALIGNED 2025H1 Binding Result

## Decision

**FAIL_2025H1_BINDING**

The one authorized candidate-specific 2025H1 scientific execution completed successfully on Rakuten MT4. This is not a technical stop. The result is final for the frozen `S3_H4_ALIGNED` candidate.

- Hypothesis: `USDJPY-HYP-029`
- Family: `T_MARKET_STATE_STRATEGY_ROUTING`
- Candidate: `S3_H4_ALIGNED`
- Research protocol commit: `a4074e8124c7c23d7bcb69a74a18b5edb29c3eab`
- Core preflight Run: `30283392068`
- Core binding Run: `30283492240`
- Core binding commit: `1df0c1ef154a4ac8a24e3d4f9f414f1fc9332dbf`
- Immutable Release: `usdjpy-s3-market-state-2025h1-binding-v1`
- Release asset: `usdjpy-s3-market-state-2025h1-30283492240-1.zip`
- Release asset SHA-256: `9961bbb2b19d9947d03ffd3446ec351ab3ebc458c3949f838d17bb354eee7865`

## Economic result

| Metric | Baseline | S3_H4_ALIGNED | Delta |
|---|---:|---:|---:|
| Opened trades | 463 | 271 | -192 |
| Net JPY | -20,808 | -11,947 | +8,861 |
| Profit factor | 0.829408 | 0.839947 | +0.010539 |
| Maximum tick-equity DD JPY | 42,737 | 23,593 | -19,144 |
| Minimum equity JPY | 57,328 | 77,170 | +19,842 |
| B02 net JPY | -6,964 | -6,525 | +439 |
| F05 net JPY | -13,844 | -5,422 | +8,422 |

The router materially compressed loss and drawdown. It reduced maximum tick-equity drawdown by approximately 44.8% and improved the portfolio result by JPY8,861. The improvement was overwhelmingly concentrated in F05 rather than B02.

However, the candidate remained negative at JPY-11,947 and its PF remained below 1.0. Risk reduction was therefore not sufficient to satisfy the positive-return binding gate.

## Period stability

| Entry period | Baseline JPY | Candidate JPY | Delta JPY |
|---|---:|---:|---:|
| 2025-01 | -14,024 | -5,576 | +8,448 |
| 2025-02 | +3,872 | +4,035 | +163 |
| 2025-03 | -18,879 | -13,518 | +5,361 |
| 2025-04 | -9,578 | -7,440 | +2,138 |
| 2025-05 | +15,313 | +9,359 | -5,954 |
| 2025-06 | +2,488 | +1,193 | -1,295 |
| 2025Q1 | -29,031 | -15,059 | +13,972 |
| 2025Q2 | +8,223 | +3,112 | -5,111 |

Four months improved, but May and June worsened. Q1 remained negative, while Q2 stayed positive but deteriorated versus baseline. The candidate therefore failed the requirement that both half-period deltas be positive and exceeded the maximum of one negative-effect month.

The total benefit was not dependent on only two dates: the total delta was JPY8,861 and remained JPY1,978 after removing the two largest positive entry-date deltas. Concentration was therefore not the failure mode.

## Blocked-trade economics

The candidate blocked 192 baseline trades.

- Avoided loss from blocked baseline losers: JPY47,331
- Sacrificed profit from blocked baseline winners: JPY38,470
- Benefit/harm ratio: 1.2303

This confirms that the H4 alignment mechanism removed more loss than profit in aggregate. It still sacrificed too much profitable Q2 exposure to create a positive full-period strategy.

## Router and execution integrity

Execution and trade identity were internally coherent:

- Baseline candidate-entry decisions: 463
- Allowed: 271
- Blocked/opposed: 192
- Missing router states: 0
- Data errors: 0
- Future-information uses: 0
- Duplicate decisions: 0
- Blocked trades that opened: 0
- Allowed trades not opened: 0
- Candidate opens without allow: 0
- Baseline reproduction: PASS
- Baseline/router entry identity: PASS
- Execution failures: 0
- Accounting reconciliation: PASS

The independent exact-H4 evaluator nevertheless recorded 128 mismatches. Samples include H4 EMA numeric differences exceeding the preregistered absolute tolerance of `1e-10`. Because the frozen protocol required zero mismatch across the independent router audit, `router_parity_zero_mismatch` failed. The tolerance cannot be relaxed after observing the candidate result.

## Failed gates

1. `candidate_net_positive`
2. `candidate_pf_at_least_1`
3. `january_to_march_net_nonnegative`
4. `both_half_period_deltas_positive`
5. `negative_effect_months_max_1`
6. `router_parity_zero_mismatch`

The candidate passed the remaining economic, drawdown, concentration, strategy-breadth, baseline reproduction, execution and accounting gates.

## Final interpretation

`S3_H4_ALIGNED` is a real **risk-compression mechanism**, but it is not a passing portable strategy permission rule for 2025H1. It reduced exposure and drawdown substantially, especially in F05, yet it did not convert the portfolio to positive economics and it damaged the profitable May-June regime. The independent numerical parity gate also failed under the preregistered tolerance.

Accordingly:

- `S3_H4_ALIGNED` is closed as `CLOSED_FAIL_2025H1_BINDING`.
- No parameter, side, strategy, session, neutral-state or period repair is permitted.
- No second candidate-specific 2025H1 scientific execution is permitted.
- 2025H2 remains locked and must not be accessed for this candidate.
- Production and live orders remain unauthorized.
- The loss/DD compression result may be retained only as prior causal evidence for a genuinely new, preregistered study.

## Exact next action

Continue the separately governed `USDJPY-HYP-027` Phase 2 sequence unchanged. Any successor market-state study must use a new Hypothesis ID and a genuinely distinct causal mechanism; it must not be a threshold, scope or exception repair of `S3_H4_ALIGNED` informed by the 2025 result.
