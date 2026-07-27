#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_REPOSITORY:?}"
: "${GITHUB_RUN_ID:?}"
: "${GITHUB_TOKEN:?}"

export GH_TOKEN="$GITHUB_TOKEN"
TARGET_BRANCH="agent/shock-failure-2025-postmortem-v1"
PHASE2_RELEASE="usdjpy-csos-shock-failure-phase2-v1"
PHASE2_ASSET="usdjpy-csos-shock-failure-phase2-v1-30206226997-1.zip"
RELEASE_TAG="usdjpy-shock-failure-2025-postmortem-v1-r1"
MT4_CONTEXT_DIR="research_inputs/usdjpy/shock_failure/2025_postmortem_v1"
CORRECTED_P6="$MT4_CONTEXT_DIR/corrected_p6_result_compact.json"
BRANCH_SHA="$(git rev-parse HEAD)"
PM_ROOT="$RUNNER_TEMP/shock-failure-postmortem-v4"
export TARGET_BRANCH PHASE2_RELEASE PHASE2_ASSET RELEASE_TAG MT4_CONTEXT_DIR CORRECTED_P6 BRANCH_SHA PM_ROOT
rm -rf "$PM_ROOT"
mkdir -p "$PM_ROOT"/{phase2-download,phase2,raw-download,raw,out,release,readback}
echo "PM_ROOT=$PM_ROOT" >> "$GITHUB_ENV"

# Materialize the frozen analyzer and replace only the incorrect file-count assertion.
cat tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py.gz.b64.part* > "$RUNNER_TEMP/analyzer.b64"
test "$(sha256sum "$RUNNER_TEMP/analyzer.b64" | awk '{print $1}')" = "dcd939525e2b602d92c16f99a827ed021c708277a4983e7af00a81a4a10bbeb1"
base64 -d "$RUNNER_TEMP/analyzer.b64" | gzip -d > tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py
python - <<'PY'
from pathlib import Path
p=Path('tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py')
s=p.read_text()
old="   if len(self.files)<8000:raise RuntimeError(f'2025 hourly tick files indexed={len(self.files)}')"
new="""   manifests=list(self.root.rglob('usdjpy-2025-raw-ticks-v1.annual-manifest.json'))
   if len(manifests)==1:
    annual=json.loads(manifests[0].read_text(encoding='utf-8'))
    expected=sum(int(m['totals']['downloaded_hours']) for m in annual['months'])
    if len(self.files)!=expected:raise RuntimeError(f'2025 hourly tick files indexed={len(self.files)} expected={expected}')
   elif len(self.files)<6000:raise RuntimeError(f'2025 hourly tick files indexed={len(self.files)}')"""
assert s.count(old)==1
p.write_text(s.replace(old,new,1))
PY
python -m py_compile tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py

# Frozen protocol and Core-derived evidence contract.
python - <<'PY'
import glob,json
p=json.load(open('configs/research/usdjpy_shock_failure_2025_postmortem_protocol_v1.json'))
assert p['status']=='FROZEN_NO_CANDIDATE_SELECTION'
assert p['candidate_id']=='B_EXECUTABLE_T0_8BAR'
assert p['fixed_candidate_changes_permitted'] is False
assert p['consumed_external_evidence']==['2025H1','2025H2']
assert p['oracle_exit_label']=='ORACLE_DIAGNOSTIC_NOT_IMPLEMENTABLE_CANDIDATE'
assert p['production_authorized'] is False and p['live_orders_authorized'] is False
files=sorted(glob.glob('research_inputs/usdjpy/shock_failure/2025_postmortem_v1/mt4_events_*.json'))
assert len(files)==5
events=[]
for path in files:
    x=json.load(open(path))
    assert x['authority']['core_run_id']==30229496015
    assert x['authority']['core_artifact_id']==8639969385
    assert x['authority']['core_artifact_sha256']=='70088c66cd1014391cabbb6f533462dcd3dbedbd7d6c537a5dc0798343594a6a'
    events.extend(x['events'])
assert len(events)==47 and len({x['event_id'] for x in events})==47
p6=json.load(open('research_inputs/usdjpy/shock_failure/2025_postmortem_v1/corrected_p6_result_compact.json'))
assert p6['candidate_id']=='B_EXECUTABLE_T0_8BAR'
assert p6['status']=='FAIL_P6_2025_GATE_RESEARCH_ONLY_NO_RETUNING'
assert p6['standalone_combined']['closed_trades']==47
assert abs(p6['standalone_combined']['net_jpy']+1277.0)<1e-6
assert p6['scientific_semantics']=='IDENTICAL_TO_PREREGISTERED_P6_EVALUATOR'
print('PASS_FIXED_RESEARCH_INPUTS')
PY

# Phase 2 immutable authority.
gh release download "$PHASE2_RELEASE" --repo "$GITHUB_REPOSITORY" --dir "$PM_ROOT/phase2-download" --pattern "$PHASE2_ASSET"
unzip -q "$PM_ROOT/phase2-download/$PHASE2_ASSET" -d "$PM_ROOT/phase2"
(cd "$PM_ROOT/phase2/phase2_output" && sha256sum -c PACKAGE_SHA256SUMS)
python - <<'PY'
import os,pandas as pd
p=os.path.join(os.environ['PM_ROOT'],'phase2','phase2_output','candidate_trade_ledger.csv.gz')
d=pd.read_csv(p)
x=d[(d.candidate_id=='B_EXECUTABLE_T0_8BAR') & d.admitted.fillna(False)]
assert len(x)==114
assert set(x['fold'])=={'2023H1','2023H2','2024H1','2024H2'}
print('PASS_PHASE2_LEDGER',len(x))
PY

# 2025 immutable Raw Bid/Ask Tick authority.
gh release download usdjpy-2025-raw-bidask-ticks-v1 --repo "$GITHUB_REPOSITORY" --dir "$PM_ROOT/raw-download" \
  --pattern 'usdjpy-2025-??-raw-ticks-v1.tar.gz' \
  --pattern usdjpy-2025-raw-ticks-v1.annual-manifest.json \
  --pattern SHA256SUMS
test "$(find "$PM_ROOT/raw-download" -maxdepth 1 -name 'usdjpy-2025-??-raw-ticks-v1.tar.gz' | wc -l)" = 12
(cd "$PM_ROOT/raw-download" && grep -E 'usdjpy-2025-(..-raw-ticks-v1\.tar\.gz|raw-ticks-v1\.annual-manifest\.json)$' SHA256SUMS | sha256sum -c -)
jq -e '.accepted==true and .resolved_hours==.expected_hours and .tick_rows>0' "$PM_ROOT/raw-download/usdjpy-2025-raw-ticks-v1.annual-manifest.json"
for a in "$PM_ROOT"/raw-download/usdjpy-2025-??-raw-ticks-v1.tar.gz; do
  tar -xzf "$a" -C "$PM_ROOT/raw"
done
cp "$PM_ROOT/raw-download/usdjpy-2025-raw-ticks-v1.annual-manifest.json" "$PM_ROOT/raw/"
expected="$(jq '[.months[].totals.downloaded_hours] | add' "$PM_ROOT/raw/usdjpy-2025-raw-ticks-v1.annual-manifest.json")"
actual="$(find "$PM_ROOT/raw" -type f -name '*.csv.gz' | wc -l)"
test "$actual" = "$expected"
echo "PASS_RAW_2025_HOURLY_FILES=$actual/$expected"

# Fixed-candidate postmortem. No tuning or candidate selection occurs here.
python tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py \
  --phase2-dir "$PM_ROOT/phase2" \
  --mt4-context-dir "$MT4_CONTEXT_DIR" \
  --raw-2025-root "$PM_ROOT/raw" \
  --corrected-p6 "$CORRECTED_P6" \
  --out-dir "$PM_ROOT/out" \
  --research-sha "$BRANCH_SHA" \
  --core-sha 0dfec6a7a9245acecbd8961a4e784efde857ef69 \
  --run-id "$GITHUB_RUN_ID" | tee "$PM_ROOT/out/run.log"
jq -e '.candidate_id=="B_EXECUTABLE_T0_8BAR" and .fixed_candidate_status=="REJECTED_FOR_PRODUCTION_AND_PORTABLE_CORE_ADOPTION" and .no_retuning==true and ."2025_consumed"==true and ."2025_reusable_as_holdout"==false' "$PM_ROOT/out/final_decision.json"
test "$(($(gzip -cd "$PM_ROOT/out/2025_event_ledger.csv.gz" | wc -l)-1))" = 47
grep -q ORACLE_DIAGNOSTIC_NOT_IMPLEMENTABLE_CANDIDATE "$PM_ROOT/out/oracle_exit_diagnostics.csv"
(cd "$PM_ROOT/out" && sha256sum -c SHA256SUMS)

# Final deterministic evidence package.
cp tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py "$PM_ROOT/out/postmortem_source_snapshot.py"
cp configs/research/usdjpy_shock_failure_2025_postmortem_protocol_v1.json "$PM_ROOT/out/"
cp "$CORRECTED_P6" "$PM_ROOT/out/corrected_p6_result.json"
cp "$MT4_CONTEXT_DIR"/mt4_events_*.json "$PM_ROOT/out/"
cp "$PM_ROOT/raw/usdjpy-2025-raw-ticks-v1.annual-manifest.json" "$PM_ROOT/out/"
rm -f "$PM_ROOT/out/manifest.json" "$PM_ROOT/out/SHA256SUMS"
python - <<'PY'
import hashlib,json,os
from pathlib import Path
root=Path(os.environ['PM_ROOT'])/'out'
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()
rows=[{'path':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(root.iterdir()) if p.is_file() and p.name not in {'manifest.json','SHA256SUMS'}]
(root/'manifest.json').write_text(json.dumps({'schema_version':'usdjpy_shock_failure_2025_postmortem_manifest_v1','files':rows},indent=2,sort_keys=True)+'\n')
with (root/'SHA256SUMS').open('w') as f:
    for p in sorted(root.iterdir()):
        if p.is_file() and p.name!='SHA256SUMS': f.write(f'{sha(p)}  {p.name}\n')
PY
(cd "$PM_ROOT/out" && sha256sum -c SHA256SUMS)

# Canonical branch output.
target="research/usdjpy/shock_failure/2025_external_gate_postmortem_v1"
rm -rf "$target"
mkdir -p "$target"
cp "$PM_ROOT/out"/* "$target/"
git config user.name github-actions[bot]
git config user.email 41898282+github-actions[bot]@users.noreply.github.com
git add "$target"
if ! git diff --cached --quiet; then
  git commit -m 'research: record completed Shock Failure 2025 postmortem'
  git push origin "HEAD:$TARGET_BRANCH"
fi
PUBLICATION_SHA="$(git rev-parse HEAD)"
export PUBLICATION_SHA
echo "PUBLICATION_SHA=$PUBLICATION_SHA" >> "$GITHUB_ENV"

# Immutable Release and readback.
tar -czf "$PM_ROOT/release/usdjpy-shock-failure-2025-postmortem-v1-r1.tar.gz" -C "$PM_ROOT/out" .
cp "$PM_ROOT/out/manifest.json" "$PM_ROOT/out/SHA256SUMS" "$PM_ROOT/release/"
(cd "$PM_ROOT/release" && sha256sum usdjpy-shock-failure-2025-postmortem-v1-r1.tar.gz manifest.json SHA256SUMS > RELEASE_SHA256SUMS)
if ! gh release view "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" >/dev/null 2>&1; then
  decision="$(jq -r .decision "$PM_ROOT/out/final_decision.json")"
  gh release create "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --target "$PUBLICATION_SHA" \
    --title 'USDJPY Shock Failure 2025 External-Gate Postmortem v1-r1' \
    --notes "Fixed candidate B_EXECUTABLE_T0_8BAR postmortem. Decision: $decision. No retuning; 2025 is consumed external evidence; production and live orders remain unauthorized."
  gh release upload "$RELEASE_TAG" "$PM_ROOT/release"/* --repo "$GITHUB_REPOSITORY"
fi
gh release download "$RELEASE_TAG" --repo "$GITHUB_REPOSITORY" --dir "$PM_ROOT/readback"
(cd "$PM_ROOT/readback" && sha256sum -c RELEASE_SHA256SUMS)

# PR receipt.
python - <<'PY'
import json,os
from pathlib import Path
root=Path(os.environ['PM_ROOT'])
x=json.loads((root/'out'/'final_decision.json').read_text())
d=x['diagnostics']
body=("## Shock Failure 2025 postmortem completed\n\n"
      f"- Run: `{os.environ['GITHUB_RUN_ID']}`\n"
      f"- Decision: `{x['decision']}`\n"
      f"- Fixed candidate: `{x['fixed_candidate_status']}`\n"
      f"- Family: `{x['family_status']}`\n"
      f"- MT4 net/PF: `{d['mt4_combined_net_jpy']:.0f} JPY / {d['mt4_pf']:.3f}`\n"
      f"- Raw-source identity match: `{d['raw_identity_match_rate']:.1%}`\n"
      f"- 2025 reusable as holdout: `{str(x['2025_reusable_as_holdout']).lower()}`\n"
      f"- Release: `{os.environ['RELEASE_TAG']}`\n"
      f"- Publication commit: `{os.environ['PUBLICATION_SHA']}`\n\n"
      "No candidate parameter, side, session, threshold, failure rule, entry timing, timeout, spread convention, Bid/Ask convention, or B02/F05 semantic was changed.")
(root/'pr-comment.md').write_text(body)
PY
gh pr comment 320 --repo "$GITHUB_REPOSITORY" --body-file "$PM_ROOT/pr-comment.md"
