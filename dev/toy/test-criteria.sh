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
cd "$d/repo"; PWD_REPO=$PWD
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }

page() { # NAME CRITERIA-LINES ENFORCED-LINES; a line "- DEL-1: text" lands Unreviewed unless it already has a stage
  mkdir -p docs/wiki
  local crit n head
  crit=$(sed -E '/\*\*/!s/^(- [A-Z]+-[0-9]+: )/\1**Unreviewed** /' <<<"$2"); n=$(grep -c '^- ' <<<"$crit"); [ -z "${TESTS:-}" ] && head="Tests: 0." || head=$TESTS
  [ "$(grep -c 'Unreviewed' <<<"$crit")" = 0 ] || head="$head
> **Unreviewed:** $(grep -c 'Unreviewed' <<<"$crit") of $n criteria on this page have not been reviewed by the owner."
  set -- "$1" "$head

$crit" "$3"
  printf '<!-- workflow-docs -->\n# %s\n\n## Summary\n\nThe %s page of the toy calculator, written for this test.\n\n## Commands\n\n- `add`: adds two numbers.\n\n#### `add`\n\n```mermaid\nflowchart LR\n  A[Add] --> B([Sum])\n```\n\nStatus: built and proven: add. Built only: none. Planned: none.\n\n## Criteria\n\n%s\n\n## Enforced by\n\n%s\n' \
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
for name in Documentation Monitoring Regression Release; do $docs add $name --paths calc.py >/dev/null; done
page Documentation "- DOC-1: x." "- DOC-1: r"; page Monitoring "- MON-1: x." "- MON-1: r"
page Regression "- REG-1: x." "- REG-1: r"; page Release "- REL-1: x." "- REL-1: r"
$docs add Home --paths README.md >/dev/null
printf '<!-- workflow-docs -->\n# Home\n\nFree-form home page with no required sections, written for this test of the toy.\n' > docs/wiki/Home.md
out=$($docs check | grep -v Extras || true); echo "$out"
grep -q "^PAGE\|^SECTIONS\|^CRITERION\|^UNENFORCED\|^DUPLICATE" <<<"$out" && bad "an allowed page failed" || ok "all five pages and Home are accepted"
rm -f docs/wiki/{Documentation,Monitoring,Regression,Release,Home}.md
grep -v '^\(Documentation\|Monitoring\|Regression\|Release\|Home\)' .loop/docs.tsv > .loop/t && mv .loop/t .loop/docs.tsv
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

echo "== docs check: no script file names, and every command has a chart"
good() { page Delivery "- DEL-1: The calculator prints a median." "- DEL-1: del-1"; }
kinds() { $docs check | grep -c "^$1 $2" || true; }
good; [ "$(kinds SCRIPT Delivery)$(kinds CHART Delivery)" = 00 ] && ok "a page with a chart and no script name passes" || bad "conforming chart page"
for name in calc.py run.sh skills/x/scripts/tool.py app.js; do
  good; echo "See \`$name\` for more." >> docs/wiki/Delivery.md
  $docs check | grep -q "^SCRIPT Delivery: names $name" && ok "script name fails: $name" || bad "script name: $name"
done
good; printf '\n```text\npython3 scripts/tool.py run\n```\n' >> docs/wiki/Delivery.md
$docs check | grep -q "^SCRIPT Delivery: names scripts/tool.py" && ok "a script name in a code block fails" || bad "script in block"
good; echo "Pages live in docs/wiki/Delivery.md, and the file .loop/docs.tsv maps them." >> docs/wiki/Delivery.md
[ "$(kinds SCRIPT Delivery)" = 0 ] && ok "other file names pass" || bad "other file names"
$docs add Home --paths README.md >/dev/null
printf '<!-- workflow-docs -->\n# Home\n\nA home page written for this test, and it names the file run.sh too.\n' > docs/wiki/Home.md
$docs check | grep -q "^SCRIPT Home: names run.sh" && ok "Home is held to the rule too" || bad "script on Home"
rm docs/wiki/Home.md; grep -v '^Home' .loop/docs.tsv > .loop/t && mv .loop/t .loop/docs.tsv
good; sed -i.bak 's/^- `add`: adds two numbers\.$/- `add`: adds two numbers.\n- `sub`: takes one away./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^CHART Delivery: sub has no chart" && ok "a bullet command with no chart fails" || bad "bullet no chart"
good; sed -i.bak 's/^## Criteria$/```text\nmul A B\n  continues the line above, so it is no command\n```\n\n## Criteria/' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
out=$($docs check || true); grep -q "^CHART Delivery: mul has no chart" <<<"$out" && ok "a text block command with no chart fails" || bad "block no chart"
grep -q "^CHART Delivery: continues" <<<"$out" && bad "indented line counted" || ok "an indented line is not a command"
good; sed -i.bak '/^Status: /d' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^CHART Delivery: add has no status line" && ok "a chart with no status line fails" || bad "no status"
good; sed -i.bak 's/^Status: .*/Status: fine./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^CHART Delivery: add has no status line" && ok "a status line needs all three labels" || bad "status labels"
good; sed -i.bak 's/^```mermaid$/```text/' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^CHART Delivery: add has no chart" && ok "a block that isn't mermaid is no chart" || bad "not mermaid"
good; sed -i.bak 's/^- `add`: adds two numbers\.$/Adds two numbers./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^CHART Delivery: Commands lists no command" && ok "a Commands section with no command fails" || bad "no command"
git add -A; git commit -qm "Bad page" >/dev/null; $docs publish 2>&1 | grep -q "REFUSED: fix the pages" && ok "publish refuses such a page" || bad "publish refused"
good; git add -A; git commit -qm "Good page" >/dev/null

echo "== docs check: stages, the Unreviewed banner, the test count, one link for each test"
good; sed -i.bak 's/^\(- DEL-1: \)\*\*Unreviewed\*\* /\1/' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^STAGE Delivery: DEL-1 has no stage" && ok "a criterion with no stage fails" || bad "no stage"
good; sed -i.bak '/^> \*\*Unreviewed/d' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^TESTS Delivery" && ok "an Unreviewed criterion needs the banner" || bad "banner"
good; sed -i.bak 's/^Tests: 0\./Tests: 9./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^TESTS Delivery" && ok "a wrong test count fails" || bad "test count"
page Delivery "- DEL-1: **Reviewed** The calculator prints a median." "- DEL-1: del-1a, del-1b"
printf '# id\tlevel\tcommand\tgoal\tseen_red\ndel-1a\tland\ttrue\tDEL-1\t2026-01-01\ndel-1b\tland\ttrue\tDEL-1\t\n' > .loop/regression.tsv
$docs check | grep -q "^STAGE Delivery: DEL-1 says Reviewed, and its tests make it Enforced" && ok "the stage must match the tests" || bad "stage from tests"
$docs check | grep -q "^TESTS Delivery" && ok "the count follows the rows" || bad "count from rows"
TESTS="Tests: 2." page Delivery "- DEL-1: **Enforced** The calculator prints a median." "- DEL-1: del-1a, del-1b"
out=$($docs check || true); grep -q "^STAGE\|^TESTS\|^LINK" <<<"$out" && bad "enforced page: $out" || ok "two rows, one failure not yet seen: Enforced"
printf '# id\tlevel\tcommand\tgoal\tseen_red\ndel-1a\tland\ttrue\tDEL-1\t2026-01-01\ndel-1b\tland\ttrue\tDEL-1\t2026-01-01\n' > .loop/regression.tsv
$docs check | grep -q "^STAGE Delivery: DEL-1 says Enforced, and its tests make it Proven" && ok "every row seen failing: Proven" || bad "proven"
TESTS="Tests: 1." page Delivery "- DEL-1: **Unreviewed** The calculator prints a median." "- DEL-1: del-1a"
out=$($docs check || true); grep -q "^LINK Delivery: DEL-1 lists del-1a, but its rows are del-1a, del-1b" <<<"$out" && ok "Enforced by must list every row" || bad "enforced list"
grep -q "^STAGE" <<<"$out" && bad "Unreviewed fought its tests" || ok "Unreviewed stays Unreviewed whatever its tests"
printf 'orphan\tland\ttrue\t\t\nDEL-9x\tland\ttrue\tDEL-9\t\n' >> .loop/regression.tsv
out=$($docs check || true); grep -q "^LINK regression: row orphan links to no criterion" <<<"$out" && ok "a test with no criterion fails" || bad "orphan"
grep -q "^LINK regression: rows link to DEL-9" <<<"$out" && ok "a test of an unknown criterion fails" || bad "dangling"
rm .loop/regression.tsv; good

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
