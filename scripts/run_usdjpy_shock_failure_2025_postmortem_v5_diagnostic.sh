#!/usr/bin/env bash
set -euo pipefail

source_script="scripts/run_usdjpy_shock_failure_2025_postmortem_v4.sh"
materialized="$RUNNER_TEMP/run_usdjpy_shock_failure_2025_postmortem_v5.sh"
python - "$source_script" "$materialized" <<'PY'
from pathlib import Path
import sys
src=Path(sys.argv[1]).read_text()
start=src.index('# Materialize the frozen analyzer')
end=src.index('# Frozen protocol and Core-derived evidence contract.')
replacement=r'''# Materialize the frozen checked-in source snapshot and replace only the incorrect file-count assertion.
snapshot="research/usdjpy/shock_failure/2025_external_gate_postmortem_v1/postmortem_source_snapshot.py"
test "$(git hash-object "$snapshot")" = "0c24aa7372dad2b6e00ff9fcc5e8b876b11a176b"
cp "$snapshot" tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py
python - <<'PY_ANALYZER'
from pathlib import Path
p=Path('tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py')
s=p.read_text()
old="  if len(self.files)<8000:raise RuntimeError(f'2025 hourly tick files indexed={len(self.files)}')"
new="""  manifests=list(self.root.rglob('usdjpy-2025-raw-ticks-v1.annual-manifest.json'))
  if len(manifests)==1:
   annual=json.loads(manifests[0].read_text(encoding='utf-8'))
   expected=sum(int(m['totals']['downloaded_hours']) for m in annual['months'])
   if len(self.files)!=expected:raise RuntimeError(f'2025 hourly tick files indexed={len(self.files)} expected={expected}')
  elif len(self.files)<6000:raise RuntimeError(f'2025 hourly tick files indexed={len(self.files)}')"""
assert s.count(old)==1
p.write_text(s.replace(old,new,1))
PY_ANALYZER
python -m py_compile tools/analyze_usdjpy_shock_failure_2025_postmortem_v1.py

'''
Path(sys.argv[2]).write_text(src[:start]+replacement+src[end:])
PY
chmod +x "$materialized"

root="$RUNNER_TEMP/shock-failure-postmortem-v4"
console="$RUNNER_TEMP/shock-failure-postmortem-v5-console.log"
rm -f "$console"
set +e
bash "$materialized" >"$console" 2>&1
code=$?
set -e
cat "$console"
mkdir -p "$root/diagnostics"
cp "$console" "$root/diagnostics/console.log"
printf '%s\n' "$code" > "$root/diagnostics/exit_code.txt"
if [[ "$code" -ne 0 ]]; then
  {
    echo "run_id=$GITHUB_RUN_ID"
    echo "exit_code=$code"
    echo "target_branch=agent/shock-failure-2025-postmortem-v1"
    echo "candidate_id=B_EXECUTABLE_T0_8BAR"
    echo "scientific_definition_changed=false"
    echo "source_snapshot_git_blob=0c24aa7372dad2b6e00ff9fcc5e8b876b11a176b"
    echo "---- console tail ----"
    tail -n 200 "$console"
  } > "$root/diagnostics/failure_summary.txt"
fi
exit "$code"
