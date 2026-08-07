'use strict';

const HOUR_MS = 60 * 60 * 1000;

function parseIssueBody(body) {
  const text = String(body || '');
  const nameMatch = text.match(/^\s*artifact_exact_name:\s*(\S+)\s*$/im);
  const workflowMatch = text.match(/^\s*workflow_name:\s*(.+?)\s*$/im);
  const keepMatch = text.match(/^\s*keep_latest_success:\s*(\d+)\s*$/im);
  if (!nameMatch) throw new Error('issue body requires artifact_exact_name: <name>');
  if (!workflowMatch) throw new Error('issue body requires workflow_name: <exact workflow name>');
  if (!keepMatch) throw new Error('issue body requires keep_latest_success: <integer>');

  const artifactExactName = nameMatch[1];
  const workflowName = workflowMatch[1].trim();
  const keepLatestSuccess = Number(keepMatch[1]);
  if (!/^[a-z0-9][a-z0-9._-]{4,160}$/.test(artifactExactName)) {
    throw new Error('artifact_exact_name must be a lowercase literal artifact name');
  }
  if (workflowName.length < 5 || workflowName.length > 180) {
    throw new Error('workflow_name length is invalid');
  }
  if (!Number.isInteger(keepLatestSuccess) || keepLatestSuccess < 1 || keepLatestSuccess > 3) {
    throw new Error('keep_latest_success must be an integer between 1 and 3');
  }
  return { artifactExactName, workflowName, keepLatestSuccess };
}

function formatBytes(bytes) {
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let value = Number(bytes || 0);
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 2)} ${units[unit]}`;
}

async function listArtifacts(github, owner, repo) {
  return github.paginate(github.rest.actions.listArtifactsForRepo, { owner, repo, per_page: 100 });
}

async function validateFamily({ github, owner, repo, artifacts, artifactExactName, workflowName, keepLatestSuccess, now }) {
  const matching = artifacts.filter((artifact) => String(artifact.name || '') === artifactExactName);
  if (matching.length < 2) throw new Error(`family requires at least two artifacts: ${matching.length}`);
  if (matching.length > 20) throw new Error(`candidate safety cap exceeded: ${matching.length}`);

  const rows = [];
  for (const artifact of matching) {
    const runId = Number(artifact.workflow_run && artifact.workflow_run.id);
    if (!Number.isInteger(runId) || runId <= 0) throw new Error(`artifact lacks valid run: ${artifact.id}`);
    const created = Date.parse(artifact.created_at);
    if (!Number.isFinite(created) || now.getTime() - created < 24 * HOUR_MS) {
      throw new Error(`artifact is younger than the 24-hour guard: ${artifact.id}`);
    }
    if (!/^sha256:[0-9a-f]{64}$/i.test(String(artifact.digest || ''))) {
      throw new Error(`artifact digest is missing or invalid: ${artifact.id}`);
    }
    const response = await github.rest.actions.getWorkflowRun({ owner, repo, run_id: runId });
    const run = response.data;
    if (run.name !== workflowName) throw new Error(`workflow mismatch for run ${runId}: ${run.name}`);
    if (run.status !== 'completed' || run.conclusion !== 'success') {
      throw new Error(`run ${runId} is not a completed success: ${run.status}/${run.conclusion}`);
    }
    if (!/^[0-9a-f]{40}$/i.test(String(run.head_sha || ''))) {
      throw new Error(`run ${runId} lacks a valid head SHA`);
    }
    rows.push({ artifact, run });
  }

  rows.sort((a, b) => Date.parse(b.artifact.created_at) - Date.parse(a.artifact.created_at));
  if (rows.length < keepLatestSuccess) throw new Error('not enough successful artifacts to preserve');
  const keep = rows.slice(0, keepLatestSuccess);
  const keepIds = new Set(keep.map((row) => Number(row.artifact.id)));
  const newestKeeper = keep[0];

  for (const row of rows.slice(keepLatestSuccess)) {
    const comparison = await github.rest.repos.compareCommitsWithBasehead({
      owner,
      repo,
      basehead: `${row.run.head_sha}...${newestKeeper.run.head_sha}`
    });
    if (!['ahead', 'identical'].includes(comparison.data.status)) {
      throw new Error(`keeper SHA does not supersede run ${row.run.id}: ${comparison.data.status}`);
    }
  }

  const candidates = rows.filter((row) => !keepIds.has(Number(row.artifact.id)));
  if (candidates.length === 0) throw new Error('no superseded artifacts remain after keep guards');
  return { rows, keep, candidates };
}

async function run({ github, context, core, mode }) {
  if (!['dry-run', 'apply'].includes(mode)) throw new Error(`unsupported mode: ${mode}`);
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const input = parseIssueBody(context.payload.issue && context.payload.issue.body);
  const before = await listArtifacts(github, owner, repo);
  const validation = await validateFamily({ github, owner, repo, artifacts: before, ...input, now: new Date() });
  const selectedBytes = validation.candidates.reduce((sum, row) => sum + Number(row.artifact.size_in_bytes || 0), 0);
  const deleted = [];
  const errors = [];

  if (mode === 'apply') {
    for (const row of validation.candidates) {
      try {
        await github.rest.actions.deleteArtifact({ owner, repo, artifact_id: row.artifact.id });
        deleted.push(row.artifact);
      } catch (error) {
        if (error && error.status === 404) deleted.push({ ...row.artifact, already_absent: true });
        else errors.push({ id: row.artifact.id, name: row.artifact.name, status: error.status || null, message: error.message || String(error) });
      }
    }
  }

  const after = mode === 'apply' ? await listArtifacts(github, owner, repo) : before;
  const remaining = after.filter((artifact) => String(artifact.name || '') === input.artifactExactName);
  const remainingIds = new Set(remaining.map((artifact) => Number(artifact.id)));
  for (const keeper of validation.keep) {
    if (!remainingIds.has(Number(keeper.artifact.id))) throw new Error(`keeper missing after readback: ${keeper.artifact.id}`);
  }

  const summary = {
    schema_version: 'fx2_exact_name_success_family_purge_receipt_v1',
    mode,
    repository: `${owner}/${repo}`,
    artifact_exact_name: input.artifactExactName,
    workflow_name: input.workflowName,
    keep_latest_success: input.keepLatestSuccess,
    inspected_count: validation.rows.length,
    selected_count: validation.candidates.length,
    selected_bytes: selectedBytes,
    deleted_count: deleted.length,
    deleted_bytes: deleted.reduce((sum, artifact) => sum + Number(artifact.size_in_bytes || 0), 0),
    remaining_count: remaining.length,
    keeper_artifact_ids: validation.keep.map((row) => Number(row.artifact.id)),
    keeper_run_ids: validation.keep.map((row) => Number(row.run.id)),
    error_count: errors.length,
    errors,
    validated_candidates: validation.candidates.map((row) => ({
      artifact_id: Number(row.artifact.id), artifact_bytes: Number(row.artifact.size_in_bytes || 0),
      digest: row.artifact.digest, run_id: Number(row.run.id), head_sha: row.run.head_sha
    })),
    generated_at: new Date().toISOString()
  };

  const lines = [
    '## FX2 Exact-name Successful Family Artifact Purge', '',
    `- Mode: \`${mode}\``, `- Exact artifact name: \`${input.artifactExactName}\``,
    `- Exact workflow: \`${input.workflowName}\``, `- Successful generations retained: \`${input.keepLatestSuccess}\``,
    `- Selected as superseded: \`${validation.candidates.length}\` (${formatBytes(selectedBytes)})`,
    `- Deleted: \`${summary.deleted_count}\` (${formatBytes(summary.deleted_bytes)})`,
    `- Remaining exact-name matches: \`${summary.remaining_count}\``,
    `- Keeper Run IDs: \`${summary.keeper_run_ids.join(', ')}\``, `- Errors: \`${summary.error_count}\``, '',
    '| Action | Artifact ID | Run | Size | Digest | Head SHA |', '|---|---:|---:|---:|---|---|'
  ];
  for (const row of validation.keep) lines.push(`| KEEP | ${row.artifact.id} | ${row.run.id} | ${formatBytes(row.artifact.size_in_bytes)} | \`${row.artifact.digest}\` | \`${row.run.head_sha}\` |`);
  for (const row of validation.candidates) lines.push(`| DELETE | ${row.artifact.id} | ${row.run.id} | ${formatBytes(row.artifact.size_in_bytes)} | \`${row.artifact.digest}\` | \`${row.run.head_sha}\` |`);
  lines.push('', '<details><summary>Machine-readable receipt</summary>', '', '```json', JSON.stringify(summary), '```', '</details>');
  const markdown = lines.join('\n');
  await core.summary.addRaw(markdown).write();
  await github.rest.issues.createComment({ owner, repo, issue_number: context.issue.number, body: markdown.slice(0, 65000) });

  if (errors.length > 0) core.setFailed(`${errors.length} artifact deletions failed`);
  if (mode === 'apply' && remaining.length !== input.keepLatestSuccess) core.setFailed(`expected ${input.keepLatestSuccess} remaining artifacts, found ${remaining.length}`);
  return summary;
}

module.exports = { formatBytes, listArtifacts, parseIssueBody, run, validateFamily };
