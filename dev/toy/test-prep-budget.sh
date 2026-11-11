#!/bin/bash
# reads: skills/workflow-delivery/scripts/budget.py skills/workflow-delivery/scripts/lane.py
# reads: skills/workflow-delivery/scripts/lanekit.py skills/workflow-delivery/scripts/lanetime.py
# reads: skills/workflow-monitoring/scripts/monitor.py skills/workflow-health/scripts/lean.py
# reads: skills/workflow-regression/scripts/slots.py skills/workflow-setup/scripts/setup.py
# Proves the preparation budget (REG-7, DEL-8): prep_budget_minutes defaults to 15 and refuses a value under 15; a lane that
# waits for a slot past the budget stops with LANE_PREP_BUDGET naming the part that ran long, runs no row and frees its place;
# the same command run again passes; every LANE line and .last record the three parts; a cut in planning, a corrupt record and a
# job without a budget are handled; the board and health list the hit with its part. A toy repo; the real lane, regression.py
# and slots run, with the test-only LOOP_PREP_BUDGET (seconds) standing in for 15 minutes. No model is called.
# usage: test-prep-budget.sh [DIR]
set -u
unset LOOP_BATCH LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN _LOOP_LANE_HELD LOOP_LANE_LIMIT LOOP_PREP_BUDGET
export LOOP_ROLE=worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
export HOME="$T/home"; mkdir -p "$HOME"
"$here/dev/toy/make.sh" "$T" >/dev/null
export LOOP_FLOW="$T/flow.json"; echo '{"limit": 60}' > "$LOOP_FLOW"
export LOOP_LANES_DIR="$T/lanes" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
S="$here/skills/workflow-delivery/scripts"; R="$here/skills/workflow-regression/scripts"
reg="python3 $R/regression.py"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
RUNS="$(git rev-parse --git-common-dir)/loop/runs"; mkdir -p "$RUNS"; RUNS=$(cd "$RUNS" && pwd)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2" 2>/dev/null; then ok "$1"; else bad "$1"; [ -z "${out:-}" ] || head -3 <<<"$out" | sed "s/^/    out: /"; fi; }
cat > "$T/h.py" <<'PY'
# A harness: call the real lane functions with no wait, so a test can see WAITING and RUNNING.
import json, os, sys
sys.path.insert(0, sys.argv[1]); import lane
runs, slug, name = sys.argv[2:5]
status, line, _ = lane.lane(runs, slug, name, lane.flow_spec(), json.load(open(".loop/config.json")), 0)
print(status); print(line)
PY
poll() { python3 "$T/h.py" "$S" "$RUNS" "$1" "$2"; }
until_done() { for _ in $(seq 600); do out=$(poll "$1" "$2"); case "$(grep -m1 -E '^(running|pass|fail)$' <<<"$out")" in running) sleep 0.3 ;; *) echo "$out"; return 0 ;; esac; done; return 1; }
holder() { # hold one slot of a one-slot pool until killed; prints its pid
  python3 - "$R" >/dev/null 2>&1 <<'PY' &
import os, sys, time
sys.path.insert(0, sys.argv[1]); import slots
pool = slots.lanes_dir(); slots.check(pool); fd, i = slots._slot(pool, 1, "toy/holder qa")
open(os.environ["HOME"] + "/holder.ready", "w").write("%d %d" % (os.getpid(), i)); time.sleep(600)
PY
  for _ in $(seq 100); do [ -s "$HOME/holder.ready" ] && break; sleep 0.1; done; cut -d' ' -f1 "$HOME/holder.ready"; rm -f "$HOME/holder.ready"
}

echo "== the setting"
bp() { python3 -c 'import json, sys; sys.path.insert(0, sys.argv[1]); import budget; print(budget.prep_seconds(json.loads(sys.argv[2])))' "$S" "$1" 2>&1; }
check "prep_budget_minutes defaults to 15 minutes" '[ "$(bp "{}")" = "(900, False)" ]'
out=$(bp '{"prep_budget_minutes": 14}')
check "a prep budget under 15 is refused with a fix line" 'grep -q "^REFUSED: prep_budget_minutes is 14 in .loop/config.json, under the 15-minute floor. Fix: set it to 15 or more" <<<"$out"'
check "LOOP_PREP_BUDGET (seconds) overrides it for tests, and a value of that name in config.json is ignored" '[ "$(LOOP_PREP_BUDGET=3 bp "{}")" = "(3, True)" ] && [ "$(bp "{\"LOOP_PREP_BUDGET\": 3}")" = "(900, False)" ]'

echo "== rows"
for i in 1 2; do $reg add r$i --level land --command "sleep 1; test ! -e broken" --describe "toy row $i" >/dev/null; done
python3 -c "import json;c=json.load(open('.loop/config.json'));c['base']='nobase';json.dump(c,open('.loop/config.json','w'),indent=2)"
python3 - <<'PY'
path = ".loop/regression.tsv"; out = []
for line in open(path).read().splitlines():
    cells = line.split("\t")
    if not line.startswith("#") and cells[0] in ("r1", "r2"):
        cells += [""] * (8 - len(cells)); cells[4] = "2026-01-01"
    out.append("\t".join(cells))
open(path, "w").write("\n".join(out) + "\n")
PY
git add -A; git commit -qm "rows"
echo '{"slug": "g", "status": "running"}' > "$RUNS/g.json"

echo "== every lane records and says the three parts"
export LOOP_LANE_LIMIT=1
out=$(until_done g qa)
check "a lane within the budget passes and its LANE line ends its text with the before-rows parts" 'grep -q "^pass$" <<<"$out" && grep -qE "before rows: prep [0-9]+s, planning [0-9]+s, slot wait 0s" <<<"$out" && ! grep -q "LOOP_PREP_BUDGET in effect" <<<"$out"'
check "the lane's .last record holds prep_s, plan_s and wait_s" 'python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if all(k in d for k in (\"prep_s\",\"plan_s\",\"wait_s\")) and d[\"wait_s\"]==0 else 1)" "$RUNS/g.qa-lane.last"'

echo "== a lane that waits for a slot past the budget stops and says which part ran long"
hp=$(holder); head=$(git rev-parse HEAD)
export LOOP_PREP_BUDGET=3
out=$(until_done h pr); echo "$out" | head -4
check "it fails with LANE_PREP_BUDGET naming waiting for a slot, the three parts, the shared budget and who holds the slots" 'grep -q "^fail$" <<<"$out" && grep -q "^LANE_PREP_BUDGET: the pr lane used its 0-minute preparation budget before any row ran: waiting for a slot ran long (prep [0-9]*s, planning [0-9]*s, slot wait [0-9]*s; the three share one budget); slots held by: toy/holder qa;" <<<"$out"'
check "it ran no row and committed nothing, and the LANE line says the override is in effect" '! grep -q "^PASS r" "$RUNS/h.pr-lane.txt" && [ "$(git rev-parse HEAD)" = "$head" ] && grep -q "LOOP_PREP_BUDGET in effect" <<<"$out"'
echo '{"slug": "h", "status": "running"}' > "$RUNS/h.json"
out=$(until_done h pr)
check "the hit is on the goal's run file as a prep hit with the part" 'python3 -c "import json,sys; d=json.load(open(sys.argv[1])); h=d[\"budget_hits\"][0]; sys.exit(0 if h[\"kind\"]==\"prep\" and h[\"step\"]==\"pr\" and \"waiting for a slot ran long\" in h[\"left\"] else 1)" "$RUNS/h.json"'
unset LOOP_PREP_BUDGET
kill "$hp" 2>/dev/null; wait "$hp" 2>/dev/null
out=$(until_done h ship)
check "its place was freed: another lane takes the slot at once and passes" 'grep -q "^pass$" <<<"$out" && ! grep -q "LANE_WAIT" "$RUNS/h.ship-lane.txt"'
out=$(until_done h pr)
check "the same command run again, with the slot free, passes" 'grep -q "^pass$" <<<"$out" && grep -q "^LANE pr" <<<"$out"'

echo "== a cut in planning, and the records that are missing or bad"
now=$(python3 -c 'import time; print(time.time() + 2)')
# the child kills its own process group at the cut, as it does in a lane (its own session): give it one
_LOOP_LANE_PREP_BY=$now _LOOP_LANE_QUEUED="$T/x.queued" _LOOP_LANE_STARTED="$T/x.started" python3 -c "import subprocess, sys; subprocess.run(sys.argv[1:], start_new_session=True)" python3 "$S/lane.py" lane-exec "$T/x.rc" 60 "$T/x.last" a1 "$T/lanes" -- sleep 30
check "a lane that writes no marker before its budget is cut in planning: exit 125 and one .times record naming it" '[ "$(cat "$T/x.rc")" = 125 ] && python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d[\"cut\"]==\"planning\" and d[\"wait\"]==0 and d[\"plan\"]>=1 else 1)" "$T/x.rc.times"'
echo '{ nope' > "$T/y.rc.times"
check "a corrupt or absent .times record reads as zeros with no part" 'python3 - "$S" "$T" <<PY
import sys; sys.path.insert(0, sys.argv[1]); import lanetime
sys.exit(0 if lanetime.timing({}, sys.argv[2] + "/y.rc") == (0.0, 0.0, "") and lanetime.timing({}, sys.argv[2] + "/none.rc") == (0.0, 0.0, "") else 1)
PY'
check "a job written without prep_by keeps the old 4x rule while queued or planning" 'python3 - "$S" "$T" <<PY
import sys, time; sys.path.insert(0, sys.argv[1]); import lane
at, why = lane.deadline({"markers": 1, "rc": sys.argv[2] + "/z.rc", "started": 100.0, "limit": 10.0})
sys.exit(0 if at == 140.0 and "queued or planning past 40s" in why else 1)
PY'
check "one with prep_by answers it until the rows begin" 'python3 - "$S" "$T" <<PY
import sys; sys.path.insert(0, sys.argv[1]); import lane
at, why = lane.deadline({"markers": 1, "rc": sys.argv[2] + "/z.rc", "started": 100.0, "limit": 10.0, "prep_by": 120.0})
sys.exit(0 if at == 120.0 and "preparation budget" in why else 1)
PY'

echo "== the board and health list it with the part"
out=$(python3 "$here/skills/workflow-monitoring/scripts/monitor.py" report 2>&1); echo "$out" | grep -A3 "BUDGET HITS"
check "the report lists the lane that hit the preparation budget and the part that ran long" 'grep -q "^- h: pr preparation hit its 0-minute budget; left: waiting for a slot ran long" <<<"$out"'
out=$(python3 -c "
import sys; sys.path.insert(0, sys.argv[1]); import lean
for r in lean.hit_rows('.'): print(r['state'], r['detail'])" "$here/skills/workflow-health/scripts" 2>&1)
check "health lists it too, in the same words" 'grep -q "^INFO h: pr preparation hit its 0-minute budget; left: waiting for a slot ran long" <<<"$out"'
check "budget.py names a prep hit the same way" 'python3 - "$S" <<PY
import sys; sys.path.insert(0, sys.argv[1]); import budget
sys.exit(0 if budget.label({"kind": "prep"}) == "preparation" and "pr preparation hit its 15-minute budget" in budget.lines({"slug": "h", "budget_hits": [{"step": "pr", "kind": "prep", "minutes": 15, "left": "x"}]})[0] else 1)
PY'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
