# USDJPY CSOS Shock Failure Phase 2

**Decision: `PASS_PORTABLE_RESEARCH_CANDIDATE`**

- Selected fixed candidate: `B_EXECUTABLE_T0_8BAR`
- CSOS events reproduced: 114/114
- Chronology: EXACT_CONFIRMED=58, BOUNDED_SOURCE_MISMATCH=53, UNRESOLVED=3
- Observed-spread net: ¥12,502
- PF: 2.381
- LOFO positive held-out folds: 3/4
- Weak-market net: ¥9,462
- Corr B02/F05: 0.052 / -0.126

## Gate checks

- held_out_positive_3_of_4: True
- observed_net_positive: True
- observed_pf_ge_1_20: True
- spread_plus_1_net_positive: True
- severe_net_nonnegative: True
- severe_pf_ge_1: True
- best_day_excluded_positive: True
- top3_excluded_positive: True
- both_sides_positive: True
- each_side_positive_fold_cell: True
- weak_market_net_positive: True
- chronology_unresolved_within_limit: True
- chronology_contradiction_within_limit: True
- combined_mdd_increase_within_10pct: True

## Boundaries

No 2025 price or outcome was accessed. B02/F05 was not changed. Core, MT4 and production remain unauthorized.

## Interpretation

The candidate is portable enough to freeze for an implementation-contract stage, not production.
