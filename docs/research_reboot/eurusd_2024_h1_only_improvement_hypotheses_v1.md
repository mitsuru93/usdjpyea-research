# EURUSD 2024 H1-only improvement hypotheses v1

Created: 2026-07-20 JST

## Boundary

This note uses only January-June 2024 development data to create and modify strategy rules. July-December 2024 is the permanent fixed validation period and may be used repeatedly to test each newly locked H1-derived iteration. H2 has no consumed or retired state. H2 may accept or reject a candidate, but it must not be used to generate or tune the next rule.

Authoritative iteration policy: `configs/research/eurusd_2024_h1_h2_iteration_policy_v1.json`.

The formal H1 screen expanded the registered A-J universe to 46 candidates and nominated A, F, G and H. The H1 source is the canonical one-hour EURUSD bar bundle with the project hard no-trade window and the registered cost model.

## Strategy definitions

### A — intraday local-currency direction

A is a clock-time anomaly strategy rather than an indicator strategy. The nominated representative, `A2_europe_local_short_hold8`, sells EURUSD at the open of the H1 bar beginning at 08:00 Europe/Berlin local time and exits after eight H1 bars. The local time is DST-aware.

### F — Bollinger/z-score mean reversion

F computes the close's z-score relative to a rolling mean and standard deviation. It buys when the z-score is below the negative threshold and sells when it is above the positive threshold. Entries are allowed only when the 24-bar Kaufman efficiency ratio is at or below 0.35, which attempts to exclude directional regimes. Registered lookbacks are 24 and 72 H1 bars, thresholds are 1.5 and 2.0 standard deviations, and holds are 6 and 12 bars.

### G — RSI-extreme mean reversion

G uses Wilder RSI(14). It buys below the lower threshold and sells above the upper threshold, again only when the 24-bar Kaufman efficiency ratio is at or below 0.35. Registered threshold pairs are 30/70 and 25/75, with 6- and 12-bar holds.

### H — failed-breakout reversal

H forms a prior rolling high/low over 24 or 48 H1 bars. A short signal occurs when the current bar trades above the prior high by at least 0.10 ATR(24) but closes back inside the prior range. A long signal is the symmetric failed downside breakout. Registered holds are 6 and 12 bars.

## H1 evidence by family

### A

`A2_europe_local_short_hold8` produced 129 trades, +1.995845 pips/trade, PF 1.177166, five positive months, and +86.613971 pips after removing the best two entry days. Severe-cost PF was 0.983449.

The four-hour European short was much weaker: +0.669101 pips/trade and PF 1.104151, while the U.S.-session long variants did not pass. The average gross path of A2 over the eight holding bars was approximately 0.94, 1.59, 2.06, 1.27, 0.99, 2.27, 2.93 and 2.60 pips. This indicates that the H1 edge was not concentrated in the first four hours and reappeared later in the European day.

The best two days contributed 170.85 of 257.46 total pips, about 66.4%. May was strongly negative and Wednesday was negative in the H1 diagnostic, but these are exploratory slices and are not registered filters.

H1-only improvement hypotheses:

1. Keep the Europe short and remove the unsupported U.S. long branch.
2. Test a causal staged exit: enter at 08:00 Berlin, inspect the completed European-morning path at a fixed checkpoint, and close weak trades while retaining the original eight-hour maximum hold. Checkpoint and threshold must be locked before the next H2 validation run.
3. Test a compact exit neighborhood around 6/8/10/12 hours or an exit anchored to the European-session close, rather than optimizing a broad hold grid.
4. Add a spread/transaction-quality gate because severe costs erase the H1 average edge.
5. Diagnose the concentration by prior 8/24-hour return, realized volatility, day of week and scheduled macro dates, but do not create a filter from a single H1 slice.

### F

F was the broadest H1 family: all eight registered variants were positive and six passed the development candidate gate.

The balanced representative `F_z_lb72_thr1p5_hold12` produced 86 trades, +5.369679 pips/trade, PF 1.709023, +277.492396 pips after removing the best two days, and severe-cost PF 1.369734. Long and short sides were similar in H1. The average gross path continued improving through roughly bars 10-11 and softened slightly at bar 12, supporting a longer mean-reversion horizon than six bars.

`F_z_lb72_thr2p0_hold12` was stronger per trade but had only 37 trades. The 72-bar lookback was broadly stronger than the 24-bar lookback, while 12-bar holds were generally more robust than 6-bar holds.

H1-only improvement hypotheses:

1. Treat 72 H1 bars and a 12-bar maximum hold as the core region, not a single optimized point.
2. Replace the purely fixed exit with a mean-reversion exit: close on a z-score return toward zero, with a preregistered 12-hour maximum hold. A small set of exit bands should be tested, not an unrestricted search.
3. Test tiered entries: a normal position at |z| >= 1.5 and a separately controlled high-conviction tier at |z| >= 2.0 only when RSI also confirms an extreme.
4. Preserve the efficiency-ratio regime filter and test only a narrow neighborhood around it. Pure trend and channel-breakout families were negative in H1, so a stronger trend veto is more plausible than removing the veto.
5. Add volatility-scaled position sizing rather than a fixed pip stop until MFE/MAE behavior is evaluated on Tick or lower-timeframe paths.

### G

The 30/70 variants passed; the 25/75 variants produced only four trades each and were negative. `G_rsi14_30_70_hold12` produced 35 trades, +7.165714 pips/trade, PF 2.087833 and severe-cost PF 1.655231. The 12-bar hold was stronger than the 6-bar hold in H1.

G overlaps materially with F. Sixteen of the 35 G hold-12 entries coincided with `F_z_lb72_thr1p5_hold12`, and 12 coincided with `F_z_lb72_thr2p0_hold12`; coincident entries always had the same direction. The subset where z >= 2.0 and RSI also confirmed contained 12 H1 trades with +20.445833 pips/trade and PF 4.568727, but this is a small, H1-selected subset and must be locked and tested on the fixed H2 period before promotion.

H1-only improvement hypotheses:

1. Do not tighten RSI to 25/75; H1 shows sparse and poor behavior.
2. Use RSI primarily as a confirmation or position-sizing tier for F rather than running F and G as independent full-size positions.
3. Keep 30/70 and a 12-bar maximum hold as the core region.
4. Separate long and short diagnostics within H1 before considering directional asymmetry; the H1 short side was stronger, but the sample is too small for a hard rule.

### H

H showed a clear timescale interaction. `H_failed_lb24_hold6` passed, while `H_failed_lb24_hold12` failed. `H_failed_lb48_hold12` passed, while `H_failed_lb48_hold6` failed. This suggests that the reversion horizon should scale with the reference range length.

A hierarchical H1-only prototype was therefore tested:

- failed 48-hour range: hold 12 hours;
- otherwise, failed 24-hour range: hold 6 hours;
- one position at a time.

On H1 this prototype produced 117 trades, +2.697863 pips/trade, PF 1.371004, five positive months, +143.35 pips after removing the best two days, maximum drawdown -136.15 pips and severe-cost PF 1.059245. This is a new H1-derived candidate and must be locked before validation on the fixed H2 period.

H1-only improvement hypotheses:

1. Replace the independent lookback/hold grid with the hierarchical timescale rule above.
2. Define the exit around the failed range structure: range midpoint or a fixed fraction back into the range, with the registered time stop as a maximum.
3. Test a close-reentry-depth condition so that a wick barely closing inside is distinguished from a decisive rejection. Use a small preregistered set such as 0%, 25% and 50% of range depth.
4. Add the same low-efficiency/trend veto used by F and G, because a failed breakout against a persistent trend is structurally different from a liquidity rejection in a range.
5. Do not run the 24-hour and 48-hour variants as separate simultaneous positions. Sixty of the 68 `H_failed_lb48_hold12` H1 entries overlapped the 24-hour signal.

## Portfolio-level design inferred from H1

1. A is the most independent component: its entry overlap with the selected F, G and H representatives was only about 2-3% in H1.
2. F should be the core mean-reversion family because its positive result covered the entire registered grid and survived severe costs more clearly than A or H.
3. G should confirm or scale F, not duplicate it.
4. H should be a single hierarchical failed-breakout engine, not two overlapping EAs.
5. Conflict policy must be explicit: one aggregate EURUSD position, with deterministic priority and net exposure limits across A/F/G/H.
6. Every new overlay or modified candidate must be derived from H1, locked as a distinct iteration, and then evaluated on the same fixed 2024 H2 validation period.

## Recommended next candidate set

For the next H1-derived/H2-validation iteration, keep the search bounded to the following hypotheses:

- `A_europe_short_staged_exit_v2`
- `F_z72_mean_cross_max12_v2`
- `F_z72_rsi_confirmed_tier_v2`
- `H_failed_hierarchical_24x6_48x12_v2`
- one aggregate portfolio rule combining A, F and H with G as confirmation

The original v1 candidates and the prior 2024 H2 result remain unchanged as the comparison baseline. The same H2 period may be used again for the locked v2 candidates.
