# Hotpath profile report

## Single-run telemetry (cache miss/hit)
- miss wall sec: 1.196597
- hit wall sec: 0.803055
- miss decision_score_prep sec: 0.034711
- miss decision_threshold_apply sec: 0.007730
- miss outcome_resolve sec: 0.012373

## Microbench (median sec, new vs legacy)
- prepare_decision_policy_inputs: new=0.016806, legacy=0.063499, speedup=3.78x
- apply_prepared_decision_policy: new=0.003952, legacy=0.013372, speedup=3.38x
- evaluate_candidates: new=0.003544, legacy=0.005455, speedup=1.54x
- build_candidates: new=0.002251, legacy=0.002070, speedup=0.92x

## cProfile targets (cumtime sec)
- evaluate_candidates: 0.007233
- prepare_decision_policy_inputs: 0.031646
- apply_prepared_decision_policy: 0.007703
- build_candidates: 0.004885
- _candidate_universe_identity: 0.006543
- _resolve_decision_score_prep_cache: 0.034654
- _resolve_outcome_cache: 0.010164
