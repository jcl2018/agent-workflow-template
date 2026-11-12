#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/fit.py
# Test goal.py adopt: a goal pushed from another machine gets this machine's run record at qa, and a branch not on origin is refused.
# usage: test-goal-adopt.sh [DIR]
# windows: ok
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
export LOOP_ROLE=worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
# gh is a stand-in inside python (a bash stub on PATH is not runnable by subprocess on Windows): `gh pr view` says the PR is open.
mkdir -p "$d/py"
cat > "$d/py/sitecustomize.py" <<'PY'
import subprocess
_run = subprocess.run
def run(args, *a, **k):
    if args and args[0] == "gh":
        return subprocess.CompletedProcess(args, 0, '{"url": "https://github.com/o/r/pull/7", "state": "OPEN"}', "")
    return _run(args, *a, **k)
subprocess.run = run
PY
export PYTHONPATH="$d/py" LOOP_FLOW="$d/flow.json"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
field() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]))" "$C/loop/runs/$1.json" "$2"; }

# The other machine freezes and pushes a goal; this machine then drops that run record, as a second machine never had it.
$goal new far --here --goal "Do far" --done "far works" --touches "calc.py" >/dev/null || bad "new"
git push -q -u origin loop/far
rm -f "$C/loop/runs/far.json"

echo "== adopt on a pushed branch with an open PR"
out=$($goal adopt far 2>&1); echo "$out" | grep -q "^ADOPTED far at qa" && ok "adopt prints ADOPTED" || bad "adopt: $out"
[ "$(field far step)" = qa ] && [ "$(field far pr)" = "https://github.com/o/r/pull/7" ] && ok "run record is at qa with the PR" || bad "record fields"
python3 - "$C/loop/runs/far.json" <<'PY' && ok "idea, plan and review done on another machine; qa, ship and pr not recorded" || bad "flow evidence"
import json, sys
f = json.load(open(sys.argv[1]))["flow"]
assert all(f[s].startswith("done on another machine") for s in ("idea", "plan", "review")), f
assert not any(s in f for s in ("qa", "ship")), f
PY
$goal pr far 2>&1 | grep -q "the flow hasn't finished: qa, ship" && ok "pr now stops at qa, not at 'no goal named'" || bad "pr after adopt"
$goal adopt far 2>&1 | grep -q "has a live, started or finished run record here" && ok "a second adopt is refused" || bad "second adopt"

echo "== adopt refuses a branch that is not on origin"
git switch -q -c loop/near main; mkdir -p .loop/goals
printf '# Near\n\n- Slug: near\n- Touches: calc.py\n\n## Done lines\n\n1. near works\n' > .loop/goals/near.md; git add -A; git commit -qm "Goal: near"
out=$($goal adopt near 2>&1); echo "$out" | grep -q "REFUSED: loop/near is not on origin" && ok "unpushed branch refused" || bad "unpushed: $out"
[ -e "$C/loop/runs/near.json" ] && bad "a record was written for the unpushed branch" || ok "no record written"

echo "== a stale running record with no pid is replaced; one with a pid is refused"
git switch -q main
$goal new stale --here --goal "Do stale" --done "stale works" --touches "calc.py" >/dev/null || bad "new stale"
git push -q -u origin loop/stale
out=$($goal adopt stale 2>&1); echo "$out" | grep -q "^ADOPTED stale at qa.*; replaced a stale record: running, no pid, no steps" && ok "stale record replaced" || bad "stale: $out"
[ "$(field stale step)" = qa ] && grep -q "replaced a stale record" "$C/loop/runs/stale.json" && ok "replacement logged, record at qa" || bad "stale record"
git switch -q main
$goal new busy --here --goal "Do busy" --done "busy works" --touches "calc.py" >/dev/null || bad "new busy"
git push -q -u origin loop/busy
python3 - "$C/loop/runs/busy.json" <<'PY'
import json, sys
f = json.load(open(sys.argv[1])); f["pid"] = 4242; json.dump(f, open(sys.argv[1], "w"))
PY
out=$($goal adopt busy 2>&1); echo "$out" | grep -q "REFUSED: busy has a live, started or finished run record" && ok "record with a pid refused" || bad "busy: $out"
[ "$(field busy pid)" = 4242 ] && ok "the busy record is unchanged" || bad "busy record changed"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
