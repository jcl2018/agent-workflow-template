#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-docs/scripts/criteria.py
# reads: skills/workflow-docs/scripts/docs.py skills/workflow-health/scripts/health.py
# reads: skills/workflow-monitoring/scripts/monitor.py skills/workflow-regression/scripts/regression.py
# reads: skills/workflow-release/scripts/release.py skills/workflow-setup/scripts/setup.py
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
gwt="Given the toy calculator, when it runs, then it works."
page() { # NAME CRITERIA-LINES: writes a page with an empty Tests section, then renders it unless NORENDER is set
  mkdir -p docs/wiki
  local reqs; reqs=$(sed -E 's/^(- [A-Z]{2,5}-[0-9]+: .*)$/\1\
  - It holds for every toy run./' <<<"$2")  # each requirement gets the sub-bullet DOC-7 asks for
  reqs=$(printf '### Functional\n\n%s\n\n### Non-functional\n\nNone' "$reqs")  # and the two DOC-7 groups
  printf '<!-- workflow-docs -->\n# %s\n\nReview: **Unreviewed**\n\n## Problem\n\n- I read the %s page of the toy calculator, written for this test.\n\n## Requirements\n\n%s\n\n## Non-goals\n\n- No other feature.\n\n## Success metrics\n\n- The toy run passes.\n\n## Tests\n\n' "$1" "$1" "$reqs" > "docs/wiki/$1.md"
  [ -n "${NORENDER:-}" ] || $cri render >/dev/null
}
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["criteria"] = True
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
printf '\n## How to use\n\n### How to use Delivery\n\n| You say | What happens |\n|---|---|\n| "Give me the median" | The calculator prints it. |\n' >> README.md  # the DOC-5 front door
git commit -qam "Front door"
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
good; sub 's/^## Problem/## Commands/'
$docs check | grep -q "^SECTIONS Delivery" && ok "a Commands section fails" || bad "commands section"
good; python3 - <<'PY'
p = "docs/wiki/Delivery.md"; t = open(p).read()
t = t.replace("## Problem", "@@").replace("## Requirements", "## Problem").replace("@@", "## Requirements")
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
ten=$(for n in 1 2 3 4 5 6 7 8 9 10; do echo "- DEL-$n: **Unreviewed** Point $n."; done)
page Delivery "$ten"; $docs check | grep -q "^CAP" && bad "ten criteria over the limit" || ok "ten criteria pass"
page Delivery "$ten
- DEL-11: **Unreviewed** Point 11."; $docs check | grep -q "^CAP Delivery: has 11 requirements" && ok "an eleventh criterion fails" || bad "cap"
for name in calc.py run.sh skills/x/scripts/tool.py app.js; do
  page Delivery "- DEL-1: **Unreviewed** Runs $name for more."
  $docs check | grep -q "^SCRIPT Delivery: DEL-1 names $name" && ok "script name fails: $name" || bad "script name: $name"
done
page Delivery "- DEL-1: **Unreviewed** Reads README.md and docs.tsv."
$docs check | grep -q "^SCRIPT" && bad "other file names failed" || ok "other file names pass"
good; sed -i.bak 's/^- I read the Delivery page of the toy calculator, written for this test\./The Problem may name run.sh freely./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "^SCRIPT" && bad "summary checked" || ok "only the criteria are checked for script names"

echo "== docs check: counts on a feature page match its criteria and tests"
good; echo "This page has 3 criteria and 2 tests, across 4 feature pages." >> docs/wiki/Delivery.md
out=$($docs check || true); echo "$out" | grep COUNT
grep -q "^COUNT docs/wiki/Delivery.md: says 3 criteria, the repo has 1$" <<<"$out" && ok "a wrong number of criteria fails" || bad "criteria count"
grep -q "^COUNT docs/wiki/Delivery.md: says 2 tests, the repo has 0$" <<<"$out" && ok "a wrong number of tests fails" || bad "tests count"
n=$(grep -c . <(grep -v '^Home' .loop/docs.tsv | grep -v '^#'))
grep -q "^COUNT docs/wiki/Delivery.md: says 4 feature pages, the repo has $n$" <<<"$out" && ok "a wrong number of feature pages fails" || bad "feature pages count ($n)"
good; printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\ndel-1a\tland\ttrue\tDEL-1\t\tFirst test.\tcriterion\t\ndel-1b\tland\ttrue\tDEL-1\t\tSecond test.\tcriterion\t\nbug-1\tland\ttrue\tDEL-1\t\tA defect test.\tdefect\thttps://example.test/1\n' > .loop/regression.tsv
echo "This page has 2 tests." >> docs/wiki/Delivery.md
$docs check | grep -q "^COUNT docs/wiki/Delivery.md: says 2 tests, the repo has 3$" && ok "a nonzero test count is checked, defect rows counted" || bad "nonzero tests count"
sed -i.bak 's/This page has 2 tests\./This page has 3 tests./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
nocount && ok "the right test count passes" || bad "the right test count failed"
good; sed -i.bak 's/^- I read the Delivery page of the toy calculator, written for this test\./- DEL-7: **Unreviewed** An example line, not a criterion. This page has 1 criterion./' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
nocount && ok "only the Requirements section is counted" || bad "a requirement-like line outside Requirements counted"
good; printf '\n~~~\n## Requirements\n- DEL-8: **Unreviewed** An example inside code.\n~~~\nThis page has 1 criterion and 2 criteria in its examples.\n' >> docs/wiki/Delivery.md
$docs check | grep -q "says 2 criteria, the repo has 1" && ok "a Requirements heading inside a ~~~ block is not the section" || bad "fenced Requirements heading counted"
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
echo "== docs check: the four count gaps (issues 104-107)"
mkdir -p skills/a; touch skills/a/SKILL.md  # one skill, so skills counts are checked
good; printf '\nThe toy has twenty workflow-ready skills.\n\nThe toy has nineteen  skills.\n\nIt also has two other skills.\n' >> docs/wiki/Delivery.md
out=$($docs check 2>&1 || true)
grep -q "^COUNT docs/wiki/Delivery.md: says twenty workflow-ready skills, " <<<"$out" && grep -q "^COUNT docs/wiki/Delivery.md: says nineteen  skills, " <<<"$out" \
  && ! grep -q "other skills" <<<"$out" && ok "a word or extra space before the noun does not hide a count (104)" || bad "a word or extra space hid a count (104): $out"
good; printf '\nAn example page:\n\n    This page has 9 criteria.\n\tIt has 8 tests.\n\n- A list item.\n\n    This page has 4 criteria.\n' >> docs/wiki/Delivery.md
out=$($docs check 2>&1 || true)
! grep -q "says 9 criteria\|says 8 tests" <<<"$out" && grep -q "^COUNT docs/wiki/Delivery.md: says 4 criteria, the repo has 1$" <<<"$out" \
  && ok "an indented code block is not read as prose (105)" || bad "an indented code block was read, or list text lost (105): $out"
good; printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\ndel-1a\tland\ttrue\tDEL-1\t\tA test.\tcriterion\t\nbug-1\tland\ttrue\tDEL-1\t\tA defect test.\tdefect\thttps://example.test/1\n' > .loop/regression.tsv
echo "This page has 2 tests, and 1 defect test." >> docs/wiki/Delivery.md
nocount && echo "It has 2 defect tests." >> docs/wiki/Delivery.md && $docs check 2>&1 | grep -q "^COUNT docs/wiki/Delivery.md: says 2 defect tests, the repo has 1$" \
  && ok "a page's tests count includes its defect tests (106)" || bad "defect tests left out of the tests count, or a wrong defect count passed (106): $($docs check 2>&1 | grep COUNT)"
$docs add Extras --paths calc.py >/dev/null; page Extras "- EXT-1: **Unreviewed** x"
good; printf '\nUnlike EXT-1, the toy has twenty skills.\n\nEXT-1 alone has 3 tests.\n\nDEL-1 needs nineteen skills.\n' >> docs/wiki/Delivery.md
out=$($docs check 2>&1 || true)
grep -q "^COUNT docs/wiki/Delivery.md: says twenty skills, " <<<"$out" && ! grep -q "says 3 tests\|says nineteen skills" <<<"$out" \
  && ok "a criterion id from another page does not hide a count (107)" || bad "another page's id hid a count (107): $out"
rm docs/wiki/Extras.md; grep -v '^Extras' .loop/docs.tsv > .loop/t && mv .loop/t .loop/docs.tsv
rm -rf skills/a
good

echo "== the Tests table: rows, last runs, and not enforced"
good; grep -qxF '| - | requirement | DEL-1 | no passing test | not enforced |' docs/wiki/Delivery.md && ok "a criterion with no test shows as not enforced" || bad "not enforced"
$docs check | grep -q "DOCS OK" && ok "a rendered table passes" || bad "rendered table"
$reg add del-1a --level land --command "true" --goal DEL-1 >/dev/null; $reg add del-1b --level land --command "false" --goal DEL-1 >/dev/null
$cri render >/dev/null
grep -qxF '| [del-1a](Tests#t-del-1a) | requirement | DEL-1 | - (not yet Given/When/Then) | not run |' docs/wiki/Delivery.md && grep -q '| not enforced |$' docs/wiki/Delivery.md && ok "a test that never ran is not enforcing" || bad "not run"
$reg run land >/dev/null || true
grep -q "^del-1a	PASS	$day" .loop/regression-runs.tsv && grep -q "^del-1b	FAIL	$day" .loop/regression-runs.tsv && ok "a run records each row's status and date" || bad "ledger"
$docs check | grep -q "^TESTS Delivery" && ok "a table behind the last run is stale" || bad "stale after run"
$cri render --check | grep -q "^STALE" && ok "render --check names the stale page" || bad "render check"
$cri render >/dev/null
grep -q "^| \[del-1a\](Tests#t-del-1a) | requirement | DEL-1 | .* | PASS $day |$" docs/wiki/Delivery.md && grep -q "^| \[del-1b\](Tests#t-del-1b) | requirement | DEL-1 | .* | FAIL $day |$" docs/wiki/Delivery.md && ok "render shows status and date" || bad "render shows"
grep -q '| not enforced |$' docs/wiki/Delivery.md && bad "one passing row still not enforced" || ok "one passing row is enough to be enforced"
$reg add del-1a --level land --command "false" --goal DEL-1 >/dev/null; $reg run del-1a >/dev/null || true; $cri render >/dev/null
grep -q '| not enforced |$' docs/wiki/Delivery.md && ok "a criterion with no passing test shows as not enforced" || bad "all failing"
sub 's/FAIL/PASS/'
$docs check | grep -q "^TESTS Delivery" && ok "a hand-edited table fails" || bad "hand edit"
printf 'orphan\tland\ttrue\t\t\nDEL-9x\tland\ttrue\tDEL-9\t\n' >> .loop/regression.tsv
out=$($docs check || true); grep -q "^LINK regression: row orphan links to no requirement" <<<"$out" && ok "a test with no criterion fails" || bad "orphan"
grep -q "^LINK regression: rows link to DEL-9" <<<"$out" && ok "a test of an unknown criterion fails" || bad "dangling"
good

echo "== a reviewed criterion is locked until the owner marks it Unreviewed"
$cri review DEL-1 2>&1 | grep -q "only the owner changes" && ok "review needs the owner's words" || bad "review --user"
$cri review DEL-9 --user 2>&1 | grep -q "no requirement DEL-9" && ok "review refuses an unknown id" || bad "review unknown"
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
$reg add del-1 --level land --command "true" --goal DEL-1 --describe "$gwt" >/dev/null
python3 - <<'PY'  # seen failing once, so the qa lane (which fails unproven rows) passes for the goal below
p = ".loop/regression.tsv"; rows = open(p).read().split("\n")
open(p, "w").write("\n".join(r.replace("del-1\tland\ttrue\tDEL-1\t", "del-1\tland\ttrue\tDEL-1\t2026-01-01", 1) for r in rows))
PY
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
$reg add del-2 --level land --command "false" --goal DEL-2 --describe "$gwt" >/dev/null
$cri render >/dev/null; git add -A; git commit -qm "Failing row" >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (row del-2 is a draft or failing)" && ok "cut refuses a failing row" || bad "cut failing row"
$reg add del-2 --level land --command "true" --goal DEL-2 --describe "$gwt" >/dev/null
$reg add del-2b --level land --command "false" --goal DEL-2 --describe "$gwt" >/dev/null
$cri render >/dev/null; git add -A; git commit -qm "Second row" >/dev/null
$rel cut crit 2>&1 | grep -q "DEL-2 (row del-2b is a draft or failing)" && ok "cut checks every row of a criterion" || bad "cut second row"
$reg sync >/dev/null || true; python3 "$here/skills/workflow-regression/scripts/regression.py" criteria | grep -q "del-2b" && ok "regression criteria runs every row" || bad "criteria every row"
$reg add del-2b --level land --command "true" --goal DEL-2 --describe "$gwt" >/dev/null
$cri render >/dev/null; git add -A; git commit -qm "Passing row" >/dev/null
mv .loop/docs.tsv "$d/docs.tsv.away"
(cd "$here/skills/workflow-release/scripts" && python3 -c "import release; print(release.criteria_trouble('$PWD_REPO', {}))") | grep -q '^\[\]$' && ok "no docs.tsv: criteria are ignored" || bad "no docs.tsv"

mv "$d/docs.tsv.away" .loop/docs.tsv
$rel cut crit | grep -q "^DRAFT" && ok "cut with every row passing" || bad "cut passing"

echo "== the Tests table shows words, description, when it runs, result and seen failing"
good
$reg add del-1c --level nightly --command "true" --goal DEL-1 --describe "Given a short list, when the median is asked, then it is printed." >/dev/null
$reg red del-1c --break "true" >/dev/null || true
printf 'del-1c\tnightly\ttrue\tDEL-1\t2026-01-02\tGiven a short list, when the median is asked, then it is printed.\n' > .loop/regression.tsv
$reg run del-1c >/dev/null || true; $cri render >/dev/null
grep -qxF "| [del-1c](Tests#t-del-1c) | requirement | DEL-1 | Given a short list, when the median is asked, then it is printed. | PASS $day |" docs/wiki/Delivery.md && ok "a Tests row carries the test link, its Given/When/Then words and its result" || bad "scenario line fields"
grep -qE "^\| <a id=\"t-del-1c\"></a>del-1c \| requirement \| DEL-1 \| PASS \| $day \| ([0-9a-f]{7}|local) \| 2026-01-02 \|$" docs/wiki/Tests.md && ok "the full Tests page carries the row's anchor, result, date, run and seen failing" || bad "row shape: $(cat docs/wiki/Tests.md)"


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
usage_page() { # USAGE-BODY: Delivery with a Usage section between Problem and Requirements
  printf '<!-- workflow-docs -->\n# Delivery\n\nReview: **Unreviewed**\n\n## Problem\n\n- I read the Delivery page of the toy calculator, written for this test.\n\n## Usage\n\n%s\n\n## Requirements\n\n### Functional\n\n%s\n  - It holds for every toy run.\n\n### Non-functional\n\nNone\n\n## Non-goals\n\n- No other feature.\n\n## Success metrics\n\n- The toy run passes.\n\n## Tests\n\n' "$1" "$one" > docs/wiki/Delivery.md
  $cri render >/dev/null
}
good; setmax unset
$docs check | grep -q "DOCS OK" && ok "a page with no commands passes without a Usage section" || bad "no usage passes"
page Delivery "$one
- DEL-2: **Unreviewed** The calculator prints a mean."
$docs check | grep -q "^CAP" && bad "default limit rejects two criteria" || ok "no criteria_max means 10"
setmax 1
$docs check | grep -q "^CAP Delivery: has 2 requirements, over the limit of 1 (criteria_max in .loop/config.json)" && ok "criteria_max 1 fails a page of two" || bad "cap 1"
python3 "$here/skills/workflow-health/scripts/health.py" check 2>&1 | grep -q "FAIL.*cap" && ok "health fails the same page" || bad "health cap"
setmax '"six"'
$docs check 2>&1 | grep -q "REFUSED: criteria_max is 'six'" && ok "a bad criteria_max refuses, naming the key" || bad "bad cap"
setmax true
$docs check 2>&1 | grep -q "REFUSED: criteria_max is True" && ok "a true criteria_max refuses" || bad "bool cap"
setmax unset; good
mkdir -p skills/toy; printf '## Command map\n\n| Ask | Runs |\n|---|---|\n| `/toy median` | `python3 scripts/calc.py median` |\n' > skills/toy/SKILL.md
usage_page '### `/toy median 1 2 3`

- Does: prints the median of the numbers given.
- Prints: the median.
- Refuses: nothing.'
$docs check | grep -q "DOCS OK" && ok "a Usage of API entries passes" || bad "usage passes: $($docs check)"
usage_page '### `calc.py median LIST`

- Prints: the median.
- Refuses: an empty list.'
$docs check | grep -q "DOCS OK" && ok "a Usage entry naming a routine from the Command map passes" || bad "usage routine"
usage_page '### `/toy median 1 2 3`

- Prints: the median.'
$docs check | grep -q "^FORMAT Delivery:[0-9]*: Usage: DOC-6 each entry has a '- Refuses:' bullet" && ok "a Usage entry with no Refuses fails" || bad "usage refuses"
usage_page '- `/toy median 1 2 3` prints the median.'
$docs check | grep -q "^FORMAT Delivery:[0-9]*: Usage: DOC-6 only ### .syntax. entries" && ok "a prose Usage line fails" || bad "usage prose"
usage_page '### `other.py run`

- Prints: x.
- Refuses: nothing.'
$docs check | grep -q "^FORMAT Delivery:[0-9]*: Usage: DOC-6 the command is in its skill's Command map (got 'other.py run')" && ok "a routine missing from the Command map fails" || bad "usage routine missing"
usage_page '### `/toy nosuch`

- Prints: x.
- Refuses: nothing.'
$docs check | grep -q "^FORMAT Delivery:[0-9]*: Usage: DOC-6 the command is in its skill's Command map (got '/toy nosuch')" && ok "a verb missing from the Command map fails" || bad "usage verb"
usage_page ''
$docs check | grep -q "^USAGE Delivery: has an empty Usage" && ok "an empty Usage section fails" || bad "empty usage"
good; sed -i.bak 's/^## Problem/## Commands/' docs/wiki/Delivery.md; rm docs/wiki/Delivery.md.bak
$docs check | grep -q "rename Commands to Usage and place it between Problem and Requirements" && ok "a Commands section fails with the fix" || bad "commands fails"
good; rm -rf skills/toy


[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
