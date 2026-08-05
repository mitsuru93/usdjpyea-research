'use strict';

const DAY_MS = 86400000;
const HOUR_MS = 3600000;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function normalizeName(value) {
  return String(value || '').trim().toLowerCase();
}

function familyKey(name) {
  return normalizeName(name)
    .replace(/[0-9a-f]{40}/g, '{sha}')
    .replace(/\b\d{8,}\b/g, '{run}')
    .replace(/-attempt-?\d+\b/g, '-attempt-{n}')
    .replace(/-\d+$/g, '-{n}');
}

function validatePolicy(policy) {
  if (!policy || policy.schema_version !== 'fx2_artifact_lifecycle_policy_v1') {
    throw new Error('unsupported artifact lifecycle policy schema');
  }
  for (const key of ['minimum_age_hours', 'keep_latest_global', 'keep_latest_per_family', 'max_deletions_per_run', 'default_retention_days']) {
    if (!Number.isInteger(policy[key]) || policy[key] < 0) throw new Error(`policy.${key} must be a non-negative integer`);
  }
  if (!Array.isArray(policy.categories) || policy.categories.length === 0) throw new Error('policy.categories is required');
  for (const category of policy.categories) {
    if (!category.id || !Number.isInteger(category.retention_days) || category.retention_days < 1) throw new Error('invalid category');
    if (!Array.isArray(category.patterns) || category.patterns.length === 0) throw new Error(`category ${category.id} requires patterns`);
  }
  return policy;
}

function classifyArtifact(name, policy) {
  const normalized = normalizeName(name);
  for (const pattern of policy.never_delete_patterns || []) {
    if (normalized.includes(normalizeName(pattern))) return { category: 'never_delete', retentionDays: null, protected: true };
  }
  for (const category of policy.categories) {
    if (category.patterns.some((pattern) => normalized.includes(normalizeName(pattern)))) {
      return { category: category.id, retentionDays: category.retention_days, protected: false };
    }
  }
  return { category: 'default', retentionDays: policy.default_retention_days, protected: false };
}

function buildPlan(artifacts, policy, options = {}) {
  validatePolicy(policy);
  const now = options.now instanceof Date ? options.now : new Date();
  const maxDeletions = Number.isInteger(options.maxDeletions) ? Math.max(0, options.maxDeletions) : policy.max_deletions_per_run;
  const sorted = [...artifacts].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  const globalKeep = new Set(sorted.slice(0, policy.keep_latest_global).map((artifact) => artifact.id));
  const familyCounts = new Map();
  const familyKeep = new Set();
  for (const artifact of sorted) {
    const key = familyKey(artifact.name);
    const count = familyCounts.get(key) || 0;
    if (count < policy.keep_latest_per_family) {
      familyKeep.add(artifact.id);
      familyCounts.set(key, count + 1);
    }
  }

  const decisions = sorted.map((artifact) => {
    const created = Date.parse(artifact.created_at);
    if (!Number.isFinite(created)) throw new Error(`artifact ${artifact.id} has invalid created_at`);
    const classification = classifyArtifact(artifact.name, policy);
    const ageMs = now.getTime() - created;
    const ageDays = ageMs / DAY_MS;
    let action = 'keep';
    let reason = 'within_retention';
    if (artifact.expired === true) {
      action = 'delete';
      reason = 'github_expired';
    } else if (classification.protected) {
      reason = 'explicit_never_delete_pattern';
    } else if (ageMs < policy.minimum_age_hours * HOUR_MS) {
      reason = 'minimum_age_guard';
    } else if (globalKeep.has(artifact.id)) {
      reason = 'latest_global_guard';
    } else if (familyKeep.has(artifact.id)) {
      reason = 'latest_family_guard';
    } else if (ageDays >= classification.retentionDays) {
      action = 'delete';
      reason = `older_than_${classification.retentionDays}d`;
    }
    return {
      artifact,
      action,
      reason,
      category: classification.category,
      retention_days: classification.retentionDays,
      family_key: familyKey(artifact.name),
      age_days: Number(ageDays.toFixed(3))
    };
  });

  const candidates = decisions.filter((item) => item.action === 'delete').sort((a, b) => {
    if (a.artifact.expired !== b.artifact.expired) return a.artifact.expired ? -1 : 1;
    return Date.parse(a.artifact.created_at) - Date.parse(b.artifact.created_at);
  });
  const selected = new Set(candidates.slice(0, maxDeletions).map((item) => item.artifact.id));
  for (const decision of decisions) {
    if (decision.action === 'delete' && !selected.has(decision.artifact.id)) {
      decision.action = 'defer';
      decision.reason = 'max_deletions_guard';
    }
  }
  return decisions;
}

function summarizePlan(decisions) {
  const summary = { total_artifacts: decisions.length, total_bytes: 0, delete_count: 0, delete_bytes: 0, defer_count: 0, defer_bytes: 0, keep_count: 0, categories: {} };
  for (const decision of decisions) {
    const bytes = Number(decision.artifact.size_in_bytes || 0);
    summary.total_bytes += bytes;
    summary.categories[decision.category] = (summary.categories[decision.category] || 0) + 1;
    if (decision.action === 'delete') {
      summary.delete_count += 1;
      summary.delete_bytes += bytes;
    } else if (decision.action === 'defer') {
      summary.defer_count += 1;
      summary.defer_bytes += bytes;
    } else summary.keep_count += 1;
  }
  return summary;
}

function formatBytes(bytes) {
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let value = Number(bytes || 0);
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toFixed(unit === 0 ? 0 : 2)} ${units[unit]}`;
}

async function deleteArtifactWithRetry(github, params, options = {}) {
  const attempts = Number.isInteger(options.attempts) ? Math.max(1, options.attempts) : 3;
  const baseDelayMs = Number.isInteger(options.baseDelayMs) ? Math.max(0, options.baseDelayMs) : 1000;
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      await github.rest.actions.deleteArtifact(params);
      return { status: 'deleted', attempts: attempt };
    } catch (error) {
      if (error && error.status === 404) return { status: 'already_absent', attempts: attempt };
      lastError = error;
      if (attempt < attempts) await sleep(baseDelayMs * (2 ** (attempt - 1)));
    }
  }
  const error = new Error(lastError && lastError.message ? lastError.message : 'artifact deletion failed');
  error.status = lastError && lastError.status;
  error.attempts = attempts;
  throw error;
}

function auditWorkflowText(text, path = 'workflow.yml') {
  const lines = String(text).split(/\r?\n/);
  const violations = [];
  for (let index = 0; index < lines.length; index += 1) {
    if (!/^\s*-?\s*uses:\s*actions\/upload-artifact@/i.test(lines[index])) continue;
    const baseIndent = lines[index].match(/^\s*/)[0].length;
    let retention = null;
    let allowLong = false;
    for (let cursor = index + 1; cursor < lines.length; cursor += 1) {
      const line = lines[cursor];
      const trimmed = line.trim();
      const indent = line.match(/^\s*/)[0].length;
      if (trimmed && indent <= baseIndent && /^-?\s*(name|uses|run|shell|if):/i.test(trimmed)) break;
      if (/artifact-policy:\s*allow-long-retention/i.test(line)) allowLong = true;
      const match = line.match(/^\s*retention-days:\s*['"]?(\d+)['"]?\s*(?:#.*)?$/i);
      if (match) retention = Number(match[1]);
    }
    if (retention === null) violations.push({ path, line: index + 1, code: 'MISSING_RETENTION_DAYS' });
    else if (retention > 30 && !allowLong) violations.push({ path, line: index + 1, code: 'RETENTION_OVER_30_DAYS', retention_days: retention });
    else if (retention < 1) violations.push({ path, line: index + 1, code: 'INVALID_RETENTION_DAYS', retention_days: retention });
  }
  return violations;
}

function runSelfTest(policy) {
  validatePolicy(policy);
  const checks = [];
  const expect = (condition, name) => { if (!condition) throw new Error(`self-test failed: ${name}`); checks.push(name); };
  expect(classifyArtifact('runner-health-probe', policy).retentionDays === 3, 'diagnostic-retention');
  expect(classifyArtifact('mt4-neutral-smoke', policy).retentionDays === 7, 'smoke-retention');
  expect(classifyArtifact('selected-authority-readback', policy).retentionDays === 14, 'binding-duplicate-retention');
  expect(auditWorkflowText('steps:\n  - uses: actions/upload-artifact@v4\n    with:\n      path: out').length === 1, 'retention-required');
  expect(auditWorkflowText('steps:\n  - uses: actions/upload-artifact@v4\n    with:\n      path: out\n      retention-days: 14').length === 0, 'bounded-retention-accepted');
  return { status: 'PASS', checks };
}

async function run({ github, context, core, policy, mode, maxDeletions }) {
  validatePolicy(policy);
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const artifacts = await github.paginate(github.rest.actions.listArtifactsForRepo, { owner, repo, per_page: 100 });
  const decisions = buildPlan(artifacts, policy, { maxDeletions: Number(maxDeletions) });
  const selected = decisions.filter((decision) => decision.action === 'delete');
  const deleted = [];
  const errors = [];
  if (mode === 'apply') {
    for (const decision of selected) {
      try {
        const result = await deleteArtifactWithRetry(github, { owner, repo, artifact_id: decision.artifact.id });
        deleted.push({ ...decision, deletion_status: result.status, deletion_attempts: result.attempts });
      } catch (error) {
        errors.push({ id: decision.artifact.id, name: decision.artifact.name, message: error.message, status: error.status || null, attempts: error.attempts || 3 });
      }
    }
  }
  const summary = summarizePlan(decisions);
  Object.assign(summary, {
    mode,
    deleted_count: deleted.length,
    deleted_bytes: deleted.reduce((sum, item) => sum + Number(item.artifact.size_in_bytes || 0), 0),
    already_absent_count: deleted.filter((item) => item.deletion_status === 'already_absent').length,
    error_count: errors.length,
    deletion_errors: errors,
    generated_at: new Date().toISOString(),
    repository: `${owner}/${repo}`
  });
  const lines = [
    '## FX2 Artifact Lifecycle Controller', '',
    `- Mode: \`${mode}\``,
    `- Artifacts inspected: \`${summary.total_artifacts}\` (${formatBytes(summary.total_bytes)})`,
    `- Selected: \`${summary.delete_count}\` (${formatBytes(summary.delete_bytes)})`,
    `- Deferred by cap: \`${summary.defer_count}\` (${formatBytes(summary.defer_bytes)})`,
    `- Deleted: \`${summary.deleted_count}\` (${formatBytes(summary.deleted_bytes)})`,
    `- Errors: \`${summary.error_count}\``, '',
    '| Artifact | Category | Age | Size | Reason |', '|---|---:|---:|---:|---|'
  ];
  for (const decision of selected.slice(0, 50)) lines.push(`| \`${decision.artifact.name}\` | ${decision.category} | ${decision.age_days}d | ${formatBytes(decision.artifact.size_in_bytes)} | ${decision.reason} |`);
  if (selected.length > 50) lines.push(`| ... | ... | ... | ... | ${selected.length - 50} additional selected items omitted |`);
  if (errors.length) lines.push('', '### Deletion errors', '', '```json', JSON.stringify(errors, null, 2), '```');
  await core.summary.addRaw(lines.join('\n')).write();
  core.setOutput('receipt_json', JSON.stringify(summary));
  core.setOutput('deleted_count', String(summary.deleted_count));
  core.setOutput('deleted_bytes', String(summary.deleted_bytes));
  core.setOutput('error_count', String(summary.error_count));
  core.setOutput('remaining_candidate_count', String(summary.defer_count));
  if (errors.length) core.setFailed(`${errors.length} artifact deletions failed`);
  return summary;
}

module.exports = { auditWorkflowText, buildPlan, classifyArtifact, deleteArtifactWithRetry, familyKey, formatBytes, run, runSelfTest, summarizePlan, validatePolicy };
