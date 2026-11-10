#!/bin/bash
# Proves the operate status block against MON-4 with a made-up mix of merged, running, queued, waiting and stale goals: Needs you
# lists only open items, a goal merged on GitHub shows merged, the roadmap is the live dependency graph, and a pass with nothing
# changed prints one line. No model is called. usage: test-operate-fit.sh [DIR]
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
unset LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
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
write("healed", status="done", step="pr", pr="https://example.test/pull/80", wiki_error=err,
      log=["2026-06-01T11:00:00Z wiki not published: z", "2026-06-01T11:50:00Z wiki published"])   # published later, not merged
write("shut", status="done", step="pr", pr="https://example.test/pull/81")      # pull request closed without merging
write("old1", status="done", step="pr", release="merged", pr="https://example.test/pull/75", log=["2026-05-01T11:00:00Z merged x"])
write("old2", status="done", step="pr", release="merged", pr="https://example.test/pull/76", log=["2026-05-02T11:00:00Z merged x"])
write("newer", status="done", step="pr", release="merged", pr="https://example.test/pull/77", log=["2026-07-01T11:00:00Z merged x"])
json.dump({"at": "2026-06-15T00:00:00Z"}, open(os.path.join(os.path.dirname(folder), "checkin.json"), "w"))
PY
echo '- slug: q | touches: x | depends-on: run, gh | goal: Q | done: q' >> .loop/queue.md
block() { LOOP_BOARD_HEALTH=green python3 -c "
import sys; sys.path.insert(0, sys.argv[1]); import live_board
print(chr(10).join(live_board.render('$T/repo')))" "$M"; }

echo "== GitHub says the pull requests are open"
FAKE_GH_PR_STATE=OPEN block > "$T/open"
check "a goal whose pull request is open waits at release" 'grep -q "^- gh " "$T/open"'
echo "== GitHub says merged"
FAKE_GH_PR_STATE=MERGED block > "$T/block"
issues() { sed -n '/^Issues/,/^Running goals/p' "$1"; }
check "a merged goal's old wiki_error and release_error are gone from Issues, in one wiki line" '! issues "$T/block" | grep -q "rec \|gh \|fresh\|boom" && [ "$(issues "$T/block" | grep -c "^- wiki")" = 1 ] && issues "$T/block" | grep -q "^- wiki pages are out of date: saved: page Home is stale"'
check "errors and asks that are still open stay, with the exact words" 'issues "$T/block" | grep -q "^- wait is waiting: Which one" && issues "$T/block" | grep -q "fix: answer by typing \"pick a\" or \"pick b\""'
check "with GitHub saying open, the unmerged goal keeps its error" 'issues "$T/open" | grep -q "^- wiki pages are out of date:.*saved: page Home is stale"'
check "a pull request merged on GitHub leaves the board, and its dependant no longer waits on it" '! grep -q "^- gh \|^- rec \|^merged" "$T/block" && grep "^- q " "$T/block" | grep -q "waits on run" && ! grep "^- q " "$T/block" | grep -q "gh"'
check "only live goals are drawn, with a 10-cell bar, and an arrow to the dependant" '! grep -q "^- old1\|^- newer" "$T/block" && grep -q "^- run  \[##--------\] 25%" "$T/block" && grep -q "^- wait " "$T/block" && grep -q "^- stale " "$T/block" && grep -qx "run --> q" "$T/block"'
check "the board ends with one finish line" 'tail -3 "$T/block" | head -1 | grep -qx Finish && tail -2 "$T/block" | head -1 | grep -q "finish about\|no estimate yet\|nothing left" && tail -1 "$T/block" | grep -q "^estimates: "'

echo "== closed, healed and old goals"
FAKE_GH_PR_STATE=OPEN FAKE_GH_PR_STATE_81=CLOSED block > "$T/closed"
check "a later publish clears the wiki_error of an unmerged goal" '! issues "$T/closed" | grep -q "healed" && issues "$T/closed" | grep -q "saved: page Docs is stale"'
check "a pull request closed without merging leaves the board; an open one stays" '! grep -q "^- shut" "$T/closed" && grep -q "^- healed " "$T/closed"'
check "running, waiting and queued goals are listed; merged ones never are" 'grep -q "^- run " "$T/closed" && grep -q "^- wait " "$T/closed" && grep -q "^- q " "$T/closed" && ! grep -q "^- newer\|^- old1\|^- old2\|^- rec " "$T/closed"'

echo "== operate"
sed -i.bak '/depends-on: run, gh/d' .loop/queue.md; rm -f .loop/queue.md.bak
FAKE_GH_PR_STATE=MERGED $OP run --once > "$T/first" 2>&1
FAKE_GH_PR_STATE=MERGED $OP run --once > "$T/second" 2>&1
check "the first pass prints the live board" 'grep -q "^LIVE BOARD" "$T/first"'
check "a pass with nothing changed prints the full board again, never one line" 'grep -q "^LIVE BOARD" "$T/second" && grep -q "^Finish" "$T/second" && ! grep -q "Nothing changed\|NO_CHANGE" "$T/second"'
python3 - "$C/loop/runs/stale.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s.pop("wiki_error"); json.dump(s, open(sys.argv[1], "w"))
PY
FAKE_GH_PR_STATE=MERGED $OP run --once > "$T/third" 2>&1
check "clearing an error counts as a change and reprints the board" 'grep -q "wiki_error" "$T/third" && grep -q "^LIVE BOARD" "$T/third"'
check "every pass writes the check-in" '[ -f "$C/loop/checkin.json" ]'

echo "== sizes"
check "every script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20479c)" ]'
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
