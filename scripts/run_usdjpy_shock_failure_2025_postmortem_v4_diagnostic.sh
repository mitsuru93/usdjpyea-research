#!/usr/bin/env bash
set -uo pipefail

root="$RUNNER_TEMP/shock-failure-postmortem-v4"
console="$RUNNER_TEMP/shock-failure-postmortem-v4-console.log"
rm -f "$console"

set +e
bash scripts/run_usdjpy_shock_failure_2025_postmortem_v4.sh >"$console" 2>&1
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
    echo "---- console tail ----"
    tail -n 160 "$console"
  } > "$root/diagnostics/failure_summary.txt"
fi
exit "$code"
