#!/bin/bash
# reads: skills/workflow-health/scripts/health.py skills/workflow-health/scripts/cost.py
# reads: skills/workflow-health/scripts/cost.py skills/workflow-health/scripts/report.py
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# REG-7: health warns when a goal's lane took over goal_lane_minutes or the newest full suite over its 30-minute limit,
# says the suite time when it is under, and says how to get one when none is recorded; a FULL lane is left to the suite.
# Value: protects=health flags a slow goal lane or full suite (REG-7); fails_when=the limits are ignored, a FULL lane
# warns as a goal lane, or a missing suite time passes silently; why_new=health had no test-run timing; seam=none;
# no_claim=times from real runs (fixture files stand in)
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
export HOME=$(mktemp -d)
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
cd "$d" && git init -q -b main && git commit -q --allow-empty -m init
mkdir -p .loop .git/loop/runs
printf '{"base": "main", "goal_lane_minutes": 1}\n' > .loop/config.json
printf '# id\tlevel\tcommand\n' > .loop/regression.tsv
H="python3 $here/skills/workflow-health/scripts/health.py check --family cost"
out=$($H 2>&1)
grep -q "^INFO performance full-suite time: no full-suite time recorded yet" <<<"$out" && ok "no suite time recorded: an INFO line says how to get one" || bad "no suite time: $out"
echo '{"status": "running"}' > .git/loop/runs/g.json; echo '{"status": "done"}' > .git/loop/runs/old.json
echo '{"state": "pass", "line": "LANE qa AFFECTED 3/3 in 125s"}' > .git/loop/runs/g.qa-lane.last
echo '{"state": "pass", "line": "LANE pr FULL 9/9 in 900s"}' > .git/loop/runs/g.pr-lane.last
echo '{"state": "pass", "line": "LANE qa AFFECTED 3/3 in 999s"}' > .git/loop/runs/old.qa-lane.last
printf 'abc1234567890\tfull\t1900\t2026-11-10\n' > .git/loop/suite-times.tsv
out=$($H 2>&1)
grep -q "^WARN performance goal-lane time: g qa took 2 min (limit 1, goal_lane_minutes)" <<<"$out" \
  && ! grep -q "goal-lane time: g pr" <<<"$out" && ! grep -q "goal-lane time: old" <<<"$out" \
  && ok "a goal lane over goal_lane_minutes warns; a FULL lane and a finished goal's lane don't" || bad "goal lanes: $out"
grep -q "^WARN performance full-suite time: 31 min (limit 30, the full-suite limit), from local run on 2026-11-10" <<<"$out" \
  && ok "a full suite over 30 minutes warns with its source and date" || bad "suite over: $out"
printf 'abc1234567890\tfull\t1900\t2026-11-10\ndef1234567890\tland\t9999\t2026-11-10\nfed1234567890\tfull\t60\t2026-11-11\n' > .git/loop/suite-times.tsv
out=$($H 2>&1)
grep -q "full-suite time: suite: 1 min (limit 30, the full-suite limit), from local run on 2026-11-11" <<<"$out" \
  && ok "the newest full line counts, a land line never does, and an under-limit suite still shows its time" || bad "suite under: $out"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
