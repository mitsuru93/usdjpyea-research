# First Simulator Scope (Intentionally Limited)

## Purpose
Define the **first** simulator boundary for pre-MT4 research.
The goal is controlled baseline research support, not full EA parity.

## What Simulator v1 SHOULD Cover
1. **Envelope baseline**
   - EMA20 envelope with ±0.070% deviation candidate reference.
2. **Rev/Trend candidate generation**
   - Separate candidate pathways for reverse and trend baseline modes.
3. **Conservative same-bar handling**
   - Deterministic, conservative assumptions when intrabar execution order is ambiguous.
4. **Session tagging**
   - JST session classification (ASIA/TOKYO/LONDON/NY) on events and trades.
5. **Feature extraction hooks**
   - Structured hooks for logging decision-time features and filter-state placeholders.

## What Simulator v1 SHOULD NOT Cover (Yet)
- Full reproduction of all MT4 edge cases.
- Exact broker execution microdetails and platform-specific quirks.
- Complete replication of every monolithic EA branch and fallback path.
- Final production-grade parameter binding across all filter families.
- Live-trading integration or broker-specific operational logic.

## Explicit Non-goals for v1
- Not a replacement for MT4 validation.
- Not the final arbiter for ambiguous legacy behavior.
- Not a production execution engine.

## Assumption Policy
- Unknown logic must be labeled **TBD / to be verified against EA**.
- Prefer conservative assumptions over optimistic assumptions.
- Track assumption versions in experiment metadata for auditability.

## Graduation Criteria to v2+
Advance beyond v1 only after:
- Stable baseline replication workflow exists.
- Major assumption risks are enumerated.
- Initial monthly/session robustness checks are in place.
- MT4 comparison plan is documented.
