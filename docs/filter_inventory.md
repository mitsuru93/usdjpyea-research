# Filter Inventory (Baseline EA Families)

This inventory is a research-side map of known filter and control families present in the current EA baseline.

Legend:
- Affects: `Rev`, `Trend`, or `Both`
- Type: `entry veto`, `mode switch`, `lock`, `risk/logging support`
- Session-sensitive: `Yes`, `No`, or `TBD`

> Any behavior not explicitly confirmed is marked **TBD / to be verified against EA**.

## Filter Family Inventory

| Family | Role (research-side interpretation) | Affects | Session-sensitive | Type | Status |
|---|---|---:|---:|---|---|
| DeepChase | Chase/intensity gate for entries and/or follow-through logic | TBD | TBD | entry veto (tentative) | TBD / to be verified against EA |
| DeepChaseV2 | Revised DeepChase variant; expected refinement of entry qualification | TBD | TBD | entry veto (tentative) | TBD / to be verified against EA |
| TrendBoost | Trend-side enhancement logic with explicit session params | Trend (likely) | Yes (known) | mode switch / entry veto (TBD) | Partially known; details TBD |
| RevZoneC | Reverse zone qualification or veto family | Rev (likely) | TBD | entry veto (likely) | TBD / to be verified against EA |
| DriveNoEntry | Prevent entries during high-drive or disallowed drive conditions | Both (likely) | TBD | entry veto | TBD / to be verified against EA |
| TrendDistFilter | Trend distance qualification (distance-to-reference gating) | Trend (likely) | TBD | entry veto | TBD / to be verified against EA |
| Shock | Shock-event gating and protection logic | Both (likely) | TBD | entry veto / lock (TBD) | TBD / to be verified against EA |
| SurpriseShock | Surprise-shock variant for abrupt regime dislocations | Both (likely) | TBD | entry veto / lock (TBD) | TBD / to be verified against EA |
| BCore | Core baseline gating block B | Both (likely) | TBD | entry veto (likely) | TBD / to be verified against EA |
| ACoreBandWalk | Core baseline band-walk handling | Trend (likely) | TBD | mode switch / entry veto (TBD) | TBD / to be verified against EA |
| BBWChopVetoRev | Reverse veto during BB width chop regimes | Rev | TBD | entry veto | Partially known; details TBD |
| TokyoTRPre60Veto | Tokyo pre-window TR veto around 60-min logic | Both (likely) | Yes (likely) | entry veto | Partially known; details TBD |
| RVBWTRForce | RV/BW/TR force or override family | Both (likely) | TBD | mode switch (tentative) | TBD / to be verified against EA |

## Other Important Logic Families (Non-exhaustive)

| Family | Role | Affects | Session-sensitive | Type | Status |
|---|---|---:|---:|---|---|
| Hook confirmation | Confirmation gate prior to entry acceptance | Both (likely) | TBD | entry veto | TBD / to be verified against EA |
| M5 slope filter | Higher-timeframe slope-based qualification | Both (likely) | TBD | entry veto | TBD / to be verified against EA |
| BB/ATR trend environment logic | Environment classification for trend/reverse suitability | Both | TBD | mode switch / entry veto | Partially known; details TBD |
| Extreme/overheat reverse-ban logic | Ban reverse entries in extreme/overheat states | Rev | TBD | lock / entry veto | Partially known; thresholds TBD |
| News filter | Event-time gating around news risk | Both | Yes (likely by timestamp) | lock / entry veto | Partially known; rules TBD |
| Split order execution | Multi-part order placement and execution handling | Both | No (likely) | risk/logging support | Partially known; details TBD |
| Lot / leverage / max unit controls | Position sizing and exposure constraints | Both | TBD | risk/logging support | Partially known; formulas TBD |
| Cooldown locks and error locks | Time/error-based temporary trading disable controls | Both | TBD | lock | Partially known; unlock rules TBD |
| Logging / official trade history export | Tracking, audit, and export of realized outcomes | Both | No (likely) | risk/logging support | Known as present; schema TBD |

## Notes for Research Layer
- Treat this inventory as a **feature map**, not a full behavior spec.
- In simulator v1, start with baseline envelope + rev/trend skeleton and add filters incrementally.
- Any undocumented rule remains **TBD / to be verified against EA** until MT4-side checks confirm it.
