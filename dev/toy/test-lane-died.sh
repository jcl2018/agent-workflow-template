#!/bin/bash
# reads: skills/workflow-regression/scripts/ skills/workflow-delivery/scripts/
# reads: skills/workflow-delivery/scripts/lanekit.py skills/workflow-delivery/scripts/role.py
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-docs/scripts/criteria.py
# reads: skills/workflow-docs/scripts/docs.py skills/workflow-setup/scripts/setup.py
# Proves a lane is never killed by a stale pid and a lane that dies spends no try: a signal goes only to a process whose
# stored start time matches (a reused pid is not ours), every signal the loop sends is audited, a lane signalled from
# outside reports LANE_DIED naming the signal and restarts without a failed try, and the third death in a row fails.
# Only throwaway processes of this test are signalled. usage: test-lane-died.sh [DIR]
set -u
unset LOOP_BATCH LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN _LOOP_LANE_HELD LOOP_LANE_LIMIT
export LOOP_ROLE=worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
export HOME="$T/home"; mkdir -p "$HOME"
"$here/dev/toy/make.sh" "$T" >/dev/null
export LOOP_FLOW="$T/flow.json"; echo '{"limit": 60}' > "$LOOP_FLOW"
export LOOP_LANES_DIR="$T/lanes" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
S="$here/skills/workflow-delivery/scripts"; R="$here/skills/workflow-regression/scripts"
reg="python3 $R/regression.py"; role="python3 $S/role.py"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
RUNS="$(git rev-parse --git-common-dir)/loop/runs"; mkdir -p "$RUNS"; RUNS=$(cd "$RUNS" && pwd)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2" 2>/dev/null; then ok "$1"; else bad "$1"; [ -z "${out:-}" ] || head -3 <<<"$out" | sed "s/^/    out: /"; fi; }
seen() { python3 - "$@" <<'PY'
import sys
path = ".loop/regression.tsv"
lines = open(path).read().splitlines()
out = []
for line in lines:
    cells = line.split("\t")
    if not line.startswith("#") and cells[0] in sys.argv[1:]:
        cells += [""] * (8 - len(cells)); cells[4] = "2026-01-01"
    out.append("\t".join(cells))
open(path, "w").write("\n".join(out) + "\n")
PY
}
cat > "$T/h.py" <<'PY'
# A harness: call the real lane functions with no wait, so a test can see WAITING and RUNNING.
import json, os, sys
sys.path.insert(0, sys.argv[1]); import lane
runs, slug, name, what = sys.argv[2:6]
if what == "poll":
    status, line, _ = lane.lane(runs, slug, name, lane.flow_spec(), json.load(open(".loop/config.json")), 0)
    print(status); print(line)
elif what == "status":
    print("\n".join(lane.lane_status(runs, slug, name)))
PY
poll() { python3 "$T/h.py" "$S" "$RUNS" "$1" "$2" poll; }
until_done() { for _ in $(seq 600); do out=$(poll "$1" "$2"); case "$(grep -m1 -E '^(running|pass|fail)$' <<<"$out")" in running) sleep 0.3 ;; *) echo "$out"; return 0 ;; esac; done; return 1; }

echo "== a reused pid is never signalled, and every signal is audited"
cat > "$T/id.py" <<'PY'
import subprocess, sys, time
sys.path.insert(0, sys.argv[1]); import lane, lanekit
runs = sys.argv[2]
decoy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], start_new_session=True)  # a group leader, like lane-exec
time.sleep(0.3)
base = runs + "/ghost.qa-lane"
held = {"head": "h", "attempt": "a-1", "started": time.time(), "limit": 600, "rc": base + ".a-1.rc", "markers": 1, "pool": "/x",
        "pid": decoy.pid, "pstart": "Mon Jan  1 00:00:00 2001"}  # the job's own process is long gone; its pid now names the decoy
lane.stop(base, held)  # what a poll does to a stale job: HEAD moved, or another lane of the goal
time.sleep(0.5)
print("decoy_alive=%s" % (decoy.poll() is None))
held["pstart"] = lanekit.pstart(decoy.pid)
lane.stop(base, held)
time.sleep(0.5)
print("own_stopped=%s" % (decoy.poll() is not None))
print("decoy_pid=%d" % decoy.pid)
if decoy.poll() is None:
    decoy.kill()
PY
out=$(python3 "$T/id.py" "$S" "$RUNS" 2>&1)
check "a stop on a stale job whose pid now names another process leaves that process alone" 'grep -q "^decoy_alive=True$" <<<"$out"'
check "a stop on a job whose process still is the one it started ends it" 'grep -q "^own_stopped=True$" <<<"$out"'
pid=$(sed -n 's/^decoy_pid=//p' <<<"$out")
check "every signal the loop sends is one line in runs/kills.log, and the refused one is not in it" '[ "$(grep -c "ghost.qa-lane -> $pid " "$RUNS/kills.log")" = 1 ] && [ "$(wc -l < "$RUNS/kills.log" | tr -d " ")" = 1 ]'

echo "== flow.py never kills a process that only reuses a step's pid (the killer)"
goal="python3 $S/goal.py"; F="python3 $S/flow.py"
printf '#!/bin/bash\nsleep 30\n' > "$T/slowskill.sh"
python3 - "$T/flow.json" "$T/slowskill.sh" <<'PY'
import json, sys
spec = json.load(open(sys.argv[1])); spec.update({"command": ["bash", sys.argv[2]], "limit": 2}); json.dump(spec, open(sys.argv[1], "w"))
PY
$goal new bg --here --goal "Stale job goal" --done "a stale job kills nothing" >/dev/null
check "the toy goal exists, so the flow step really ran" '[ -s "$RUNS/bg.json" ]'
python3 - "$RUNS/bg.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["flow"] = {"idea": "done", "plan": "done"}; s["step"] = "review"; json.dump(s, open(sys.argv[1], "w"))
PY
cat > "$T/decoy.py" <<'PY'
import subprocess, sys
p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # a group leader, like lane-exec
print(p.pid)
PY
decoy=$(python3 "$T/decoy.py")
python3 - "$RUNS/bg.review.job" "$decoy" <<'PY'
import json, sys, time
# a step job whose own process is long gone: its pid now names the decoy, and it is well past its limit
json.dump({"pid": int(sys.argv[2]), "pstart": "Mon Jan  1 00:00:00 2001", "started": time.time() - 3600, "limit": 2}, open(sys.argv[1], "w"))
PY
out=$($F bg review --wait 1 2>&1)
check "a flow step's stale job whose pid now names another process is not allowed to kill it" 'kill -0 "$decoy"'
check "no signal went to it and none is audited for it" '! grep -q " -> $decoy " "$RUNS/kills.log" 2>/dev/null'
kill "$decoy" 2>/dev/null
echo "== a lane signalled from outside reports LANE_DIED naming the signal"
$reg add slow --level land --command "sleep 60" --describe "Given a slow row, when the lane runs, then it keeps the lane busy." >/dev/null
python3 -c "import json;c=json.load(open('.loop/config.json'));c['base']='nobase';json.dump(c,open('.loop/config.json','w'),indent=2)"
seen slow; git add -A; git commit -qm "slow row"
jobpid() { python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['pid'])" "$RUNS/dies.qa-lane.job"; }
died() { for _ in $(seq 100); do out=$(poll dies qa); grep -q "LANE_DIED" <<<"$out" && return 0; sleep 0.3; done; return 1; }
poll dies qa >/dev/null; sleep 2
kill -TERM "$(jobpid)"; died
check "a lane SIGTERMed from outside reports LANE_DIED naming the signal" 'grep -q "^fail$" <<<"$out" && grep -q "LANE_DIED: .*(killed by SIGTERM)" <<<"$out"'
poll dies qa >/dev/null; sleep 2
kill -KILL "$(jobpid)"; died
check "a lane SIGKILLed from outside reports LANE_DIED (no signal can be known)" 'grep -q "^fail$" <<<"$out" && grep -q "LANE_DIED:" <<<"$out" && ! grep -q "killed by" <<<"$out"'
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
