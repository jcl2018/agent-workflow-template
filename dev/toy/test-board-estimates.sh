#!/bin/bash
# reads: skills/workflow-monitoring/scripts/
# Issue 93: an overrunning step moves time left and the finish time, and no board line passes 60 characters. A made-up repo with
# one done run (idea 10m, build 30m) and one running run on build, sampled twice. No model is called. usage: test-board-estimates.sh [DIR]
set -u
unset LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
M="$here/skills/workflow-monitoring/scripts"
export HOME="$T/home"; mkdir -p "$HOME"
export LOOP_BOARD_HEALTH=green PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
export TZ=UTC  # the checks compare HH:MM text and the zone name; pin the zone so they hold everywhere
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
def write(slug, **more):
    json.dump(dict({"slug": slug, "goal": "Goal " + slug, "tries": 0, "pr": "", "waits_on": []}, **more), open(os.path.join(folder, slug + ".json"), "w"))
write("hist", status="done", step="pr", release="merged", updated=stamp(-14000),
      log=[stamp(-20000) + " queued", stamp(-19400) + " idea done", stamp(-17600) + " build done"])
write("a-very-long-goal-name-that-keeps-going", status="running", step="build", updated=stamp(0), pid=1,
      log=[stamp(-3000) + " queued", stamp(-2400) + " idea done", stamp(0) + " start build"],
      waits_on=[])
PY
cat > "$T/at.py" <<'PY'
import sys, datetime
sys.path.insert(0, sys.argv[1]); import live_board
at = datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=int(sys.argv[3]))
print("\n".join(live_board.render(sys.argv[2], at)))
PY
board() { python3 "$T/at.py" "$M" "$T/repo" "$1"; }
mins() { sed -n 's/.* \([0-9]*\)m left.*/\1/p' | head -1; }
board 600 > "$T/early"      # build 10m in, 30m usual: on time
board 3600 > "$T/late"      # 60m in: 30m over
board 7200 > "$T/later"     # 120m in
cat "$T/late"
fin() { sed -n '$p' "$1" | grep -Eo '[0-9]{2}:[0-9]{2}' | head -1; }
check "on time: no over-by mark" '! grep -q "over by" "$T/early"'
check "over: the step reads over by 30m" 'grep -q "\[build over by 30m\]" "$T/late"'
check "over: time left is re-estimated from time spent (30m)" '[ "$(mins < "$T/late")" = 30 ]'
check "over: time left keeps growing as the step runs (1h00m)" 'grep -q "1h00m left" "$T/later"'
check "over: the finish time grows with it" '[ "$(fin "$T/later")" \> "$(fin "$T/late")" ] && [ "$(fin "$T/late")" \> "$(fin "$T/early")" ]'
wide() { python3 -c "import sys; sys.exit(0 if any(len(l.rstrip(chr(10))) > 60 for l in sys.stdin) else 1)"; }
check "no line is over 60 characters (early, late, later)" '! cat "$T/early" "$T/late" "$T/later" | wide'
check "the HTML fragment holds the same short lines" '! python3 "$M/board_status.py" --html | sed "s/<[^>]*>//g; s/&gt;/>/g" | wide'
# Value: protects=a header past 60 chars splits into name+clock, then version+health; fails_when=the split is removed or cuts the
#   wrong fields; why_new=the other checks use a short repo name; seam=none; no_claim=real terminal width (text model only)
ln -s "$T/repo" "$T/a-repo-with-a-rather-long-name-12345"
python3 "$T/at.py" "$M" "$T/a-repo-with-a-rather-long-name-12345" 600 > "$T/longhead"
check "a long header splits: name and clock, then version and health" 'sed -n 1p "$T/longhead" | grep -Eq "^LIVE BOARD  a-repo-with-a-rather-long-name-12345  [0-9]{2}:[0-9]{2}( [A-Z]+)?$" && sed -n 2p "$T/longhead" | grep -Eq "^v0\.1\.2  health: green$" && ! wide < "$T/longhead"'
# Value: protects=a re-estimated step never reads under 60s left, however short its usual time; fails_when=the max(60, ...) floor
#   is removed; why_new=the fixture's 30m estimate never reaches the floor; seam=none; no_claim=none beyond protects (direct call)
check "re-estimate: a short step past its time still has a minute left" '[ "$(python3 -B -c "import sys; sys.path.insert(0, sys.argv[1]); import board_status as b; print(b.step_left(30, 40))" "$M")" = "(60, 10)" ]'
# Value: protects=a single token over 60 chars is cut to the board width; fails_when=break_long_words is turned off; why_new=no
#   fixture line holds a 60+ char word; seam=none; no_claim=real terminal width (text model only)
check "fit: a word longer than the width is cut to it" 'python3 -B -c "import sys; sys.path.insert(0, sys.argv[1]); import live_board as l; o = l.fit([\"x\" * 75]); sys.exit(0 if o[0] == \"x\" * 60 and all(len(i) <= 60 for i in o) and \"\".join(i.strip() for i in o) == \"x\" * 75 else 1)" "$M"'
# Value: protects=the over-by mark shows only from a full minute over; fails_when=the over >= 60 threshold is dropped or moved;
#   why_new=the fixture is only 0 or 30m over, never near the minute; seam=none; no_claim=none beyond protects (direct call)
check "over by: 59s over has no mark, 60s over reads over by 1m" 'python3 -B -c "import sys; sys.path.insert(0, sys.argv[1]); import live_board as l; r = {\"status\": \"running\", \"step\": \"build\"}; a, b = \" \".join(l.flow_lines(r, 59)), \" \".join(l.flow_lines(r, 60)); sys.exit(0 if \"over by\" not in a and \"[build over by 1m]\" in b else 1)" "$M"'
# Value: protects=a wrapped line keeps hyphenated names whole and indents its continuation two past its own indent;
#   fails_when=break_on_hyphens is turned on or the continuation indent changes; why_new=the other checks collapse whitespace or
#   never put a hyphenated word across the 60th column; seam=none; no_claim=real terminal width (text model only)
check "fit: a hyphenated name is not split and the continuation is indented two more" 'python3 -B -c "import sys; sys.path.insert(0, sys.argv[1]); import live_board as l; o = l.fit([\"    next: merge \" + \"a\" * 30 + \" the-goal-with-a-long-name now\"]); sys.exit(0 if o == [\"    next: merge \" + \"a\" * 30, \"      the-goal-with-a-long-name now\"] else 1)" "$M"'
echo
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
