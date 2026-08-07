'use strict';

function parseReceiptPath(body) {
  const match = String(body || '').match(/^\s*receipt_path:\s*(\S+)\s*$/im);
  if (!match) throw new Error('issue body requires receipt_path: <path>');
  const path = match[1];
  if (!path.startsWith('configs/research/') || !path.endsWith('.json') || path.includes('..')) {
    throw new Error('receipt_path must be a safe configs/research/*.json path');
  }
  return path;
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

async function fetchJsonFile(github, context, path) {
  const response = await github.rest.repos.getContent({
    owner: context.repo.owner,
    repo: context.repo.repo,
    path,
    ref: context.sha
  });
  if (Array.isArray(response.data) || response.data.type !== 'file') {
    throw new Error(`receipt path is not a file: ${path}`);
  }
  return JSON.parse(Buffer.from(response.data.content, response.data.encoding).toString('utf8'));
}

function validateReleaseBinding(receipt, release) {
  if (receipt.status !== 'PASS_SHA256_FULL_READBACK') {
    throw new Error(`receipt status is not authoritative: ${receipt.status}`);
  }
  if (!Number.isInteger(Number(receipt.binding_run_id)) || Number(receipt.binding_run_id) <= 0) {
    throw new Error('receipt.binding_run_id must be a positive integer');
  }
  if (!receipt.release_tag || release.tag_name !== receipt.release_tag) {
    throw new Error('release tag mismatch');
  }
  if (!receipt.publication_commit || release.target_commitish !== receipt.publication_commit) {
    throw new Error('release publication commit mismatch');
  }
  if (!Array.isArray(receipt.assets) || receipt.assets.length === 0) {
    throw new Error('receipt.assets must be non-empty');
  }
  const releaseAssets = new Map((release.assets || []).map((asset) => [asset.name, asset]));
  for (const expected of receipt.assets) {
    const actual = releaseAssets.get(expected.name);
    if (!actual) throw new Error(`release asset missing: ${expected.name}`);
    if (Number(actual.size) !== Number(expected.bytes)) {
      throw new Error(`release asset size mismatch: ${expected.name}`);
    }
    if (!actual.digest || actual.digest !== `sha256:${expected.sha256}`) {
      throw new Error(`release asset digest mismatch: ${expected.name}`);
    }
  }
  return true;
}

async function listRunArtifacts(github, owner, repo, runId) {
  return github.paginate(github.rest.actions.listWorkflowRunArtifacts, {
    owner,
    repo,
    run_id: runId,
    per_page: 100
  });
}

async function run({ github, context, core, mode }) {
  if (!['dry-run', 'apply'].includes(mode)) throw new Error(`unsupported mode: ${mode}`);
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const receiptPath = parseReceiptPath(context.payload.issue && context.payload.issue.body);
  const receipt = await fetchJsonFile(github, context, receiptPath);
  const releaseResponse = await github.rest.repos.getReleaseByTag({
    owner,
    repo,
    tag: receipt.release_tag
  });
  validateReleaseBinding(receipt, releaseResponse.data);

  const runId = Number(receipt.binding_run_id);
  const artifacts = await listRunArtifacts(github, owner, repo, runId);
  const selectedBytes = artifacts.reduce((sum, artifact) => sum + Number(artifact.size_in_bytes || 0), 0);
  const deleted = [];
  const errors = [];

  if (mode === 'apply') {
    for (const artifact of artifacts) {
      try {
        await github.rest.actions.deleteArtifact({ owner, repo, artifact_id: artifact.id });
        deleted.push(artifact);
      } catch (error) {
        if (error && error.status === 404) {
          deleted.push({ ...artifact, already_absent: true });
        } else {
          errors.push({
            id: artifact.id,
            name: artifact.name,
            status: error && error.status ? error.status : null,
            message: error && error.message ? error.message : String(error)
          });
        }
      }
    }
  }

  const remaining = mode === 'apply'
    ? await listRunArtifacts(github, owner, repo, runId)
    : artifacts;
  const summary = {
    schema_version: 'fx2_release_bound_artifact_purge_receipt_v1',
    mode,
    repository: `${owner}/${repo}`,
    receipt_path: receiptPath,
    release_tag: receipt.release_tag,
    release_status: receipt.status,
    binding_run_id: runId,
    selected_count: artifacts.length,
    selected_bytes: selectedBytes,
    deleted_count: deleted.length,
    deleted_bytes: deleted.reduce((sum, artifact) => sum + Number(artifact.size_in_bytes || 0), 0),
    remaining_count: remaining.length,
    error_count: errors.length,
    errors,
    generated_at: new Date().toISOString()
  };

  const lines = [
    '## FX2 Release-bound Artifact Purge',
    '',
    `- Mode: \`${mode}\``,
    `- Receipt: \`${receiptPath}\``,
    `- Release: \`${receipt.release_tag}\``,
    `- Binding run: \`${runId}\``,
    `- Release readback: \`${receipt.status}\``,
    `- Selected: \`${artifacts.length}\` (${formatBytes(selectedBytes)})`,
    `- Deleted: \`${summary.deleted_count}\` (${formatBytes(summary.deleted_bytes)})`,
    `- Remaining for binding run: \`${summary.remaining_count}\``,
    `- Errors: \`${summary.error_count}\``,
    '',
    '| Artifact | Size | Created |',
    '|---|---:|---|'
  ];
  for (const artifact of artifacts) {
    lines.push(`| \`${artifact.name}\` | ${formatBytes(artifact.size_in_bytes)} | ${artifact.created_at} |`);
  }
  lines.push('', '<details><summary>Machine-readable receipt</summary>', '', '```json', JSON.stringify(summary), '```', '</details>');
  const markdown = lines.join('\n');
  await core.summary.addRaw(markdown).write();
  await github.rest.issues.createComment({
    owner,
    repo,
    issue_number: context.issue.number,
    body: markdown.slice(0, 65000)
  });

  if (errors.length > 0) core.setFailed(`${errors.length} artifact deletions failed`);
  if (mode === 'apply' && remaining.length > 0) {
    core.setFailed(`${remaining.length} artifacts remain after purge readback`);
  }
  return summary;
}

module.exports = {
  fetchJsonFile,
  formatBytes,
  listRunArtifacts,
  parseReceiptPath,
  run,
  validateReleaseBinding
};
