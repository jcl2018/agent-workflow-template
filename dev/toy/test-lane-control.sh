#!/bin/bash
# reads: skills/workflow-regression/scripts/ skills/workflow-delivery/scripts/lane.py
# reads: skills/workflow-delivery/scripts/tables.py skills/workflow-delivery/scripts/role.py
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-docs/scripts/criteria.py
# reads: skills/workflow-docs/scripts/docs.py skills/workflow-setup/scripts/setup.py
# Proves lane-control (issues 150, 135, 152, 168, 151): lane slots that a FULL lane waits for, FIFO and fail-open;
# locked row writes; a stable .last and lane-wait; record checks against HEAD; the prep commit of re-rendered Tests
# tables. A toy repo with land rows that sleep; the real lane, regression.py and slots run. No model is called.
# usage: test-lane-control.sh [DIR]
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
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
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
until_done() { for _ in $(seq 600); do out=$(poll "$1" "$2"); case "$(head -1 <<<"$out")" in running) sleep 0.3 ;; *) echo "$out"; return 0 ;; esac; done; return 1; }
holder() { # SLOT-COUNT: hold one slot in the pool until killed; prints its pid
  python3 - "$R" "$1" <<'PY' &
import os, sys, time
sys.path.insert(0, sys.argv[1]); import slots
pool = slots.lanes_dir(); slots.check(pool); fd, i = slots._slot(pool, int(sys.argv[2]), "toy/holder qa")
open(os.environ["HOME"] + "/holder.ready", "w").write("%d %d" % (os.getpid(), i)); time.sleep(600)
PY
  for _ in $(seq 100); do [ -s "$HOME/holder.ready" ] && break; sleep 0.1; done; cut -d' ' -f1 "$HOME/holder.ready"; rm -f "$HOME/holder.ready"
}

echo "== rows and slots"
for i in 1 2 3; do $reg add r$i --level land --command "sleep 3; test ! -e broken" --describe "toy row $i" >/dev/null; done
seen r1 r2 r3; git add -A; git commit -qm "rows"

# Value: protects=a FULL lane waits for a lane slot and starts when one frees (150); fails_when=no slot pool, or the wait counts against the time limit; why_new=no slot code existed; seam=none; no_claim=real CPU contention (sleep rows)
export LOOP_LANE_LIMIT=2
for g in ga gb gc; do (until_done $g qa > "$T/$g.res") & sleep 0.4; done; wait
waited=$(grep -l "^LANE_WAIT: 2 of 2 lane slots busy" "$RUNS"/g[abc].qa-lane.txt 2>/dev/null | wc -l | tr -d ' ')
check "three full lanes with 2 lane slots: one waits with LANE_WAIT naming the holders, all three pass" '[ "$waited" = 1 ] && [ "$(grep -l "^pass" "$T"/g[abc].res | wc -l | tr -d " ")" = 3 ] && grep -q "since" "$RUNS"/g[abc].qa-lane.txt'
check "the waiting lane's time counts from its slot, and its queue time is printed separately" 'grep -h "^LANE qa" "$T"/g[abc].res | grep -q "(queued [0-9]*s)"'
check ".last holds each lane's terminal result with its head" 'for g in ga gb gc; do python3 -c "import json,sys;d=json.load(open(sys.argv[1]));assert d[\"state\"]==\"pass\" and d[\"head\"]==sys.argv[2]" "$RUNS/$g.qa-lane.last" "$(git rev-parse HEAD)" || exit 1; done'

# Value: protects=a nested run never waits on its own parent's slot; fails_when=the LANE_HELD bypass is removed or ignores the holder; why_new=nested runs are new; seam=none; no_claim=none beyond protects
export LOOP_LANE_LIMIT=1
hp=$(holder 1)
_LOOP_LANE_HELD="$LOOP_LANES_DIR:0:$hp" timeout 60 $reg run land > "$T/nested.out" 2>&1 </dev/null
check "a nested FULL run under its parent's held slot starts at once" '! grep -q LANE_WAIT "$T/nested.out" && grep -q "^RESULT 3 passed" "$T/nested.out"'
(_LOOP_LANE_HELD="$LOOP_LANES_DIR:0:1" timeout 60 $reg run land > "$T/stale.out" 2>&1 </dev/null) & sp=$!
sleep 2; kill "$hp"; wait "$sp"
check "a stale _LOOP_LANE_HELD naming another pid does not bypass: it waits, then runs" 'grep -q "^LANE_WAIT: 1 of 1" "$T/stale.out" && grep -q "^RESULT 3 passed" "$T/stale.out"'

hp=$(holder 1)
LOOP_LANE_LIMIT=0 timeout 60 $reg run land > "$T/zero.out" 2>&1 </dev/null
check "lane_limit 0 never waits" '! grep -q LANE_WAIT "$T/zero.out" && grep -q "^RESULT 3 passed" "$T/zero.out"'
echo '{"limit": 1}' > "$LOOP_FLOW"
timeout 60 $reg run land > "$T/hand.out" 2>"$T/hand.err" </dev/null; rc=$?
echo '{"limit": 60}' > "$LOOP_FLOW"
check "a hand run off a terminal stops waiting after 4x the time limit: LANE_WAIT_TIMEOUT on stderr, exit 4, nothing ran" '[ $rc = 4 ] && grep -q "^LANE_WAIT_TIMEOUT: waited .* nothing ran. Fix: .*LOOP_LANE_LIMIT=0" "$T/hand.err" && ! grep -q "^PASS r" "$T/hand.out"'
kill "$hp" 2>/dev/null; wait 2>/dev/null

# Value: protects=waiting lanes are served first in, first out, and a killed holder frees its slot (O8, O18, D-O23); fails_when=polling order wins or a dead ticket blocks; why_new=tickets are new; seam=none; no_claim=fairness across machines
hp=$(holder 1)
(timeout 120 $reg run land > "$T/w1.out" 2>&1 </dev/null; date +%s.%N > "$T/w1.end") & sleep 1.5
(timeout 120 $reg run land > "$T/w2.out" 2>&1 </dev/null; date +%s.%N > "$T/w2.end") & sleep 1.5
python3 - "$LOOP_LANES_DIR" <<'PY' &
import fcntl, os, sys, time
d = sys.argv[1]; name = os.path.join(d, "ticket-%09d" % 999999999)
fd = os.open(name, os.O_RDWR | os.O_CREAT, 0o600); fcntl.flock(fd, fcntl.LOCK_EX); time.sleep(600)
PY
dead=$!; sleep 0.5; kill -9 "$dead"; kill -9 "$hp"; wait
check "a SIGKILLed holder frees its slot and the older waiter starts first; a dead ticket never blocks" 'grep -q "^RESULT 3 passed" "$T/w1.out" && grep -q "^RESULT 3 passed" "$T/w2.out" && python3 -c "import sys;a,b=(float(open(p).read()) for p in sys.argv[1:]);assert a<b" "$T/w1.end" "$T/w2.end"'
export LOOP_LANE_LIMIT=2

echo "== pool failures fail open"
mkdir -p "$T/open"; chmod 777 "$T/open"
LOOP_LANES_DIR="$T/open" timeout 60 $reg run land > "$T/open.out" 2>&1 </dev/null
check "a group- or other-writable lanes dir gives LANE_SLOTS_UNAVAILABLE with its fix, and the run still passes" 'grep -q "^LANE_SLOTS_UNAVAILABLE: .*not owned by you, or writable by group or others; running without a slot. Fix: chmod 700" "$T/open.out" && grep -q "^RESULT 3 passed" "$T/open.out"'
mkdir -p "$T/sym"; chmod 700 "$T/sym"; echo keep > "$T/target"; ln -s "$T/target" "$T/sym/slot-0"
LOOP_LANES_DIR="$T/sym" LOOP_LANE_LIMIT=1 timeout 60 $reg run land > "$T/sym.out" 2>&1 </dev/null
check "a symlinked slot file is never written through (O_NOFOLLOW); the run fails open" '[ "$(cat "$T/target")" = keep ] && grep -q "^LANE_SLOTS_UNAVAILABLE" "$T/sym.out" && grep -q "^RESULT 3 passed" "$T/sym.out"'

echo "== locked row writes (135)"
for i in 1 2 3 4 5 6 7 8; do $reg add k$i --level land --command "test ! -e broken" --describe "lock $i" >/dev/null; done
git add -A; git commit -qm "k rows"
# Value: protects=parallel red runs keep every seen-failing date (135); fails_when=write_rows rewrites the table from a read taken before the run; why_new=no concurrent writer test existed; seam=none; no_claim=none beyond protects
for i in 1 2 3 4 5 6 7 8; do $reg red k$i --break "touch broken" > /dev/null 2>&1 & done; wait
check "eight parallel red runs keep all eight seen-failing dates" '[ "$(grep -c "^k[1-8]	land	test ! -e broken	[^	]*	2[0-9-]*" .loop/regression.tsv)" = 8 ]'
$reg add p1 --level land --command "true" --describe one >/dev/null & $reg add p2 --level land --command "true" --describe two >/dev/null & wait
$reg add p1 --level nightly --command "true" --describe one-again >/dev/null
check "two parallel adds keep both rows; adding an id again replaces only that row" 'grep -q "^p2	land" .loop/regression.tsv && grep -q "^p1	nightly	true	.*one-again" .loop/regression.tsv && [ "$(grep -c "^p1	" .loop/regression.tsv)" = 1 ]'
check "no lock file ever lands in the worktree" 'git add -A >/dev/null; [ -z "$(git status --porcelain | grep -i lock)" ] && [ -f "$(git rev-parse --git-common-dir)/loop/locks/regression.tsv.lock" ]'
git commit -qm "p rows" >/dev/null 2>&1
chmod 500 "$(git rev-parse --git-common-dir)/loop/locks"; rm -f "$(git rev-parse --git-common-dir)/loop/locks/regression.tsv.lock" 2>/dev/null
out=$($reg add p3 --level land --command true --describe three 2>&1); rc=$?
chmod 700 "$(git rev-parse --git-common-dir)/loop/locks"
check "a lock that can't be taken refuses with its fix and writes nothing" '[ $rc != 0 ] && grep -q "^REFUSED: cannot lock .loop/regression.tsv: .*nothing was written. Fix: make .* writable" <<<"$out" && ! grep -q "^p3	" .loop/regression.tsv'

echo "== a stable result and lane-wait (152)"
# Value: protects=one stable result path and a blocking wait (152); fails_when=the result only lands in an attempt-suffixed rc file; why_new=.last and lane-wait are new; seam=none; no_claim=none beyond protects
poll lw qa >/dev/null
$role lane-wait lw qa > "$T/lw.out" 2>&1; rc=$?
check "role.py lane-wait blocks until the lane ends and exits 0 with its LANE line" '[ $rc = 0 ] && grep -q "^LANE qa" "$T/lw.out" && python3 -c "import json,sys;assert json.load(open(sys.argv[1]))[\"state\"]==\"pass\"" "$RUNS/lw.qa-lane.last"'
echo x >> README.md; git commit -qam "move"
$role lane-wait lw qa > "$T/none.out" 2>&1; rc=$?
check "lane-wait with no lane for this HEAD exits 3 naming the start command; an old pass never counts" '[ $rc = 3 ] && grep -q "^NO LANE: none ran on .*role.py lane lw qa" "$T/none.out"'
python3 - "$S" "$RUNS/lw.qa-lane.last" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1]); import lane
d = json.load(open(sys.argv[2])); lane.set_last(sys.argv[2], d["attempt"], state="ended", rc=0)
PY
check "a late ended write never replaces a terminal pass" 'python3 -c "import json,sys;assert json.load(open(sys.argv[1]))[\"state\"]==\"pass\"" "$RUNS/lw.qa-lane.last"'

echo "== records check HEAD (168)"
# Value: protects=record ship refuses a lane from before a merge or commit (168); fails_when=need_lane only checks qa; why_new=ship had no check; seam=none; no_claim=none beyond protects
reply="$T/reply.txt"; printf 'DEPTH: full\nSTEP: done\n' > "$reply"
out=$(cd "$S" && python3 -c "import role,sys;role.need_lane(sys.argv[1],'rs',sys.argv[2],'ship')" "$RUNS" "$reply" 2>&1)
check "record ship with no ship lane refuses LANE_MISSING with the lane command" 'grep -q "REFUSED: the ship lane has not passed on .*(LANE_MISSING). Fix: python3 .*role.py lane rs ship" <<<"$out"'
git rev-parse HEAD > "$RUNS/rs.ship-lane.ok"; echo y >> README.md; git commit -qam "fix after the lane"
out=$(cd "$T/repo" && python3 -c "import sys;sys.path.insert(0,sys.argv[3]);import role;role.need_lane(sys.argv[1],'rs',sys.argv[2],'ship')" "$RUNS" "$reply" "$S" 2>&1)
check "record ship after a commit refuses: HEAD moved since the ship lane passed, with the rerun command" 'grep -q "REFUSED: HEAD moved since the ship lane passed (lane on .*, HEAD .*). Fix: python3 .*role.py lane rs ship (reruns only the rows the change can affect" <<<"$out"'
git rev-parse HEAD > "$RUNS/rs.ship-lane.ok"
check "after the rerun passes on HEAD, record ship goes through" 'python3 -c "import sys;sys.path.insert(0,sys.argv[3]);import role;role.need_lane(sys.argv[1],\"rs\",sys.argv[2],\"ship\")" "$RUNS" "$reply" "$S"'

# Value: protects=a lane on an older HEAD never blocks the new one (E-O30, done line 4); fails_when=the one-lane rule ignores head; why_new=one-lane rule is new; seam=none; no_claim=none beyond protects
poll st ship >/dev/null; old=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['head'])" "$RUNS/st.ship-lane.job")
echo z >> README.md; git commit -qam "ship fix"
out=$(poll st pr)
check "a live lane of the goal on an older HEAD is stopped and the new lane starts at once" 'head -1 <<<"$out" | grep -q running && [ "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))[\"head\"])" "$RUNS/st.pr-lane.job")" = "$(git rev-parse HEAD)" ] && [ ! -e "$RUNS/st.ship-lane.job" ]'
poll st2 qa >/dev/null; out=$(poll st2 ship)
check "a sibling lane on the same HEAD makes the new lane wait, naming lane-wait" 'grep -q "^WAITING: the qa lane of this goal is still running; .*role.py lane-wait SLUG qa" <<<"$out"'
until_done st pr >/dev/null; until_done st2 qa >/dev/null

echo "== the plan is rechecked after a wait"
export LOOP_LANE_LIMIT=1; hp=$(holder 1)
(timeout 120 $reg run land > "$T/stale1.out" 2>"$T/stale1.err" </dev/null; echo $? > "$T/stale1.rc") & sleep 2
echo w >> README.md; git commit -qam "while queued"; kill "$hp"; wait
check "a commit while a lane waits gives LANE_STALE (HEAD moved), exit 5, no rows ran" '[ "$(cat "$T/stale1.rc")" = 5 ] && grep -q "^LANE_STALE: HEAD moved while queued .* no rows ran. Fix: run the same command again" "$T/stale1.err" && ! grep -q "^PASS r" "$T/stale1.out"'
hp=$(holder 1)
(timeout 120 $reg run land > "$T/stale2.out" 2>"$T/stale2.err" </dev/null; echo $? > "$T/stale2.rc") & sleep 2
echo v >> README.md; kill "$hp"; wait; git checkout -q README.md
check "an uncommitted edit while a lane waits gives the worktree LANE_STALE with the path, exit 5" '[ "$(cat "$T/stale2.rc")" = 5 ] && grep -q "^LANE_STALE: the worktree changed while queued (README.md); no rows ran" "$T/stale2.err"'
export LOOP_LANE_LIMIT=2

echo "== the prep commit keeps Tests tables fresh (151)"
docs="python3 $here/skills/workflow-docs/scripts/docs.py"; cri="python3 $here/skills/workflow-docs/scripts/criteria.py"
python3 -c "import json;c=json.load(open('.loop/config.json'));c['criteria']=True;json.dump(c,open('.loop/config.json','w'),indent=2)"
mkdir -p docs/wiki
printf '<!-- workflow-docs -->\n# Calc\n\nReview: **Unreviewed**\n\n## Problem\n\nThe toy calculator, written for this test.\n\n## Requirements\n\n- CAL-1: **Unreviewed** The calculator adds.\n\n## Non-goals\n\n- No other feature.\n\n## Success metrics\n\n- The toy run passes.\n\n## Tests\n\n' > docs/wiki/Calc.md
$docs add Calc --paths calc.py >/dev/null 2>&1
$reg add r1 --level land --command "sleep 3; test ! -e broken" --goal CAL-1 --describe "Given the calculator, when it adds, then it works." >/dev/null
seen r1; $cri render >/dev/null; git add -A; git commit -qm "Calc page"
# Value: protects=a by-id rerun never leaves the Tests tables stale for the next lane (151); fails_when=no prep commit, or it commits more than rendered paths; why_new=prep is new; seam=none; no_claim=none beyond protects
$reg run r1 >/dev/null 2>&1
check "a by-id rerun leaves new run dates uncommitted" '[ -n "$(git status --porcelain -- .loop/regression-runs.tsv)" ]'
echo staged > staged.txt; git add staged.txt
out=$(poll pp qa)
check "a staged unrelated file makes the lane refuse LANE_DIRTY before any render or commit" 'grep -q "^LANE_DIRTY at start: staged.txt" <<<"$out" && [ "$(git log -1 --format=%s)" = "Calc page" ]'
git rm -q --cached staged.txt; rm staged.txt
printf '#!/bin/sh\necho hook says no >&2\nexit 1\n' > "$(git rev-parse --git-path hooks)/pre-commit"; chmod +x "$(git rev-parse --git-path hooks)/pre-commit"
out=$(poll pp qa)
check "a refused prep commit is LANE_PREP_FAILED with its fix, leaves the index empty and starts no lane" 'grep -q "^LANE_PREP_FAILED: git commit failed: hook says no .*Fix: make the commit pass" <<<"$out" && [ -z "$(git diff --cached --name-only)" ] && [ ! -e "$RUNS/pp.qa-lane.job" ]'
printf '#!/bin/sh\nsleep 90\n' > "$(git rev-parse --git-path hooks)/pre-commit"
began=$(date +%s); out=$(poll pp qa); took=$(( $(date +%s) - began ))
check "a hanging pre-commit hook times out to LANE_PREP_FAILED within about a minute" 'grep -q "^LANE_PREP_FAILED: git commit failed: timed out after 60s" <<<"$out" && [ $took -lt 90 ]'
rm -f "$(git rev-parse --git-path hooks)/pre-commit"
out=$(until_done pp qa)
check "the next lane commits only the re-rendered page and run dates, says LANE_PREP, and passes" 'grep -q "^LANE_PREP: re-rendered the Tests tables (commit " "$RUNS/pp.qa-lane.txt" && [ "$(git log -1 --format=%s)" = "Lane: re-render the Tests tables" ] && [ "$(git show --name-only --format= HEAD | sort | tr "\n" " ")" = ".loop/regression-runs.tsv docs/wiki/Calc.md " ] && head -1 <<<"$out" | grep -q pass'
$cri render --check >/dev/null; rc=$?
check "after the prep commit the docs check finds no stale Tests table" '[ $rc = 0 ]'
sed -i.bak 's/The toy calculator, written/The calculator, rewritten/' docs/wiki/Calc.md; rm docs/wiki/Calc.md.bak
out=$(poll pp ship)
check "a hand edit above a page's Tests section refuses LANE_DIRTY naming the page, and nothing is committed" 'grep -q "^LANE_DIRTY: docs/wiki/Calc.md has edits above its ## Tests section" <<<"$out" && [ "$(git log -1 --format=%s)" = "Lane: re-render the Tests tables" ]'
git checkout -q docs/wiki/Calc.md

echo "== upgrade and races"
# Value: protects=an attempt started by the old code finishes under the old rule (D-O27); fails_when=a job with no markers is treated as planning; why_new=job format changed; seam=none; no_claim=none beyond protects
sleep 120 & sp=$!
python3 - "$RUNS" "$sp" "$(git rev-parse HEAD)" <<'PY'
import json, sys, time
runs, pid, head = sys.argv[1:]
base = runs + "/old.qa-lane"
json.dump({"head": head, "attempt": "1-1", "started": time.time() - 3000, "limit": 2700, "rc": base + ".1-1.rc", "pid": int(pid)}, open(base + ".job", "w"))
PY
out=$(poll old qa)
check "an old-format lane job (no markers) keeps the old rule and is not killed as planning" 'head -1 <<<"$out" | grep -q running && kill -0 $sp'
printf 'FULL: no record\nPASS r1\nRESULT 1 passed, 0 known, 0 failed, 0 unproven\n' > "$RUNS/old.qa-lane.txt"; echo 0 > "$RUNS/old.qa-lane.1-1.rc"; kill $sp
out=$(poll old qa)
check "it finishes as a pass once its exit status lands" 'head -1 <<<"$out" | grep -q pass'
# Value: protects=two callers finishing one lane give one result (E-O28); fails_when=both read and delete the rc file; why_new=lane-wait adds a second finalizer; seam=none; no_claim=none beyond protects
died=0
for i in $(seq 20); do
  python3 - "$RUNS" "$(git rev-parse HEAD)" "$i" <<'PY'
import json, sys, time
runs, head, i = sys.argv[1:]
base = runs + "/race%s.qa-lane" % i
json.dump({"head": head, "attempt": "9-%s" % i, "started": time.time() - 5, "limit": 60, "rc": base + ".rc", "pid": 1, "markers": 1, "pool": "/nonexistent"}, open(base + ".job", "w"))
open(base + ".txt", "w").write("FULL: x\nPASS r1\nRESULT 1 passed\n"); open(base + ".rc", "w").write("0")
PY
  a=$(python3 "$T/h.py" "$S" "$RUNS" race$i qa status &); b=$(python3 "$T/h.py" "$S" "$RUNS" race$i qa status); wait
  grep -q LANE_DIED <<<"$a$b" && died=$((died + 1))
done
check "two callers finishing the same lane 20 times never report LANE_DIED and leave one terminal pass" '[ $died = 0 ] && for i in $(seq 20); do python3 -c "import json,sys;assert json.load(open(sys.argv[1]))[\"state\"]==\"pass\"" "$RUNS/race$i.qa-lane.last" || exit 1; done'
$role lane-wait nolane qa >"$T/o.out" 2>"$T/o.err"; rc=$?
check "status lines go to stdout and the exit code says what happened (3: no lane)" '[ $rc = 3 ] && grep -q "^NO LANE" "$T/o.out" && [ ! -s "$T/o.err" ]'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
