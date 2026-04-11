# Policy Layer Usage (Research-Side Screening)

## Purpose

The policy layer is a **research-side candidate screening step** for pre-MT4 experiments.

It runs after:
1. candidate generation
2. feature attachment

and before:
3. outcome evaluation and summaries

This allows deterministic, YAML-driven screening tests without changing Python code each time.

## Important boundaries

- This is **not** final MT4/live EA logic.
- This is **not** MT4 parity.
- MT4 remains the final source of truth for execution behavior.
- The policy layer only filters candidate rows in research runs.

## Config shape

Add either:
- an inline `policy` block (existing behavior), or
- a top-level `policy_file` reference (preset file).

### Inline policy (existing)

```yaml
policy:
  enabled: true
  name: rev_danger_zone_test
  semantics: last_match_wins
  rules:
    - name: deny_rev_sell_danger
      type: deny
      candidate_family: rev
      direction: sell
      conditions:
        - feature: pre60_change_pips
          op: ">="
          value: 20
        - feature: net10_change_pips
          op: "<="
          value: -14
        - feature: rsi14
          op: "<="
          value: 40
```

### Policy preset file (new convenience)

```yaml
policy_file: configs/policies/rev_danger_zone_example.yaml
```

Preset files use the exact same policy schema (`enabled`, `name`, `semantics`, `rules`).
After loading, inline and file-based policies are normalized identically.

Path resolution for relative `policy_file` is deterministic:
1. resolve relative to the current config file directory
2. if not found, resolve relative to repository root
3. if still missing/unloadable, raise a clear error

When using `tools/run_study.py`, generated runtime experiment configs normalize
`policy_file` to a resolved absolute path based on the original study config directory
(then repo-root fallback), so execution remains consistent with study-config validation.

## Supported rule fields

### Rule action (`type`)
- `allow`
- `deny`

### Optional selectors
- `candidate_family`
- `direction`
- `session`
- `touch_side`

Selectors accept scalar or list values.
If omitted, selector behavior is wildcard (no restriction).

### Conditions
Each condition has:
- `feature`
- `op`
- `value`

Supported operators:
- `>`
- `>=`
- `<`
- `<=`
- `==`
- `!=`
- `between` (inclusive, expects `[lower, upper]`)
- `in`
- `not_in`

Conditions can reference both base candidate columns and attached feature columns.

## Deterministic semantics

Policy semantics are **`last_match_wins`**.

- Start with all candidates included.
- Evaluate rules in listed order.
- A matching `deny` sets row to excluded.
- A matching `allow` sets row to included.
- Later matching rules override earlier matching rules.
- No-match rows remain included.

Semantics are recorded in `run_metadata.yaml`.

## Auditability

Run outputs include:

- `candidates.csv`:
  - only included candidates (screened set)
  - includes policy audit columns
- `candidates_policy_audit.csv`:
  - all candidates before final exclusion
  - includes policy decision fields

Policy audit columns:
- `policy_enabled`
- `policy_name`
- `policy_semantics`
- `policy_decision` (`include` / `exclude`)
- `matched_rule_index`
- `matched_rule_name`
- `excluded_by_policy`

`run_metadata.yaml` also records:
- `enabled`
- `name`
- `semantics`
- `rule_count`
- `matched_rule_events` (total rule-row matches across rules; not unique candidates)
- `base_candidate_count`
- `included_candidate_count`
- `excluded_candidate_count`
