#!/bin/bash
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
# Test the release step's wiki half on a throwaway toy repo with a bare wiki. usage: test-wiki.sh [DIR]
unset LOOP_BATCH
set -e
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d"
export LOOP_FLOW="$d/flow.json"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
wiki="python3 $here/skills/workflow-release/scripts/wiki.py"
merge="python3 $here/skills/workflow-release/scripts/merge.py"
cd "$d/repo"
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
wikifile() { git --git-dir="$d/origin.wiki.git" show "main:$1" 2>/dev/null; }

python3 - <<'PY'
import json
cfg = json.load(open(".loop/config.json")); cfg["auto_merge"] = True
json.dump(cfg, open(".loop/config.json", "w"), indent=2)
PY
$docs add Using-the-toy --paths calc.py >/dev/null
printf '<!-- workflow-docs -->\n# Using the toy\n\nRun `python3 calc.py` to use the toy calculator. Its tests sit beside it.\n' > docs/wiki/Using-the-toy.md
git add -A; git commit -qm "Add the page"; git push -q origin main
$docs publish >/dev/null

echo "== a goal that changes a mapped path"
$goal new w --here --goal "Add w" --done "calc has w" >/dev/null
printf '\n\ndef w():\n    return 1\n' >> calc.py; git add calc.py; git commit -qm "Add w to calc"
python3 - <<'PY'
path = ".loop/goals/w.md"
text = open(path).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: it has w.\n", 1)
open(path, "w").write(text)
PY
git commit -qam "Verify steps for w"
bash "$here/dev/toy/flow-done.sh" w && $goal pr w >/dev/null || bad "goal did not reach a pull request"
out=$($wiki prepare w 2>&1 || true); echo "$out"
grep -q "^REWRITE Using-the-toy: STALE" <<<"$out" && ok "prepare lists the stale mapped page" || bad "prepare stale"
$merge w 2>&1 | grep -q "REFUSED: stale wiki pages: .*Using-the-toy" && ok "merge refuses while the page is stale" || bad "merge stale"

echo "== the page is updated, committed and pushed"
echo "It now has a w function too, so the page covers it as well." >> docs/wiki/Using-the-toy.md
$wiki prepare w --commit | grep -q "WIKI CURRENT" && ok "no stale page after the update" || bad "still stale"
$docs check | grep -q "DOCS OK" && ok "docs.py check reports no stale page" || bad "docs check"
[ -z "$(git status --porcelain)" ] && git ls-remote --heads origin loop/w | grep -q "$(git rev-parse HEAD)" && ok "update committed on the branch and pushed" || bad "not committed or pushed"

echo "== after the merge the wiki is published"
git switch -q main; git merge -q --no-ff --no-edit loop/w; git push -q origin main; git switch -q loop/w
FAKE_GH_PR_STATE=MERGED $merge w | grep -q PUBLISHED && ok "merge publishes the wiki" || bad "merge publish"
wikifile Using-the-toy.md | grep -q "w function" && ok "the page is on the wiki" || bad "page not on wiki"

echo "== a page no touched path maps to goes stale on the base"
git switch -q main; git pull -q --no-edit origin main
$docs add Notes --paths notes.txt >/dev/null
printf '<!-- workflow-docs -->\n# Notes\n\nThe toy keeps its notes in notes.txt, which people read first.\n' > docs/wiki/Notes.md
echo one > notes.txt; git add -A; git commit -qm "Add the Notes page"; git push -q origin main
$docs publish >/dev/null
echo two >> notes.txt; git commit -qam "Change the notes"; git push -q origin main
$goal new x --here --goal "Add x" --done "calc has x" >/dev/null
printf '\n\ndef x():\n    return 1\n' >> calc.py; git add calc.py; git commit -qm "Add x to calc"
python3 - <<'PY'
path = ".loop/goals/x.md"
text = open(path).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: it has x.\n", 1)
open(path, "w").write(text)
PY
git commit -qam "Verify steps for x"
bash "$here/dev/toy/flow-done.sh" x && $goal pr x >/dev/null || bad "goal x did not reach a pull request"
out=$($wiki prepare x 2>&1 || true); echo "$out"
grep -q "^REWRITE Notes: STALE" <<<"$out" && ok "prepare lists the unmapped stale page" || bad "prepare unmapped"
[ "$(grep -c '^REWRITE' <<<"$out")" = "$($docs check | grep -c '^STALE')" ] && ok "prepare lists what docs.py check calls stale" || bad "stale sets differ"
$merge x 2>&1 | grep -q "REFUSED: stale wiki pages: .*Notes" && ok "merge refuses and names the page" || bad "merge unmapped"
echo "The notes now say two, so the page covers both lines." >> docs/wiki/Notes.md
echo "It also has an x function now." >> docs/wiki/Using-the-toy.md
$wiki prepare x --commit | grep -q "WIKI CURRENT" && $docs check | grep -q "DOCS OK" && ok "refreshed page clears the check" || bad "notes still stale"
git switch -q main; git merge -q --no-ff --no-edit loop/x; git push -q origin main; git switch -q loop/x
FAKE_GH_PR_STATE=MERGED $merge x | grep -q PUBLISHED && wikifile Notes.md | grep -q "now say two" && ok "merge publishes the refreshed page" || bad "notes not published"

echo "== a refused publish says which page and why, under Needs you"
git switch -q main; git pull -q --no-edit origin main; $docs add Home --paths README.md >/dev/null
printf '<!-- workflow-docs -->\n# Home\n\nThe toy home page, written by the tool, with enough words to count as written.\n' > docs/wiki/Home.md
git add -A; git commit -qm "Map Home"; git push -q origin main
$wiki publish w | grep -q "WIKI REFUSED w: .*Home" && ok "publish reports the page" || bad "publish report"
python3 "$here/skills/workflow-monitoring/scripts/board_status.py" | tr '\n' ' ' | tr -s ' ' | grep -q "wiki pages are out of date: saved: REFUSED: .*Home" && ok "shows under Issues" || bad "needs you"

echo "== every script stays under 20 KB"
big=$(find "$here/skills" -name '*.py' -size +20479c); [ -z "$big" ] && ok "scripts under 20 KB" || bad "too big: $big"
[ "$fails" -eq 0 ]
