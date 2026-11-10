#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-setup/scripts/setup.py
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# Issue 143: regression.py sync (and so health's done-lines warning) counts only the done lines of goals still being
# built: a goal whose run record says done, failed, retired or stopped, or that has no run record, is history.
# Value: protects=the done-lines warning names only active goals (issue 143); fails_when=sync counts every goal file;
# why_new=no check of which goals count; seam=none; no_claim=health's own wording (it reads sync's GAP lines)
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
export HOME=$(mktemp -d)
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
cd "$d" && git init -q -b main && git commit -q --allow-empty -m init
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null 2>&1
mkdir -p .loop/goals .git/loop/runs
for g in old live gone; do printf '# %s\n\n## Done lines\n\n1. %s works\n' "$g" "$g" > .loop/goals/$g.md; done
echo '{"slug": "old", "status": "done"}' > .git/loop/runs/old.json
echo '{"slug": "live", "status": "running"}' > .git/loop/runs/live.json
out=$(python3 "$here/skills/workflow-regression/scripts/regression.py" sync 2>&1)
grep -q "^GAP live:1" <<<"$out" && ok "a running goal's uncovered done line is a GAP" || bad "running goal: $out"
! grep -qE "^GAP (old|gone):1" <<<"$out" && ok "a done goal's and an unrecorded goal's done lines are not counted" \
  || bad "finished goals counted: $(grep -E '^GAP (old|gone)' <<<"$out")"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
