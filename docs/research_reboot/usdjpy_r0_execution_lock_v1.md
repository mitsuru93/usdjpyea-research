# USDJPY R0 Execution Lock v1

## Purpose

Build one durable, byte-deterministic 2024 USDJPY canonical bundle from the frozen GitHub Release and prove that the existing H1 and H2 research results are reproduced from that canonical input.

## Frozen input

- Release tag: `usdjpy-r0-artifact-archive-2024-v1`
- Release assets: 29
- Accepted original artifacts represented by the Release: 288
- Excluded artifact: `8412658745`
- 2025 artifacts: prohibited

## Canonical output

- Symbol: USDJPY
- Year: 2024
- Timeframes: M1, M5, M15, H1
- Repair priority: aggregate repair over normal day bars
- Identical same-priority duplicates: consolidate and record
- Different same-priority duplicates: hard fail
- Gzip mtime: 0
- Fixed UTF-8, LF and float serialization

## Regression obligations

- H1: all 13 candidate summaries, all monthly rows and normalized trade ledger
- H2: A1/E3 H1 regression, H2 summaries, monthly rows, gates, direction, daily attribution, normalized trade ledger and final decision
- Horizon reference: 13 registered candidates, 12 unique entries, no H2 read, no promotion
- Hard no-trade violations: zero

## Decision boundary

Any failure blocks R1. R0 PASS only unblocks R1. It does not promote a strategy to Core or MT4.
