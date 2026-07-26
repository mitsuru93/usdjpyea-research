# USDJPY Impact Atlas — new-thread handoff v1

Use this document to continue the program in a new conversation without relying on chat memory.

## Authoritative repositories

- Research: `mitsuru93/usdjpyea-research`
- Core / MT4: `mitsuru93/usdjpyea-core`

At the start of every new thread, fetch the latest `main` commit for both repositories and report both SHAs. Do not rely on the SHA recorded here as current.

## Required first reads

1. `docs/research/USDJPY_CURRENT_RESEARCH_STATE.md`
2. `docs/research/USDJPY_IMPACT_ATLAS_PROGRAM_V1.md`
3. `configs/research/usdjpy_impact_atlas_v1_prereg.json`
4. `configs/research/usdjpy_b02_f05_experiment_registry_v1.json`
5. the latest source inventory and accepted Release receipts referenced by the current-state document
6. relevant completed factor, lifecycle, structural-SL, and failed-reclaim reports

## Direct user decision

The primary research direction is no longer local SL optimization. Structural-stop work remains a supporting track only.

The primary objective is to identify and validate high-impact improvements in:

1. market-state strategy permission;
2. entry establishment;
3. portfolio exposure and loss clustering;
4. profit lifecycle;
5. complementary strategy mechanisms.

## Period policy

- 2023H1, 2023H2, 2024H1, 2024H2: development and falsification evidence according to frozen contracts.
- 2025H1: external gate; never use it to choose factors, thresholds, sides, sessions, or mechanisms.
- 2025 failed-reclaim status: pending accepted raw Bid/Ask Tick collection and unchanged-candidate retest.
- 2025 M1/HST zero detections are not raw-Tick evidence.
- Confirm current H2 policy from GitHub before execution; do not infer it from old chat context.

## Immediate execution task

Build `USDJPY_IMPACT_ATLAS_V1`, beginning with Phase 0 source and lineage lock and then Phase 1 descriptive diagnosis.

Required Phase 1 outputs:

- source inventory;
- trade loss contribution;
- portfolio loss clusters;
- entry-establishment cohorts;
- market-state cohorts;
- profit-lifecycle cohorts;
- research-program priority table;
- missing-data report;
- final atlas report.

Phase 1 does not authorize a trading candidate.

## Scientific constraints

- Use only decision-time information for prospective state definitions.
- Keep diagnostic outcome variables separate from deployable predictors.
- Report all four historical folds separately.
- Quantify winner exposure and winner damage for every improvement target.
- Do not prioritize pooled gains that fail fold breadth.
- Do not silently substitute M1/HST for raw Tick.
- Do not reopen hundreds of local SL thresholds.
- Do not combine router, entry, exposure, profit, and exit changes before independent evaluation.
- Do not use Notion as the task selector.

## Execution placement

- Large analysis and dataset processing: Research GitHub-hosted runners.
- EA implementation and MT4 parity only after Research authorization: Core self-hosted/VPS runners.
- Store durable evidence in GitHub Releases/receipts before artifact expiry.

## Completion reporting

Every execution report must include:

- Research and Core main SHAs;
- source Release/artifact IDs, digests, and timestamps;
- exact periods accessed;
- whether 2025 was accessed;
- output identities and hashes;
- technical failures versus scientific failures;
- what changed in the registry and current-state document;
- the next authorized action.
