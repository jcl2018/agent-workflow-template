#!/bin/bash
# Test the criteria contract across workflow-docs, workflow-regression and workflow-release. usage: test-criteria.sh [DIR]
unset LOOP_BATCH
set -e
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d"
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"; rel="python3 $here/skills/workflow-release/scripts/release.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
cd "$d/repo"
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }

page() { # NAME CRITERIA-LINES ENFORCED-LINES
  mkdir -p docs/wiki
  printf '<!-- workflow-docs -->\n# %s\n\n## Summary\n\nThe %s page of the toy calculator, written for this test.\n\n## Commands\n\nRun `python3 calc.py`.\n\n## Criteria\n\n%s\n\n## Enforced by\n\n%s\n' \
    "$1" "$1" "$2" "$3" > "docs/wiki/$1.md"
}
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["criteria"] = True
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY

echo "== docs check: allowed pages and exact sections"
$docs add Delivery --paths calc.py >/dev/null
page Delivery "- DEL-1: The calculator prints a median." "- DEL-1: del-1"
git add -A; git commit -qm "Delivery page"
$docs check | grep -q "DOCS OK" && ok "a conforming page passes" || bad "conforming page"
$docs add Extras --paths calc.py >/dev/null
page Extras "- EXT-1: x" "- EXT-1: x"
$docs check | grep -q "^PAGE Extras" && ok "a page outside the list fails" || bad "extra page"
rm docs/wiki/Extras.md; grep -v '^Extras' .loop/docs.tsv > .loop/t && mv .loop/t .loop/docs.tsv
page Delivery "- DEL-1: The calculator prints a median." "- DEL-1: del-1"
sed -i.bak 's/^## Commands/## Usage/' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^SECTIONS Delivery" && ok "wrong sections fail" || bad "sections"
page Delivery "- DEL-1: The calculator prints a median." "- DEL-1: del-1"
python3 - <<'PY'
p = "docs/wiki/Delivery.md"; t = open(p).read()
t = t.replace("## Commands", "@@").replace("## Criteria", "## Commands").replace("@@", "## Criteria")
open(p, "w").write(t)
PY
$docs check | grep -q "^SECTIONS Delivery" && ok "wrong order fails" || bad "order"

echo "== docs check: ids"
page Delivery "- DEL-1: The calculator prints a median.
- DEL-1: Again." "- DEL-1: del-1"
$docs check | grep -q "^DUPLICATE Delivery" && ok "duplicate id fails" || bad "duplicate"
page Delivery "- DEL-1: The calculator prints a median.
- DEL-2: It exits 0." "- DEL-1: del-1"
$docs check | grep -q "^UNENFORCED Delivery: DEL-2" && ok "unenforced criterion fails" || bad "unenforced"
$docs criteria Delivery | grep -q "NEXT DEL-3" && ok "criteria prints the next free id" || bad "criteria"
$docs criteria Delivery | grep -q "FORMAT" && ok "criteria prints the format" || bad "format"

echo "== regression sync reports criteria with no row"
page Delivery "- DEL-1: The calculator prints a median.
- DEL-2: It exits 0." "- DEL-1: del-1
- DEL-2: del-2"
out=$($reg sync || true); echo "$out"
grep -q "^GAP DEL-1" <<<"$out" && grep -q "^GAP DEL-2" <<<"$out" && ok "both criteria are gaps" || bad "gaps"
$reg add del-1 --level land --command "true" --goal DEL-1 >/dev/null
out=$($reg sync || true)
grep -q "^GAP DEL-1" <<<"$out" && bad "DEL-1 still a gap" || ok "a row closes the gap"
grep -q "^GAP DEL-2" <<<"$out" && ok "DEL-2 still a gap" || bad "DEL-2 gap"
git add -A; git commit -qm "Criteria" >/dev/null

echo "== cut needs a passing row for every criterion"
git push -q origin main
$goal new crit --here --goal "Change calc" --done "calc changed" --level 0 >/dev/null
printf '\n# crit\n' >> calc.py
python3 - <<'PY'
p = ".loop/goals/crit.md"; t = open(p).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: the change.\n", 1); open(p, "w").write(t)
PY
echo "Covers the change too, with more words for the check." >> docs/wiki/Delivery.md
git add -A; git commit -qm "Change calc"
$goal check crit >/dev/null; $goal pr crit >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (no regression row)" && ok "cut refuses a missing row" || bad "cut missing row"
$reg add del-2 --level land --command "false" --goal DEL-2 >/dev/null
git add -A; git commit -qm "Failing row" >/dev/null; $goal check crit >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (row del-2 is failing)" && ok "cut refuses a failing row" || bad "cut failing row"
$reg add del-2 --level land --command "true" --goal DEL-2 >/dev/null
git add -A; git commit -qm "Passing row" >/dev/null; $goal check crit >/dev/null
$rel cut crit | grep -q "^DRAFT" && ok "cut with every row passing" || bad "cut passing"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
