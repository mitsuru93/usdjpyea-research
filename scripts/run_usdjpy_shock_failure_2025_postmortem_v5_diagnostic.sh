#!/usr/bin/env bash
set -euo pipefail

finalizer_commit=bac409cf96b9c8d70abf6f29335c05c634297007
finalizer_b64="$RUNNER_TEMP/shock-postmortem-r2-finalizer.b64"
finalizer="$RUNNER_TEMP/shock-postmortem-r2-finalizer.sh"

git fetch --no-tags --depth=1 origin "$finalizer_commit"
: > "$finalizer_b64"
for n in 00 01 02 03 04 05; do
  git show "$finalizer_commit:tools/finalize_usdjpy_shock_failure_2025_postmortem_r2.sh.b64.part$n" >> "$finalizer_b64"
done
test "$(sha256sum "$finalizer_b64" | awk '{print $1}')" = 7a4d10dd82d21c15a3f225ae2711122a632a81a2559a22162a24569af47ffdc6
base64 -d "$finalizer_b64" > "$finalizer"
test "$(sha256sum "$finalizer" | awk '{print $1}')" = 9b188e655795a9f5fb5de1f31b5bd5c503fc834e47f9a3178db7b007648d9c3e
bash -n "$finalizer"

git fetch --no-tags origin main
git checkout --detach origin/main
export HEAD_SHA="$(git rev-parse HEAD)"
export HEAD_BRANCH=main
export GH_TOKEN="${GITHUB_TOKEN:?GITHUB_TOKEN is required}"

bash "$finalizer"
