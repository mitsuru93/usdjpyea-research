# USDJPY Research Roadmap — 2024 Primary / 2025 Replication v4

> **SUPERSEDED — 2026-07-20**
>
> The 2025 replication provisions in this document are no longer authorized. USDJPY must not collect, download, aggregate, inspect, or evaluate 2025 market data. The binding replacement is `docs/research_reboot/usdjpy_no_2025_data_mt4_tester_rule_v1.md`: 2024 H2 remains reusable validation data, and further implementation validation uses only the already-installed 2024 history in MT4 Strategy Tester.
>
> The remainder of this file is retained only as historical methodology documentation and must not be used to authorize 2025 work.

## 1. Methodological decision

The prior v3 roadmap required separate unchanged replications on both 2025 H1 and 2025 H2 before Core or MT4 work. That requirement was stricter than necessary and incorrectly implied that 2024 was not enough to perform the primary research programme.

The corrected allocation is:

```text
2024-01-01 through 2024-07-01 exclusive:
  development of Entry, time, Exit, cost and position rules

2024-07-01 through 2025-01-01 exclusive:
  one candidate-specific unused confirmation of newly frozen complete strategies

2025-01-01 through 2026-01-01 exclusive:
  one full-year unchanged historical replication for H2 survivors
```

2025 does not replace 2024. It is not used before the 2024 programme is complete.

## 2. Why 2025 exists

2024 H1 plus H2 is enough to:

1. develop strategies on H1;
2. freeze complete strategies and gates;
3. perform a first unused confirmation on H2;
4. decide which strategies merit implementation work.

The reason to retain 2025 is narrower: the expanded H1 programme may compare up to sixty Entry definitions, eleven fixed horizons and controlled Exit branches. Even with family caps and a one-shot H2 run, a six-month H2 pass can still be specific to one market regime or survive selection by chance. One unchanged full-year replication tests whether the edge persists outside the 2024 selection and confirmation year.

2025 is therefore a capital-allocation replication gate, not a prerequisite for completing 2024 research and not an Exit-development block.

## 3. Core and MT4 timing

A strategy that passes candidate-specific unused 2024 H2 may immediately enter:

```text
research/Core parity implementation
MT4/Rakuten execution reproduction
non-executing shadow infrastructure
```

These tasks do not alter the strategy and can run while the unchanged 2025 historical replication is evaluated.

A strategy is not approved for live capital merely because Core or MT4 parity succeeds. Live-capital eligibility requires the 2025 full-year replication and the separately frozen operational/forward gate.

## 4. 2024 primary research programme

### R0 — canonical 2024 bundle and regression lock

Build the accepted January-December M1/M5/M15/H1 bundle and reproduce:

- all thirteen corrected H1 registered-hold results;
- authoritative A1/E3 H1 results;
- authoritative A1/E3 H2 results.

### R1 — expanded Entry registry on 2024 H1

- maximum sixty unique Entry definitions;
- fixed family caps;
- registry committed before expanded results;
- no new Entry definition after results are opened.

### R2 — fixed-horizon surface on 2024 H1

```text
1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 48 M15 bars
```

Map expectancy, PF, severe cost, monthly stability, concentration and price path. Prefer coherent neighbouring regions over isolated maxima.

### R3 — internal H1 stability diagnostics

- monthly and Q1/Q2 attribution;
- rolling two- and three-month blocks;
- anchored ranking diagnostics;
- spread and realized-volatility attribution.

These are development diagnostics, not independent validation.

### R4 — select Entry/horizon representatives

Common requirements and sample classes are fixed before selection. Retain no more than two representatives per family and eight overall.

### R5 — controlled Exit research on 2024 H1

For each representative:

```text
E0: robust fixed-time Exit
E1: one mechanism-defined invalidation Exit
E2: one mechanism-defined profit-preservation/trailing Exit
E3: optional target Exit only when justified by path evidence
```

No more than four policies including E0 per Entry mechanism. Retain at most one non-baseline Exit per mechanism.

### R6 — freeze the 2024 H2 shortlist

Before opening new-candidate H2 outcomes, commit:

- maximum five complete strategies;
- exact Entry, time and next-bar execution;
- exact Exit;
- overlap and re-entry rules;
- default and severe costs;
- H1 regression values;
- candidate-specific sample gates;
- all H2 promotion gates;
- the list of strategies whose H2 results remain unopened.

## 5. 2024 H2 confirmation

Run the maximum-five shortlist once on:

```text
2024-07-01T00:00:00Z through 2025-01-01T00:00:00Z exclusive
```

Each strategy is judged independently. A failed strategy is closed and may not be repaired using H2 information.

A passing strategy may proceed immediately to Core/MT4 parity work and to the unchanged 2025 replication.

## 6. 2025 full-year replication

Use one continuous block:

```text
2025-01-01T00:00:00Z through 2026-01-01T00:00:00Z exclusive
```

Do not split 2025 into two mandatory selection gates. Report:

- twelve monthly results;
- four quarterly results;
- H1 versus H2 attribution;
- aggregate default and severe metrics;
- concentration and direction attribution;
- exact trade-ledger regression.

The strategy remains unchanged. The full-year gate and any minimum quarterly/monthly conditions are committed before the 2025 result is opened.

A 2025 failure closes the strategy for live allocation. It does not invalidate the research or MT4 parity implementation as an engineering artifact, but the EA does not advance to capital deployment.

## 7. Final operating sequence

```text
1. Complete the 2024 canonical bundle and regression lock.
2. Expand and freeze the H1 Entry universe.
3. Run H1 horizon and stability research.
4. Run controlled H1 Exit research.
5. Freeze at most five complete strategies.
6. Run one candidate-specific unused 2024 H2 confirmation.
7. Begin Core/MT4 parity for H2 survivors.
8. Run one unchanged full-year 2025 replication.
9. Move only 2025 replication survivors to the frozen forward/operational gate.
10. Allocate live capital only after research, execution and forward gates pass.
```

## 8. Explicitly rejected sequence

The following sequence is not authoritative:

```text
2024 H2 pass
-> mandatory 2025 H1 pass
-> mandatory 2025 H2 pass
-> only then begin Core/MT4
```

It unnecessarily delays implementation parity, treats two correlated six-month slices as separate hurdles and is not required to answer the immediate question of whether the 2024-developed strategy replicated in its candidate-specific unused H2 block.
