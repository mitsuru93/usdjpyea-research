# USDJPY Shock Failure 2025 External-Gate Failure Postmortem v1

## Boundary

Candidate `B_EXECUTABLE_T0_8BAR` was not changed. No direction, session, month, threshold, median length, failure rule, entry timing, timeout or exit was selected. Oracle diagnostics are labelled `ORACLE_DIAGNOSTIC_NOT_IMPLEMENTABLE_CANDIDATE` and are not implementation candidates.

## Authority

- Research SHA: `e695895089f58358c4a5fa561609ef9f527258c4`
- Core SHA: `e92ac28d908cb5c6ca89224507b24690822e0f35`
- P6 Run: `30229496015`
- Original artifact: `8639969385`, SHA-256 `70088c66cd1014391cabbb6f533462dcd3dbedbd7d6c537a5dc0798343594a6a`
- Corrected evidence status: `FAIL_P6_2025_GATE_RESEARCH_ONLY_NO_RETUNING`

## Evidence repair

The integrated Shock audit omitted a duplicate `account_contract` row. The original evaluator raised before writing the P6 JSON. Packaging was repaired by reading the same integrated test's base-audit contract. Logs, outcomes, periods, gates, formulas and MT4 code were unchanged.

## Fold metrics

|   trades |   net |       pf |   win_rate |   median |   gross_profit |   gross_loss |   mdd |   mean_mfe_pips |   mean_mae_pips |   profit_then_giveback_rate |   immediate_failure_rate |   timeout_truncation_rate |   positive_months | fold   |
|---------:|------:|---------:|-----------:|---------:|---------------:|-------------:|------:|----------------:|----------------:|----------------------------:|-------------------------:|--------------------------:|------------------:|:-------|
|       21 |  2776 | 2.58992  |   0.666667 |     55   |           4522 |        -1746 |   807 |         33.8286 |        -21.6143 |                    0.238095 |                0         |                         0 |                 5 | 2023H1 |
|       35 |  -662 | 0.792151 |   0.485714 |    -15   |           2523 |        -3185 |  1360 |         19.5371 |        -19.7686 |                    0.257143 |                0         |                         0 |                 2 | 2023H2 |
|       30 |  2153 | 2.84332  |   0.666667 |     70.5 |           3321 |        -1168 |   184 |         20.16   |        -18.27   |                    0.3      |                0.0333333 |                         0 |                 5 | 2024H1 |
|       28 |  8235 | 3.78586  |   0.714286 |    103.5 |          11191 |        -2956 |  1232 |         53.8071 |        -23.8214 |                    0.214286 |                0.0357143 |                         0 |                 5 | 2024H2 |
|       17 |  -280 | 0.902812 |   0.352941 |    -74   |           2601 |        -2881 |  2284 |         29.9471 |        -30.8353 |                    0.117647 |                0         |                         0 |                 3 | 2025H1 |
|       30 |  -997 | 0.708224 |   0.433333 |    -24.5 |           2420 |        -3417 |  1487 |         17.72   |        -21.4767 |                    0.333333 |                0         |                         0 |                 2 | 2025H2 |

## 2025 side metrics

|   trades |   net |       pf |   win_rate |   median |   gross_profit |   gross_loss |   mdd |   mean_mfe_pips |   mean_mae_pips |   profit_then_giveback_rate |   immediate_failure_rate |   timeout_truncation_rate |   positive_months | fold   | side_label   |
|---------:|------:|---------:|-----------:|---------:|---------------:|-------------:|------:|----------------:|----------------:|----------------------------:|-------------------------:|--------------------------:|------------------:|:-------|:-------------|
|       11 |    82 | 1.05381  |   0.363636 |    -89   |           1606 |        -1524 |  1387 |         31.4455 |        -27.0818 |                    0.181818 |                        0 |                         0 |                 2 | 2025H1 | LONG         |
|        6 |  -362 | 0.733235 |   0.333333 |    -60.5 |            995 |        -1357 |  1141 |         27.2    |        -37.7167 |                    0        |                        0 |                         0 |                 1 | 2025H1 | SHORT        |
|       13 |    16 | 1.01752  |   0.307692 |    -39   |            929 |         -913 |   429 |         18.7231 |        -17.1231 |                    0.230769 |                        0 |                         0 |                 2 | 2025H2 | LONG         |
|       17 | -1013 | 0.595447 |   0.529412 |     12   |           1491 |        -2504 |  1127 |         16.9529 |        -24.8059 |                    0.411765 |                        0 |                         0 |                 3 | 2025H2 | SHORT        |

## 2025 session metrics

|   trades |   net |        pf |   win_rate |   median |   gross_profit |   gross_loss |   mdd |   mean_mfe_pips |   mean_mae_pips |   profit_then_giveback_rate |   immediate_failure_rate |   timeout_truncation_rate |   positive_months | fold   | session           |
|---------:|------:|----------:|-----------:|---------:|---------------:|-------------:|------:|----------------:|----------------:|----------------------------:|-------------------------:|--------------------------:|------------------:|:-------|:------------------|
|        2 |  -834 | 0         |   0        |   -417   |              0 |         -834 |   643 |         11.2    |        -49.1    |                    0        |                        0 |                         0 |                 0 | 2025H1 | LONDON            |
|        4 |   538 | 1.68015   |   0.5      |    143.5 |           1329 |         -791 |   791 |         45.425  |        -37.875  |                    0.25     |                        0 |                         0 |                 1 | 2025H1 | LONDON_NY_OVERLAP |
|        2 |    66 | 1.89189   |   0.5      |     33   |            140 |          -74 |     0 |         11.45   |        -19.75   |                    0        |                        0 |                         0 |                 1 | 2025H1 | NEW_YORK          |
|        6 |   202 | 1.25473   |   0.333333 |    -50.5 |            995 |         -793 |   739 |         41.2333 |        -22.25   |                    0.166667 |                        0 |                         0 |                 2 | 2025H1 | TOKYO             |
|        3 |  -252 | 0.352185  |   0.333333 |   -173   |            137 |         -389 |   389 |         11.5667 |        -33.8333 |                    0        |                        0 |                         0 |                 1 | 2025H1 | TRANSITION        |
|        5 | -1567 | 0.0705813 |   0.4      |   -198   |            119 |        -1686 |  1125 |         10.28   |        -40.16   |                    0.2      |                        0 |                         0 |                 0 | 2025H2 | LONDON            |
|       10 |   343 | 1.4098    |   0.6      |     19   |           1180 |         -837 |   338 |         21.17   |        -21.45   |                    0.3      |                        0 |                         0 |                 3 | 2025H2 | LONDON_NY_OVERLAP |
|        4 |   -47 | 0.678082  |   0.25     |    -27.5 |             99 |         -146 |    91 |         11.2    |         -5.575  |                    0.75     |                        0 |                         0 |                 1 | 2025H2 | NEW_YORK          |
|        9 |   128 | 1.19335   |   0.333333 |    -52   |            790 |         -662 |   577 |         19.2111 |        -18.1778 |                    0.333333 |                        0 |                         0 |                 2 | 2025H2 | TOKYO             |
|        2 |   146 | 2.69767   |   0.5      |     73   |            232 |          -86 |    86 |         25.4    |        -21.55   |                    0        |                        0 |                         0 |                 1 | 2025H2 | TRANSITION        |

## Signal vs Exit lifecycle classification

|   trades |   net |    pf |   win_rate |   median |   gross_profit |   gross_loss |   mdd |   mean_mfe_pips |   mean_mae_pips |   profit_then_giveback_rate |   immediate_failure_rate |   timeout_truncation_rate |   positive_months | fold   | failure_class             |
|---------:|------:|------:|-----------:|---------:|---------------:|-------------:|------:|----------------:|----------------:|----------------------------:|-------------------------:|--------------------------:|------------------:|:-------|:--------------------------|
|        2 |  -143 |   0   |        0   |    -71.5 |              0 |         -143 |    89 |        62.05    |        -10.3    |                           1 |                        0 |                         0 |                 0 | 2025H1 | D_PROFIT_THEN_GIVEBACK    |
|        9 | -2738 |   0   |        0   |   -191   |              0 |        -2738 |  2547 |         9.87778 |        -49.3889 |                           0 |                        0 |                         0 |                 0 | 2025H1 | F_CONTINUATION_RESUMPTION |
|        6 |  2601 | nan   |        1   |    296   |           2601 |            0 |     0 |        49.35    |         -9.85   |                           0 |                        0 |                         0 |                 5 | 2025H1 | H_SUSTAINED_REVERSAL      |
|       10 |    54 |   1.3 |        0.5 |      5.5 |            234 |         -180 |    72 |        17.14    |        -10.5    |                           1 |                        0 |                         0 |                 3 | 2025H2 | D_PROFIT_THEN_GIVEBACK    |
|       12 | -3237 |   0   |        0   |   -206.5 |              0 |        -3237 |  2965 |         6.975   |        -34.5167 |                           0 |                        0 |                         0 |                 0 | 2025H2 | F_CONTINUATION_RESUMPTION |
|        8 |  2186 | nan   |        1   |    308.5 |           2186 |            0 |     0 |        34.5625  |        -15.6375 |                           0 |                        0 |                         0 |                 5 | 2025H2 | H_SUSTAINED_REVERSAL      |

## Source/history/spread comparison

- MT4 events: 47
- Raw Tick candidate events: 46
- Matched: 39
- MT4-only: 8
- Raw-only: 7

## Decision

`DIRECTIONAL_OR_REGIME_CONDITIONAL_MECHANISM`

The fixed candidate failed its consumed 2025 external gate and is not eligible for production. Any continuation requires a new hypothesis ID, candidate ID and preregistration using only 2023H1–2024H2 for development. 2025 remains postmortem evidence and cannot be reused as holdout.
