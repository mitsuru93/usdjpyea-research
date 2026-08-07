'use strict';

const HOUR_MS = 60 * 60 * 1000;

function parseIssueBody(body) {
  const text = String(body || '');
  const fields = {};
  for (const key of ['release_repo', 'release_tag', 'source_artifact_id', 'artifact_prefix', 'workflow_name']) {
    const pattern = new RegExp(`^\\s*${key}:\\s*(.+?)\\s*$`, 'im');
    const match = text.match(pattern);
    if (!match) throw new Error(`issue body requires ${key}: <value>`);
    fields[key] = match[1].trim();
  }
  if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(fields.release_repo)) {
    throw new Error('release_repo must be owner/repository');
  }
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{2,160}$/.test(fields.release_tag)) {
    throw new Error('release_tag is invalid');
  }
  fields.source_artifact_id = Number(fields.source_artifact_id);
  if (!Number.isInteger(fields.source_artifact_id) || fields.source_artifact_id <= 0) {
    throw new Error('source_artifact_id must be a positive integer');
  }
  if (!/^[a-z0-9][a-z0-9._-]{4,140}-$/.test(fields.artifact_prefix)) {
    throw new Error('artifact_prefix must be a lowercase literal prefix ending in hyphen');
  }
  if (fields.workflow_name.length < 5 || fields.workflow_name.length > 180) {
    throw new Error('workflow_name length is invalid');
  }
  return fields;
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

async function getArtifact(github, owner, repo, artifactId) {
  const response = await github.rest.actions.getArtifact({ owner, repo, artifact_id: artifactId });
  return response.data;
}

function validateReleaseMirror({ release, sourceArtifact }) {
  if (release.draft || release.prerelease) throw new Error('release must be published and non-prerelease');
  const body = String(release.body || '');
  const exactArtifactText = `Actions artifact ${sourceArtifact.id}`;
  if (!body.includes(exactArtifactText)) {
    throw new Error(`release body does not bind ${exactArtifactText}`);
  }
  const digest = String(sourceArtifact.digest || '');
  if (!/^sha256:[0-9a-f]{64}$/i.test(digest)) throw new Error('source artifact digest is missing or invalid');
  const digestHex = digest.slice('sha256:'.length);
  if (!body.toLowerCase().includes(digestHex.toLowerCase())) {
    throw new Error('release body does not contain the source artifact outer SHA-256');
  }

  const assets = new Map((release.assets || []).map((asset) => [asset.name, asset]));
  for (let month = 1; month <= 12; month += 1) {
    const token = `-${String(month).padStart(2, '0')}-mt4-tick-import-v1.csv.gz`;
    const matches = [...assets.values()].filter((asset) => asset.name.endsWith(token));
    if (matches.length !== 1) throw new Error(`release monthly asset count mismatch for ${token}`);
    if (!/^sha256:[0-9a-f]{64}$/i.test(String(matches[0].digest || ''))) {
      throw new Error(`release monthly asset digest missing: ${matches[0].name}`);
    }
  }
  for (const required of ['SHA256SUMS', 'IMPORT_GUIDE.md']) {
    const asset = assets.get(required);
    if (!asset || !/^sha256:[0-9a-f]{64}$/i.test(String(asset.digest || ''))) {
      throw new Error(`release support asset missing or lacks digest: ${required}`);
    }
  }
  const manifests = [...assets.values()].filter((asset) => asset.name.endsWith('-mt4-tick-import-v1.manifest.json'));
  if (manifests.length !== 1 || !/^sha256:[0-9a-f]{64}$/i.test(String(manifests[0].digest || ''))) {
    throw new Error('release manifest asset missing or lacks digest');
  }
  return true;
}

async function validateCandidates({ github, owner, repo, artifacts, sourceArtifact, artifactPrefix, workflowName, now }) {
  const matching = artifacts.filter((artifact) => String(artifact.name || '').startsWith(artifactPrefix));
  if (matching.length === 0) throw new Error('no artifacts matched the requested prefix');
  if (matching.length > 10) throw new Error(`candidate safety cap exceeded: ${matching.length}`);
  if (!matching.some((artifact) => Number(artifact.id) === Number(sourceArtifact.id))) {
    throw new Error('bound source artifact is not present in the selected family');
  }

  const validated = [];
  for (const artifact of matching) {
    const runId = Number(artifact.workflow_run && artifact.workflow_run.id);
    if (!Number.isInteger(runId) || runId <= 0) throw new Error(`invalid run binding: ${artifact.name}`);
    if (!artifact.name.includes(`-${runId}-`)) throw new Error(`artifact name/run mismatch: ${artifact.name}`);
    const created = Date.parse(artifact.created_at);
    if (!Number.isFinite(created) || now.getTime() - created < 24 * HOUR_MS) {
      throw new Error(`artifact is younger than the 24-hour guard: ${artifact.name}`);
    }
    const runResponse = await github.rest.actions.getWorkflowRun({ owner, repo, run_id: runId });
    const run = runResponse.data;
    if (run.name !== workflowName) throw new Error(`workflow name mismatch for run ${runId}: ${run.name}`);
    if (run.status !== 'completed') throw new Error(`run ${runId} is not completed`);
    if (Number(artifact.id) === Number(sourceArtifact.id)) {
      if (run.conclusion !== 'success') throw new Error('bound source artifact does not belong to a successful run');
      if (artifact.digest !== sourceArtifact.digest) throw new Error('bound source digest changed during validation');
    } else if (run.conclusion !== 'failure') {
      throw new Error(`non-source family artifact run is not a failure: ${runId}/${run.conclusion}`);
    }
    validated.push({ artifact, run, role: Number(artifact.id) === Number(sourceArtifact.id) ? 'release_bound_source' : 'failed_duplicate' });
  }
  return validated.sort((a, b) => Number(b.artifact.size_in_bytes || 0) - Number(a.artifact.size_in_bytes || 0));
}

async function run({ github, context, core, mode }) {
  if (!['dry-run', 'apply'].includes(mode)) throw new Error(`unsupported mode: ${mode}`);
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const input = parseIssueBody(context.payload.issue && context.payload.issue.body);
  const [releaseOwner, releaseRepo] = input.release_repo.split('/');

  const sourceArtifact = await getArtifact(github, owner, repo, input.source_artifact_id);
  const releaseResponse = await github.rest.repos.getReleaseByTag({ owner: releaseOwner, repo: releaseRepo, tag: input.release_tag });
  validateReleaseMirror({ release: releaseResponse.data, sourceArtifact });

  const before = await listArtifacts(github, owner, repo);
  const candidates = await validateCandidates({
    github,
    owner,
    repo,
    artifacts: before,
    sourceArtifact,
    artifactPrefix: input.artifact_prefix,
    workflowName: input.workflow_name,
    now: new Date()
  });
  const selectedBytes = candidates.reduce((sum, row) => sum + Number(row.artifact.size_in_bytes || 0), 0);
  const deleted = [];
  const errors = [];

  if (mode === 'apply') {
    for (const row of candidates) {
      try {
        await github.rest.actions.deleteArtifact({ owner, repo, artifact_id: row.artifact.id });
        deleted.push(row.artifact);
      } catch (error) {
        if (error && error.status === 404) deleted.push({ ...row.artifact, already_absent: true });
        else errors.push({
          id: row.artifact.id,
          name: row.artifact.name,
          status: error && error.status ? error.status : null,
          message: error && error.message ? error.message : String(error)
        });
      }
    }
  }

  const after = mode === 'apply' ? await listArtifacts(github, owner, repo) : before;
  const remaining = after.filter((artifact) => String(artifact.name || '').startsWith(input.artifact_prefix));
  // Re-read the Release after deletion to ensure the durable copy still exists.
  const releaseReadback = await github.rest.repos.getReleaseByTag({ owner: releaseOwner, repo: releaseRepo, tag: input.release_tag });
  validateReleaseMirror({ release: releaseReadback.data, sourceArtifact });

  const summary = {
    schema_version: 'fx2_cross_repo_release_mirror_purge_receipt_v1',
    mode,
    repository: `${owner}/${repo}`,
    release_repository: input.release_repo,
    release_tag: input.release_tag,
    source_artifact_id: input.source_artifact_id,
    source_artifact_digest: sourceArtifact.digest,
    artifact_prefix: input.artifact_prefix,
    workflow_name: input.workflow_name,
    selected_count: candidates.length,
    selected_bytes: selectedBytes,
    deleted_count: deleted.length,
    deleted_bytes: deleted.reduce((sum, artifact) => sum + Number(artifact.size_in_bytes || 0), 0),
    remaining_count: remaining.length,
    error_count: errors.length,
    errors,
    validated_candidates: candidates.map((row) => ({
      role: row.role,
      artifact_id: Number(row.artifact.id),
      artifact_name: row.artifact.name,
      artifact_bytes: Number(row.artifact.size_in_bytes || 0),
      digest: row.artifact.digest,
      run_id: Number(row.run.id),
      conclusion: row.run.conclusion
    })),
    generated_at: new Date().toISOString()
  };

  const lines = [
    '## FX2 Cross-repository Release Mirror Purge',
    '',
    `- Mode: \`${mode}\``,
    `- Durable Release: \`${input.release_repo}@${input.release_tag}\``,
    `- Bound source Artifact: \`${input.source_artifact_id}\``,
    `- Prefix: \`${input.artifact_prefix}\``,
    `- Selected: \`${candidates.length}\` (${formatBytes(selectedBytes)})`,
    `- Deleted: \`${summary.deleted_count}\` (${formatBytes(summary.deleted_bytes)})`,
    `- Remaining prefix matches: \`${summary.remaining_count}\``,
    `- Errors: \`${summary.error_count}\``,
    '',
    '| Role | Artifact | Run | Conclusion | Size | Digest |',
    '|---|---|---:|---|---:|---|'
  ];
  for (const row of candidates) {
    lines.push(`| ${row.role} | \`${row.artifact.name}\` | ${row.run.id} | ${row.run.conclusion} | ${formatBytes(row.artifact.size_in_bytes)} | \`${row.artifact.digest}\` |`);
  }
  lines.push('', '<details><summary>Machine-readable receipt</summary>', '', '```json', JSON.stringify(summary), '```', '</details>');
  const markdown = lines.join('\n');
  await core.summary.addRaw(markdown).write();
  await github.rest.issues.createComment({ owner, repo, issue_number: context.issue.number, body: markdown.slice(0, 65000) });

  if (errors.length > 0) core.setFailed(`${errors.length} artifact deletions failed`);
  if (mode === 'apply' && remaining.length > 0) core.setFailed(`${remaining.length} matching artifacts remain after purge readback`);
  return summary;
}

module.exports = {
  formatBytes,
  getArtifact,
  listArtifacts,
  parseIssueBody,
  run,
  validateCandidates,
  validateReleaseMirror
};
