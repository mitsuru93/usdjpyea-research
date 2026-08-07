'use strict';

const fs = require('fs');

const DAY_MS = 24 * 60 * 60 * 1000;
const HOUR_MS = 60 * 60 * 1000;

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function normalizeName(value) {
  return String(value || '').trim().toLowerCase();
}

// Existing broad family key retained for ordinary retention guards.
function familyKey(name) {
  return normalizeName(name)
    .replace(/[0-9a-f]{40}/g, '{sha}')
    .replace(/\b\d{8,}\b/g, '{run}')
    .replace(/-attempt-?\d+\b/g, '-attempt-{n}')
    .replace(/-\d+$/g, '-{n}');
}

// Conservative key for accelerated duplicate pruning. It strips only an
// unambiguous Actions run id and its attempt suffix. Four-digit years,
// candidate numbers, versions, and SHA values remain distinct.
function duplicateFamilyKey(name) {
  return normalizeName(name)
    .replace(/\b\d{8,}\b/g, '{run}')
    .replace(/-attempt-?\d+\b/g, '-attempt-{n}')
    .replace(/\{run\}-\d+$/g, '{run}-{attempt}');
}

function validatePolicy(policy) {
  if (!policy || policy.schema_version !== 'fx2_artifact_lifecycle_policy_v1') {
    throw new Error('unsupported artifact lifecycle policy schema');
  }
  for (const key of [
    'minimum_age_hours',
    'keep_latest_global',
    'keep_latest_per_family',
    'max_deletions_per_run',
    'default_retention_days'
  ]) {
    if (!Number.isInteger(policy[key]) || policy[key] < 0) {
      throw new Error(`policy.${key} must be a non-negative integer`);
    }
  }
  if (!Array.isArray(policy.categories) || policy.categories.length === 0) {
    throw new Error('policy.categories must be a non-empty array');
  }
  for (const category of policy.categories) {
    if (!category.id || !Number.isInteger(category.retention_days) || category.retention_days < 1) {
      throw new Error('each category requires id and positive integer retention_days');
    }
    if (!Array.isArray(category.patterns) || category.patterns.length === 0) {
      throw new Error(`category ${category.id} requires patterns`);
    }
  }
  const duplicate = policy.duplicate_prune;
  if (duplicate !== undefined) {
    if (!duplicate || typeof duplicate !== 'object' || typeof duplicate.enabled !== 'boolean') {
      throw new Error('policy.duplicate_prune requires enabled boolean');
    }
    for (const key of ['minimum_age_hours', 'keep_latest_exact_digest', 'keep_latest_regenerable_family']) {
      if (!Number.isInteger(duplicate[key]) || duplicate[key] < 0) {
        throw new Error(`policy.duplicate_prune.${key} must be a non-negative integer`);
      }
    }
    for (const key of ['regenerable_patterns', 'exempt_patterns']) {
      if (!Array.isArray(duplicate[key])) {
        throw new Error(`policy.duplicate_prune.${key} must be an array`);
      }
    }
  }
  return policy;
}

function classifyArtifact(name, policy) {
  const normalized = normalizeName(name);
  for (const pattern of policy.never_delete_patterns || []) {
    if (normalized.includes(normalizeName(pattern))) {
      return { category: 'never_delete', retentionDays: null, protected: true };
    }
  }
  for (const category of policy.categories) {
    if (category.patterns.some((pattern) => normalized.includes(normalizeName(pattern)))) {
      return {
        category: category.id,
        retentionDays: category.retention_days,
        protected: false
      };
    }
  }
  return { category: 'default', retentionDays: policy.default_retention_days, protected: false };
}

function ageMilliseconds(artifact, now) {
  const created = Date.parse(artifact.created_at);
  if (!Number.isFinite(created)) throw new Error(`artifact ${artifact.id} has invalid created_at`);
  return now.getTime() - created;
}

function matchesAny(name, patterns) {
  const normalized = normalizeName(name);
  return (patterns || []).some((pattern) => normalized.includes(normalizeName(pattern)));
}

function addNewestToKeep(sorted, keyFn, keepCount) {
  const counts = new Map();
  const totals = new Map();
  const keep = new Set();
  for (const artifact of sorted) {
    const key = keyFn(artifact);
    if (!key) continue;
    totals.set(key, (totals.get(key) || 0) + 1);
    const count = counts.get(key) || 0;
    if (count < keepCount) {
      keep.add(artifact.id);
      counts.set(key, count + 1);
    }
  }
  return { keep, totals };
}

function buildPlan(artifacts, policy, options = {}) {
  validatePolicy(policy);
  const now = options.now instanceof Date ? options.now : new Date();
  const maxDeletions = Number.isInteger(options.maxDeletions)
    ? Math.max(0, options.maxDeletions)
    : policy.max_deletions_per_run;
  const sorted = [...artifacts].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  const globalKeep = new Set(sorted.slice(0, policy.keep_latest_global).map((artifact) => artifact.id));

  const ordinaryFamily = addNewestToKeep(
    sorted,
    (artifact) => familyKey(artifact.name),
    policy.keep_latest_per_family
  );

  const duplicate = policy.duplicate_prune || {
    enabled: false,
    minimum_age_hours: policy.minimum_age_hours,
    keep_latest_exact_digest: 1,
    keep_latest_regenerable_family: policy.keep_latest_per_family,
    regenerable_patterns: [],
    exempt_patterns: []
  };

  const digestGroups = addNewestToKeep(
    sorted,
    (artifact) => {
      const digest = String(artifact.digest || '').trim().toLowerCase();
      return digest ? `digest:${digest}` : null;
    },
    duplicate.keep_latest_exact_digest
  );

  const regenerableGroups = addNewestToKeep(
    sorted,
    (artifact) => {
      if (!matchesAny(artifact.name, duplicate.regenerable_patterns)) return null;
      if (matchesAny(artifact.name, duplicate.exempt_patterns)) return null;
      const size = Number(artifact.size_in_bytes || 0);
      return `family-size:${duplicateFamilyKey(artifact.name)}:${size}`;
    },
    duplicate.keep_latest_regenerable_family
  );

  const decisions = [];
  for (const artifact of sorted) {
    const classification = classifyArtifact(artifact.name, policy);
    const ageMs = ageMilliseconds(artifact, now);
    const ageDays = ageMs / DAY_MS;
    const digest = String(artifact.digest || '').trim().toLowerCase();
    const digestKey = digest ? `digest:${digest}` : null;
    const regenerable = matchesAny(artifact.name, duplicate.regenerable_patterns)
      && !matchesAny(artifact.name, duplicate.exempt_patterns);
    const regenerableKey = regenerable
      ? `family-size:${duplicateFamilyKey(artifact.name)}:${Number(artifact.size_in_bytes || 0)}`
      : null;

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
    } else if (
      duplicate.enabled
      && ageMs >= duplicate.minimum_age_hours * HOUR_MS
      && digestKey
      && (digestGroups.totals.get(digestKey) || 0) > duplicate.keep_latest_exact_digest
      && !digestGroups.keep.has(artifact.id)
    ) {
      action = 'delete';
      reason = 'byte_identical_digest_duplicate';
    } else if (
      duplicate.enabled
      && ageMs >= duplicate.minimum_age_hours * HOUR_MS
      && regenerableKey
      && (regenerableGroups.totals.get(regenerableKey) || 0) > duplicate.keep_latest_regenerable_family
      && !regenerableGroups.keep.has(artifact.id)
    ) {
      action = 'delete';
      reason = 'regenerable_same_family_same_size_duplicate';
    } else if (ordinaryFamily.keep.has(artifact.id)) {
      reason = 'latest_family_guard';
    } else if (ageDays >= classification.retentionDays) {
      action = 'delete';
      reason = `older_than_${classification.retentionDays}d`;
    }

    decisions.push({
      artifact,
      action,
      reason,
      category: classification.category,
      retention_days: classification.retentionDays,
      family_key: familyKey(artifact.name),
      duplicate_family_key: duplicateFamilyKey(artifact.name),
      age_days: Number(ageDays.toFixed(3))
    });
  }

  const deleteCandidates = decisions
    .filter((decision) => decision.action === 'delete')
    .sort((a, b) => {
      if (a.artifact.expired !== b.artifact.expired) return a.artifact.expired ? -1 : 1;
      return Date.parse(a.artifact.created_at) - Date.parse(b.artifact.created_at);
    });
  const selectedIds = new Set(deleteCandidates.slice(0, maxDeletions).map((decision) => decision.artifact.id));
  for (const decision of decisions) {
    if (decision.action === 'delete' && !selectedIds.has(decision.artifact.id)) {
      decision.planned_reason = decision.reason;
      decision.action = 'defer';
      decision.reason = 'max_deletions_guard';
    }
  }
  return decisions;
}

function summarizePlan(decisions) {
  const summary = {
    total_artifacts: decisions.length,
    total_bytes: 0,
    delete_count: 0,
    delete_bytes: 0,
    defer_count: 0,
    defer_bytes: 0,
    keep_count: 0,
    categories: {},
    selected_reasons: {},
    deferred_reasons: {}
  };
  for (const decision of decisions) {
    const bytes = Number(decision.artifact.size_in_bytes || 0);
    summary.total_bytes += bytes;
    summary.categories[decision.category] = (summary.categories[decision.category] || 0) + 1;
    if (decision.action === 'delete') {
      summary.delete_count += 1;
      summary.delete_bytes += bytes;
      summary.selected_reasons[decision.reason] = (summary.selected_reasons[decision.reason] || 0) + 1;
    } else if (decision.action === 'defer') {
      summary.defer_count += 1;
      summary.defer_bytes += bytes;
      const reason = decision.planned_reason || decision.reason;
      summary.deferred_reasons[reason] = (summary.deferred_reasons[reason] || 0) + 1;
    } else {
      summary.keep_count += 1;
    }
  }
  return summary;
}

function formatBytes(bytes) {
  if (!Number.isFinite(Number(bytes)) || Number(bytes) < 0) return '0 B';
  const units = ['B', 'KiB', 'MiB', 'GiB', 'TiB'];
  let value = Number(bytes || 0);
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 2)} ${units[unit]}`;
}

async function deleteArtifactWithRetry(github, params, options = {}) {
  const attempts = Number.isInteger(options.attempts) ? Math.max(1, options.attempts) : 3;
  const baseDelayMs = Number.isInteger(options.baseDelayMs) ? Math.max(0, options.baseDelayMs) : 1000;
  let lastError = null;
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
  const now = new Date('2026-08-07T00:00:00Z');
  const make = (id, name, ageDays, extra = {}) => ({
    id,
    name,
    size_in_bytes: 100,
    digest: `sha256:${id}`,
    expired: false,
    created_at: new Date(now.getTime() - ageDays * DAY_MS).toISOString(),
    ...extra
  });
  const checks = [];
  const expect = (condition, name) => {
    if (!condition) throw new Error(`self-test failed: ${name}`);
    checks.push(name);
  };
  expect(classifyArtifact('runner-health-probe', policy).retentionDays === 3, 'diagnostic-retention');
  expect(classifyArtifact('mt4-neutral-smoke', policy).retentionDays === 7, 'smoke-retention');
  expect(classifyArtifact('selected-authority-readback', policy).retentionDays === 14, 'binding-duplicate-retention');

  const testPolicy = {
    ...policy,
    keep_latest_global: 0,
    duplicate_prune: {
      ...policy.duplicate_prune,
      enabled: true,
      minimum_age_hours: 24,
      keep_latest_exact_digest: 1,
      keep_latest_regenerable_family: 2
    }
  };
  const digestPlan = buildPlan([
    make(1, 'opaque-a', 3, { digest: 'sha256:same' }),
    make(2, 'opaque-b', 2, { digest: 'sha256:same' }),
    make(3, 'opaque-c', 1.5, { digest: 'sha256:same' })
  ], testPolicy, { now, maxDeletions: 10 });
  expect(digestPlan.filter((item) => item.reason === 'byte_identical_digest_duplicate').length === 2, 'exact-digest-prune');

  const familyPlan = buildPlan([
    make(10, 'mt4-parity-30000000010-1', 4, { size_in_bytes: 500, digest: 'sha256:a' }),
    make(11, 'mt4-parity-30000000011-1', 3, { size_in_bytes: 500, digest: 'sha256:b' }),
    make(12, 'mt4-parity-30000000012-1', 2, { size_in_bytes: 500, digest: 'sha256:c' }),
    make(13, 'mt4-parity-30000000013-1', 1.5, { size_in_bytes: 500, digest: 'sha256:d' })
  ], testPolicy, { now, maxDeletions: 10 });
  expect(familyPlan.filter((item) => item.reason === 'regenerable_same_family_same_size_duplicate').length === 2, 'regenerable-family-prune');

  const protectedPlan = buildPlan([
    make(20, 'dukascopy-tick-2020-parity-30000000020-1', 4, { size_in_bytes: 500, digest: 'sha256:u1' }),
    make(21, 'dukascopy-tick-2020-parity-30000000021-1', 3, { size_in_bytes: 500, digest: 'sha256:u2' }),
    make(22, 'dukascopy-tick-2020-parity-30000000022-1', 2, { size_in_bytes: 500, digest: 'sha256:u3' })
  ], testPolicy, { now, maxDeletions: 10 });
  expect(protectedPlan.every((item) => item.action === 'keep'), 'source-data-exempt-from-family-prune');

  const expiredPlan = buildPlan([make(30, 'fresh-expired', 0.1, { expired: true })], testPolicy, { now, maxDeletions: 10 });
  expect(expiredPlan[0].action === 'delete', 'expired-first');
  expect(auditWorkflowText('steps:\n  - uses: actions/upload-artifact@v4\n    with:\n      path: out').length === 1, 'retention-required');
  expect(auditWorkflowText('steps:\n  - uses: actions/upload-artifact@v4\n    with:\n      path: out\n      retention-days: 14').length === 0, 'bounded-retention-accepted');
  return { status: 'PASS', checks };
}

async function loadArtifacts(github, owner, repo) {
  return github.paginate(github.rest.actions.listArtifactsForRepo, { owner, repo, per_page: 100 });
}

async function run({ github, context, core, policyPath, policy: policyInput, mode, maxDeletions }) {
  const policy = validatePolicy(policyInput || JSON.parse(fs.readFileSync(policyPath, 'utf8')));
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const artifacts = await loadArtifacts(github, owner, repo);
  const decisions = buildPlan(artifacts, policy, {
    maxDeletions: Number.isFinite(Number(maxDeletions)) ? Number(maxDeletions) : undefined
  });
  const selected = decisions.filter((decision) => decision.action === 'delete');
  const errors = [];
  const deleted = [];

  if (mode === 'apply') {
    for (const decision of selected) {
      try {
        const result = await deleteArtifactWithRetry(github, {
          owner,
          repo,
          artifact_id: decision.artifact.id
        });
        deleted.push({ ...decision, deletion_status: result.status, deletion_attempts: result.attempts });
      } catch (error) {
        errors.push({
          id: decision.artifact.id,
          name: decision.artifact.name,
          message: error.message,
          status: error.status || null,
          attempts: error.attempts || 3
        });
      }
    }
  }

  const summary = summarizePlan(decisions);
  Object.assign(summary, {
    mode,
    deleted_count: deleted.length,
    deleted_bytes: deleted.reduce((sum, decision) => sum + Number(decision.artifact.size_in_bytes || 0), 0),
    error_count: errors.length,
    deletion_errors: errors,
    already_absent_count: deleted.filter((decision) => decision.deletion_status === 'already_absent').length,
    generated_at: new Date().toISOString(),
    repository: `${owner}/${repo}`
  });

  const lines = [
    '## FX2 Artifact Lifecycle Controller',
    '',
    `- Mode: \`${mode}\``,
    `- Artifacts inspected: \`${summary.total_artifacts}\` (${formatBytes(summary.total_bytes)})`,
    `- Selected for deletion: \`${summary.delete_count}\` (${formatBytes(summary.delete_bytes)})`,
    `- Deleted: \`${summary.deleted_count}\` (${formatBytes(summary.deleted_bytes)})`,
    `- Deferred by safety cap: \`${summary.defer_count}\` (${formatBytes(summary.defer_bytes)})`,
    `- Already absent (idempotent success): \`${summary.already_absent_count}\``,
    `- Errors: \`${summary.error_count}\``,
    `- Selection reasons: \`${JSON.stringify(summary.selected_reasons)}\``,
    '',
    '| Artifact | Category | Age | Size | Reason |',
    '|---|---:|---:|---:|---|'
  ];
  for (const decision of selected.slice(0, 50)) {
    lines.push(`| \`${decision.artifact.name}\` | ${decision.category} | ${decision.age_days}d | ${formatBytes(Number(decision.artifact.size_in_bytes || 0))} | ${decision.reason} |`);
  }
  if (selected.length > 50) lines.push(`| ... | ... | ... | ... | ${selected.length - 50} additional candidates omitted |`);
  if (errors.length > 0) lines.push('', '### Deletion errors', '', '```json', JSON.stringify(errors, null, 2), '```');
  const markdown = lines.join('\n');
  await core.summary.addRaw(markdown).write();

  core.setOutput('receipt_json', JSON.stringify(summary));
  core.setOutput('selected_count', String(summary.delete_count));
  core.setOutput('deleted_count', String(summary.deleted_count));
  core.setOutput('deleted_bytes', String(summary.deleted_bytes));
  core.setOutput('error_count', String(summary.error_count));
  core.setOutput('remaining_candidate_count', String(summary.defer_count));
  core.setOutput('summary_markdown', markdown);

  if (errors.length > 0) core.setFailed(`${errors.length} artifact deletions failed`);
  return { policy, decisions, summary, errors, markdown };
}

module.exports = {
  auditWorkflowText,
  buildPlan,
  classifyArtifact,
  deleteArtifactWithRetry,
  duplicateFamilyKey,
  familyKey,
  formatBytes,
  loadArtifacts,
  normalizeName,
  run,
  runSelfTest,
  summarizePlan,
  validatePolicy
};
