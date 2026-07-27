# S3_H4_ALIGNED Economic Attribution Audit v1 — Preregistered Specification

## Purpose

Determine why the previously reported native MT4 gross-price improvement did not appear to convert into the reported account-balance improvement. This is an accounting and economic-attribution audit only. It does not search for a new candidate, tune any parameter, or access 2025.

## Frozen authorities

- Research start main: `2c9f87c9d7b5ccca978928fefa19e4e0c7d26f72`
- Core start main: `21565b92a1197381211987a866bef714367970a4`
- H4 parity Run: `30237882923`
- Binding 1,882-trade parity evaluator Run: `30238772493`
- Controlled integration source MT4 Run: `30241240995`
- Controlled integration evaluator repair Run: `30241915781`
- Controlled integration archive Run: `30242254591`

The candidate remains `S3_H4_ALIGNED`: H4 EMA 6/24, latest completed H4 only, allow only when state equals trade side, Neutral blocked, no strategy/side/session/period exceptions.

## Preregistered populations

The exact frozen 1,882 Research trades remain the scientific binding population. The native regenerated 1,898 trades remain non-binding and are used only to audit the real MT4 order path and its accounting.

Four executions are fixed before outcome inspection:

1. Native B02/F05 baseline.
2. Native B02/F05 with S3.
3. Exact frozen 1,882 schedule baseline.
4. Exact frozen 1,882 schedule with S3.

## Accounting gate

The audit must read the effective account currency and symbol contract directly from MT4. A requested tester currency is not treated as authoritative unless the generated report and runtime ledger confirm it.

For every closed ticket:

- Price P/L: `side × (exit − entry) × contract size × lots`.
- Reported account P/L: `OrderProfit + OrderSwap + OrderCommission`.
- Account balance: opening balance plus every history balance/credit/trade event.

The unexplained residual must be at most `0.01` in the effective account currency, except for an explicitly demonstrated per-ticket rounding convention.

## Required attribution

The audit will separately identify price P/L, account-currency conversion, spread, commission, swap, balance-only events, forced period-end close, partial/multiple closes, ticket identity, the 1,882/1,898 population bridge, and maximum-equity-drawdown contributors.

## Hard boundary

No 2025 data, production deployment, live orders, candidate change, parameter adjustment, rollover filter, session filter, side adjustment, or strategy exception is authorized by this specification.
