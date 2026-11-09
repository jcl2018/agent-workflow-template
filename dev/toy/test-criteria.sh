#!/bin/bash
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
# Test the criteria contract across workflow-docs, workflow-regression and workflow-release. usage: test-criteria.sh [DIR]
unset LOOP_BATCH
set -e
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d"
export LOOP_FLOW="$d/flow.json"
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"; rel="python3 $here/skills/workflow-release/scripts/release.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
cd "$d/repo"; PWD_REPO=$PWD
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
nocount() { local out; out=$($docs check 2>&1); ! grep -q "Traceback" <<<"$out" && ! grep -q "^COUNT" <<<"$out"; }  # no COUNT line, and the check finished

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
$docs check | grep -q "^PAGE Extras" && bad "a page in docs.tsv was refused" || ok "a page in docs.tsv outside the old set passes"
$docs criteria Extras | grep -q "NEXT EXT-2" && ok "criteria numbers a listed page by its own prefix" || bad "extra page prefix"
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
six=$(for n in 1 2 3 4 5 6; do echo "- DEL-$n: **Unreviewed** Point $n."; done)
page Delivery "$six"; $docs check | grep -q "^CAP" && bad "six criteria over the limit" || ok "six criteria pass"
page Delivery "$six
- DEL-7: **Unreviewed** Point 7."; $docs check | grep -q "^CAP Delivery: has 7 criteria" && ok "a seventh criterion fails" || bad "cap"
for name in calc.py run.sh skills/x/scripts/tool.py app.js; do
  page Delivery "- DEL-1: **Unreviewed** Runs $name for more."
  $docs check | grep -q "^SCRIPT Delivery: DEL-1 names $name" && ok "script name fails: $name" || bad "script name: $name"
done
page Delivery "- DEL-1: **Unreviewed** Reads README.md and docs.tsv."
$docs check | grep -q "^SCRIPT" && bad "other file names failed" || ok "other file names pass"
good; echo "The Summary may name run.sh freely." >> docs/wiki/Delivery.md
$docs check | grep -q "^SCRIPT" && bad "summary checked" || ok "only the criteria are checked for script names"

echo "== docs check: counts on a feature page match its criteria and tests"
good; echo "This page has 3 criteria and 2 tests, across 4 feature pages." >> docs/wiki/Delivery.md
out=$($docs check || true); echo "$out" | grep COUNT
grep -q "^COUNT docs/wiki/Delivery.md: says 3 criteria, the repo has 1$" <<<"$out" && ok "a wrong number of criteria fails" || bad "criteria count"
grep -q "^COUNT docs/wiki/Delivery.md: says 2 tests, the repo has 0$" <<<"$out" && ok "a wrong number of tests fails" || bad "tests count"
n=$(grep -c . <(grep -v '^Home' .loop/docs.tsv | grep -v '^#'))
grep -q "^COUNT docs/wiki/Delivery.md: says 4 feature pages, the repo has $n$" <<<"$out" && ok "a wrong number of feature pages fails" || bad "feature pages count ($n)"
good; printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\ndel-1a\tland\ttrue\tDEL-1\t\tFirst test.\tcriterion\t\ndel-1b\tland\ttrue\tDEL-1\t\tSecond test.\tcriterion\t\nbug-1\tland\ttrue\tDEL-1\t\tA defect test.\tdefect\thttps://example.test/1\n' > .loop/regression.tsv
echo "This page has 3 tests." >> docs/wiki/Delivery.md
$docs check | grep -q "^COUNT docs/wiki/Delivery.md: says 3 tests, the repo has 2$" && ok "a nonzero test count is checked, defect rows left out" || bad "nonzero tests count"
sed -i.bak 's/This page has 3 tests\./This page has 2 tests./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
nocount && ok "the right test count passes" || bad "the right test count failed"
good; sed -i.bak 's/^The Delivery page of the toy calculator, written for this test\./- DEL-7: **Unreviewed** An example line, not a criterion. This page has 1 criterion./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
nocount && ok "only the Criteria section is counted" || bad "a criterion-like line outside Criteria counted"
good; printf '\n~~~\n## Criteria\n- DEL-8: **Unreviewed** An example inside code.\n~~~\nThis page has 1 criterion and 2 criteria in its examples.\n' >> docs/wiki/Delivery.md
$docs check | grep -q "says 2 criteria, the repo has 1" && ok "a Criteria heading inside a ~~~ block is not the section" || bad "fenced Criteria heading counted"
good; printf '\nSee DEL-1 for details.\nThis page has 3 criteria.\n' >> docs/wiki/Delivery.md
$docs check | grep -q "says 3 criteria, the repo has 1" && ok "a line naming a criterion doesn't hide the next line" || bad "an id line hid the next line"
good; echo "DEL-1 alone has 3 tests." >> docs/wiki/Delivery.md
nocount && ok "a line naming a criterion is not a page count" || bad "a line about one criterion counted"
NORENDER=1 page Delivery ""; echo "This page has 2 criteria." >> docs/wiki/Delivery.md
$docs check | grep -q "^COUNT docs/wiki/Delivery.md: says 2 criteria, the repo has 0$" && ok "a page with no criteria still checks its count" || bad "zero criteria"
# Generated by /ship coverage audit.
# Value: protects=criteria and test counts are checked only on a feature page, never in the README; fails_when=the README
#   gets a repo-wide or another page's total; why_new=only feature pages were tested; seam=none; no_claim=Home not tried
good; echo "The README lists 5 criteria and 7 tests." >> README.md
$docs check | grep -q "^COUNT README.md" && bad "the README's criteria or tests count was checked" || ok "criteria and tests counts outside a feature page are not checked"
git checkout -q -- README.md
good

echo "== the Tests table: rows, last runs, and not enforced"
good; grep -q '^| \*\*DEL-1\*\* [^|]* | \*\*not enforced\*\* |' docs/wiki/Delivery.md && ok "a criterion with no test shows as not enforced" || bad "not enforced"
$docs check | grep -q "DOCS OK" && ok "a rendered table passes" || bad "rendered table"
$reg add del-1a --level land --command "true" --goal DEL-1 >/dev/null; $reg add del-1b --level land --command "false" --goal DEL-1 >/dev/null
$cri render >/dev/null
grep -q '^| \*\*DEL-1\*\* [^|]* | \[del-1a\](.*) | - | both | not run | no |' docs/wiki/Delivery.md && grep -q '^| \*\*DEL-1\*\* [^|]* | \*\*not enforced\*\*' docs/wiki/Delivery.md && ok "a test that never ran is not enforcing" || bad "not run"
$reg run land >/dev/null || true
grep -q "^del-1a	PASS	$day" .loop/regression-runs.tsv && grep -q "^del-1b	FAIL	$day" .loop/regression-runs.tsv && ok "a run records each row's status and date" || bad "ledger"
$docs check | grep -q "^TESTS Delivery" && ok "a table behind the last run is stale" || bad "stale after run"
$cri render --check | grep -q "^STALE" && ok "render --check names the stale page" || bad "render check"
$cri render >/dev/null
grep -q "^| \*\*DEL-1\*\* [^|]* | \[del-1a\](.*) | - | both | PASS $day | no |" docs/wiki/Delivery.md && grep -q "^| \*\*DEL-1\*\* [^|]* | \[del-1b\](.*) | - | both | FAIL $day | no |" docs/wiki/Delivery.md && ok "render shows status and date" || bad "render shows"
grep -q '^| \*\*DEL-1\*\* [^|]* | \*\*not enforced' docs/wiki/Delivery.md && bad "one passing row still not enforced" || ok "one passing row is enough to be enforced"
$reg add del-1a --level land --command "false" --goal DEL-1 >/dev/null; $reg run del-1a >/dev/null || true; $cri render >/dev/null
grep -q '^| \*\*DEL-1\*\* [^|]* | \*\*not enforced' docs/wiki/Delivery.md && ok "a criterion with no passing test shows as not enforced" || bad "all failing"
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
page Delivery "- DEL-1: **Unreviewed** The calculator prints a median.
- DEL-2: **Unreviewed** It exits 0."; $cri render >/dev/null
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
$cri render >/dev/null; git add -A; git commit -qm "Change calc"
bash "$here/dev/toy/flow-done.sh" crit; $goal pr crit >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (no regression row)" && ok "cut refuses a missing row" || bad "cut missing row"
$reg add del-2 --level land --command "false" --goal DEL-2 >/dev/null
$cri render >/dev/null; git add -A; git commit -qm "Failing row" >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (row del-2 is a draft or failing)" && ok "cut refuses a failing row" || bad "cut failing row"
$reg add del-2 --level land --command "true" --goal DEL-2 >/dev/null
$reg add del-2b --level land --command "false" --goal DEL-2 >/dev/null
$cri render >/dev/null; git add -A; git commit -qm "Second row" >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (row del-2b is a draft or failing)" && ok "cut checks every row of a criterion" || bad "cut second row"
$reg sync >/dev/null || true; python3 "$here/skills/workflow-regression/scripts/regression.py" criteria | grep -q "del-2b" && ok "regression criteria runs every row" || bad "criteria every row"
$reg add del-2b --level land --command "true" --goal DEL-2 >/dev/null
$cri render >/dev/null; git add -A; git commit -qm "Passing row" >/dev/null
mv .loop/docs.tsv "$d/docs.tsv.away"
(cd "$here/skills/workflow-release/scripts" && python3 -c "import release; print(release.criteria_trouble('$PWD_REPO', {}))") | grep -q '^\[\]$' && ok "no docs.tsv: criteria are ignored" || bad "no docs.tsv"

mv "$d/docs.tsv.away" .loop/docs.tsv
$rel cut crit | grep -q "^DRAFT" && ok "cut with every row passing" || bad "cut passing"

echo "== the Tests table shows words, description, when it runs, result and seen failing"
good
$reg add del-1c --level nightly --command "true" --goal DEL-1 --describe "Checks the median of a short list." >/dev/null
$reg red del-1c --break "true" >/dev/null || true
printf 'del-1c\tnightly\ttrue\tDEL-1\t2026-01-02\tChecks the median of a short list.\n' > .loop/regression.tsv
$reg run del-1c >/dev/null || true; $cri render >/dev/null
grep -q "^| Criterion | Test | What it checks | Runs | Last result | Seen failing |" docs/wiki/Delivery.md && ok "table has the six columns" || bad "columns"
grep -q "^| \*\*DEL-1\*\* The calculator prints a median. | \[del-1c\](.*) | Checks the median of a short list. | nightly | PASS $day | 2026-01-02 |" docs/wiki/Delivery.md && ok "a row shows the criterion words, description, schedule, result and seen-failing date" || bad "row shape"


echo "== criteria_max and the Usage section"
setmax() { python3 - "$1" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
if sys.argv[1] == "unset":
    c.pop("criteria_max", None)
else:
    c["criteria_max"] = json.loads(sys.argv[1])
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
}
usage_page() { # USAGE-BODY: Delivery with a Usage section between Summary and Criteria
  printf '<!-- workflow-docs -->\n# Delivery\n\n## Summary\n\nThe Delivery page of the toy calculator, written for this test.\n\n## Usage\n\n%s\n\n## Criteria\n\n%s\n\n## Tests\n\n' "$1" "$one" > docs/wiki/Delivery.md
  $cri render >/dev/null
}
good; setmax unset
$docs check | grep -q "DOCS OK" && ok "a page with no commands passes without a Usage section" || bad "no usage passes"
page Delivery "$one
- DEL-2: **Unreviewed** The calculator prints a mean."
$docs check | grep -q "^CAP" && bad "default limit rejects two criteria" || ok "no criteria_max means 6"
setmax 1
$docs check | grep -q "^CAP Delivery: has 2 criteria, over the limit of 1 (criteria_max in .loop/config.json)" && ok "criteria_max 1 fails a page of two" || bad "cap 1"
python3 "$here/skills/workflow-health/scripts/health.py" check 2>&1 | grep -q "FAIL.*cap" && ok "health fails the same page" || bad "health cap"
setmax '"six"'
$docs check 2>&1 | grep -q "REFUSED: criteria_max is 'six'" && ok "a bad criteria_max refuses, naming the key" || bad "bad cap"
setmax true
$docs check 2>&1 | grep -q "REFUSED: criteria_max is True" && ok "a true criteria_max refuses" || bad "bool cap"
setmax unset; good
mkdir -p skills/toy; printf '## Command map\n\n| Ask | Runs |\n|---|---|\n| `/toy median` | `python3 scripts/calc.py median` |\n' > skills/toy/SKILL.md
usage_page '- `/toy median 1 2 3` prints the median of the numbers given.
- "print the median of 1 2 3" does the same in plain words.'
$docs check | grep -q "DOCS OK" && ok "a Usage of agent requests passes" || bad "usage passes"
usage_page '- `calc.py median` prints the median.'
$docs check | grep -q "^USAGE Delivery: .calc.py median. names a script" && ok "a Usage naming a .py file fails" || bad "usage py"
usage_page '- `run.sh` runs it.'
$docs check | grep -q "^USAGE Delivery: .run.sh. names a script" && ok "a Usage naming a .sh file fails" || bad "usage sh"
usage_page '- `python3 calc.py median` prints the median.'
$docs check | grep -q "^USAGE Delivery: .python3 calc.py median. names a script" && ok "a python command in Usage fails" || bad "usage python"
usage_page '- `/toy nosuch` does nothing.'
$docs check | grep -q "^USAGE Delivery: .*/toy nosuch. is not in the Command map" && ok "a verb missing from the Command map fails" || bad "usage verb"
usage_page ''
$docs check | grep -q "^USAGE Delivery: has an empty Usage" && ok "an empty Usage section fails" || bad "empty usage"
good; sed -i.bak 's/^## Summary/## Commands/' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "rename Commands to Usage and place it between Summary and Criteria" && ok "a Commands section fails with the fix" || bad "commands fails"
good; rm -rf skills/toy


[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
