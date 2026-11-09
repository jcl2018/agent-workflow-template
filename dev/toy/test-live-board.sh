#!/bin/bash
# Proves the live board line by line with a made-up repo: two running goals, queued and chained goals and one open issue (a stuck
# worker). No model is called. usage: test-live-board.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
unset LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
M="$here/skills/workflow-monitoring/scripts"
export HOME="$T/home"; mkdir -p "$HOME"
export LOOP_BOARD_HEALTH=green PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
cd "$T/repo" || exit 1
echo 0.1.2 > VERSION
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
mkdir -p "$C/loop/runs"
python3 - "$C/loop/runs" <<'PY'
import json, os, sys, datetime
folder = sys.argv[1]
def stamp(s):
    return (datetime.datetime(2026, 6, 1, 12, 0, 0) + datetime.timedelta(seconds=s)).strftime("%Y-%m-%dT%H:%M:%SZ")
past = [stamp(-18000) + " queued", stamp(-17400) + " idea done", stamp(-16140) + " plan done", stamp(-14310) + " build done"]
def write(slug, **more):
    json.dump(dict({"slug": slug, "goal": "Goal " + slug, "tries": 0, "pr": "", "waits_on": []}, **more), open(os.path.join(folder, slug + ".json"), "w"))
write("hist", status="done", step="pr", release="merged", updated=stamp(-14000), log=past)
write("alpha", status="running", step="build", updated=stamp(0), pid=1, log=[stamp(-1000) + " queued", stamp(-400) + " idea done", stamp(-300) + " plan done", stamp(0) + " start build"])
write("beta", status="waiting", step="plan", updated=stamp(0), pid=1, log=[stamp(-100) + " queued"],
      waiting={"ask": "Which database? See /srv/me/secret/notes.md", "words": ["use sqlite", "use postgres"]})
PY
mkdir -p .loop
cat >> .loop/queue.md <<'Q'
- slug: gamma | touches: x | depends-on: alpha | goal: G | done: g
- slug: delta | touches: x | depends-on: gamma, beta | goal: D | done: d
- slug: eps | touches: x | goal: E | done: e
Q
AT=2026-06-01T12:00:00Z
python3 - "$M" "$T/repo" > "$T/board" <<'PY'
import sys, datetime
sys.path.insert(0, sys.argv[1]); import live_board
at = datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
print("\n".join(live_board.render(sys.argv[2], at)))
PY
cat "$T/board"
L() { sed -n "$1p" "$T/board"; }

echo "== the format, line by line"
check "line 1 is the header: LIVE BOARD, repo, local time, version, health" 'L 1 | grep -Eq "^LIVE BOARD  repo  [0-9]{2}:[0-9]{2} [A-Za-z0-9+]+  v0\.1\.2  health: green$"'
check "the sections come in order: Issues, Running goals, Queued goals, Dependencies, Finish" 'grep -nE "^(Issues|Running goals|Queued goals|Dependencies|Finish)$" "$T/board" | cut -d: -f2 | paste -sd, - | grep -qx "Issues,Running goals,Queued goals,Dependencies,Finish"'
check "Issues puts the stuck worker first, with its fix and the exact words" 'sed -n "/^Issues/,/^Running/p" "$T/board" | sed -n 2,3p | grep -q "^- beta is waiting" && sed -n "/^Issues/,/^Running/p" "$T/board" | grep -q "fix: answer by typing \"use sqlite\" or \"use postgres\""'
check "no local path appears anywhere" '! grep -Eq "/srv|/home|~/|\.git/|\.loop" "$T/board"'
check "a running goal has a 10-cell bar, percent and time left" 'grep -Eq "^- alpha  \[#{2}-{8}\] 25%  [0-9]+m left$" "$T/board"'
check "its step flow ticks done steps and brackets the current one" 'grep -qx "    idea✓ > plan✓ > \[build\] > review > qa > ship > pr > release" "$T/board"'
check "the other running goal shows its own flow" 'grep -qx "    idea✓ > \[plan\] > build > review > qa > ship > pr > release" "$T/board"'
check "each running goal has a one-line next step" '[ "$(grep -c "^    next: " "$T/board")" = 2 ]'
check "Queued goals list gamma, delta and eps with what they wait on" 'sed -n "/^Queued goals/,/^Dependencies/p" "$T/board" | grep -q "^- gamma .*waits on alpha$" && sed -n "/^Queued goals/,/^Dependencies/p" "$T/board" | grep -q "^- delta .*waits on gamma, beta$" && sed -n "/^Queued goals/,/^Dependencies/p" "$T/board" | grep -Eq "^- eps  [^ ].*$" && ! sed -n "/^Queued goals/,/^Dependencies/p" "$T/board" | grep eps | grep -q waits'
check "Dependencies are arrows between running and queued goals" 'sed -n "/^Dependencies/,/^Finish/p" "$T/board" | grep -qx "alpha --> gamma" && sed -n "/^Dependencies/,/^Finish/p" "$T/board" | grep -qx "gamma --> delta" && sed -n "/^Dependencies/,/^Finish/p" "$T/board" | grep -qx "beta --> delta"'
check "one finish time closes the board" 'tail -2 "$T/board" | head -1 | grep -qx Finish && tail -1 "$T/board" | grep -Eq "^(at least )?finish about [0-9]{2}:[0-9]{2} "'
check "merged work, history, totals, milestones, tokens and done lines are left out" '! grep -Eiq "merged|hist|closed|milestone|tokens|total|done lines|longest|Roadmap|Needs you|level [0-9]" "$T/board"'

echo "== the same board everywhere"
out=$(python3 "$M/board_status.py"); echo "$out" | head -1 | grep -q "^LIVE BOARD" && ok "board_status prints the live board" || bad "board_status prints the live board"
check "the HTML fragment holds the same lines" 'python3 "$M/board_status.py" --html | grep -q "<pre>LIVE BOARD  repo"'
python3 "$M/operate.py" run --once > "$T/op" 2>&1
check "operate prints the full live board" 'grep -q "^LIVE BOARD  repo" "$T/op" && grep -q "^Finish" "$T/op"'
python3 "$M/operate.py" run --once > "$T/op2" 2>&1
check "an unchanged second pass prints the full board too, with no one-line mode" 'grep -q "^LIVE BOARD  repo" "$T/op2" && ! grep -q "NO_CHANGE\|Nothing changed" "$T/op2"'
art=$(find "$C/loop" -name board-artifact.html)
check "the board artifact page shows the same live board" '[ -n "$art" ] && grep -q "<pre>LIVE BOARD  repo" "$art" && grep -q "alpha --&gt; gamma" "$art" && ! grep -q "<html" "$art"'
check "the default cadence is 30 minutes" 'python3 "$M/board.py" cadence | grep -qx "CADENCE 30"'

echo
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
