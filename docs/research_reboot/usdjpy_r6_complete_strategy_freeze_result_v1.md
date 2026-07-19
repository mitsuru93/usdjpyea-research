# USDJPY R6 Complete-Strategy Freeze Result v1

## Decision

```text
R6: PASS
audited complete strategies: 32
fully eligible complete strategies: 9
frozen complete strategies: 5
eligible pairwise comparisons: 36
H2 rows parsed: 0
2025 access: none
Core promotion: false
MT4 promotion: false
```

## Accepted run

```text
run_id: 29672853145
workflow_head_sha: 23e0933182aa43b3fa6f9f83611a8a0213ddeb19
evaluator_lock_commit: 7cdbf84ae2da1eaf05cc3b901727b8e284f8fe93
artifact_id: 8437864148
artifact: usdjpy-r6-complete-strategy-freeze-v1-29672853145
artifact_digest: sha256:e15d63fb0fcebf18f623e10852548420ec21affef459de1f8912a78e16d02320
release_tag: usdjpy-r6-complete-strategy-freeze-v1
```

## Frozen complete strategies

| Freeze rank | H1 eligible rank | Strategy | Family | Time cap | Trades | Avg severe pips | Severe PF |
|---:|---:|---|---|---:|---:|---:|---:|
| 1 | 1 | R1H04_ramom_32_64_z125__T0_fixed_time_cap | volatility_adjusted_momentum | 32 | 146 | +10.731084 | 1.863500 |
| 2 | 2 | R1B02_legacy_asia_00_07_breakout__T0_fixed_time_cap | session_range_breakout | 48 | 97 | +7.780860 | 1.536142 |
| 3 | 3 | R1E02_legacy_trend_8h_resumption__T0_fixed_time_cap | trend_pullback_resumption | 48 | 366 | +4.282925 | 1.254909 |
| 4 | 5 | R1F05_donchian_96__T0_fixed_time_cap | donchian_channel_breakout | 32 | 343 | +2.329856 | 1.154176 |
| 5 | 6 | R1E03_trend_12h_resumption__T0_fixed_time_cap | trend_pullback_resumption | 32 | 722 | +2.736377 | 1.198722 |

All five use the accepted R5 fixed-time-cap policy. The fourth eligible combination was an alternative Exit for the same R1H04 Entry definition and was skipped by the one-definition cap. The freeze stopped at five; lower-ranked eligible strategies were not substituted.

## Validation handling

The five frozen strategies enter one joint candidate-specific unused 2024 H2 validation with Entry, Exit and time cap unchanged. Each strategy passes or fails independently; H2 reranking and rescue changes are prohibited.

If every strategy fails, this R6 branch closes and research returns to H1 for a new preregistered hypothesis or optimization branch. The same 2024 H2 remains the fixed validation gate for the new branch; detailed H2 outcomes may not be used to modify or rescue a failed strategy. 2025 remains unopened.

R6 did not parse H2, access 2025, reselect R4 representatives, modify R5 policies, or promote any strategy to Core or MT4.
