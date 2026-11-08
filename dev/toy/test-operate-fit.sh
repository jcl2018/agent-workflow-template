#!/bin/bash
# Proves the operate status block against MON-4 with a made-up mix of merged, running, queued, waiting and stale goals: Needs you
# lists only open items, a goal merged on GitHub shows merged, the roadmap is the live dependency graph, and a pass with nothing
# changed prints one line. No model is called. usage: test-operate-fit.sh [DIR]
set -u
unset LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
M="$here/skills/workflow-monitoring/scripts"; OP="python3 $M/operate.py"
export HOME="$T/home"; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["mend"] = False; c["cadence"] = "10"
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
mkdir -p "$C/loop/runs"
python3 - "$C/loop/runs" <<'PY'
import json, os, sys
folder = sys.argv[1]
def write(slug, **more):
    json.dump(dict({"slug": slug, "goal": "Goal " + slug, "tries": 0, "pr": "", "waits_on": [], "updated": "2026-06-01T12:00:00Z",
                    "log": ["2026-06-01T11:00:00Z queued"]}, **more), open(os.path.join(folder, slug + ".json"), "w"))
err = "page Home is stale"
merged = ["2026-06-01T11:30:00Z merged https://example.test/pull/71 (auto_merge)"]
write("rec", status="done", step="pr", release="merged", pr="https://example.test/pull/71", wiki_error=err,
      log=["2026-06-01T11:00:00Z wiki not published: x"] + merged)   # merged in the record, stale error
write("gh", status="done", step="pr", pr="https://example.test/pull/72", wiki_error=err, release_error="boom")  # merged only on GitHub
write("late", status="done", step="pr", release="merged", pr="https://example.test/pull/74", wiki_error=err,
      log=merged + ["2026-06-01T11:45:00Z wiki not published: y"])   # the publish after the merge failed: still open
write("fresh", status="done", step="pr", release="merged", pr="https://example.test/pull/73")                  # published again: no error left
write("run", status="running", step="build", pid=1)
write("wait", status="waiting", step="plan", waiting={"ask": "Which one?", "words": ["pick a", "pick b"]})
write("stale", status="done", step="pr", wiki_error="page Docs is stale")   # still open: not merged
PY
echo '- slug: q | touches: x | depends-on: run, gh | goal: Q | done: q' >> .loop/queue.md
block() { python3 -c "
import sys; sys.path.insert(0, sys.argv[1]); import board_status
print(board_status.text(board_status.sections('$T/repo')))" "$M"; }

echo "== GitHub says the pull requests are open"
FAKE_GH_PR_STATE=OPEN block > "$T/open"
check "a goal merged on GitHub but not yet in GitHub's answer reads awaiting merge" 'grep -q "\[awaiting merge\] gh " "$T/open"'
echo "== GitHub says merged"
FAKE_GH_PR_STATE=MERGED block > "$T/block"
needs() { sed -n '/== Needs you ==/,/== Roadmap ==/p' "$T/block"; }
road() { sed -n '/== Roadmap ==/,/== Total ==/p' "$T/block"; }
check "line 1: a merged goal's old wiki_error and release_error are gone from Needs you" '! needs | grep -q "rec\|gh\|fresh" && needs | grep -q "late (wiki not published)"'
check "line 1: errors and asks that are still open stay" 'needs | grep -q "wait (waiting): Which one" && needs | grep -q "answer: pick a"'
FAKE_GH_PR_STATE=OPEN block > "$T/open"
check "line 1: with GitHub saying open, the unmerged goal keeps its error" 'sed -n "/== Needs you ==/,/== Roadmap ==/p" "$T/open" | grep -q "gh (wiki not published)"'
check "line 2: a pull request merged on GitHub shows merged, never awaiting merge" '! grep -q "awaiting merge\] gh\|waiting to merge: .*72" "$T/block" && road | grep -q "^merged: .*#72"'
check "line 2: its dependant no longer waits on it" 'road | grep "\[queued\] q " | grep -q "waits on run" && ! road | grep "\[queued\] q " | grep -q "gh"'
check "line 3: only live goals are drawn, with the stage, a 10-cell bar and an arrow" '! road | grep -q "\[merged\]" && road | grep -q "\[running\] run  stage 3 of 8 \[####------\]" && road | grep -q "\[waiting\] wait " && road | grep -q "\[awaiting merge\] stale "'
check "line 3: merged goals collapse to one line of pull request numbers" '[ "$(road | grep -c "^merged:")" = 1 ] && road | grep -q "^merged: #71 #72 #73 #74$"'
check "line 3: the total names the longest path, then a finish time" 'grep -q "^no estimate yet\|the longest chain:.*, finish about [0-9][0-9]:[0-9][0-9]" "$T/block" || python3 - "$M" <<PY
import sys, datetime
sys.path.insert(0, sys.argv[1]); import status_graph as g
t = g.total([dict(slug="a", mark="running", depends=[], stage=1, left=600), dict(slug="b", mark="queued", depends=["a"], stage=0, left=600)], datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.timezone.utc))
import re; assert re.search(r"about 20m, the longest chain: a > b, finish about \d\d:\d\d$", t), t
PY'

echo "== operate"
sed -i.bak '/depends-on: run, gh/d' .loop/queue.md; rm -f .loop/queue.md.bak
FAKE_GH_PR_STATE=MERGED $OP run --once > "$T/first" 2>&1
FAKE_GH_PR_STATE=MERGED $OP run --once > "$T/second" 2>&1
check "line 4: the first pass prints the block" 'grep -q "== Needs you ==" "$T/first"'
check "line 4: a pass with nothing changed prints exactly one line" '[ "$(wc -l < "$T/second" | tr -d " ")" = 1 ] && grep -q "^Nothing changed" "$T/second"'
python3 - "$C/loop/runs/stale.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s.pop("wiki_error"); json.dump(s, open(sys.argv[1], "w"))
PY
FAKE_GH_PR_STATE=MERGED $OP run --once > "$T/third" 2>&1
check "line 1: clearing an error counts as a change and reprints the block" 'grep -q "wiki_error" "$T/third" && grep -q "== Needs you ==" "$T/third"'

echo "== sizes"
check "every script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20479c)" ]'
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
