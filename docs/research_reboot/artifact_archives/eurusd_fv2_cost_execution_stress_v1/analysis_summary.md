# EURUSD F v2 cost and execution stress v1

Production primary: `F_v2_z72_1p5_mean_target_0p5_max12`
Registered acceptance: **True**

| scenario   | candidate_id                       | role               | period    |   spread_multiplier |   slippage_pips_per_side |   trades |   avg_net_pips |   total_net_pips |   profit_factor |   positive_months |   total_excluding_best_two_days |   max_drawdown_pips |
|:-----------|:-----------------------------------|:-------------------|:----------|--------------------:|-------------------------:|---------:|---------------:|-----------------:|----------------:|------------------:|--------------------------------:|--------------------:|
| default    | F_v2_z72_1p5_mean_target_0p5_max12 | production_primary | H2        |                 1   |                      0   |      114 |       1.83421  |         209.1    |        1.18532  |                 3 |                         47.35   |            -192.1   |
| default    | F_v2_z72_1p5_mean_target_0p5_max12 | production_primary | FULL_2024 |                 1   |                      0   |      204 |       2.64678  |         539.942  |        1.30385  |                 8 |                        378.192  |            -192.1   |
| moderate   | F_v2_z72_1p5_mean_target_0p5_max12 | production_primary | H2        |                 1.5 |                      0.1 |      114 |       1.33421  |         152.1    |        1.1316   |                 3 |                         -8.15   |            -202.4   |
| moderate   | F_v2_z72_1p5_mean_target_0p5_max12 | production_primary | FULL_2024 |                 1.5 |                      0.1 |      204 |       2.14615  |         437.814  |        1.24016  |                 8 |                        277.564  |            -202.4   |
| severe     | F_v2_z72_1p5_mean_target_0p5_max12 | production_primary | H2        |                 3   |                      0.5 |      114 |      -0.365789 |         -41.7    |        0.966719 |                 1 |                       -196.85   |            -255.1   |
| severe     | F_v2_z72_1p5_mean_target_0p5_max12 | production_primary | FULL_2024 |                 3   |                      0.5 |      204 |       0.444251 |          90.6272 |        1.04561  |                 4 |                        -64.5228 |            -308.573 |

No signal, exit, entry filter or candidate role was changed from this stress result.
Operational fault-injection and simulated state reinitialization are deferred to the Core production-EA implementation. The Rakuten account is not disconnected for a restart test.
