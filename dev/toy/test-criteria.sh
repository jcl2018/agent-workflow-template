#!/bin/bash
# Test the criteria contract across workflow-docs, workflow-regression and workflow-release. usage: test-criteria.sh [DIR]
unset LOOP_BATCH
set -e
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d"
export LOOP_FLOW="$d/flow.json"
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"; rel="python3 $here/skills/workflow-release/scripts/release.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
cd "$d/repo"; PWD_REPO=$PWD
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }

cri="python3 $here/skills/workflow-docs/scripts/criteria.py"; mon="python3 $here/skills/workflow-monitoring/scripts/monitor.py"
day=$(date -u +%F)
page() { # NAME CRITERIA-LINES: writes a page with an empty Tests section, then renders it unless NORENDER is set
  mkdir -p docs/wiki
  printf '<!-- workflow-docs -->\n# %s\n\n## Summary\n\nThe %s page of the toy calculator, written for this test.\n\n## Criteria\n\n%s\n\n## Tests\n\n' "$1" "$1" "$2" > "docs/wiki/$1.md"
  [ -n "${NORENDER:-}" ] || $cri render >/dev/null
}
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["criteria"] = True
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
sub() { sed -i.bak "$1" docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak; }
one="- DEL-1: **Unreviewed** The calculator prints a median."
good() { rm -f .loop/regression.tsv .loop/regression-runs.tsv; page Delivery "$one"; }

echo "== docs check: allowed pages and exact sections"
$docs add Delivery --paths calc.py >/dev/null
good; git add -A; git commit -qm "Delivery page"
$docs check | grep -q "DOCS OK" && ok "a conforming page passes" || bad "conforming page"
$docs add Extras --paths calc.py >/dev/null; page Extras "- EXT-1: **Unreviewed** x"
$docs check | grep -q "^PAGE Extras" && ok "a page outside the list fails" || bad "extra page"
rm docs/wiki/Extras.md; grep -v '^Extras' .loop/docs.tsv > .loop/t && mv .loop/t .loop/docs.tsv
good; sub 's/^## Tests/## Usage/'
$docs check | grep -q "^SECTIONS Delivery" && ok "wrong sections fail" || bad "sections"
good; sub 's/^## Summary/## Commands/'
$docs check | grep -q "^SECTIONS Delivery" && ok "a Commands section fails" || bad "commands section"
good; python3 - <<'PY'
p = "docs/wiki/Delivery.md"; t = open(p).read()
t = t.replace("## Summary", "@@").replace("## Criteria", "## Summary").replace("@@", "## Criteria")
open(p, "w").write(t)
PY
$docs check | grep -q "^SECTIONS Delivery" && ok "wrong order fails" || bad "order"

echo "== docs check: criteria"
good; page Delivery "$one
- DEL-1: **Unreviewed** Again."
$docs check | grep -q "^DUPLICATE Delivery" && ok "duplicate id fails" || bad "duplicate"
good; sub 's/\*\*Unreviewed\*\* //'
$docs check | grep -q "^CRITERION Delivery" && ok "a criterion with no mark fails" || bad "no mark"
good; sub 's/\*\*Unreviewed\*\*/**Reviewed**/'
$docs check | grep -q "^CRITERION Delivery" && ok "Reviewed with no date fails" || bad "no date"
$docs criteria Delivery | grep -q "NEXT DEL-2" && ok "criteria prints the next free id" || bad "criteria"
six=$(for n in 1 2 3 4 5; do echo "- DEL-$n: **Unreviewed** Point $n."; done)
page Delivery "$six"; $docs check | grep -q "^CAP" && bad "five criteria over the cap" || ok "five criteria pass"
page Delivery "$six
- DEL-6: **Unreviewed** Point 6."; $docs check | grep -q "^CAP Delivery: has 6 criteria" && ok "a sixth criterion fails" || bad "cap"
for name in calc.py run.sh skills/x/scripts/tool.py app.js; do
  page Delivery "- DEL-1: **Unreviewed** Runs $name for more."
  $docs check | grep -q "^SCRIPT Delivery: DEL-1 names $name" && ok "script name fails: $name" || bad "script name: $name"
done
page Delivery "- DEL-1: **Unreviewed** Reads README.md and docs.tsv."
$docs check | grep -q "^SCRIPT" && bad "other file names failed" || ok "other file names pass"
good; echo "The Summary may name run.sh freely." >> docs/wiki/Delivery.md
$docs check | grep -q "^SCRIPT" && bad "summary checked" || ok "only the criteria are checked for script names"

echo "== the Tests table: rows, last runs, and not enforced"
good; grep -q '^| DEL-1 | \*\*not enforced\*\* |' docs/wiki/Delivery.md && ok "a criterion with no test shows as not enforced" || bad "not enforced"
$docs check | grep -q "DOCS OK" && ok "a rendered table passes" || bad "rendered table"
$reg add del-1a --level land --command "true" --goal DEL-1 >/dev/null; $reg add del-1b --level land --command "false" --goal DEL-1 >/dev/null
$cri render >/dev/null
grep -q '^| DEL-1 | \[del-1a\](.*) | not run |' docs/wiki/Delivery.md && grep -q '^| DEL-1 | \*\*not enforced\*\*' docs/wiki/Delivery.md && ok "a test that never ran is not enforcing" || bad "not run"
$reg run land >/dev/null || true
grep -q "^del-1a	PASS	$day" .loop/regression-runs.tsv && grep -q "^del-1b	FAIL	$day" .loop/regression-runs.tsv && ok "a run records each row's status and date" || bad "ledger"
$docs check | grep -q "^TESTS Delivery" && ok "a table behind the last run is stale" || bad "stale after run"
$cri render --check | grep -q "^STALE" && ok "render --check names the stale page" || bad "render check"
$cri render >/dev/null
grep -q "^| DEL-1 | \[del-1a\](.*) | PASS $day |" docs/wiki/Delivery.md && grep -q "^| DEL-1 | \[del-1b\](.*) | FAIL $day |" docs/wiki/Delivery.md && ok "render shows status and date" || bad "render shows"
grep -q '^| DEL-1 | \*\*not enforced' docs/wiki/Delivery.md && bad "one passing row still not enforced" || ok "one passing row is enough to be enforced"
$reg add del-1a --level land --command "false" --goal DEL-1 >/dev/null; $reg run del-1a >/dev/null || true; $cri render >/dev/null
grep -q '^| DEL-1 | \*\*not enforced' docs/wiki/Delivery.md && ok "a criterion with no passing test shows as not enforced" || bad "all failing"
sub 's/FAIL/PASS/'
$docs check | grep -q "^TESTS Delivery" && ok "a hand-edited table fails" || bad "hand edit"
printf 'orphan\tland\ttrue\t\t\nDEL-9x\tland\ttrue\tDEL-9\t\n' >> .loop/regression.tsv
out=$($docs check || true); grep -q "^LINK regression: row orphan links to no criterion" <<<"$out" && ok "a test with no criterion fails" || bad "orphan"
grep -q "^LINK regression: rows link to DEL-9" <<<"$out" && ok "a test of an unknown criterion fails" || bad "dangling"
good

echo "== a reviewed criterion is locked until the owner marks it Unreviewed"
$cri review DEL-1 2>&1 | grep -q "only the owner changes" && ok "review needs the owner's words" || bad "review --user"
$cri review DEL-9 --user 2>&1 | grep -q "no criterion DEL-9" && ok "review refuses an unknown id" || bad "review unknown"
$cri review DEL-1 --user | grep -q "REVIEWED DEL-1" && grep -q "^- DEL-1: \*\*Reviewed $day\*\* .*<!-- reviewed [0-9a-f]* -->$" docs/wiki/Delivery.md && ok "review marks the line Reviewed with the date" || bad "review marks"
$docs check | grep -q "DOCS OK" && ok "a reviewed page passes the check" || bad "reviewed page"
git add -A; git commit -qm "Reviewed" >/dev/null
sub 's/prints a median/prints a mean/'
$docs check | grep -q "^LOCKED Delivery: DEL-1 was reviewed" && ok "changing a reviewed criterion fails the check" || bad "lock"
$mon report | grep -A1 "^REVIEWED CRITERIA CHANGED" | grep -q "DEL-1 (Delivery): The calculator prints a mean" && ok "report names a changed reviewed criterion" || bad "report"
git checkout -q -- docs/wiki/Delivery.md
$docs check | grep -q "^LOCKED" && bad "restored text still locked" || ok "restoring the wording clears the lock"
sub 's/^- DEL-1: \*\*Reviewed [0-9-]*\*\*/- DEL-1: **Unreviewed**/'
sub 's/prints a median\./prints a mean./'
$docs check | grep -q "^LOCKED" && bad "unreviewed criterion locked" || ok "after Unreviewed the wording may change"
$cri unreview DEL-1 --user >/dev/null; git checkout -q -- docs/wiki/Delivery.md
$cri unreview DEL-1 --user | grep -q "UNREVIEWED DEL-1" && sub 's/prints a median/prints a mode/' && $docs check | grep -q "^LOCKED" && bad "unreview left a lock" || ok "unreview lifts the lock"
git checkout -q -- docs/wiki/Delivery.md; good; git add -A; git commit -qm "Good page again" >/dev/null || true

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
$goal new crit --here --goal "Change calc" --done "calc changed" >/dev/null
printf '\n# crit\n' >> calc.py
python3 - <<'PY'
p = ".loop/goals/crit.md"; t = open(p).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: the change.\n", 1); open(p, "w").write(t)
PY
echo "Covers the change too, with more words for the check." >> docs/wiki/Delivery.md
git add -A; git commit -qm "Change calc"
bash "$here/dev/toy/flow-done.sh" crit; $goal check crit >/dev/null; $goal pr crit >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (no regression row)" && ok "cut refuses a missing row" || bad "cut missing row"
$reg add del-2 --level land --command "false" --goal DEL-2 >/dev/null
git add -A; git commit -qm "Failing row" >/dev/null; $goal check crit >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (row del-2 is a draft or failing)" && ok "cut refuses a failing row" || bad "cut failing row"
$reg add del-2 --level land --command "true" --goal DEL-2 >/dev/null
$reg add del-2b --level land --command "false" --goal DEL-2 >/dev/null
git add -A; git commit -qm "Second row" >/dev/null; $goal check crit >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (row del-2b is a draft or failing)" && ok "cut checks every row of a criterion" || bad "cut second row"
$reg sync >/dev/null || true; python3 "$here/skills/workflow-regression/scripts/regression.py" criteria | grep -q "del-2b" && ok "regression criteria runs every row" || bad "criteria every row"
$reg add del-2b --level land --command "true" --goal DEL-2 >/dev/null
git add -A; git commit -qm "Passing row" >/dev/null; $goal check crit >/dev/null
mv .loop/docs.tsv "$d/docs.tsv.away"
(cd "$here/skills/workflow-release/scripts" && python3 -c "import release; print(release.criteria_trouble('$PWD_REPO', {}))") | grep -q '^\[\]$' && ok "no docs.tsv: criteria are ignored" || bad "no docs.tsv"
mv "$d/docs.tsv.away" .loop/docs.tsv
$rel cut crit | grep -q "^DRAFT" && ok "cut with every row passing" || bad "cut passing"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
