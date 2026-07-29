# USDJPY-HYP-037 Short Pullback Continuation Portability Result v1

## Final decision

`TECHNICAL_NO_RESULT_HISTORICAL_SOURCE_AUTHORITY_UNRESOLVED`

This is a technical stop, not a scientific failure. HYP-036 remains closed as `NO_PORTABLE_EXECUTABLE_CANDIDATE`; its candidate and decision were not rewritten.

## Identity and fixed boundary

- Hypothesis: `USDJPY-HYP-037`
- Family: `S_SHORT_PULLBACK_CONTINUATION_PORTABILITY`
- Candidate: `C1_SHORT_DUKASCOPY_NATIVE_16BAR`
- Only difference from HYP-036: direction is prospectively fixed to Short for a new unseen-period confirmation question.
- EMA20/EMA96, ATR20, 0.25 ATR pullback tolerance, source-native Bid entry, Ask exit after 16 observed M15 bars, suppression, 0.01 lot and JPY contract are unchanged.
- 2023-2024 receives discovery/mechanism credit only, never confirmation credit.

## 2023-2024 discovery and mechanism attribution

| Metric | Long | Short |
|---|---:|---:|
| Trades | 832 | 500 |
| Net | ¥-674 | +¥17,679 |
| PF | 0.993 | 1.273 |
| Win rate | 48.68% | 49.00% |
| Mean MFE | 21.43 pips | 33.76 pips |
| Mean MAE | -23.73 pips | -28.09 pips |
| Mean 120m return | 0.65 pips | 2.59 pips |
| Mean 240m return | -0.36 pips | 3.85 pips |

Trend/pullback/confirmation geometry is largely similar: pullback depth is 0.369 versus 0.372 ATR, duration 3.017 versus 3.012 bars, confirmation body 0.625 versus 0.652 ATR, and confirmation range 1.160 versus 1.176 ATR for Long versus Short. Short has a steeper directional EMA96 slope (3.329 versus 2.547 pips over four bars), slightly deeper retracement ratio (0.416 versus 0.373), higher Tick velocity, and wider executable spread.

The main economic difference is post-entry payoff shape, not hit rate or immediate confirmation. Short has worse mean returns at 15/30/60 minutes, but mean MFE is 12.33 pips larger and mean returns turn more favorable at 120/240 minutes. Median fixed-exit P/L is -¥4 for both sides, so the Short edge is carried by the positive tail rather than a broad shift in every trade. This supports a plausible delayed downtrend-continuation mechanism, but does not prove portability.

## Historical source authority

The binding 2020-2022 source gate failed before any candidate outcome was constructed.

- Required annual Release absent: 2020
- 2021 Release tag exists but 12 complete immutable months were not verified
- Required annual Release absent: 2022
- Prior acquisition Run `30318515957` is incomplete
- Inspected 2020-12 artifact `8675274277`: `accepted=false`, 0/31 day packets, 0/744 resolved hours
- HYP-032 supplies a JPY B02/F05 historical full-equity baseline, but it cannot reproduce Pullback signals or source-native Bid/Ask executions

No MT4/HST, venue substitution, reconstructed proxy, or mixed source was used.

## Stop consequences

The following are intentionally not results: 2020-2022 trade count, year/half-year/month/session P/L, net, PF, MDD, minimum equity, concentration, bootstrap, execution stress, historical portfolio gate, candidate freeze, Core/MT4 parity, 2025H1 and 2025H2. They were not accessed or executed.

The 2023-2024 portfolio diagnostics remain descriptive: combined net rose from ¥51,627 to ¥68,632 and realized DD fell from ¥40,487 to ¥34,339, but worst 5-day and 20-day results worsened to -¥12,103 and -¥18,137. No binding portfolio credit is awarded.

## Evidence

- PR: #398
- Scientific/preflight Run: `30423475688`
- Head SHA: `f8cc0cc9c952acc319b97ffdd9bb30b9c1b18c50`
- Artifact: `8712825068`
- Artifact digest: `sha256:ef2dc9458f4f15dbcab20172ddad611d8342dec9784d80a4428c2a5bd1bf8ad4`
- Deterministic archive SHA256: `aca8758a39805c4e56122460013b3a9bf3446a3f06f1d8b322041760f292bc0a`
- 2020-2022 candidate outcomes accessed: `false`
- 2025 accessed: `false`

## Authorization

Candidate freeze: false. Core: false. MT4: false. Production: false. Live: false.

## Exact next action

Complete and checksum immutable Dukascopy BI5 Bid/Ask monthly archives for 2020-2022, then rerun the unchanged HYP-037 preregistration. Do not change candidate, gate, source lineage, periods, or lot.
