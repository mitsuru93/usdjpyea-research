# USDJPY R1 Entry Registry Result v1 — Excluded

## Decision

```text
run_id: 29641805182
artifact_id: 8428842719
release_tag: usdjpy-r1-entry-registry-v1
status: EXCLUDED
R2 authorization: none
```

R1 v1 generated no price, Exit, horizon, cost or PnL output. However, it applied `entry_hours_utc` to the signal-bar hour instead of the actual next-M15-bar Entry timestamp used by the authoritative corrected H1 implementation.

The mismatch was detected by comparing the legacy A1 Entry ledger with the authoritative H1 reference:

```text
R1 v1 A1 signals: 388
authoritative registered-hold A1 trades: 391
```

This is an implementation-semantics defect, not evidence about candidate profitability. The v1 run and artifact may not be used by R2 or any later stage.

The corrected successor is:

```text
registry: configs/research/usdjpy_r1_entry_universe_v2.json
runner: tools/run_usdjpy_r1_entry_registry_v2.py
preregistration: docs/research_reboot/usdjpy_r1_entry_universe_prereg_v2.md
result: docs/research_reboot/usdjpy_r1_entry_registry_result_v2.md
```

V2 changes no family, Entry definition, parameter or threshold. It corrects only the application time of `entry_hours_utc` and requires exact Entry-ledger reproduction for all thirteen historical registered-hold candidates.
