# Session Model (JST)

## Current Session Buckets
The current baseline uses JST-based session segmentation:

- **ASIA**: 03:00-08:59 JST
- **TOKYO**: 09:00-15:59 JST
- **LONDON**: 16:00-20:59 JST
- **NY**: 21:00-02:59 JST

## Why Session Tagging Is Core
Many baseline thresholds appear session-dependent in the EA design.
Research artifacts should therefore:

1. Tag each candidate and each filled trade with session label.
2. Report metrics by session in addition to global aggregates.
3. Avoid cross-session leakage when calibrating thresholds.

## Modeling Notes
- Session classification should be deterministic and based on JST clock time.
- Cross-midnight handling (NY 21:00-02:59) must be explicit in implementation.
- Exact DST interactions and timezone conversion operational details are **TBD / to be verified against EA**.
- Exact list of parameters that are session-specific is **TBD / to be verified against EA**.

## Validation Notes
MT4 remains the final source of truth. Any discrepancy in session assignment or session-parameter use must be resolved against EA behavior.
