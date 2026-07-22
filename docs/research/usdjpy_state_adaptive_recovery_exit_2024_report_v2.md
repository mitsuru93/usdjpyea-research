# USDJPY State-Adaptive Recovery Exit 2024 Result v2

## Decision

`PASS_EXACT_2024_DEVELOPMENT_CANDIDATE`

Selected: `E2_ADAPTIVE_60_90__A15_B5_C15_R0`

The evaluator dynamically recomputes entry exposure after every candidate-adjusted close. Same-timestamp unchanged entries remain simultaneous peers. The exact selected trade keys and candidate P/L are unchanged from the static v1 reproduction, and the full 63-cell equivalence count remains 43.

## Exact rule

- F05 only; entries are unchanged.
- Initial condition: executable marked P/L at 30 minutes <= -15 pips and at 60 minutes <= -5 pips.
- Dynamic unsupported state (`standalone`, `opposite_overlap`, `mixed_overlap`): close at 60 minutes.
- Dynamic same-direction-supported state (`same_direction_stack`, `simultaneous_same_direction`): defer at 60 minutes; close at 90 minutes only when P/L <= -15 pips and recovery from 60 to 90 minutes is <= 0 pips.
- B02 and positions not selected by this rule retain their baseline exits.

## Metrics

- H1: 11 changed, delta 2,288 JPY, PF 1.431644.
- H2: 26 changed, delta 5,770 JPY, PF 1.428159.
- Full 2024: 37 changed on 36 dates, delta 8,058 JPY, PF 1.429420.
- Positive/negative months: 10/1.
- Minimum calendar-quarter effect: 537 JPY.
- Benefit/harm: 10,045/1,987 JPY.
- Winner harm: 273 JPY.
- Prior-candidate overlap: 35.135%.

Every frozen 2024 development gate passes. This is development-period selection, not independent validation. Exact 2024 Research-to-MT4 parity is required before candidate-specific 2025 H1 access.
