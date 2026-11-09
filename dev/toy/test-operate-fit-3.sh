#!/bin/bash
# Proves OPERATE-FIT-3 on a toy repo with TZ pinned to Asia/Kolkata: Needs you holds at most one wiki line built from the current docs
# check (old saved wiki errors for a page the check no longer reports are gone), the roadmap draws chained goals as a flow chart and ends
# with the longest path and a local finish time, and nothing operate prints says UTC. No model is called. usage: test-operate-fit-3.sh [DIR]
set -u
unset LOOP_ROLE
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
M="$here/skills/workflow-monitoring/scripts"; OP="python3 $M/operate.py"; DOCS="python3 $here/skills/workflow-docs/scripts/docs.py"
export HOME="$T/home"; mkdir -p "$HOME"; export TZ=Asia/Kolkata
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh" FAKE_GH_PR_STATE=OPEN
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["mend"] = False; c["cadence"] = "10"
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
$DOCS add Using-the-toy --paths calc.py >/dev/null
printf '<!-- workflow-docs -->\n# Using the toy\n\nRun `python3 calc.py` to use the toy calculator. Its tests sit beside it.\n' > docs/wiki/Using-the-toy.md
git add -A; git commit -qm "Docs page"; git push -q origin main
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
mkdir -p "$C/loop/runs"
python3 - "$C/loop/runs" <<'PY'
import json, os, sys
folder = sys.argv[1]
def write(slug, **more):
    json.dump(dict({"slug": slug, "goal": "Goal " + slug, "tries": 0, "pr": "", "waits_on": [], "updated": "2026-06-01T12:00:00Z",
                    "log": ["2026-06-01T11:00:00Z queued"]}, **more), open(os.path.join(folder, slug + ".json"), "w"))
write("oldclean", status="done", step="pr", pr="https://example.test/pull/90", wiki_error="page Using-the-toy is stale")
write("oldgone", status="done", step="pr", pr="https://example.test/pull/91", wiki_error="page Vanished is stale")
steps = ["2026-06-01T10:%02d:00Z %s" % (n * 5, w) for n, w in enumerate(["queued", "idea", "plan", "build", "review", "qa", "ship", "pr"])]
write("hist", status="done", step="pr", pr="https://example.test/pull/89", release="merged", log=steps)   # gives every step a 5 minute estimate
write("nopage", status="done", step="pr", pr="https://example.test/pull/92", wiki_error="push rejected by the wiki remote")
PY
printf '%s\n' '- slug: a | touches: x | goal: A | done: a' '- slug: b | touches: x | depends-on: a | goal: B | done: b' \
  '- slug: c | touches: x | depends-on: b | goal: C | done: c' '- slug: d | touches: x | depends: a | goal: D | done: d' >> .loop/queue.md
needs() { sed -n '/== Needs you ==/,/== Roadmap ==/p' "$1"; }
road() { sed -n '/== Roadmap ==/,/== Total ==/p' "$1"; }

echo "== a clean docs check"
$DOCS check | grep -q "DOCS OK" || bad "setup: docs check should be clean"
$OP run --once > "$T/clean" 2>&1
check "line 1: old saved errors for pages the check does not report are gone" '! needs "$T/clean" | grep -q "Using-the-toy\|Vanished\|oldclean\|oldgone"'
check "line 1: a saved error naming no page is kept, in the one wiki line" '[ "$(needs "$T/clean" | grep -c "wiki")" = 1 ] && needs "$T/clean" | grep -q "saved: push rejected"'

echo "== one page goes stale"
printf '\n# changed\n' >> calc.py; git commit -qam "Change calc"
python3 - "$C/loop/runs/nopage.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s.pop("wiki_error"); json.dump(s, open(sys.argv[1], "w"))
PY
$OP run --once > "$T/stale" 2>&1
check "line 1: exactly one wiki line names today's stale page and the fix" '[ "$(needs "$T/stale" | grep -c "wiki")" = 1 ] && needs "$T/stale" | grep "wiki" | grep -q "stale Using-the-toy.*Fix: python3 .*docs.py audit"'
check "line 1: the old goal's error is folded in, not repeated per goal" '! needs "$T/stale" | grep -q "oldclean\|oldgone\|Vanished"'
$OP run --once > "$T/again" 2>&1
check "line 1: two passes with an unchanged check print one line" '[ "$(wc -l < "$T/again" | tr -d " ")" = 1 ]'

echo "== the flow chart"
check "line 2: chained goals are drawn with arrows" 'road "$T/stale" | grep -q "^flow" && road "$T/stale" | grep -q "\] a --> \[queued\] b, \[queued\] d" && road "$T/stale" | grep -q "\[queued\] b --> \[queued\] c"'
last=$(road "$T/stale" | awk '/^== Total/ {next} NF {line = $0} END {print line}')
check "line 2: the roadmap ends with the longest path and a local finish time" 'echo "$last" | grep -q "^longest path: about .*the longest chain: .*, finish about [0-9][0-9]:[0-9][0-9] IST"'

echo "== local time"
check "line 3: nothing operate prints says UTC" '! grep -q "UTC" "$T/clean" "$T/stale" "$T/again"'
check "line 3: the quiet pass names the local zone" 'grep -q "IST" "$T/again"'
python3 - "$M" <<'PY' && ok "line 3: clock and localize" || bad "line 3: clock and localize"
import sys, datetime
sys.path.insert(0, sys.argv[1]); import graph
at = datetime.datetime(2026, 6, 1, 12, 0, tzinfo=datetime.timezone.utc)
assert graph.clock(at) == "17:30 IST", graph.clock(at)
assert "IST" in graph.localize("Next check-in 12:00 UTC.") and "UTC" not in graph.localize("Next check-in 12:00 UTC.")
assert "17:30 IST" in graph.localize("x 2026-06-01T12:00:00Z y")
assert graph.localize("no time here") == "no time here"
PY

echo "== direct branches"
python3 - "$M" "$T/repo" <<'PY' && ok "line 4: unreachable branches" || bad "line 4: unreachable branches"
import sys, os
sys.path.insert(0, sys.argv[1]); import graph, board_status as b
node = lambda s, d=(): dict(slug=s, mark="queued", depends=list(d))
assert graph.flow([node("a"), node("b")]) == []
assert any("? not a goal here] zzz" in l for l in graph.flow([node("a", ["zzz"])]))
cyc = graph.flow([node("a", ["b"]), node("b", ["a"])]); assert len(cyc) == 3, cyc
b.DOCS = "/nonexistent/docs.py"; assert b.wiki_check(sys.argv[2]) is None
run = dict(slug="r", status="done", wiki_error="page Home is stale", log=["2026-06-01T11:00:00Z queued"])
assert "saved: page Home" in b.wiki_line([run], set(), None)[0]
assert b.wiki_line([run], set(), []) == []
PY

echo "== sizes"
check "every script is under 20 KB" '[ -z "$(find "$here/skills" -name "*.py" -size +20479c)" ]'
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
