#!/bin/bash
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py
# reads: skills/workflow-docs/scripts/pageformat.py skills/workflow-docs/scripts/render.py
# reads: skills/workflow-docs/scripts/prd.py skills/workflow-docs/scripts/counting.py
# reads: skills/workflow-docs/scripts/audit.py skills/workflow-docs/references/template.md
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tests.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py
# Test the docs fixes for four issues: a guide page skips the PRD contract (125), the audit takes a page's own
# Milestone line and matches titles loosely (130), the LOCKED hints never say review and --user needs the owner's
# words without a terminal (133), and commits merged in from the base branch don't stale a page (156).
# usage: test-docs-issues.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH LOOP_OWNER_WORDS  # a toy test never reaches a real session tool
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
export LOOP_FLOW="$d/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" PYTHONDONTWRITEBYTECODE=1
unset GH_TOKEN GITHUB_TOKEN
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
cri="python3 $here/skills/workflow-docs/scripts/criteria.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 -c "import json; c = json.load(open('.loop/config.json')); c['criteria'] = True; c.pop('criteria_max', None); json.dump(c, open('.loop/config.json', 'w'), indent=2)"
mkdir -p "$FAKE_GH_DIR" docs/wiki skills/toy
printf '## Command map\n\n| Ask | Runs |\n|---|---|\n| `/toy median LIST` | `python3 scripts/calc.py median LIST` |\n' > skills/toy/SKILL.md
printf 'Delivery\tcalc.py\nHome\tREADME.md\n' > .loop/docs.tsv
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { $docs check 2>&1; }
H=docs/wiki/Home.md; P=docs/wiki/Delivery.md; G=docs/wiki/Workflow-guide.md
edit() { python3 - "$1" "$2" "$3" <<'PY'
import sys
p, a, b = sys.argv[1:]
t = open(p).read()
assert a in t, a
open(p, "w").write(t.replace(a, b, 1))
PY
}
cat > $H <<'EOF'
<!-- workflow-docs -->
# Toy

## Features

| Feature | What it does | How to use | Milestone |
|---|---|---|---|
| [Delivery](Delivery) | Prints the median of the numbers given. | [README](https://github.com/toy/repo#how-to-use-delivery) | https://github.com/toy/repo/milestone/1 |
EOF
cat >> README.md <<'EOF'

## How to use

### How to use Delivery

Say these to the agent:

| You say | What happens |
|---|---|
| "What is the median of 1 2 3?" | The calculator prints 2. |
EOF
cat > $P <<'EOF'
<!-- workflow-docs -->
# Delivery

Review: **Unreviewed**

## Problem

- I want the median of my numbers without working it out by hand.

## Usage

- `/toy median LIST` — Works out the median and prints it (`MEDIAN 2`). Refuses an empty list (exit 1, `REFUSED: no numbers`).

## Requirements

### Functional

- DEL-1: **Unreviewed** The calculator prints a median.
  - The median of the numbers given is printed.

### Non-functional

- DEL-2: **Unreviewed** It answers quickly.
  - It prints within a second for a short list.

## Non-goals

- No charts.

## Success metrics

- The median is right for every list in the toy run.

## Tests

EOF
$reg add del-1a --level land --command "true" --goal DEL-1 --describe "Given 1 2 3, when the median is asked, then it prints 2." >/dev/null
$reg add del-2a --level land --command "true" --goal DEL-2 --describe "Given a short list, when it runs, then it answers in a second." >/dev/null
$reg run del-1a >/dev/null 2>&1; $reg run del-2a >/dev/null 2>&1
$cri render >/dev/null
git add -A; git commit -qm "Toy pages in the format" >/dev/null
reset() { git checkout -q -- .; git clean -qfd docs .loop >/dev/null; }
out=$(check); grep -q "^DOCS OK" <<<"$out" && ok "the toy pages pass the docs check" || bad "good pages: $out"

echo "== issue 125: a guide page is checked for freshness, not for the PRD contract"
printf 'Workflow-guide\t.loop,guide.txt\n' >> .loop/docs.tsv; echo "guide notes" > guide.txt
cat > $G <<'EOF'
<!-- workflow-docs -->
<!-- workflow-docs guide -->
# Workflow guide

How to work in this repo: say what you want, and the workflow plans, builds, tests and ships it for you.
EOF
git add -A; git commit -qm "Guide page" >/dev/null
out=$(check); grep -q "^DOCS OK" <<<"$out" && ok "a page marked as a guide passes with no PRD sections, Home row or README section (issue 125)" || bad "guide: $out"
python3 -c "import json; c = json.load(open('.loop/config.json')); c['cadence'] = 45; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
git commit -qam "Settings change" >/dev/null
out=$(check); ! grep -q "^STALE Workflow-guide" <<<"$out" && ok "a settings change doesn't make a guide page stale (issue 125)" || bad "guide config stale: $out"
echo "more notes" >> guide.txt; git commit -qam "Guide notes change" >/dev/null
check | grep -q "^STALE Workflow-guide" && ok "a change to a guide page's other paths still makes it stale (issue 125)" || bad "guide freshness"
echo "It now covers the newer notes as well, in a few more words." >> $G; git commit -qam "Guide sees the notes" >/dev/null
edit $H "| [Delivery](Delivery)" "| [Workflow-guide](Workflow-guide) | How to work. | [README](https://github.com/toy/repo#how-to-use-workflow-guide) | https://github.com/toy/repo/milestone/2 |
| [Delivery](Delivery)"
check | grep -q "^FORMAT Home:[0-9]*: Features: DOC-4 a row for a page that is not a feature page (got Workflow-guide)" && ok "a guide page is not a feature page for the Home rows (issue 125)" || bad "guide home row"; reset
edit $G "<!-- workflow-docs guide -->
" ""
check | grep -q "^SECTIONS Workflow-guide" && ok "the same page without the guide line still gets the PRD contract (issue 125)" || bad "guide control"; reset
check | grep -q "^DOCS OK" || bad "guide reset: $(check)"

echo "== issue 130: the audit takes the page's own Milestone line"
gh api repos/toy/repo/milestones -f title=Backlog >/dev/null
gh api repos/toy/repo/milestones -f "title=Delivery of medians" >/dev/null
edit $P "# Delivery
" "# Delivery

Milestone: https://example.test/milestone/2
"
git commit -qam "Milestone line" >/dev/null
out=$($docs audit --dry-run 2>&1)
! grep -q "^MILESTONE Delivery" <<<"$out" && ok "a page whose Milestone line names a real milestone has its milestone (issue 130)" || bad "milestone line: $out"
edit $P "milestone/2" "milestone/9"; out=$($docs audit --dry-run 2>&1); reset
grep -q "^MILESTONE Delivery" <<<"$out" && ok "a Milestone line naming no milestone is still found (issue 130)" || bad "milestone ghost: $out"
got=$(python3 - "$here" <<'PY'
import os, sys
sys.path.insert(0, os.path.join(sys.argv[1], "skills", "workflow-docs", "scripts"))
import audit
held = {"Bloom hedge-fund demo": "https://github.com/o/r/milestone/3", "Other": "https://github.com/o/r/milestone/4"}
print(audit.milestone_of("Bloom-hedge-fund-demo", "# Bloom\n", held, "Milestone"),
      audit.milestone_of("X", "# X\n\nMilestone: https://github.com/o/r/milestone/4\n", held, "Milestone"))
PY
)
[ "$got" = "https://github.com/o/r/milestone/3 https://github.com/o/r/milestone/4" ] && ok "a hyphenated page name matches a milestone titled with spaces (issue 130)" || bad "loose title: $got"

echo "== issue 133: LOCKED hints never say review, and --user needs the owner's words without a terminal"
$cri review DEL-1 --user </dev/null 2>&1 | grep -q "REFUSED: .*LOOP_OWNER_WORDS" && ! grep -q "Reviewed" $P && ok "review --user with no terminal and no owner words is refused (issue 133)" || bad "unchecked user"
LOOP_OWNER_WORDS='"review DEL-1"' $cri review DEL-1 --user </dev/null | grep -q "REVIEWED DEL-1" && grep -q "review	DEL-1	\"review DEL-1\"" "$(git rev-parse --git-common-dir)/loop/reviews.tsv" && ok "review --user with the owner's words reviews and records the words (issue 133)" || bad "owner words"
edit $P "The calculator prints a median." "The calculator prints a mode."
out=$(check | grep "^LOCKED Delivery: DEL-1")
grep -q "unreview DEL-1 --user) and reviews it again" <<<"$out" && ! grep -q "docs review" <<<"$out" && ok "a changed reviewed requirement's LOCKED hint says restore or unreview, never review (issue 133)" || bad "criterion hint: $out"
reset
LOOP_OWNER_WORDS='"review Delivery"' $cri review Delivery --user >/dev/null; edit $P "- No charts." "- No graphs."
out=$(check | grep "^LOCKED Delivery: the reviewed PRD")
grep -q "unreview Delivery --user .*and reviews it again" <<<"$out" && ! grep -q "docs review" <<<"$out" && ok "a changed reviewed PRD's LOCKED hint says restore or unreview, never review (issue 133)" || bad "prd hint: $out"
reset

echo "== issue 156: commits merged in from the base branch don't stale the branch's pages"
fork=$(git rev-parse HEAD)
git switch -q -c side; git switch -q -c other main
printf '\n# other goal\n' >> calc.py; git commit -qam "Other goal code" >/dev/null
edit $P "- No charts." "- No charts.
- No graphs."; git commit -qam "Other goal page" >/dev/null
git switch -q main; git merge -q --no-ff --no-edit other; printf '\n# owner\n' >> calc.py; git commit -qam "Owner code on main" >/dev/null
git switch -q side; edit $P "- No charts." "- No charts.
- No tables."; git commit -qam "Branch page" >/dev/null
git merge -q --no-edit main >/dev/null 2>&1 || { git checkout -q --ours $P; git add -A; git commit -qm "Merge main" >/dev/null; }
$docs check --base "$fork" 2>&1 | grep -q "^STALE Delivery: .* Owner code on main" && ok "base-branch commits only in a local main, not on origin, still stale the page (only origin's base is read)" || bad "local base read"
git push -q origin main
out=$($docs check --base "$fork" 2>&1)
! grep -q "^STALE Delivery" <<<"$out" && ok "after merging the base branch, its commits don't make the branch's page stale (issue 156)" || bad "merged base: $out"
printf '\n# branch\n' >> calc.py; git commit -qam "Branch code" >/dev/null
$docs check --base "$fork" | grep -q "^STALE Delivery: 1 commits since the page: [0-9a-f]* Branch code" && ok "the branch's own later change still makes the page stale (issue 156)" || bad "own change"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
