#!/bin/bash
# Proves worker.py cleanup deletes merged loop/* branches (never an unmerged or checked-out one) and that the health check
# names it and shows no merged-branch warning afterwards. No model is called. usage: test-cleanup.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
unset LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
export HOME="$T/home"; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
W="python3 $here/skills/workflow-monitoring/scripts/worker.py"; H="python3 $here/skills/workflow-health/scripts/health.py"
git branch loop/aaa-first; git branch loop/merged-one; git branch loop/merged-two; git branch other/merged
git switch -q -c loop/open-work; echo x > x.txt; git add x.txt; git commit -qm "Unmerged work"; git switch -q main
git worktree add -q "$T/wt" -b loop/in-use
out=$($H check --family hygiene)
check "merged loop branches warn, and the fix line names cleanup" 'grep -q "^WARN hygiene loop/merged-one branch: .* -> fix: worker.py cleanup" <<<"$out"'
out=$($W cleanup --dry-run)
check "dry run lists them and deletes nothing" 'grep -q "WOULD DELETE loop/merged-one" <<<"$out" && git rev-parse -q --verify loop/merged-one >/dev/null'
out=$($W cleanup); echo "$out"
check "cleanup deletes the merged loop branches" '! git rev-parse -q --verify loop/merged-one >/dev/null && ! git rev-parse -q --verify loop/merged-two >/dev/null && ! git rev-parse -q --verify loop/aaa-first >/dev/null'
check "it keeps an unmerged branch, a non-loop branch and a branch checked out in a worktree" 'git rev-parse -q --verify loop/open-work >/dev/null && git rev-parse -q --verify other/merged >/dev/null && git rev-parse -q --verify loop/in-use >/dev/null'
check "the health check shows no merged-branch warning" '! $H check --family hygiene | grep -q "branch: already merged"'
[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
