#!/bin/bash
# reads: skills/workflow-monitoring/scripts/ skills/workflow-setup/scripts/setup.py
# Proves issues 102 and 108 with a made-up repo and a stand-in session pool: the live board takes the latest session
# report for the next line, lists held goals under Queued goals marked held, shows a goal handed to a session before it
# is frozen as [freezing], keeps an off-flow step at the last flow step, and counts tries; sessions.py binds before
# freezing, frees, refuses an unreadable pool and keeps a done goal done; watch.py fails closed. No model is called.
# usage: test-board-held.sh [DIR]
set -u
unset LOOP_ROLE LOOP_SESSION LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
S="$here/skills/workflow-monitoring/scripts"
SE="python3 $S/sessions.py"
export HOME="$T/home" LOOP_BOARD_HEALTH=green PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c.update(parallel=0, mend=False, auto_merge=False, agent_command=["true"])
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Config"
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); R="$C/loop/runs"; POOL="$C/loop/session-pool.json"; mkdir -p "$R"
mkdir -p "$T/tree"
# A board at 12:00 with one goal for each state the board must read.
python3 - "$R" "$POOL" "$T/tree" <<'PY'
import json, os, sys, datetime
runs, pool, tree = sys.argv[1:4]
def at(s):
    return (datetime.datetime(2026, 6, 1, 12, 0, 0) + datetime.timedelta(seconds=s)).strftime("%Y-%m-%dT%H:%M:%SZ")
def write(slug, **more):
    json.dump(dict({"slug": slug, "goal": "Goal " + slug, "tries": 0, "pr": "", "waits_on": [], "updated": at(0)}, **more),
              open(os.path.join(runs, slug + ".json"), "w"))
write("stale", status="running", step="review", worker="session", session={"id": "s1", "name": "worker · stale"},
      report={"status": "failed", "text": "OLD FAILURE", "at": at(-3600)},
      reports=[{"at": at(-3600), "step": "build", "status": "failed", "text": "OLD FAILURE"},
               {"at": at(-60), "step": "review", "status": "running", "text": "review in progress"}])
write("heldg", status="running", step="plan", worktree="/nonexistent/heldg", updated=at(-7200), tries=1)
write("heldk", status="running", step="build", worker="session", session={"id": "s5", "name": "worker · heldk"},
      worktree=tree, updated=at(-7200))
write("heldn", status="running", step="idea", worktree=tree, updated="")
write("deadpid", status="running", step="qa", pid=999999)
write("offflow", status="running", step="checks", pid=1, reports=[{"at": at(-30), "step": "build", "status": "running", "text": ""}])
write("rel", status="running", step="release", pid=1)
write("usedup", status="running", step="ship", pid=1, tries=3)
write("donep", status="done", step="pr")
write("rebound", status="running", step="build", worker="session", session={"id": "s6", "name": "worker · rebound"},
      bound_at=at(-30), reports=[{"at": at(-60), "step": "build", "status": "failed", "text": "OLD WORKER"}])
write("retired1", status="retired", step="plan")
json.dump({"s1": {"name": "worker · stale", "slug": "stale", "state": "busy", "since": at(-9000)},
           "s3": {"name": "worker · newgoal", "slug": "newgoal", "state": "busy", "since": at(-180)},
           "s4": {"name": "worker · oldassign", "slug": "oldassign", "state": "busy", "since": at(-7200)},
           "s6": {"name": "worker · rebound", "slug": "rebound", "state": "busy", "since": at(-30)},
           "s7": {"name": "worker · retired1", "slug": "retired1", "state": "busy", "since": at(-100)},
           "s8": {"name": "worker · x", "slug": "", "state": "free"}}, open(pool, "w"))
PY
cat >> .loop/queue.md <<'Q'
- slug: newgoal | touches: n | goal: N | done: n
- slug: later | touches: l | goal: L | done: l
Q
board() { python3 - "$S" "$T/repo" <<'PY'
import sys, datetime
sys.path.insert(0, sys.argv[1]); import live_board
out, base = [], 0  # undo the 60-column wrap so each check reads one logical line
for line in live_board.render(sys.argv[2], datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)):
    indent = len(line) - len(line.lstrip())
    if out and line.strip() and (out[-1].endswith(" >") or indent == base + 2):
        out[-1] += " " + line.strip()
        continue
    out.append(line)
    base = indent
print("\n".join(out))
PY
}
board > "$T/board" 2> "$T/board.err"; echo "exit $?" >> "$T/board.err"
cat "$T/board"
sec() { sed -n "/^$1\$/,/^$2\$/p" "$T/board"; }
goal() { awk -v s="- $1 " 'index($0, s) == 1 {on=1; print; next} on && /^    / {print; next} {on=0}' "$T/board"; }

echo "== issue 102: the next line, held goals, freezing goals"
check "the board renders without an error" 'grep -qx "exit 0" "$T/board.err"'
check "the board keeps exactly the five MON-4 sections" '[ "$(grep -xE "Issues|Running goals|Queued goals|Dependencies|Finish|Held goals" "$T/board" | paste -sd, -)" = "Issues,Running goals,Queued goals,Dependencies,Finish" ]'
check "a session goal's next line is its latest session report, not an older failure" 'goal stale | grep -qx "    next: review in progress" && ! goal stale | grep -q "OLD FAILURE"'
check "a report older than the run's bound_at doesn't make the next line" '! goal rebound | grep -q "OLD WORKER" && goal rebound | grep -qx "    next: finish build, then review"'
check "a held goal is listed under Queued goals marked held, not under Running goals" 'sec "Queued goals" Dependencies | grep -q "^- heldg .*  held$" && ! sec "Running goals" "Queued goals" | grep -q "^- heldg "'
check "a held goal is not called a background worker" 'goal heldg | grep -q "worker: none (held, last change 2h ago, worktree gone)" && ! goal heldg | grep -q background'
check "a held goal whose worktree is gone says how to make it again" 'goal heldg | grep -q "next: give it a worker session (sessions.py bind heldg ID.*git worktree add <common>/loop/worktrees/heldg loop/heldg)"'
check "a held goal with no recorded time still reads held, worktree kept" 'goal heldn | grep -qx "    worker: none (held, worktree kept)"'
check "a held session goal that holds a slot says so, and is named under Issues past the quiet time" 'goal heldk | grep -q "holds a slot)" && sec Issues "Running goals" | grep -q "^- heldk: held 2h and holds a slot" && sec Issues "Running goals" | grep -q "sessions.py free heldk"'
check "a held goal gets no quiet-session line" '! grep -q "^- heldk: its session" "$T/board"'
check "a running goal with a dead pid is never marked held" 'sec "Running goals" "Queued goals" | grep -q "^- deadpid " && goal deadpid | grep -q "worker: background"'
check "a goal handed to a session before it is frozen shows at once under Running goals as freezing" 'goal newgoal | grep -q "^- newgoal  \[----------\] 0%" && goal newgoal | grep -qx "    \[freezing\] > idea > plan > build > review > qa > ship > pr > release" && goal newgoal | grep -qx "    worker: session worker · newgoal"'
check "the freezing goal says what happens next and how long ago it was assigned" 'goal newgoal | grep -qx "    next: the worker freezes it (goal.py new newgoal --here in its worktree), binds again, then idea (assigned 3m ago)"'
check "the freezing goal leaves Queued goals" '! sec "Queued goals" Dependencies | grep -q "^- newgoal " && sec "Queued goals" Dependencies | grep -q "^- later "'
check "a freezing goal assigned longer than the quiet time is named under Issues with its fix" 'sec Issues "Running goals" | grep -q "^- oldassign: assigned to session worker · oldassign 2h ago and still not frozen" && grep -q "sessions.py free oldassign" "$T/board"'
check "a retired goal with a busy pool entry is not shown as freezing" '! grep -q "retired1" "$T/board"'
check "a step outside the flow keeps the last known flow step, not idea 0%" 'goal offflow | grep -qx "    idea✓ > plan✓ > \[build\] > review > qa > ship > pr > release" && goal offflow | grep -q "^- offflow  \[##--------\] 25%"'
check "a running goal at the release step reads finish release" 'goal rel | grep -qx "    next: finish release"'
check "a done goal still reads merge the pull request" 'goal donep | grep -qx "    next: merge the pull request"'
check "a goal that failed a try shows try N of M" 'goal heldg | grep -q "^- heldg .*  try 2 of 3  held$"'
check "a goal past its tries shows tries used up" 'goal usedup | grep -q "tries used up (3 of 3)"'
check "Finish says at least while a goal is held or freezing" 'sed -n "/^Finish$/,\$p" "$T/board" | grep -qE "^(at least finish about|no estimate yet)"'

echo "== an unreadable pool, a bad entry, a bad max_tries"
cp "$POOL" "$T/pool.good"
printf '{bad' > "$POOL"
board > "$T/board2" 2>&1
check "an unreadable pool is named under Issues with its fix, and nothing is called held or freezing" 'grep -q "^- the session pool can.t be read (bad JSON" "$T/board2" && grep -q "python3 -m json.tool" "$T/board2" && ! grep -qE "  held$|\[freezing\]" "$T/board2"'
printf '{"s1": "x"}' > "$POOL"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["max_tries"] = "abc"; json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
board > "$T/board3" 2>&1; rc=$?
check "a malformed pool entry counts as an unknown pool and a bad max_tries never crashes the board" '[ $rc = 0 ] && grep -q "entry s1 is not an object" "$T/board3" && grep -q "try 2 of 3" "$T/board3"'
git checkout -q -- .loop/config.json

echo "== watch.py fails closed"
printf '{bad' > "$POOL"
out=$(python3 "$S/watch.py" watch --once 2>&1)
check "a watch pass with an unreadable pool starts nothing and says why" 'echo "$out" | grep -q "the session pool can.t be read" && [ ! -e "$R/later.json" ] && ! echo "$out" | grep -qi "mend"'
cp "$T/pool.good" "$POOL"
python3 - "$S" "$T/repo" > "$T/watch.out" 2>&1 <<'PY'
import sys, json, os
sys.path.insert(0, sys.argv[1]); os.chdir(sys.argv[2])
import graph, watch, sessions
print("known", "newgoal" in watch.known())
start, held = watch.plan(0)
print("held", [(g["slug"], why) for g, why in held if g["slug"] == "newgoal"])
# parallel=1: a frozen goal its session hasn't bound yet still holds the one slot
records = {"frozen": {"slug": "frozen", "status": "running", "pid": None}}
start, held = graph.ready([{"slug": "q", "depends": []}], records, 1, {"frozen": {"id": "s9"}})
print("window", [g["slug"] for g in start])
start, held = graph.ready([{"slug": "q", "depends": []}], {}, 0, None, "bad JSON")
print("unknown", [g["slug"] for g in start], held[0][1][:35])
# the pool breaks between plan and assign: the goal fails closed, never a background worker
calls = []
watch.plan = lambda limit: ([{"slug": "race", "goal": "R", "done": ["r"], "touches": [], "depends": [], "release": ""}], [])
watch.freeze = lambda goal, cfg: {"slug": "race", "status": "running", "goal": "R", "touches": [], "branch": "loop/race", "worktree": "/x", "log": []}
watch.go_prompt = lambda state, goal, skill_dir: "p"
watch.launch = lambda *a: calls.append("launch")
def broken(*a):
    raise sessions.PoolUnreadable("bad JSON")
sessions.assign = broken
class A: max = 0; skill_dir = None
watch.save = lambda state, note=None: json.dump(state, open(os.path.join(watch.loop_dir("runs"), "race.json"), "w"))
watch.start_round(A, {})
race = json.load(open(os.path.join(watch.loop_dir("runs"), "race.json")))
print("race", race["status"], "launch" in calls)
PY
cat "$T/watch.out"
check "watch.py go never picks a slug already assigned to a session" 'grep -qx "known True" "$T/watch.out"'
check "watch holds a queued goal a session was handed, with its reason" 'grep -q "^held \[(.newgoal., .assigned to session worker · newgoal; not frozen yet.)\]" "$T/watch.out"'
check "slot accounting holds through the window between freezing and the worker's bind" 'grep -qx "window \[\]" "$T/watch.out"'
check "an unknown pool starts nothing" 'grep -q "^unknown \[\] the session pool can.t be read" "$T/watch.out"'
check "the pool breaking between plan and assign fails the goal and starts no background worker" 'grep -qx "race failed False" "$T/watch.out"'
rm -f "$R/race.json"

echo "== sessions.py: bind before freezing, free, --force"
$SE bind Bad_Slug s10 > "$T/o" 2>&1; rc=$?
check "bind refuses a bad goal name and names the rule" '[ $rc = 1 ] && grep -q "REFUSED: bad goal name .Bad_Slug.: use lowercase letters" "$T/o"'
$SE bind lc s20 > "$T/o" 2>&1
check "bind before freezing records the handoff and says what comes next" 'grep -q "^ASSIGNED lc to session s20 (worker · lc); not frozen yet. Next: in its worktree the worker runs goal.py new lc --here" "$T/o" && board | grep -q "^- lc  \[----------\] 0%"'
$SE report lc --status running > "$T/o" 2>&1; rc=$?
check "report on a goal that is assigned but not frozen gives the fix" '[ $rc = 1 ] && grep -q "REFUSED: lc is assigned to session worker · lc but not frozen yet. Fix: the worker runs goal.py new lc --here" "$T/o"'
$SE send lc "hi" > "$T/o" 2>&1; rc=$?
check "send on a goal that is assigned but not frozen gives the same fix" '[ $rc = 1 ] && grep -q "not frozen yet" "$T/o"'
echo '{"slug": "lc", "status": "running", "step": "idea", "tries": 0, "goal": "L", "log": []}' > "$R/lc.json"
$SE bind lc s20 > "$T/o" 2>&1
first=$(python3 -c "import json;print(json.load(open('$R/lc.json')).get('bound_at'))")
check "after the worker freezes, its bind goes through on the same session and fills the run" 'grep -q "^BOUND lc to session s20" "$T/o" && [ "$(python3 -c "import json;d=json.load(open(\"$R/lc.json\"));print(d[\"worker\"],d[\"session\"][\"id\"])")" = "session s20" ] && [ "$first" != None ]'
sleep 1; $SE bind lc s20 > "$T/o" 2>&1
check "a repeat bind of the same session changes nothing and keeps bound_at" 'grep -q "^BOUND lc" "$T/o" && [ "$(python3 -c "import json;print(json.load(open(\"$R/lc.json\")).get(\"bound_at\"))")" = "$first" ]'
check "the bound goal moves from freezing to running" 'board | grep -A3 "^- lc " | grep -q "worker: session worker · lc" && ! board | grep -A1 "^- lc " | grep -q freezing'
$SE bind c1 s31 >/dev/null 2>&1 & $SE bind c2 s32 >/dev/null 2>&1 & wait
check "two binds at the same moment both survive (the pool lock)" 'python3 -c "import json;p=json.load(open(\"$POOL\"));assert p[\"s31\"][\"slug\"]==\"c1\" and p[\"s32\"][\"slug\"]==\"c2\""'
# Value: protects=the pool lock serializes two binds even when one is slow between its read and its write; fails_when=locked() is removed or bind reads the pool outside it (the slow bind writes its stale copy and drops the other's entry); why_new=the plain concurrent check rarely interleaves; seam=none (save_pool slowed in-process); no_claim=locks across machines
python3 - "$S" <<'PY' > "$T/slow.out" 2>&1 &
import sys, time
sys.path.insert(0, sys.argv[1]); import sessions
first = sessions.save_pool
def slow(found):
    time.sleep(1.5)
    first(found)
sessions.save_pool = slow
sys.argv = ["sessions.py", "bind", "c3", "s33"]
sys.exit(sessions.main())
PY
sleep 0.5; $SE bind c4 s34 >/dev/null 2>&1; wait
check "a slow bind and a fast bind both survive (the lock holds the read and the write together)" 'python3 -c "import json;p=json.load(open(\"$POOL\"));assert p[\"s33\"][\"slug\"]==\"c3\" and p[\"s34\"][\"slug\"]==\"c4\""'
$SE free lc > "$T/o" 2>&1
check "free gives back the goal's session and its slot" 'grep -q "^FREED 1 session(s) for lc; slot released" "$T/o" && python3 -c "
import json,sys;sys.path.insert(0,\"$S\");import graph
p=json.load(open(\"$POOL\"));r=json.load(open(\"$R/lc.json\"))
assert p[\"s20\"][\"state\"]==\"free\" and p[\"s20\"][\"freed_from\"]==\"lc\" and not graph.holds_slot(r)"'
check "a freed goal with no session shows as held" 'board | grep -q "^- lc .*  held$"'
$SE bind lc s20 > "$T/o" 2>&1; rc=$?
check "a late bind of the freed session is refused" '[ $rc = 1 ] && grep -q "REFUSED: session s20 was freed from lc at .*--force" "$T/o"'
$SE bind lc s20 --force > "$T/o" 2>&1
check "--force takes it back" 'grep -q "^BOUND lc to session s20" "$T/o"'
$SE free nothere > "$T/o" 2>&1
check "free on a goal with nothing to free says so" 'grep -qx "NOTHING TO FREE for nothere: no busy session and no session run." "$T/o"'
echo '{"slug": "wt", "status": "waiting", "step": "plan", "worker": "session", "waiting": {"ask": "Which one?"}, "log": []}' > "$R/wt.json"
$SE free wt > "$T/o" 2>&1; rc=$?
check "free refuses a goal waiting on the owner" '[ $rc = 1 ] && grep -q "REFUSED: wt is waiting on the owner (Which one?); answer it first. Nothing was changed." "$T/o"'
echo "{\"slug\": \"bg\", \"status\": \"running\", \"step\": \"plan\", \"pid\": $$, \"log\": []}" > "$R/bg.json"
$SE free bg > "$T/o" 2>&1; rc=$?
check "free refuses a goal whose background process is alive" '[ $rc = 1 ] && grep -q "REFUSED: bg is running as background pid" "$T/o"'
# a stale assignment, once freed, is ready for watch to start
python3 - "$POOL" <<'PY'
import json, sys
p = json.load(open(sys.argv[1])); p["s40"] = {"name": "worker · st1", "slug": "st1", "state": "busy", "since": "2026-01-01T00:00:00Z"}
json.dump(p, open(sys.argv[1], "w"))
PY
echo '- slug: st1 | touches: s | goal: S | done: s' >> .loop/queue.md
ready() { python3 -c "import sys,os;sys.path.insert(0,'$S');os.chdir('$T/repo');import watch;print([g['slug'] for g in watch.plan(0)[0]])"; }
before=$(ready); $SE free st1 >/dev/null; after=$(ready)
check "a stale assignment, once freed, is ready for watch to start" 'echo "$before" | grep -vq st1 && echo "$after" | grep -q st1'

echo "== issue 108: done is final"
echo '{"slug": "dn", "status": "done", "step": "pr", "pr": "https://x/pull/1", "report": {"status": "merged", "pr": "https://x/pull/1", "text": "dn merged as v1", "at": "2026-06-01T11:00:00Z"}, "log": []}' > "$R/dn.json"
echo '- slug: dep | touches: d | depends-on: dn | goal: D | done: d' >> .loop/queue.md
$SE report dn --status running --step qa > "$T/o1" 2>&1
$SE report dn --status failed --text "late failure" > "$T/o2" 2>&1
$SE report dn --status waiting --ask "Again?" > "$T/o3" 2>&1
check "a session report never moves a done goal back to running" 'grep -q "^KEPT done for dn: report recorded, status running not applied (done is final)." "$T/o1" && [ "$(python3 -c "import json;d=json.load(open(\"$R/dn.json\"));print(d[\"status\"],d[\"step\"])")" = "done pr" ]'
check "a late failed or waiting report keeps the merge evidence, so dependants stay unblocked" 'grep -q "^KEPT" "$T/o2" && grep -q "^KEPT" "$T/o3" && python3 -c "
import json,sys,os;sys.path.insert(0,\"$S\");os.chdir(\"$T/repo\");import graph,watch
d=json.load(open(\"$R/dn.json\"));assert graph.merged(d) and d[\"report\"][\"text\"]==\"dn merged as v1\" and not d.get(\"finding\") and not d.get(\"waiting\")
assert \"dep\" in [g[\"slug\"] for g in watch.plan(0)[0]]"'

mkdir -p "$T/nogh"; printf '#!/bin/bash\necho "gh: no answer" >&2; exit 1\n' > "$T/nogh/gh"; chmod +x "$T/nogh/gh"
PATH="$T/nogh:$PATH" $SE report dn --status waiting --pr https://x/pull/1 > "$T/o4" 2>&1
PATH="$T/nogh:$PATH" $SE report dn --status merged --pr https://x/pull/1 > "$T/o5" 2>&1
check "a late merged or waiting report on a merged goal, with gh unreachable, keeps the merge evidence" 'grep -q "^KEPT" "$T/o4" && grep -q "^KEPT" "$T/o5" && python3 -c "
import json,sys,os;sys.path.insert(0,\"$S\");os.chdir(\"$T/repo\");import graph,watch
d=json.load(open(\"$R/dn.json\"));assert graph.merged(d) and d[\"report\"][\"status\"]==\"merged\"
assert \"dep\" in [g[\"slug\"] for g in watch.plan(0)[0]]"'

echo "== an unreadable pool is never written"
printf '{bad' > "$POOL"; cp "$POOL" "$T/bad.copy"
$SE bind zz s50 > "$T/o1" 2>&1; r1=$?
$SE free lc > "$T/o2" 2>&1; r2=$?
check "bind and free on an unreadable pool exit 1, say why, and leave the file unchanged" '[ $r1 = 1 ] && [ $r2 = 1 ] && grep -q "REFUSED: the session pool .* can.t be read (bad JSON.*Nothing was changed." "$T/o1" && cmp -s "$POOL" "$T/bad.copy"'
cp "$T/pool.good" "$POOL"

echo "== review: report on an unreadable pool, the start_round re-check, held and done transitions"
printf '{bad' > "$POOL"; cp "$R/lc.json" "$T/lc.before"
$SE report lc --status failed --text x > "$T/o3" 2>&1; r3=$?
check "a report that ends a goal on an unreadable pool exits 1 and changes nothing" '[ $r3 = 1 ] && grep -q "REFUSED: the session pool" "$T/o3" && cmp -s "$R/lc.json" "$T/lc.before" && cmp -s "$POOL" "$T/bad.copy"'
cp "$T/pool.good" "$POOL"
python3 - "$S" "$T/repo" "$POOL" > "$T/race2.out" 2>&1 <<'PY'
import sys, os, json
sys.path.insert(0, sys.argv[1]); os.chdir(sys.argv[2])
import watch
p = json.load(open(sys.argv[3])); p["s77"] = {"name": "worker · race2", "slug": "race2", "state": "busy", "since": "2026-01-01T00:00:00Z"}
json.dump(p, open(sys.argv[3], "w"))
calls = []
watch.plan = lambda limit: ([{"slug": "race2", "goal": "R", "done": ["r"], "touches": [], "depends": [], "release": ""}], [])
watch.freeze = lambda goal, cfg: calls.append("freeze") or {"slug": "race2"}
watch.launch = lambda *a: calls.append("launch")
class A: max = 0; skill_dir = None
begun, held = watch.start_round(A, {})
print("race2", [g["slug"] for g in begun], calls)
PY
check "start_round skips a goal a session took after plan" 'grep -qx "race2 \[\] \[\]" "$T/race2.out"'
echo '{"slug": "hb", "status": "running", "step": "build", "worker": "session", "session": {"id": "s90", "name": "worker · hb"}, "updated": "2026-01-01T00:00:00Z", "log": []}' > "$R/hb.json"
$SE free hb > "$T/o" 2>&1
check "free on a held session goal with no busy entry releases its slot and it stays held" 'grep -q "^FREED 0 session(s) for hb; slot released" "$T/o" && board | grep -q "^- hb .*  held$"'
$SE report hb --step review --text "still here" >/dev/null 2>&1
check "a report on a held goal is recorded and the goal stays held" 'board | grep -q "^- hb .*  held$" && [ "$(python3 -c "import json;d=json.load(open(\"$R/hb.json\"));print(d[\"status\"],d[\"reports\"][-1][\"text\"])")" = "running still here" ]'
$SE bind hb s91 > "$T/o" 2>&1
check "binding a held goal to a new session makes it running under that session" 'grep -q "^BOUND hb to session s91" "$T/o" && board | grep -A3 "^- hb " | grep -q "worker: session worker · hb" && ! board | grep -q "^- hb .*  held$" && python3 -c "import json;p=json.load(open(\"$POOL\"));assert p[\"s91\"][\"slug\"]==\"hb\" and p[\"s91\"][\"state\"]==\"busy\""'
$SE bind dn s92 > "$T/o" 2>&1; $SE free dn > "$T/o2" 2>&1
check "bind and free on a done goal keep it done with its merge evidence" 'python3 -c "
import json,sys;sys.path.insert(0,\"$S\");import graph
d=json.load(open(\"$R/dn.json\"));assert d[\"status\"]==\"done\" and graph.merged(d)"'
$SE bind fz s93 >/dev/null 2>&1; $SE free fz > "$T/o" 2>&1
check "free on a freezing goal says its slot was released" 'grep -q "^FREED 1 session(s) for fz; slot released" "$T/o"'

python3 - "$R/hb.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["status"] = "failed"; json.dump(d, open(sys.argv[1], "w"))
PY
$SE bind hb s91 > "$T/o" 2>&1
check "binding a failed goal to the session it already has brings it back to running" 'grep -q "^BOUND hb" "$T/o" && [ "$(python3 -c "import json;print(json.load(open(\"$R/hb.json\"))[\"status\"])")" = running ]'
echo '{"slug": "badrep", "status": "running", "step": "plan", "pid": 1, "reports": {"x": 1}, "log": []}' > "$R/badrep.json"
check "a malformed reports field never crashes the board" 'board > "$T/board5" 2>&1 && grep -q "^- badrep " "$T/board5"'

echo "== coverage: mend on an unreadable pool, assign races, a report saved but not freed, Finish, a pool-only slot"
cp "$POOL" "$T/pool.keep"
# Value: protects=mend.relaunch fails closed when a session goal's pool can't be read; fails_when=the except sessions.PoolUnreadable branch in mend.relaunch is removed (a traceback, or a background relaunch); why_new=no check ran mend.py against an unreadable pool; seam=none; no_claim=one_pass's own scheduling
echo "{\"slug\": \"mr\", \"status\": \"failed\", \"step\": \"build\", \"branch\": \"loop/mr\", \"worktree\": \"$T/tree\", \"worker\": \"session\", \"session\": {\"id\": \"s95\", \"name\": \"worker · mr\"}, \"log\": []}" > "$R/mr.json"
cp "$R/mr.json" "$T/mr.before"; printf '{bad' > "$POOL"
python3 "$S/mend.py" --resume mr > "$T/o" 2>&1; rc=$?
check "mend on a session goal with an unreadable pool refuses and launches nothing" '[ $rc = 1 ] && grep -q "^REFUSED: mr not restarted: the session pool can.t be read" "$T/o" && cmp -s "$R/mr.json" "$T/mr.before" && ! grep -q Traceback "$T/o"'
cat > "$T/racetool.py" <<'TOOL'
#!/usr/bin/env python3
import json, os, subprocess, sys
cmd, pool = sys.argv[1], os.environ["RACE_POOL"]
if cmd == "start":
    print("snew")
elif cmd == "rename" and sys.argv[2] == "sfa":  # sfa can't be reached, and meanwhile another goal takes sfb
    p = json.load(open(pool)); p["sfb"] = {"name": "worker · other", "slug": "other", "state": "busy", "since": "2026-01-01T00:00:00Z"}
    json.dump(p, open(pool, "w")); sys.exit(1)
elif cmd == "send" and os.environ.get("RACE_BIND"):  # the operator binds the goal elsewhere during the send
    subprocess.run([sys.executable, os.environ["RACE_SE"], "bind", os.environ["RACE_BIND"], os.environ.get("RACE_TO", "sop")],
                   stdout=subprocess.DEVNULL)
elif cmd == "send" and os.environ.get("RACE_RUN"):  # the run moves to another session without a bind
    r = json.load(open(os.environ["RACE_RUN"])); r["session"] = {"id": "sother", "name": "w"}; json.dump(r, open(os.environ["RACE_RUN"], "w"))
TOOL
chmod +x "$T/racetool.py"
# Value: protects=assign re-checks a reused free session under the lock; fails_when=the reused-and-no-longer-free continue in sessions.assign is removed (sfb is taken from goal other); why_new=no check raced a free session against assign; seam=none; no_claim=the session tool's real timing
echo "{\"slug\": \"ra\", \"status\": \"running\", \"step\": \"idea\", \"worktree\": \"$T/tree\", \"log\": []}" > "$R/ra.json"
echo '{"sfa": {"name": "w", "slug": "", "state": "free"}, "sfb": {"name": "w", "slug": "", "state": "free"}}' > "$POOL"
LOOP_SESSION_TOOL="$T/racetool.py" RACE_POOL="$POOL" $SE assign ra > "$T/o" 2>&1; rc=$?
check "assign skips a reused free session another goal took before the claim" '[ $rc = 0 ] && python3 -c "
import json;p=json.load(open(\"$POOL\"));r=json.load(open(\"$R/ra.json\"))
assert p[\"sfb\"][\"slug\"]==\"other\" and p[\"sfb\"][\"state\"]==\"busy\" and p[\"sfa\"][\"state\"]==\"unreachable\"
assert p[\"snew\"][\"slug\"]==\"ra\" and r[\"session\"][\"id\"]==\"snew\""'
# Value: protects=an operator's bind during assign's send wins; fails_when=the HANDED guard after the send in sessions.assign is removed (the run is overwritten with snew); why_new=no check bound a goal while assign was sending; seam=none; no_claim=which session the operator should pick
echo "{\"slug\": \"rb\", \"status\": \"running\", \"step\": \"idea\", \"worktree\": \"$T/tree\", \"log\": []}" > "$R/rb.json"
echo '{}' > "$POOL"
LOOP_SESSION_TOOL="$T/racetool.py" RACE_POOL="$POOL" RACE_BIND=rb RACE_SE="$S/sessions.py" $SE assign rb > "$T/o" 2>&1; rc=$?
check "a bind during assign's send keeps the operator's bind and prints HANDED" '[ $rc = 0 ] && grep -q "^HANDED rb elsewhere during the send; session snew keeps no claim" "$T/o" && python3 -c "
import json;p=json.load(open(\"$POOL\"));r=json.load(open(\"$R/rb.json\"))
assert r[\"session\"][\"id\"]==\"sop\" and p[\"sop\"][\"slug\"]==\"rb\" and p[\"sop\"][\"state\"]==\"busy\" and p[\"snew\"][\"state\"]==\"free\""'
# Value: protects=a failed or merged report is saved before the session is freed, and a pool that breaks in between says how to finish; fails_when=the except PoolUnreadable around release in cmd_report is removed (main's REFUSED ... Nothing was changed, which is false) or the save moves after release; why_new=no check broke the pool between save and release; seam=none (sessions.save wrapped in-process); no_claim=the gh merged check
cp "$T/pool.keep" "$POOL"
echo '{"slug": "rs", "status": "running", "step": "qa", "worker": "session", "session": {"id": "s96", "name": "worker · rs"}, "log": []}' > "$R/rs.json"
python3 - "$S" "$POOL" > "$T/o" 2>&1 <<'PY'
import sys
here, pool = sys.argv[1:3]
sys.path.insert(0, here); import sessions
first = sessions.save
def save_then_break(state, note):
    first(state, note)
    open(pool, "w").write("{bad")
sessions.save = save_then_break
sys.argv = ["sessions.py", "report", "rs", "--status", "failed", "--text", "broke"]
sys.exit(sessions.main())
PY
rc=$?
check "a report saved when the pool breaks before release keeps its result, exits 1 and says to run free" '[ $rc = 1 ] && grep -q "^SAVED rs as failed, but its session wasn.t freed: the session pool can.t be read .*run sessions.py free rs" "$T/o" && python3 -c "
import json;r=json.load(open(\"$R/rs.json\"));assert r[\"status\"]==\"failed\" and r[\"report\"][\"status\"]==\"failed\""'
# Value: protects=Finish says at least only because a goal is held or freezing, when every goal has an estimate; fails_when=or held or freezing is dropped from live_board.render's missing; why_new=the old Finish check also passed on no estimate yet; seam=none; no_claim=the estimate's accuracy
mv "$R" "$R.keep"; mkdir -p "$R"
python3 - "$R" <<'PY'
import json, os, sys
log = ["2026-06-01T08:00:00Z start"] + ["2026-06-01T%02d:00:00Z %s done" % (9 + i, s) for i, s in enumerate(("idea", "plan", "build", "review", "qa", "ship", "pr"))]
json.dump({"slug": "hist", "goal": "H", "status": "done", "step": "pr", "pr": "", "log": log}, open(os.path.join(sys.argv[1], "hist.json"), "w"))
PY
echo '{}' > "$POOL"; plain=$(board | sed -n '/^Finish$/{n;p;}')
echo "{\"slug\": \"heldx\", \"status\": \"running\", \"step\": \"plan\", \"worktree\": \"$T/tree\", \"log\": []}" > "$R/heldx.json"
withheld=$(board | sed -n '/^Finish$/{n;p;}'); rm -f "$R/heldx.json"
echo '{"s97": {"name": "worker · fzz", "slug": "fzz", "state": "busy", "since": "2026-06-01T11:59:00Z"}}' > "$POOL"
withfz=$(board | sed -n '/^Finish$/{n;p;}')
echo "finish: [$plain] [$withheld] [$withfz]"
check "Finish reads at least with a real time for a held or freezing goal, and not without one" 'echo "$plain" | grep -qE "^finish about [0-9]" && echo "$withheld" | grep -qE "^at least finish about [0-9]" && echo "$withfz" | grep -qE "^at least finish about [0-9]"'
rm -rf "$R"; mv "$R.keep" "$R"
# Value: protects=a pool entry with no run (a freezing goal) uses a worker slot; fails_when=the used += taken-slugs-without-a-run line in graph.ready is removed; why_new=the window check's slot came from holds_slot on a run record; seam=none; no_claim=watch's launch path
python3 - "$S" > "$T/o" 2>&1 <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import graph
q = [{"slug": "q", "depends": []}]
start, held = graph.ready(q, {}, 1, {"fz": {"id": "s9", "name": "worker · fz"}})
print("full", [g["slug"] for g in start], [why for _, why in held])
start, held = graph.ready(q, {}, 1, {})
print("free", [g["slug"] for g in start])
PY
check "a pool entry with no run counts against parallel" 'grep -qx "full \[\] \[.slots full (1 of 1).\]" "$T/o" && grep -qx "free \[.q.\]" "$T/o"'
# Value: protects=assign on a failed goal that still names its old session gives it to the new session; fails_when=the HANDED check treats the run's earlier session id as an operator's bind (the run stays failed on the old session and the new one keeps a hidden busy entry); why_new=the HANDED check only covered a bind made during the send; seam=none; no_claim=the session tool's real timing
echo "{\"slug\": \"rc\", \"status\": \"failed\", \"step\": \"build\", \"worktree\": \"$T/tree\", \"worker\": \"session\", \"session\": {\"id\": \"sx\", \"name\": \"worker · rc\"}, \"log\": []}" > "$R/rc.json"
echo '{"sx": {"name": "worker · gb", "slug": "gb", "state": "busy", "since": "2026-06-01T11:00:00Z"}}' > "$POOL"
LOOP_SESSION_TOOL="$T/racetool.py" RACE_POOL="$POOL" $SE assign rc > "$T/o" 2>&1; rc=$?
check "assign gives a failed goal that still names its old session to the new session" '[ $rc = 0 ] && ! grep -q HANDED "$T/o" && python3 -c "
import json;p=json.load(open(\"$POOL\"));r=json.load(open(\"$R/rc.json\"))
assert r[\"session\"][\"id\"]==\"snew\" and r[\"status\"]==\"running\" and p[\"snew\"][\"slug\"]==\"rc\" and p[\"sx\"][\"slug\"]==\"gb\""'
# Value: protects=an operator who binds a failed goal back to its old session during assign's send keeps that bind; fails_when=bind stops freeing the goal's other busy sessions, or assign overwrites a bind back to the run's old session (the run moves to snew); why_new=the failed-goal check had no operator in it; seam=none; no_claim=the session tool's real timing
echo "{\"slug\": \"rd\", \"status\": \"failed\", \"step\": \"build\", \"worktree\": \"$T/tree\", \"worker\": \"session\", \"session\": {\"id\": \"sy\", \"name\": \"worker · rd\"}, \"log\": []}" > "$R/rd.json"
echo '{}' > "$POOL"  # the old session is out of the pool, so assign starts snew
LOOP_SESSION_TOOL="$T/racetool.py" RACE_POOL="$POOL" RACE_BIND=rd RACE_TO=sy RACE_SE="$S/sessions.py" $SE assign rd > "$T/o" 2>&1; rc=$?
check "a bind back to the old session during assign's send keeps the operator's bind" '[ $rc = 0 ] && grep -q "^HANDED rd" "$T/o" && python3 -c "
import json;p=json.load(open(\"$POOL\"));r=json.load(open(\"$R/rd.json\"))
assert r[\"session\"][\"id\"]==\"sy\" and p[\"sy\"][\"state\"]==\"busy\" and p[\"snew\"][\"state\"]==\"free\""'
# Value: protects=a bind back to the old session during assign's send wins even while that session is still busy for the goal; fails_when=assign's final check stops noticing the bind (bound_at changed) and overwrites the run with snew, leaving two busy sessions; why_new=the other rebind check frees snew through bind's release, so it never reaches assign's own check; seam=none; no_claim=the session tool's real timing
echo "{\"slug\": \"rz\", \"status\": \"failed\", \"step\": \"build\", \"worktree\": \"$T/tree\", \"worker\": \"session\", \"session\": {\"id\": \"sz\", \"name\": \"worker · rz\"}, \"bound_at\": \"2026-06-01T10:00:00Z\", \"log\": []}" > "$R/rz.json"
echo '{"sz": {"name": "worker · rz", "slug": "rz", "state": "busy", "since": "2026-06-01T10:00:00Z"}}' > "$POOL"
LOOP_SESSION_TOOL="$T/racetool.py" RACE_POOL="$POOL" RACE_BIND=rz RACE_TO=sz RACE_SE="$S/sessions.py" $SE assign rz > "$T/o" 2>&1; rc=$?
check "a bind back to a still-busy old session during assign's send keeps the operator's bind" '[ $rc = 0 ] && grep -q "^HANDED rz" "$T/o" && python3 -c "
import json;p=json.load(open(\"$POOL\"));r=json.load(open(\"$R/rz.json\"))
assert r[\"session\"][\"id\"]==\"sz\" and p[\"sz\"][\"state\"]==\"busy\" and p[\"snew\"][\"state\"]==\"free\""'
# Value: protects=a manual assign never gives a goal that already has a worker to a second session; fails_when=cmd_assign stops refusing a running, waiting or done goal with a worker (a new session is started and sent the goal); why_new=the failed-goal check covers only a failed run; seam=none; no_claim=watch never assigns a running goal
echo "{\"slug\": \"rf\", \"status\": \"running\", \"step\": \"build\", \"worktree\": \"$T/tree\", \"worker\": \"session\", \"session\": {\"id\": \"sa\", \"name\": \"worker · rf\"}, \"log\": []}" > "$R/rf.json"
echo '{"sa": {"name": "worker · rf", "slug": "rf", "state": "busy", "since": "2026-06-01T11:00:00Z"}}' > "$POOL"
LOOP_SESSION_TOOL="$T/racetool.py" RACE_POOL="$POOL" $SE assign rf > "$T/o" 2>&1; rc=$?
check "assign on a goal running in a session refuses before any session is started or sent to" '[ $rc = 1 ] && grep -q "^REFUSED: rf is running with a worker; nothing was sent" "$T/o" && python3 -c "
import json;p=json.load(open(\"$POOL\"));r=json.load(open(\"$R/rf.json\"))
assert r[\"session\"][\"id\"]==\"sa\" and p[\"sa\"][\"state\"]==\"busy\" and \"snew\" not in p"'
# Value: protects=a HANDED assign gives back the session it claimed; fails_when=the free of the claimed entry on HANDED is removed (snew stays busy for the goal, a hidden slot); why_new=in the bind races bind itself frees snew first; seam=none; no_claim=how the run moved
echo "{\"slug\": \"re\", \"status\": \"running\", \"step\": \"idea\", \"worktree\": \"$T/tree\", \"log\": []}" > "$R/re.json"
echo '{}' > "$POOL"
LOOP_SESSION_TOOL="$T/racetool.py" RACE_POOL="$POOL" RACE_RUN="$R/re.json" $SE assign re > "$T/o" 2>&1; rc=$?
check "a HANDED assign frees the session it claimed" '[ $rc = 0 ] && grep -q "^HANDED re" "$T/o" && python3 -c "
import json;p=json.load(open(\"$POOL\"));assert p[\"snew\"][\"state\"]==\"free\""'
# Value: protects=binding a waiting goal to a new session keeps the owner's question and moves the slot; fails_when=bind sets a waiting goal running or drops waiting, or leaves the old session busy; why_new=the state matrix's waiting x bind cell had no test; seam=none; no_claim=the operation session's message routing
echo '{"slug": "wb", "status": "waiting", "step": "plan", "worker": "session", "session": {"id": "sw1", "name": "worker · wb"}, "waiting": {"ask": "Q?", "words": ["yes"]}, "log": []}' > "$R/wb.json"
echo '{"sw1": {"name": "worker · wb", "slug": "wb", "state": "busy", "since": "2026-06-01T11:00:00Z"}}' > "$POOL"
$SE bind wb sw2 > "$T/o" 2>&1; rc=$?
check "binding a waiting goal to a new session keeps its question and frees the old session" '[ $rc = 0 ] && python3 -c "
import json;p=json.load(open(\"$POOL\"));r=json.load(open(\"$R/wb.json\"))
assert r[\"status\"]==\"waiting\" and r[\"waiting\"][\"ask\"]==\"Q?\" and r[\"session\"][\"id\"]==\"sw2\" and p[\"sw2\"][\"state\"]==\"busy\" and p[\"sw1\"][\"state\"]==\"free\""'
cp "$T/pool.keep" "$POOL"

echo "== sizes"
check "watch.py and sessions.py stay under the health rule's 20 KB" '[ $(wc -c < "$S/watch.py") -le 20480 ] && [ $(wc -c < "$S/sessions.py") -le 20480 ]'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
