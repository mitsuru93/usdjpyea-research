# Cloud Timing Study Playbook (iPhone-first)

Use this runbook when you want to launch a timing study quickly from GitHub mobile.

## Workflow to run

- Workflow: `.github/workflows/run_research_timing_study.yml`
- Trigger: **Actions → Run Research Timing Study → Run workflow**

## Recommended defaults

- `study_config`: `configs/studies/cloud_timing_rv_close_confirm_first.yaml`
- `dataset_id`: leave blank unless you intentionally want to force one dataset across all runs
- `output_tag`: optional short label (example: `apr12-mobile-check`)

## Input guidance

### Leave `dataset_id` blank when:
- the study config already defines the right `dataset_id` values
- you are running the normal cloud candidate screen

### Set `dataset_id` when:
- you want all runs in this dispatch to use one specific registry dataset
- you need to re-run the same logic on a different staged dataset quickly

### Set `output_tag` when:
- you want a separate output folder under the same `output_root`
- you are running multiple mobile checks and want easy separation

## Where outputs appear

- Action job uploads one artifact for the run (named with config + dataset/tag + run id).
- Artifact includes:
  - `runs/`
  - `compare/`
  - `study_metadata.yaml`
  - `study_summary.md`

The job summary also shows:
- study config used
- dataset override used (or none)
- output tag (or none)
- resolved study output root
- artifact name

## What to read first after download

1. `compare/timing_study_review.md`
2. compare CSVs in `compare/`

## Scope reminder

This is **pre-MT4 candidate screening only**.  
Do not treat these results as MT4 parity or MT4-tested behavior.
