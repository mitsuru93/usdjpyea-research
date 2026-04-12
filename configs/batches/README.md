# Batch Specs

Batch specs define cloud-first shard expansion for research screening.

- Deterministic YAML-first input.
- Shards compile into standard study configs consumed by `tools/run_study.py`.
- Pre-MT4 research only; MT4 remains final source of truth.
- Keep main research batches and smoke batches separated (`*_screen_*` vs `*_smoke_*` naming).

See `docs/batch_runner_usage.md` for schema and workflow usage.
