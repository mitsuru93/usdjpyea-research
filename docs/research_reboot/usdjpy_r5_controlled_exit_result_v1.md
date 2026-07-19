# USDJPY R5 Controlled Exit Research Result v1

## Decision

```text
R5: PASS
strategy selection: none
H2 rows parsed: 0
2025 access: none
Core promotion: false
MT4 promotion: false
```

## Accepted run

```text
run_id: 29666989206
evaluator_lock_commit: 1e4b27aab1f7b1cda51a902da26f4d3080cda8ad
formal_workflow_commit: 63c8bcbfa9f7584354c4e84f20bf865c6a828162
artifact_id: 8436023286
artifact: usdjpy-r5-controlled-exit-v1-29666989206
artifact_digest: sha256:0f0238a509c4bd6dc9bbe43c941001b7d2c54c66ba07b48f0aa9343f6c4a05cb
release_tag: usdjpy-r5-controlled-exit-v1
```

## Complete comparison

```text
representatives: 8
policies: 4
representative/policy combinations: 32
policy trade rows: 11,928
T0 exact R2 regressions: 8 / 8
policy Entry-set regressions: 32 / 32
same-bar bracket ambiguities: 18
stop-gap exits: 73
target-gap exits: 0
```

## Descriptive result

The fixed time-cap baseline had the highest average default-cost return for 8 of eight representatives and the highest average severe-cost return for 8 of eight.

This is not an R5 selection decision. R6 common complete-strategy gates must be preregistered before any Entry/Exit pair is selected.

| R4 rank | Candidate | Policy | Trades | Avg default | Avg severe | Default PF | Severe PF | Positive months | Ex-best-two-days | Avg bars |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | R1H04_ramom_32_64_z125 | B1_bracket_1p5_3atr | 146 | +4.003820 | +1.860844 | 1.443325 | 1.180990 | 6 | +241.646 | 10.548 |
| 1 | R1H04_ramom_32_64_z125 | C1_chandelier_3atr | 146 | +1.952523 | -0.190453 | 1.182533 | 0.984104 | 2 | -184.194 | 17.007 |
| 1 | R1H04_ramom_32_64_z125 | S1_static_stop_2atr | 146 | +9.669504 | +7.526528 | 1.912792 | 1.638899 | 6 | +621.754 | 20.842 |
| 1 | R1H04_ramom_32_64_z125 | T0_fixed_time_cap | 146 | +12.874060 | +10.731084 | 2.120088 | 1.863500 | 6 | +1021.405 | 32.000 |
| 2 | R1B02_legacy_asia_00_07_breakout | B1_bracket_1p5_3atr | 97 | +2.728205 | +0.589672 | 1.350656 | 1.064813 | 4 | +153.366 | 10.227 |
| 2 | R1B02_legacy_asia_00_07_breakout | C1_chandelier_3atr | 97 | +1.021839 | -1.116694 | 1.112031 | 0.893515 | 3 | -134.681 | 17.907 |
| 2 | R1B02_legacy_asia_00_07_breakout | S1_static_stop_2atr | 97 | +5.889232 | +3.750699 | 1.523357 | 1.294786 | 5 | +247.207 | 24.021 |
| 2 | R1B02_legacy_asia_00_07_breakout | T0_fixed_time_cap | 97 | +9.919393 | +7.780860 | 1.729683 | 1.536142 | 6 | +638.133 | 48.000 |
| 3 | R1E02_legacy_trend_8h_resumption | B1_bracket_1p5_3atr | 366 | -1.316383 | -3.454815 | 0.869587 | 0.699144 | 1 | -913.768 | 12.656 |
| 3 | R1E02_legacy_trend_8h_resumption | C1_chandelier_3atr | 366 | -2.187082 | -4.325514 | 0.802229 | 0.653431 | 2 | -1322.085 | 17.836 |
| 3 | R1E02_legacy_trend_8h_resumption | S1_static_stop_2atr | 366 | +2.255823 | +0.117391 | 1.169627 | 1.007936 | 4 | -35.992 | 26.279 |
| 3 | R1E02_legacy_trend_8h_resumption | T0_fixed_time_cap | 366 | +6.421358 | +4.282925 | 1.407761 | 1.254909 | 6 | +1147.010 | 48.000 |
| 4 | R1A04_impulse_lb24_med16_x125 | B1_bracket_1p5_3atr | 739 | -0.789212 | -3.008285 | 0.920841 | 0.737254 | 3 | -1281.813 | 10.735 |
| 4 | R1A04_impulse_lb24_med16_x125 | C1_chandelier_3atr | 739 | -0.668593 | -2.887666 | 0.936065 | 0.757720 | 3 | -1727.196 | 17.714 |
| 4 | R1A04_impulse_lb24_med16_x125 | S1_static_stop_2atr | 739 | +1.920669 | -0.298403 | 1.146662 | 0.979612 | 5 | -177.829 | 24.992 |
| 4 | R1A04_impulse_lb24_med16_x125 | T0_fixed_time_cap | 739 | +5.098650 | +2.879578 | 1.284906 | 1.151733 | 4 | +1777.549 | 48.000 |
| 5 | R1F05_donchian_96 | B1_bracket_1p5_3atr | 343 | -0.479414 | -2.683319 | 0.948833 | 0.750741 | 3 | -473.207 | 10.924 |
| 5 | R1F05_donchian_96 | C1_chandelier_3atr | 343 | -1.160463 | -3.364368 | 0.891574 | 0.723472 | 3 | -1051.243 | 17.114 |
| 5 | R1F05_donchian_96 | S1_static_stop_2atr | 343 | +0.822447 | -1.381458 | 1.067221 | 0.898940 | 4 | -520.722 | 19.668 |
| 5 | R1F05_donchian_96 | T0_fixed_time_cap | 343 | +4.533761 | +2.329856 | 1.322515 | 1.154176 | 5 | +419.548 | 32.000 |
| 6 | R1E03_trend_12h_resumption | B1_bracket_1p5_3atr | 722 | -1.116134 | -3.283896 | 0.879196 | 0.691556 | 1 | -1366.604 | 12.342 |
| 6 | R1E03_trend_12h_resumption | C1_chandelier_3atr | 722 | -0.087848 | -2.255609 | 0.990937 | 0.797320 | 4 | -839.668 | 17.443 |
| 6 | R1E03_trend_12h_resumption | S1_static_stop_2atr | 722 | +1.514698 | -0.653064 | 1.133405 | 0.948891 | 4 | +111.771 | 20.569 |
| 6 | R1E03_trend_12h_resumption | T0_fixed_time_cap | 722 | +4.904139 | +2.736377 | 1.387020 | 1.198722 | 5 | +2234.625 | 32.000 |
| 7 | R1H05_ramom_48_96_z125 | B1_bracket_1p5_3atr | 125 | -1.546668 | -3.733785 | 0.827348 | 0.637935 | 2 | -368.515 | 7.160 |
| 7 | R1H05_ramom_48_96_z125 | C1_chandelier_3atr | 125 | -1.075223 | -3.262340 | 0.873594 | 0.668355 | 3 | -347.169 | 9.832 |
| 7 | R1H05_ramom_48_96_z125 | S1_static_stop_2atr | 125 | -0.464676 | -2.651793 | 0.948790 | 0.745052 | 3 | -282.369 | 9.584 |
| 7 | R1H05_ramom_48_96_z125 | T0_fixed_time_cap | 125 | +3.973241 | +1.786124 | 1.555793 | 1.215066 | 4 | +154.885 | 12.000 |
| 8 | R1F04_donchian_64 | B1_bracket_1p5_3atr | 444 | -1.489332 | -3.691850 | 0.838302 | 0.653331 | 3 | -971.050 | 10.126 |
| 8 | R1F04_donchian_64 | C1_chandelier_3atr | 444 | -1.589451 | -3.791969 | 0.843936 | 0.673586 | 3 | -1315.891 | 15.387 |
| 8 | R1F04_donchian_64 | S1_static_stop_2atr | 444 | -0.527074 | -2.729592 | 0.952000 | 0.779934 | 4 | -724.392 | 16.432 |
| 8 | R1F04_donchian_64 | T0_fixed_time_cap | 444 | +2.996601 | +0.794083 | 1.256922 | 1.062023 | 5 | +499.047 | 24.000 |

R5 compared the four frozen mechanisms only. It did not tune parameters, reselect R4 representatives, access H2 or 2025, or promote any strategy.
