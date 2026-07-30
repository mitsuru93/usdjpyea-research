# USDJPY-PORTABILITY-001 Final Result

Decision: `PARTIAL_COMMON_CONTRACT_WITH_REMAINING_SOURCE_LIMITATIONS`.

Same-source Research/Core parity is exact for HYP-039 (500/500) and HYP-040 (545/545). Binding Core/MT4 mismatch counts are 242 and 265. First divergence is overwhelmingly executable-Tick price semantics under Model=0: 500 `FIRST_EXECUTABLE_TICK_DIFFERENCE`, 4 `MT4_TESTER_MODEL_LIMITATION`, 2 lifecycle, and 1 suppression mismatch. Unresolved mismatch is zero.

Rakuten broker-native raw Bid/Ask Tick is unavailable. Therefore Model=0 cannot certify source-native Rakuten executable chronology. T1, T2 within identical raw input, and T4 are accepted. T3 exact deployment certification is rejected.

HYP-039 and HYP-040 were not reopened and their formal decisions remain unchanged. No strategy rule was changed, no P/L optimization was performed, 2025H2 was not accessed, and production/live authorization is false.
