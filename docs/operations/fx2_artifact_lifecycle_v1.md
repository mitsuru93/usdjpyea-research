# FX2 Artifact Lifecycle Controller v1

## Scope

GitHub Actions Artifacts are temporary transport and diagnostic storage. Binding research authority remains an immutable GitHub Release after remote byte-identical readback and is referenced from PR, Issue, receipt, and Notion records.

This controller lists and deletes Actions Artifacts in `mitsuru93/usdjpyea-research` only. It never deletes Releases, local checkpoints, source data, research decisions, or Core implementation evidence.

## Retention

- diagnostic: 3 days
- smoke: 7 days
- failed technical evidence: 14 days
- intermediate/checkpoint: 14 days
- Release-promoted binding duplicates: 14 days
- unclassified legacy Artifacts: 30 days

Safety guards:

- preserve everything younger than 24 hours;
- preserve the newest 20 Artifacts globally;
- preserve the newest two generations in each normalized Artifact family;
- delete GitHub-expired Artifacts first;
- preserve names containing `do-not-delete` or `retain-forever`;
- retry transient deletion failures three times and treat HTTP 404 as idempotent success.

## Execution

- Daily apply: 02:40 JST, maximum 500 deletions.
- Issue dry-run: title `[FX2-ARTIFACT-LIFECYCLE] DRY-RUN`.
- Issue apply: title `[FX2-ARTIFACT-LIFECYCLE] APPLY`.
- Optional Issue body override: `max_deletions: 800` (hard maximum 800).

The Issue receives a machine-readable receipt and closes automatically after an error-free run. The controller does not upload its own Artifact.

## Regression guard

Every newly added or modified `actions/upload-artifact` step must declare `retention-days`. Values above 30 days are rejected unless the upload configuration contains `# artifact-policy: allow-long-retention`.

Legacy workflows are corrected when next modified; existing storage is handled centrally by the lifecycle controller.
