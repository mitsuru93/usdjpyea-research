# Batch parallel model benchmark

This is a model-based benchmark using measured miss/hit single-run times.

- workers (max-parallel): 8
- per-run miss sec: 0.283279
- per-run hit sec: 0.079951

## lite_sh2_v1
- shard_count: 18
- total_runs: 35
- modeled first wave sec: 0.363229
- modeled total completion sec: 1.089688
- modeled shard duration variance: 0.000335
- modeled cache hit rate: 0.485714

## lite_sh1_v1
- shard_count: 35
- total_runs: 35
- modeled first wave sec: 0.283279
- modeled total completion sec: 1.416394
- modeled shard duration variance: 0.000000
- modeled cache hit rate: 0.000000
