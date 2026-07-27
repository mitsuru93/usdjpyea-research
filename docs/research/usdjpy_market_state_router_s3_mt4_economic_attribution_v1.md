# USDJPY Market-State Router S3_H4_ALIGNED — MT4 Economic Attribution v1

## Final decision

`PASS_ECONOMIC_ATTRIBUTION_ACCOUNTING_ERROR_REPAIRED`

Final immutable Release content readback: `PASS_FINAL_RELEASE_CONTENT_READBACK`.

Native full-equity DD reconciliation: `PASS_PREPERIOD_PEAK_CONTAMINATION_RESOLVED_BOUNDED_DD_NONWORSE`.

The frozen `S3_H4_ALIGNED` router produced economically favorable results in both the binding 1,882-trade MT4 replay and the native regenerated B02/F05 order path. Ticket accounting reconciled to final balance with no unexplained account-currency residual. Bounded 2023–2024 native full-equity DD improved in the pooled interval and in every half-year fold.

## Required accounting correction

The effective Strategy Tester account currency was **USD**, not JPY. The earlier controlled-integration labels `balance_net_jpy` and `max_equity_dd_jpy` are superseded as currency labels. Those values were account-currency numbers and must be read as USD.

The audit distinguishes:

- Research counterfactual P/L in quote currency JPY.
- MT4 gross price P/L in quote currency JPY.
- MT4 `OrderProfit`, swap, commission, balance, and equity in account currency USD.

Observed commission and swap were zero in all four paths. The unexplained final-balance residual was exactly zero.

## Native order-path result

The native population is an integration diagnostic and does not replace the binding Research identity population.

| Metric | Baseline | S3 candidate | Delta |
|---|---:|---:|---:|
| Trades | 1,898 | 1,222 | 676 blocked |
| Net account P/L | $317.00 | $496.78 | **+$179.78** |
| Profit factor | 1.121774 | 1.311332 | **+0.189558** |
| Closed-trade MDD | $296.11 | $195.06 | **−$101.05** |
| Bounded 2023–2024 full-equity MDD | $311.87 | $201.70 | **−$110.17 / −35.33%** |
| Gross quote-currency P/L | ¥51,408 | ¥76,391 | **+¥24,983** |

## Binding 1,882-trade result

| Metric | Baseline | S3 candidate | Delta |
|---|---:|---:|---:|
| Trades | 1,882 | 1,211 | 671 blocked |
| Net account P/L | $294.56 | $467.24 | **+$172.68** |
| Profit factor | 1.113796 | 1.294391 | **+0.180596** |
| Closed-trade MDD | $296.11 | $195.06 | **−$101.05** |
| Gross quote-currency P/L | ¥48,203 | ¥72,081 | **+¥23,878** |

Research counterfactual delta was `+¥22,687`. The binding MT4 gross delta was `+¥23,878`, a difference of `+¥1,191` in the same quote-currency unit.

## Population identity bridge

- Research identities: 1,882
- Native regenerated identities: 1,898
- Research-only missing-native: 9
- Native-only extra: 25
- Total nonmatching identities: 34

The binding replay remains the scientific identity authority. Native results demonstrate that the integrated order path preserves the same favorable direction without replacing the frozen population.

## Native full-equity DD reconciliation

The legacy unbounded equity-snapshot calculation reproduced an apparent worsening:

- Baseline: `$615.74`
- Candidate: `$687.48`
- Peak timestamp: `2021-06-04T07:33:59Z`

Each population contained exactly one pre-2023 authority snapshot. That row contaminated a calculation intended to represent 2023–2024.

The preregistered bounded interval was `[2023-01-01T00:00:00Z, 2025-01-01T00:00:00Z)`. Each population contributed 49,163 in-window snapshots, with zero rows at or after 2025 and zero duplicate observation timestamps.

### Pooled 2023–2024 full-equity DD

| Metric | Baseline | S3 candidate | Delta |
|---|---:|---:|---:|
| Full-equity MDD | $311.87 | $201.70 | **−$110.17 / −35.33%** |
| Peak | 2023-01-05 15:30 UTC | 2023-01-13 16:00 UTC | — |
| Trough | 2023-10-26 13:45 UTC | 2023-10-30 11:45 UTC | — |
| Recovery | 2024-03-19 09:45 UTC | 2024-01-03 15:30 UTC | candidate recovered earlier |
| Balance-path DD contribution | $278.67 | $188.91 | −$89.76 |
| Floating-path DD contribution | $33.20 | $12.79 | −$20.41 |

The decomposition identity residual was `$0.00` for both paths.

### Half-year breadth

| Window | Baseline MDD | Candidate MDD | Delta |
|---|---:|---:|---:|
| 2023H1 | $256.03 | $198.06 | −22.64% |
| 2023H2 | $182.36 | $131.75 | −27.75% |
| 2024H1 | $67.17 | $57.86 | −13.86% |
| 2024H2 | $124.62 | $96.59 | −22.49% |

The candidate was non-worse in every half-year window.

## Evidence authority

Economic attribution:

- Core source Run: `30256893465`
- Core source SHA: `2deb131bdda3dd13d0b5b69d0c80967235fb3e66`
- Final Release content readback Run: `30259858011`
- Core source PASS Issue: `mitsuru93/usdjpyea-core#368`
- Core final content readback Issue: `mitsuru93/usdjpyea-core#377`
- Core canonical correction Issue: `mitsuru93/usdjpyea-core#379`
- Release: `usdjpy-market-state-router-s3-economic-attribution-v1`
- Archive SHA-256: `40cdd1f8c6e7984e500a79ce430e697c3c33d31c6c4d8daa30e6ad6a5bb7062b`

Native full-equity DD reconciliation:

- Research protocol SHA: `f6ab7cdbfb51cd46bbc4c02c2a2be7be6ee60a8b`
- Core Run: `30261603069`
- Core execution SHA: `64db8dbdb697e500d449936c004830992b081c8f`
- Core Issue: `mitsuru93/usdjpyea-core#395`
- Release: `usdjpy-s3-native-equity-dd-reconciliation-v1`
- Release target: `b3cc4faa4c83e6a3c00df0fec8262b7d9290f7e1`
- Archive SHA-256: `8896d464935eccaba551847de3a332d5d744f3d1e42d1e0d7b7851af9a83fa72`

Machine-readable Research receipt:

`configs/research/usdjpy_market_state_router_s3_mt4_economic_attribution_receipt_v1.json`

Core canonical receipt:

`docs/research/market_state_router_s3_h4_aligned_mt4_economic_attribution_v1/final_receipt.json`

## Authorization boundary

- Candidate definition changed: false
- Parameter change: false
- 2025H1 accessed: false
- 2025H2 accessed: false
- 2025 gate authorized: false
- Production authorized: false
- Live orders authorized: false

A separate outcome-free authorization decision is required before any 2025 out-of-sample execution.
