# USDJPY RQ-022 Native H1/H4 Feasibility and HYP-023 Freeze v1

## Decision

RQ-022 feasibility passed without calculating a strategy signal or P/L. A single scientifically distinct six-cell family, `N_NATIVE_H4_H1_EMA_STATE_TRANSITION`, is frozen as `USDJPY-HYP-023` before outcomes.

The family is not yet validated and no candidate is selected. After this preregistration is merged, only the exact six cells may be evaluated on 2023 H1/H2 and 2024 H1/H2. MT4 and 2025 remain locked.

## Data-construction result

The accepted 2023 historical-compatible M15 lineage preserves the binding `1,543` shifted first-tick timestamps. However, 123 accepted display timestamps are not logical fifteen-minute boundaries, with a maximum first-tick offset of nine minutes.

Native higher-timeframe membership therefore uses logical MT4 server buckets:

- 2023: floor `first_timestamp_mt4_server` to fifteen minutes;
- 2024: convert historical UTC to MT4 server UTC+2 in winter and UTC+3 during US DST;
- H1: exactly four logical M15 slots;
- H4: exactly sixteen logical M15 slots;
- partial market-open, market-close or holiday buckets do not update state and are not imputed;
- completed-bar information time is the server-bucket close converted through the historical `ServerToUtc` contract;
- M15 is used only for the next execution open and accepted trade identity.

Exact completed buckets are:

| Year | H1 | H4 |
|---|---:|---:|
| 2023 | 6,204 | 1,547 |
| 2024 | 6,109 | 1,508 |

2024 UTC→server→UTC mismatches, duplicate logical timestamps and duplicate information times are all zero.

## Literature boundary

Primary literature supports the mechanism class and controls, not the exact EMA periods:

- intraday FX volatility and activity have strong clock/session structure;
- technical-rule profitability is time-varying;
- transaction costs can eliminate apparent intraday excess returns;
- momentum/persistence exists in currencies at longer horizons;
- macro-announcement jumps create concentration and non-smooth risk.

No primary source establishes that H1/H4, any exact EMA pair or the proposed termination rule is optimal for USDJPY. The six cells therefore use natural powers-of-two and session/day scales frozen before outcomes, not literature-optimized parameters.

## Duplicate-research audit

The family does not reopen earlier work:

- Families A/F/I and HYP-001–006 modified admission, shock, acceptance or confirmation of existing M15/B02/F05 signals.
- Families B/E routed exposure or recovery state around existing signals.
- Families C/D/G/H changed checkpoint, invalidation or recovery exits after existing entries.
- RQ-019 partitioned a local B02 band.
- RQ-020B tested static 5-day/20-day overlays.
- RQ-020E exhausted all frozen M15 Entry × fixed-time horizon cells.
- The prior “higher-timeframe trend continuation” remained an M15 pullback/resumption trigger with an M15 lookback and fixed M15 hold.
- R1 EMA cross was calculated on M15 and paired with fixed-time exits.

HYP-023 is distinct because both the primary transition and termination are defined by completed exact-slot native H1/H4 bars. M15 supplies execution price only. Its payoff is not algebraically derivable from an opened result.

## Frozen six-cell family

H4 fast/slow pairs:

- 3 / 12
- 6 / 24
- 12 / 48

H1 confirmation fast/slow pairs:

- 4 / 16
- 8 / 32

The Cartesian product yields six cells. No expansion is allowed.

Entry lifecycle:

1. A completed H4 EMA state changes directly from −1 to +1 or +1 to −1.
2. The co-terminal completed H1 state must match the H4 direction, or match within the next four completed exact H1 bars.
3. Entry is the next accepted logical M15 open after confirmation.
4. If that M15 is in the frozen low-liquidity exclusion, the episode is cancelled rather than delayed.
5. Only one position may be open.

Exit lifecycle:

- first completed H1 state opposite the position, or first opposite completed H4 transition, whichever information time is earlier;
- execution at the next accepted logical M15 open;
- no fixed-time fallback;
- fold-boundary liquidations are flagged and event-only metrics must independently pass.

## Binding gates

Every fold must have at least ten positions and positive default/severe net and PF, including event-exited-only metrics. Both three-month sub-blocks must have nonnegative severe net. Full gates require at least four positive and at most two negative severe months plus positive default/severe ex-best-two-date net.

The family passes only if at least two Manhattan-adjacent cells pass all core gates and at least one cell in that component passes all full and pooled gates. An isolated cell cannot be selected. Long and short positions must each represent at least 20% of pooled trades, and positive-date concentration is capped.

## Outcome-free evaluator preflight

The modular evaluator passed before merge:

- M15 rows: 49,264
- exact H1 rows: 12,313
- exact H4 rows: 3,055
- candidates: 6
- duplicate execution times: 0
- outcomes computed: false

The evaluator, data module and lifecycle simulator are committed and blob-verified. The next permitted action after merge is one exact six-cell development evaluation. No MT4 or 2025 access is authorized.
