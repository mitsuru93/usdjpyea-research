#!/usr/bin/env bash
set -euo pipefail

finalizer_b64="$RUNNER_TEMP/shock-postmortem-r2-finalizer.b64"
finalizer="$RUNNER_TEMP/shock-postmortem-r2-finalizer.sh"
evidence="$RUNNER_TEMP/shock-failure-postmortem-v4"
mkdir -p "$evidence"

: > "$finalizer_b64"
for n in 00 01 02 03 04 05; do
  cat "tools/finalize_usdjpy_shock_failure_2025_postmortem_r2.sh.b64.part$n" >> "$finalizer_b64"
done
test "$(sha256sum "$finalizer_b64" | awk '{print $1}')" = 7a4d10dd82d21c15a3f225ae2711122a632a81a2559a22162a24569af47ffdc6
base64 -d "$finalizer_b64" > "$finalizer"
test "$(sha256sum "$finalizer" | awk '{print $1}')" = 9b188e655795a9f5fb5de1f31b5bd5c503fc834e47f9a3178db7b007648d9c3e
bash -n "$finalizer"
python -m pip install --disable-pip-version-check 'pytest==8.3.4'

git fetch --no-tags origin main
git checkout -B main origin/main
export HEAD_SHA="$(git rev-parse HEAD)"
export HEAD_BRANCH=main
export GH_TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN is required}"

set +e
bash "$finalizer" > >(tee "$evidence/finalizer_stdout.log") 2> >(tee "$evidence/finalizer_stderr.log" >&2)
code=$?
set -e
printf '%s\n' "$code" > "$evidence/finalizer_exit_code.txt"
if [[ -d "$RUNNER_TEMP/shock-failure-postmortem-r2" ]]; then
  cp -a "$RUNNER_TEMP/shock-failure-postmortem-r2/." "$evidence/"
fi
exit "$code"
