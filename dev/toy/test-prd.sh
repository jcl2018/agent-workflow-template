#!/bin/bash
# Test the PRD page format: section order, the owner's PRD review lock, Usage drift, Given/When/Then scenarios, the prd
# command, convert, the requirement readers, and that this repo stays green. usage: test-prd.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
cri="python3 $here/skills/workflow-docs/scripts/criteria.py"
prd="python3 $here/skills/workflow-docs/scripts/prd.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 -c "import json; c = json.load(open('.loop/config.json')); c['criteria'] = True; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
mkdir -p "$FAKE_GH_DIR" docs/wiki skills/toy
printf '## Command map\n\n| Ask | Runs |\n|---|---|\n| `/toy median` | `python3 scripts/calc.py median` |\n| `/toy mean` | `python3 scripts/calc.py mean` |\n' > skills/toy/SKILL.md
printf 'Delivery\tcalc.py\nHome\tREADME.md\n' > .loop/docs.tsv
printf '<!-- workflow-docs -->\n# Home\n\nThe home page of the toy repo, with enough words to count as written.\n' > docs/wiki/Home.md
repo=$PWD; fails=0; day=$(date -u +%F)
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
P=docs/wiki/Delivery.md
USAGE='- `/toy median 1 2 3` prints the median.'
REQS='- DEL-1: **Unreviewed** The calculator prints a median.
- DEL-2: **Unreviewed** It exits 0.'
page() { # page [USAGE]: a PRD page for Delivery, rendered
  local usage=""; [ -n "${1:-}" ] && usage="## Usage

$1

"
  cat > $P <<EOF
<!-- workflow-docs -->
# Delivery

$MS

Review: **Unreviewed**

## Problem

The owner of the toy calculator wants its numbers summed up.

${usage}## Requirements

$REQS

## Non-goals

- No charts.

- No files.

## Success metrics

- The median is right for every list in the toy run.

## Tests

EOF
  $cri render >/dev/null
}
edit() { python3 - "$P" "$1" "$2" <<'PY'
import sys
p, a, b = sys.argv[1:]
t = open(p).read()
assert a in t, a
open(p, "w").write(t.replace(a, b, 1))
PY
}
check() { $docs check 2>&1; }
MS=""; page "$USAGE"
python3 "$here/skills/workflow-health/scripts/milestone.py" new --all --live >/dev/null
MS=$(grep "^Milestone: " $P); page "$USAGE"; git add -A; git commit -qm "Toy PRD" >/dev/null

echo "== 1. the sections, in order, and nothing else"
check | grep -q "DOCS OK" && ok "a PRD page passes" || bad "PRD page: $(check)"
edit "## Non-goals" "## Scope"; check | grep -q "^SECTIONS Delivery: have Problem, Usage, Requirements, Scope" && ok "an unknown section fails" || bad "unknown section"
page "$USAGE"; python3 - "$P" <<'PY'
import sys
p = sys.argv[1]; t = open(p).read()
a, b = t.index("## Non-goals"), t.index("## Success metrics"); c = t.index("## Tests")
open(p, "w").write(t[:a] + t[b:c] + t[a:b] + t[c:])
PY
check | grep -q "^SECTIONS Delivery: .*want Problem, Usage, Requirements, Non-goals, Success metrics, Tests" && ok "swapped sections fail" || bad "swapped"
page "$USAGE"; edit "## Problem" "A stray line.

## Problem"; check | grep -q "^SECTIONS Delivery: has text between the Review line and the first section: A stray line.*Fix:" && ok "stray text before the first section fails" || bad "stray text"
page "$USAGE"; edit "- No files." "- No files.

\`\`\`
## Example heading in a fence
\`\`\`"; check | grep -q "DOCS OK" && ok "a fenced heading is not a section" || bad "fenced heading: $(check)"
page "$USAGE"; edit "## Non-goals

- No charts.

- No files.

" "## Non-goals

"; check | grep -q "^NONGOALS Delivery: .*Fix:" && ok "empty Non-goals fail" || bad "nongoals"
page "$USAGE"; edit "- The median is right for every list in the toy run." "- One.

- Two.

- Three.
- Four."; check | grep -q "^METRICS Delivery: Success metrics has 4 lines, want 1 to 3. Fix:" && ok "more than three Success metrics lines fail" || bad "metrics"
page "$USAGE"; edit "Review: **Unreviewed**" "Review: maybe"; check | grep -q "^REVIEW Delivery: a malformed Review line.*Fix:" && ok "a malformed Review line fails" || bad "review malformed"
page "$USAGE"; edit "Review: **Unreviewed**

" ""; check | grep -q "^REVIEW Delivery: has no Review line. Fix:" && ok "a missing Review line fails" || bad "review missing"

echo "== 2. the owner's PRD review locks Problem, Requirements, Non-goals and Success metrics"
page "$USAGE"; git commit -qam "Clean" >/dev/null || true
$cri review Delivery 2>&1 | grep -q "only the owner" && ok "a PRD review needs --user" || bad "review --user"
$cri review Delivery --user --date 2026-11-08 | grep -q "^REVIEWED PAGE Delivery" && grep -q "^Review: \*\*Reviewed 2026-11-08\*\* <!-- prd P=[0-9a-f]\{8\} R=[0-9a-f]\{8\} N=[0-9a-f]\{8\} M=[0-9a-f]\{8\} U=[0-9a-f]\{8\} -->$" $P && ok "review PAGE --user --date stamps the PRD line with five fingerprints" || bad "review page"
check | grep -q "DOCS OK" && ok "a reviewed PRD passes" || bad "reviewed: $(check)"
git commit -qam "Reviewed PRD" >/dev/null
for pair in "owner of the toy calculator|owner of the big calculator|Problem" "prints a median.|prints a mode.|Requirements" "- No charts.|- No graphs.|Non-goals" "for every list|for most lists|Success metrics"; do
  IFS='|' read -r a b name <<<"$pair"
  edit "$a" "$b"; out=$(check)
  grep -q "^LOCKED Delivery: the reviewed PRD changed in $name (reviewed lock" <<<"$out" && grep -q "Fix: git log -p -- docs/wiki/Delivery.md .*unreview Delivery --user (and /workflow-docs unreview ID --user" <<<"$out" && ok "a change to $name is LOCKED with both un-review fixes" || bad "lock $name: $out"
  git checkout -q -- $P
done
python3 - "$P" <<'PY'
import sys
p = sys.argv[1]; t = open(p).read()
t = t.replace("- No files.\n\n", "", 1).replace("## Success metrics\n\n", "## Success metrics\n\n- No files.\n\n", 1)
open(p, "w").write(t)
PY
check | grep -q "^LOCKED Delivery: the reviewed PRD changed in Non-goals, Success metrics" && ok "a line moved from Non-goals to Success metrics is LOCKED naming both" || bad "moved line"
git checkout -q -- $P; edit "owner of the toy" "owner of the old"; edit "- No charts." "- No plots."
check | grep -q "^LOCKED Delivery: the reviewed PRD changed in Problem, Non-goals (reviewed lock P=.* N=.*, now P=.* N=" && ok "two sections changed at once are both named, with both locks" || bad "two sections"
git checkout -q -- $P; edit "The owner of the toy calculator wants its numbers summed up." "The owner of the toy calculator
wants   its numbers summed up."
check | grep -q "LOCKED" && bad "a reflow-only edit is LOCKED" || ok "a reflow-only edit is not LOCKED"
git checkout -q -- $P; edit "- DEL-2: **Unreviewed** It exits 0." "- DEL-2: **Unreviewed** It exits 0.
- DEL-3: **Unreviewed** It is quick."; check | grep -q "^LOCKED Delivery: the reviewed PRD changed in Requirements" && ok "adding a requirement is LOCKED" || bad "add requirement"
git checkout -q -- $P; edit "- DEL-2: **Unreviewed** It exits 0.
" ""; check | grep -q "^LOCKED Delivery: the reviewed PRD changed in Requirements" && ok "removing a requirement is LOCKED" || bad "remove requirement"
git checkout -q -- $P
$cri review DEL-1 --user --date 2026-11-08 >/dev/null; check | grep -q "LOCKED" && bad "reviewing a requirement tripped the PRD lock" || ok "reviewing a requirement after the PRD review doesn't trip the lock"
$cri unreview DEL-1 --user >/dev/null; check | grep -q "LOCKED" && bad "unreviewing a requirement tripped the PRD lock" || ok "unreviewing a requirement doesn't trip the lock either"
git checkout -q -- $P; before=$(grep "^Review:" $P)
$cri unreview Delivery --user | grep -q "^UNREVIEWED PAGE Delivery" && grep -q "^Review: \*\*Unreviewed\*\*$" $P && ok "unreview PAGE clears the PRD review" || bad "unreview page"
edit "- No charts." "- No graphs."; check | grep -q "LOCKED" && bad "an unreviewed PRD is locked" || ok "after unreview the PRD may change"
$cri review Delivery --user >/dev/null; after=$(grep "^Review:" $P)
[ "$before" != "$after" ] && grep -q "Reviewed $day" <<<"$after" && ! check | grep -q "LOCKED" && ok "review again gives new fingerprints and no lock" || bad "re-review"
git checkout -q -- $P

echo "== 3. review and unreview check every argument first"
cp $P "$d/before.md"
$cri review DEL-9 Delivery --user 2>&1 | grep -q "REFUSED: no requirement DEL-9 .*Nothing was changed. Fix:" && cmp -s $P "$d/before.md" && ok "a bad ID with a good page changes nothing" || bad "bad id + page"
$cri review DEL-1 Nosuch --user 2>&1 | grep -q "REFUSED: Nosuch is not a feature page.*Nothing was changed. Fix:" && cmp -s $P "$d/before.md" && ok "a good ID with a bad page changes nothing" || bad "id + bad page"
$cri review Delivery --user --date 2026-13-45x 2>&1 | grep -q "REFUSED: --date 2026-13-45x is not a YYYY-MM-DD date.*Fix:" && ok "a bad --date is refused" || bad "bad date"
$cri review Delivery --user --date 2999-01-01 2>&1 | grep -q "REFUSED: --date 2999-01-01 .*on or before today" && cmp -s $P "$d/before.md" && ok "a future --date is refused" || bad "future date"
$cri unreview Home --user 2>&1 | grep -q "REFUSED: Home is not a feature page" && ok "Home is not a feature page" || bad "home"
! $cri review DEL-1 delivery --user >/dev/null 2>&1 && cmp -s $P "$d/before.md" && ok "a page name must match the page's own case; nothing changes" || bad "page case"
! $cri unreview ../../README --user >/dev/null 2>&1 && ok "a page name outside the wiki is refused" || bad "page path"

echo "== 4. a Usage change after the review is CHANGED: the check fails, the board lists it, audit and publish ignore it"
edit "prints the median." "prints the median of the numbers."
out=$(check); rc=$?
grep -q "^CHANGED Delivery: Usage edited since the owner's review on 2026-11-08 (reviewed U=[0-9a-f]*, now U=[0-9a-f]*). Fix: the owner runs /workflow-docs review Delivery --user; an agent cannot clear this" <<<"$out" && ! grep -q LOCKED <<<"$out" && [ "$rc" = 1 ] && ok "an edited Usage is CHANGED, not LOCKED, and the check exits 1" || bad "usage edited: $out"
(cd "$here/skills/workflow-monitoring/scripts" && python3 -c "import board_status; print(board_status.wiki_check('$repo'))") | grep -q "('CHANGED', 'Delivery')" && ok "the board's wiki check lists the CHANGED page" || bad "board"
out=$($docs audit --dry-run); rc=$?
! grep -q CHANGED <<<"$out" && grep -q "^UNTESTED DEL-1" <<<"$out" && [ "$rc" = 0 ] && ok "audit --dry-run with only CHANGED and UNTESTED lines prints no CHANGED and exits 0" || bad "audit: $rc $out"
out=$($docs publish --dry-run --adopt Home 2>&1)
! grep -q "fix the pages above" <<<"$out" && ! grep -q "^CHANGED" <<<"$out" && grep -q "WOULD WRITE Delivery" <<<"$out" && ok "publish's pre-check passes with only a CHANGED line" || bad "publish: $out"
git checkout -q -- $P; edit "- \`/toy median 1 2 3\` prints the median." "- \`/toy median 1 2 3\` prints the median.
- \`/toy mean 1 2 3\` prints the mean."
check | grep -q "^CHANGED Delivery: Usage edited" && ok "a new Usage line is CHANGED" || bad "usage line added"
git checkout -q -- $P; python3 - "$P" <<'PY'
import re, sys
p = sys.argv[1]; t = open(p).read()
open(p, "w").write(re.sub(r"## Usage\n\n.*?\n\n(?=## Requirements)", "", t, flags=re.S))
PY
check | grep -q "^CHANGED Delivery: Usage removed since" && ok "a removed Usage is CHANGED" || bad "usage removed: $(check)"
$cri unreview Delivery --user >/dev/null; $cri review Delivery --user >/dev/null; git commit -qam "No usage, reviewed" >/dev/null
edit "## Requirements" "## Usage

$USAGE

## Requirements"; check | grep -q "^CHANGED Delivery: Usage added since" && ok "an added Usage is CHANGED" || bad "usage added: $(check)"
git checkout -q -- $P

echo "== 5. a PRD review makes every requirement with no passing test UNTESTED, and fixes never touch Usage"
$docs audit --dry-run | grep -q "^UNTESTED DEL-2: no test" && ok "a PRD review with Unreviewed requirements lists UNTESTED for one with no row" || bad "untested via PRD review"
page "$USAGE"; $cri review Delivery --user >/dev/null; git commit -qam "Usage back" >/dev/null
sed -n '/^## Usage/,/^## Requirements/p' $P > "$d/usage.before"; echo "# change" >> calc.py; git commit -qam "Code" >/dev/null
(cd "$here/skills/workflow-release/scripts" && python3 -c "import release; release.docs_trouble('$repo', 'main', True)") >/dev/null 2>&1
sed -n '/^## Usage/,/^## Requirements/p' $P | cmp -s - "$d/usage.before" && ! check | grep -q "^CHANGED\|^LOCKED" && ok "the release step's mechanical fixes never change Usage" || bad "fixes touched usage"
git checkout -q -- .; git reset -q --hard HEAD~1  # drop the code commit, so the page is not stale

echo "== 6. Tests are Given/When/Then scenarios with the test, its result and date"
$reg add del-1a --level land --command "true" --goal DEL-1 --describe "Given 1 2 3, when the median is asked, then it prints 2." >/dev/null
$reg add del-2a --level land --command "true" --goal DEL-2 --describe "It exits 0." >/dev/null
$reg add bug-1 --level land --command "true" --goal DEL-1 --describe "Empty input crashes." >/dev/null
python3 - <<'PY'
p = ".loop/regression.tsv"; rows = [r.split("\t") for r in open(p).read().split("\n")]
for r in rows:
    if r[0] == "bug-1":
        r[6:8] = ["defect", "https://example.test/issues/7"]
open(p, "w").write("\n".join("\t".join(r) for r in rows))
PY
$reg run del-1a >/dev/null || true; $cri render >/dev/null
grep -q "^- Given 1 2 3, when the median is asked, then it prints 2\. — \[del-1a\](../../.loop/regression.tsv), both, PASS $day, seen failing no$" $P && ok "a row renders as a scenario with its test, result and date" || bad "scenario line"
grep -A6 "^#### DEL-2$" $P | grep -q "^- It exits 0\. (not yet Given/When/Then) — \[del-2a\]" && grep -A6 "^#### DEL-2$" $P | grep -q "^- \*\*not enforced\*\*" && ok "a plain description renders flagged, and a requirement with no passing row is not enforced" || bad "flagged"
grep -A3 "^### Defect tests" $P | grep -q "^- Empty input crashes\. (not yet Given/When/Then) — \[#7\](https://example.test/issues/7), \[bug-1\]" && ok "defect tests render in the same scenario form" || bad "defect scenario"
out=$($docs audit --dry-run)
grep -q "^REWRITE regression: SCENARIO row del-2a: 'It exits 0.' is not 'Given ..., when ..., then ...'. Fix:" <<<"$out" && grep -q "SCENARIO row bug-1" <<<"$out" && ! grep -q "SCENARIO row del-1a" <<<"$out" && ok "audit lists each plain row, defect rows too, as SCENARIO" || bad "scenario audit: $out"
check | grep -q "SCENARIO" && bad "SCENARIO failed the docs check" || ok "SCENARIO is not a docs check failure"
rm -f .loop/regression.tsv .loop/regression-runs.tsv; git checkout -q -- .

echo "== 7. the requirement readers find the same IDs under either heading, outside fences"
mkdir -p "$d/r/docs/wiki" "$d/r/.loop"; cp .loop/config.json "$d/r/.loop/"
printf 'Alpha\tcalc.py\nBeta\tcalc.py\n' > "$d/r/.loop/docs.tsv"
printf '<!-- workflow-docs -->\n# Alpha\n\nReview: **Unreviewed**\n\n## Problem\n\nAn example:\n\n```\n## Requirements\n- ZZZ-9: **Unreviewed** Not real.\n```\n\n## Requirements\n\n- ALP-1: **Unreviewed** One.\n- ALP-2: **Unreviewed** Two.\n\n## Non-goals\n\n- None.\n\n## Success metrics\n\n- Works.\n\n## Tests\n\n' > "$d/r/docs/wiki/Alpha.md"
printf '<!-- workflow-docs -->\n# Beta\n\n## Summary\n\nOld page.\n\n## Criteria\n\n- BET-1: **Unreviewed** Old one.\n\n## Tests\n\n' > "$d/r/docs/wiki/Beta.md"
ids=$(cd "$d/r" && python3 - "$here" <<'PY'
import sys, os
here = sys.argv[1]
for sub in ("workflow-release", "workflow-regression", "workflow-health", "workflow-docs"):
    sys.path.insert(0, os.path.join(here, "skills", sub, "scripts"))
import release, regression, judge, criteria
root, out = os.getcwd(), []
release.doc_rows = lambda top: ["Alpha", "Beta"]
release.run = lambda *a, **k: type("R", (), {"returncode": 0})()
out.append(sorted(x.split()[0] for x in release.criteria_trouble(root, {})))
out.append(sorted(regression.criteria_ids(root)))
out.append(sorted(i for p in ("Alpha", "Beta") for i, _ in judge.criteria(root, p)))
seen = {}
for page in ("Alpha", "Beta"):
    text = open("docs/wiki/%s.md" % page).read()
    parts = dict(criteria.sections(text))
    out.append(sorted(m.group(1) for _, m in criteria.criteria_of(parts.get("Requirements") or parts.get("Criteria")) if m))
print(out[0] == out[1] == out[2] == sorted(out[3] + out[4]) == ["ALP-1", "ALP-2", "BET-1"], out)
PY
)
grep -q "^True" <<<"$ids" && ok "release, regression, judge and the page parser read the same IDs under both headings, ignoring a fenced heading" || bad "readers: $ids"
(cd "$d/r" && git init -q && python3 -c "
import sys; sys.path.insert(0, '$here/skills/workflow-docs/scripts')
import docs; print([c for c in docs.counts('.') if 'Alpha' in c[1]])") | grep -q '^\[\]$' && ok "the docs counts reader reads Requirements, not the fenced example" || bad "counts reader"

echo "== 8. sync and the release see requirements on a PRD page"
out=$($reg sync 2>&1 || true); grep -q "^GAP DEL-1" <<<"$out" && grep -q "^GAP DEL-2" <<<"$out" && ok "regression sync reports a requirement with no row" || bad "sync: $out"
(cd "$here/skills/workflow-release/scripts" && python3 -c "import release; print(release.criteria_trouble('$repo', {}))") | grep -q "DEL-1 (no regression row)" && ok "the release's requirement check refuses an unmet requirement" || bad "release refuses"

echo "== 9. prd new drafts an Unreviewed PRD from a one-line idea"
$prd new DEL-4 "x" --paths calc.py 2>&1 | grep -q "REFUSED: DEL-4 looks like a requirement ID.*Fix: .*prd.py new Billing" && ok "an ID-shaped name is refused with an example" || bad "id name"
$prd new Billing "charge cards" 2>&1 | grep -q "REFUSED: no --paths.*Fix: .*--paths" && [ ! -f docs/wiki/Billing.md ] && ok "a missing --paths is refused" || bad "no paths"
$prd new Delivery "x" --paths calc.py 2>&1 | grep -q "REFUSED: docs/wiki/Delivery.md already exists" && ok "an existing page is refused" || bad "existing"
out=$($prd new Delight "Owners want a smile when the sum is right." --paths calc.py); echo "$out"
grep -q "^DRAFTED docs/wiki/Delight.md: Review \*\*Unreviewed\*\*, requirement DELI-1" <<<"$out" && grep -q "^NEXT replace the two placeholder lines" <<<"$out" && grep -q "regression row in this same pull request" <<<"$out" && ok "prd new drafts the page, takes a free prefix (DEL is used) and prints the next steps" || bad "new output"
grep -q "^Review: \*\*Unreviewed\*\*$" docs/wiki/Delight.md && grep -q "^- DELI-1: \*\*Unreviewed\*\* Owners want a smile" docs/wiki/Delight.md && ! grep -q "^Milestone:" docs/wiki/Delight.md && ok "the draft is Unreviewed, with no Milestone line" || bad "draft shape"
out=$(check); grep -q "^UNMAPPED" <<<"$out" && bad "the draft is unmapped" || ok "the draft is mapped in docs.tsv"
grep -q "^UNWRITTEN Delight" <<<"$out" && ! grep -q "^SECTIONS Delight" <<<"$out" && ok "the draft is UNWRITTEN until its placeholders are replaced" || bad "unwritten: $out"
python3 -c "
import sys; sys.path.insert(0, '$here/skills/workflow-docs/scripts')
import audit; p = 'docs/wiki/Delight.md'; t = open(p).read(); open(p, 'w').write(audit.milestone_line(t, 'Milestone', 'https://example.test/m/1'))"
grep -v '^$' docs/wiki/Delight.md | sed -n '2,4p' | tr '\n' '~' | grep -q "^# Delight~Milestone: https://example.test/m/1~Review: \*\*Unreviewed\*\*~$" && ! check | grep -q "^REVIEW Delight" && ok "the audit's Milestone fix goes under the title and keeps Review next" || bad "milestone order"
$prd new Qq "x" --paths calc.py --prefix DEL 2>&1 | grep -q "REFUSED: --prefix DEL must be 2 to 5 capital letters not already in use" && ok "a used --prefix is refused" || bad "prefix"
git checkout -q -- .; rm -f docs/wiki/Delight.md

echo "== 10. convert turns old pages into PRD pages"
printf '<!-- workflow-docs -->\n# Delivery\n\nMilestone: https://example.test/m/2\n\n## Summary\n\nThe toy calculator, an old page.\n\n## Usage\n\n%s\n\n## Criteria\n\n%s\n\n## Tests\n\n' "$USAGE" "$REQS" > $P
cp $P "$d/old.md"; out=$($prd convert); grep -q "^Delivery converted (dry run)" <<<"$out" && cmp -s $P "$d/old.md" && ok "convert without --write changes nothing" || bad "dry convert"
$prd convert --write | grep -q "^Delivery converted$" && ok "convert --write converts an old page" || bad "convert"
grep -v '^$' $P | sed -n '3,5p' | tr '\n' '~' | grep -q "^Milestone: https://example.test/m/2~Review: \*\*Unreviewed\*\*~## Problem~$" && grep -q "^- DEL-1: \*\*Unreviewed\*\* The calculator prints a median.$" $P && ok "Summary becomes Problem, Criteria Requirements, lines and stamps kept, Review under Milestone" || bad "converted shape"
$prd convert --write | grep -q "^Delivery skipped$" && ok "converting twice changes nothing" || bad "twice"
$cri render >/dev/null; out=$(check)
grep -q "^UNWRITTEN Delivery" <<<"$out" && ! grep -q "^SECTIONS" <<<"$out" && ok "a converted page is UNWRITTEN until its placeholder drafts are replaced" || bad "convert unwritten: $out"
sed -i.bak 's/^- Write this page from what is really in the repo\./- A real draft line./' $P; rm $P.bak
check | grep -q "DOCS OK" && ok "with real drafts the converted page passes" || bad "drafted: $(check)"
printf '<!-- workflow-docs -->\n# Delivery\n\nReview: **Unreviewed**\n\n## Problem\n\nHalf done.\n\n## Criteria\n\n%s\n\n## Non-goals\n\n- None.\n\n## Tests\n\n' "$REQS" > $P
$prd convert --write | grep -q "^Delivery completed$" && grep -q "^## Requirements$" $P && grep -q "^## Success metrics$" $P && [ "$(grep -c '^Review:' $P)" = 1 ] && ok "a half-converted page is completed" || bad "completed"
printf '<!-- workflow-docs -->\n# Delivery\n\n## Overview\n\nOdd.\n\n## Tests\n\n' > $P
out=$($prd convert --write); rc=$?
grep -q "^Delivery refused: sections are Overview, Tests" <<<"$out" && [ "$rc" = 1 ] && grep -q "Fix:" <<<"$out" && ok "an unrecognized page is refused with what is missing" || bad "refused: $out"
git checkout -q -- .

echo "== 11. this repo stays green: no docs check line but CHANGED, no health FAIL but a docs changed row"
# STALE and TESTS are left out too: a goal's own run or code change makes them mid-goal, and its release step fixes them.
out=$(cd "$here" && python3 skills/workflow-docs/scripts/docs.py check 2>&1)
! grep -Ev "^(CHANGED|STALE|TESTS) " <<<"$out" | grep -qv "^DOCS OK" && ok "this repo's docs check has no line other than CHANGED" || bad "repo docs: $out"
out=$(cd "$here" && python3 skills/workflow-health/scripts/health.py check 2>&1)
! grep "^FAIL" <<<"$out" | grep -Eqv "^FAIL docs \S+ (changed|tests)" && ok "this repo's health has no FAIL other than a docs changed row" || bad "repo health: $(grep '^FAIL' <<<"$out")"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
