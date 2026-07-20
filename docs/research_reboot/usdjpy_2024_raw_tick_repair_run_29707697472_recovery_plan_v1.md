# USDJPY 2024 Raw Tick Repair Recovery Plan v1

The recovery workflow is intentionally package-only. It does not contact Dukascopy and does not recollect any market data.

It enumerates every artifact page for source run `29689427642` and repair run `29707697472`, resolves exact per-date artifact names, overlays the 28 repaired day packets, validates all 366 day directories and 8,784 hourly records, rebuilds deterministic monthly archives, and publishes the release only if every monthly manifest is accepted.

The failed run `29707697472` remains immutable evidence of the packaging defect. Its repaired day artifacts are reused as inputs and are not overwritten.
