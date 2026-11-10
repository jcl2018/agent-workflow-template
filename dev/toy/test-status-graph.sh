#!/bin/bash
# reads: skills/workflow-delivery/scripts/defect.py skills/workflow-delivery/scripts/flow.py
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-delivery/scripts/role.py
# reads: skills/workflow-monitoring/scripts/board.py skills/workflow-monitoring/scripts/board_page.py
# reads: skills/workflow-monitoring/scripts/board_runs.py skills/workflow-monitoring/scripts/board_status.py
# reads: skills/workflow-monitoring/scripts/graph.py skills/workflow-monitoring/scripts/live_board.py
# reads: skills/workflow-monitoring/scripts/status_graph.py skills/workflow-setup/scripts/setup.py
# Proves the roadmap graph with a made-up queue: parallel and chained goals, the marks, the total as the longest chain, the same
# graph on the board, and the step label changing when a step starts. No model is called. usage: test-status-graph.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
unset LOOP_ROLE  # these tests act as the operation session; workers get LOOP_ROLE=worker where they need it
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
M="$here/skills/workflow-monitoring/scripts"; D="$here/skills/workflow-delivery/scripts"
BO="python3 $M/board.py"; BP="python3 $M/board_page.py"
goal="env LOOP_ROLE=worker python3 $D/goal.py"; F="env LOOP_ROLE=worker python3 $D/flow.py"
export HOME="$T/home"; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null || true  # a bare agent_command exits 1 after writing
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
AT=2026-06-01T12:00:00Z

echo "== a made-up queue"
# Finished goals took idea 10m, plan 21m and build 30m30s, so a goal that has not started needs 61m30s. b is running at plan,
# which began at AT, so it needs the plan's 21m and the build's 30m30s: 51m30s. a is merged.
mkdir -p "$C/loop/runs"
python3 - "$C/loop/runs" <<'PY'
import json, os, sys
folder = sys.argv[1]
def stamp(minutes):
    import datetime
    return (datetime.datetime(2026, 6, 1, 12, 0, 0) + datetime.timedelta(seconds=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
past = [stamp(-18000), stamp(-18000 + 600) + " idea done", stamp(-18000 + 1860) + " plan done", stamp(-18000 + 3690) + " build done"]
def write(slug, **more):
    json.dump(dict({"slug": slug, "goal": "Goal " + slug, "tries": 0, "pr": "", "waits_on": []}, **more), open(os.path.join(folder, slug + ".json"), "w"))
write("hist", status="done", step="pr", release="merged", updated=stamp(-14000), log=[x if " " in x else x + " queued" for x in past])
write("a", status="done", step="pr", release="merged", updated=stamp(-60), log=[x if " " in x else x + " queued" for x in past])
write("b", status="running", step="plan", updated=stamp(0), pid=1, log=[stamp(-1000) + " queued", stamp(-400) + " idea done", stamp(0) + " start plan"])
PY
cat >> .loop/queue.md <<'Q'
- slug: c | touches: x | depends-on: a, b | goal: C | done: c
- slug: d | touches: x | depends-on: c | goal: D | done: d
- slug: e | touches: x | goal: E | done: e
- slug: f | touches: x | depends-on: ghost | goal: F | done: f
Q
block() { LOOP_BOARD_HEALTH=green python3 -c "
import sys, datetime
sys.path.insert(0, sys.argv[1]); import live_board
at = datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
print(chr(10).join(live_board.render('$T/repo', at)))" "$M"; }  # lanes: no read ($M only goes on sys.path)
block > "$T/block"
check "the live board sections are in the fixed order" 'python3 -c "
t=open(\"$T/block\").read()
at=[t.index(\"\n%s\n\" % n) for n in (\"Issues\",\"Running goals\",\"Queued goals\",\"Dependencies\",\"Finish\")]
assert at==sorted(at)"'
check "chained goals are drawn as arrows between running and queued goals" 'grep -qx "b --> c" "$T/block" && grep -qx "c --> d" "$T/block" && ! grep -q "ghost -->" "$T/block"'
check "a queued goal shows what it waits on, a standalone one waits on nothing" 'grep -q "^- c .*waits on b" "$T/block" && grep -q "^- d .*waits on c" "$T/block" && grep -q "^- e " "$T/block" && ! grep "^- e " "$T/block" | grep -q waits'
check "merged goals are left out; a running goal has its bar and time left" '! grep -q "merged\|hist\|^- a " "$T/block" && grep -q "^- b  \[#---------\] 12%  51m left" "$T/block" && grep -q "^- c  1h01m left" "$T/block"'
check "the finish is the longest chain b > c > d, not the sum" 'grep -q "^finish about " "$T/block" && ! grep -q "at least" "$T/block" && python3 -c "
import re,sys
t=open(\"$T/block\").read()
mins=lambda s: sum(int(n)*(60 if u==\"h\" else 1) for n,u in re.findall(r\"(\\d+)([hm])\", s))
left={g: mins(m) for g,m in re.findall(r\"^- (\\w+)  (?:\\[.*?\\] \\d+%  )?(\\d+h\\d+m|\\d+h|\\d+m) left\", t, re.M)}
h=re.search(r\"^LIVE BOARD  \\S+  (\\d\\d):(\\d\\d)\", t, re.M); f=re.search(r\"finish about (\\d\\d):(\\d\\d)\", t)
gap=(int(f[1])*60+int(f[2])-int(h[1])*60-int(h[2]))%1440
chain=left[\"b\"]+left[\"c\"]+left[\"d\"]
assert abs(gap-chain)<=1 and abs(gap-sum(left.values()))>1, (gap, chain, left)"'
check "a running goal shows its step flow with the current step in brackets" 'grep -qx "    idea✓ > \[plan\] > build > review > qa > ship > pr >" "$T/block"'

echo "== the pure graph"
python3 - "$M" <<'PY' && ok "no estimate gives at least, a cycle is cut, an empty queue is empty" || bad "pure graph"
import sys
sys.path.insert(0, sys.argv[1]); import status_graph as g
def node(slug, mark="queued", depends=(), left=60):
    return dict(slug=slug, mark=mark, depends=list(depends), stage=0, left=left)
assert g.total([node("a", left=600), node("b", depends=["a"], left=None)]).startswith("at least 10m"), g.total([node("a", left=600), node("b", depends=["a"], left=None)])
assert g.total([node("a", left=None)]).startswith("no estimate yet")
assert g.total([]) == "nothing left" and g.render_text([]) == ["(no goals)"]
assert g.total([node("a", "merged", left=0)]) == "nothing left"
loop = [node("a", depends=["b"]), node("b", depends=["a"])]
assert "cycle cut at" in g.total(loop) and len(g.render_text(loop)) >= 3
assert g.total([node("a", left=600), node("b", left=300)]).startswith("about 10m, the longest chain: a"), "parallel goals are not summed"
PY

echo "== both dependency spellings"
check "depends: and depends-on: parse to the same waits" 'python3 -c "
import sys; sys.path.insert(0, \"$M\"); import graph
a=graph.parse(\"- slug: x | depends: a, b | goal: X\")
b=graph.parse(\"- slug: x | depends-on: a, b | goal: X\")
assert a[\"depends\"]==b[\"depends\"]==[\"a\",\"b\"], (a, b)
c=graph.parse(\"- slug: x | depends: a | depends-on: a, b | goal: X\")
assert c[\"depends\"]==[\"a\",\"b\"], c
assert graph.parse(\"- slug: x | goal: X\")[\"depends\"]==[]"'

echo "== the step label"
$goal new lv --here --goal "Label" --done "label" >/dev/null
label() { python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['step'])" "$C/loop/runs/lv.json"; }
$F lv plan --wait 0 >/dev/null
check "the label changes when the step starts, before anything is recorded" '[ "$(label)" = plan ] && grep -q " start plan\"" "$C/loop/runs/lv.json" && block | grep -q "^- lv  .*" && block | grep -q "\[plan\]"'
$F lv plan --wait 10 >/dev/null
check "a finished but unrecorded step is still the current one" '[ "$(label)" = plan ]'
$goal record lv plan --file "$C/loop/runs/lv.plan.txt" >/dev/null
check "recording moves the label on, so the finished step is never shown as current" '[ "$(label)" = build ] && block | grep -q "idea✓ > plan✓ > \[build\]"'

echo "== sizes"
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
