#!/bin/bash
# reads: dev/toy/reap.sh dev/toy/reap.py
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# Issue 435: two lanes run toy tests at once and both finish. Lane A's test keeps a worker whose own nested test shell
# has ended (its marker names a gone owner) while A still waits on it; lane B, at the same time, runs the sweep the
# REAP line suggests. The sweep may stop only lane B's processes, never lane A's.
# Value: protects=REG-8 lanes never stop each other (issue 435); fails_when=a sweep judges another lane's markers;
# why_new=test-no-leftovers.sh checks one lane only; seam=none; no_claim=real lane runners (two shells with two
# _LOOP_LANE_LABEL values stand in for two lanes)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
T=$(mktemp -d); toy_on_exit 'rm -rf "$T"'
# lane A: a nested toy test starts a worker (a non-system python3, as reap.py's docstring asks) and exits; the outer
# test still needs that worker for 6 seconds, then checks it finished on its own
( unset TOY_REAP_ID TOY_REAP_LANE _toy_reap_on; export _LOOP_LANE_LABEL="toy/laneA qa"
  bash -c '. "'"$here"'/dev/toy/reap.sh"; toy_reap() { :; }; python3 -c "import time; time.sleep(6); open(\"'"$T"'/a.done\", \"w\")" & echo $! > "'"$T"'/a.pid"; disown' 
  sleep 7; [ -e "$T/a.done" ] && echo finished > "$T/a.result" || echo killed > "$T/a.result" ) &
lane_a=$!
sleep 1.5
# lane B: the sweep a REAP line suggests, run while lane A works
( unset TOY_REAP_ID TOY_REAP_LANE _toy_reap_on; export _LOOP_LANE_LABEL="toy/laneB qa"
  bash "$here/dev/toy/reap.sh" --sweep-dead > "$T/b.out" 2>&1; echo "rc=$?" >> "$T/b.out" ) &
lane_b=$!
wait "$lane_a" "$lane_b"
[ "$(cat "$T/a.result" 2>/dev/null)" = finished ] && ok "lane A's worker finished while lane B swept" \
  || bad "lane B's sweep stopped lane A's worker ($(cat "$T/b.out" 2>/dev/null | tr '\n' ' '))"
grep -q '^rc=0' "$T/b.out" && ok "lane B's sweep finished" || bad "lane B's sweep failed: $(cat "$T/b.out")"
# the lane's own leftovers are still swept: a marker of lane B whose shell is gone is stopped by lane B's sweep
( unset TOY_REAP_ID TOY_REAP_LANE _toy_reap_on; export _LOOP_LANE_LABEL="toy/laneB qa"
  bash -c '. "'"$here"'/dev/toy/reap.sh"; toy_reap() { :; }; python3 -c "import time; time.sleep(30)" & echo $! > "'"$T"'/b.pid"; disown'
  sleep 0.5; bash "$here/dev/toy/reap.sh" --sweep-dead > "$T/b2.out" 2>&1 )
p=$(cat "$T/b.pid"); sleep 0.3
if kill -0 "$p" 2>/dev/null; then bad "lane B's sweep left its own dead test's worker $p"; kill -9 "$p"; else ok "a lane still sweeps its own dead test's worker"; fi
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
