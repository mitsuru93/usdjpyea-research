# Policy Preset Examples (Research Templates)

These files are **research-side templates** for pre-MT4 screening experiments.

They are convenience presets to reduce repeated inline `policy` blocks in local/private study configs.
They are **not production truth** and do not change policy semantics.

## Usage

Reference a preset from an experiment/study run config with:

```yaml
policy_file: configs/policies/rev_danger_zone_example.yaml
```

Resolution order for relative `policy_file` values is deterministic:
1. relative to the config file directory
2. then relative to repository root

Loaded preset content is treated the same as inline `policy` YAML.
Semantics remain `last_match_wins`.

## Included examples

- `rev_danger_zone_example.yaml`: deny rev entries in a simple danger-zone feature pattern.
- `session_ban_rev_example.yaml`: deny rev entries in selected sessions.
- `trend_bias_example.yaml`: allow trend entries under a compact selector pattern.
