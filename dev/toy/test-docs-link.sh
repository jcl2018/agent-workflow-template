#!/bin/bash
# windows: ok
# reads: skills/
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py
# reads: skills/workflow-docs/scripts/pageformat.py skills/workflow-docs/scripts/render.py
# reads: skills/workflow-docs/scripts/prd.py skills/workflow-docs/scripts/counting.py skills/workflow-docs/scripts/audit.py
# reads: skills/workflow-docs/references/template.md skills/workflow-health/scripts/judge.py
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tests.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py
# Test link-form feature pages and Home's Topic column (DOC-1, DOC-2, DOC-4 proposals): a page holding "PRD: <link>" plus
# the generated sections passes when the linked PRD is readable and its ids drive the Tests table; an unreadable link
# is UNREAD and never a pass; a Notion link is read through $LOOP_PRD_READER; Home groups rows by the topics setting.
# usage: test-docs-link.sh [DIR]

set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_BATCH  # a toy test never reaches a real session tool
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
export LOOP_OWNER_WORDS='"review it" (the toy owner)'  # review --user with no terminal needs the owner's words
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
export LOOP_FLOW="$d/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" PYTHONDONTWRITEBYTECODE=1
unset GH_TOKEN GITHUB_TOKEN
docs="python3 $here/skills/workflow-docs/scripts/docs.py"
cri="python3 $here/skills/workflow-docs/scripts/criteria.py"
prd="python3 $here/skills/workflow-docs/scripts/prd.py"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
python3 -c "import json; c = json.load(open('.loop/config.json')); c['criteria'] = True; c.pop('criteria_max', None); json.dump(c, open('.loop/config.json', 'w'), indent=2)"
mkdir -p "$FAKE_GH_DIR" docs/wiki skills/toy
printf '## Command map\n\n| Ask | Runs |\n|---|---|\n| `/toy median LIST` | `python3 scripts/calc.py median LIST` |\n' > skills/toy/SKILL.md
printf 'Delivery\tcalc.py\nHome\tREADME.md\n' > .loop/docs.tsv
fails=0; day=$(date -u +%F)
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { $docs check 2>&1; }
H=docs/wiki/Home.md; P=docs/wiki/Delivery.md; T=docs/wiki/Tests.md
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
has() { check | grep -q "$1"; }


echo "== a link-form page passes when its link is readable"
dw=$(cd "$d" && { pwd -W 2>/dev/null || pwd; })
cat > "$d/linked-prd.md" <<'EOF'
# Delivery PRD

## Requirements

### Functional

- DEL-1: **Unreviewed** The calculator prints a median.

### Non-functional

- DEL-2: **Unreviewed** It answers quickly.
EOF
cat > $P <<EOF
<!-- workflow-docs -->
# Delivery

PRD: $dw/linked-prd.md

## Tests

EOF
$reg add del-1a --level land --command "true" --goal DEL-1 --describe "Given 1 2 3, when the median is asked, then it prints 2." >/dev/null
$reg run del-1a >/dev/null 2>&1
$cri render >/dev/null
grep -q "DEL-1" $P && ok "render fills the Tests table from the linked PRD's ids" || bad "tests table: $(cat $P)"
grep -q "calculator prints" $P && bad "the linked PRD's text was copied into the page" || ok "the linked text is not copied into the repo"
out=$(check); grep -q "^DOCS OK" <<<"$out" && ok "a link-form page passes the docs check" || bad "link page: $out"

echo "== an unreadable link is UNREAD, never a pass"
edit $P "$dw/linked-prd.md" "$dw/missing-prd.md"
out=$(check); rc=$?
grep -q "^UNREAD Delivery:" <<<"$out" && ! grep -q "^DOCS OK" <<<"$out" && ok "an unreadable link reports UNREAD and no DOCS OK" || bad "unread: $out"
$docs check >/dev/null 2>&1 && bad "an unreadable link exited 0" || ok "an unreadable link exits non-zero"
reset

echo "== a Notion link needs the reader"
cat > $P <<EOF
<!-- workflow-docs -->
# Delivery

PRD: https://app.notion.com/p/4178261590fd81d59adff26e65faec0a

## Tests

EOF
cp "$d/linked-prd.md" "$d/reader-out.md"; printf 'import sys
print(open(sys.argv[1]).read())
' > "$d/reader.py"; rd="python3 $dw/reader.py $dw/reader-out.md"
out=$(check); grep -q "^UNREAD Delivery: .*MCP connector" <<<"$out" && ok "a Notion link with no reader is UNREAD naming the connector" || bad "notion: $out"
LOOP_PRD_READER="$rd" $cri render >/dev/null
out=$(LOOP_PRD_READER="$rd" check); grep -q "^DOCS OK" <<<"$out" && ok "a Notion link read through the reader passes" || bad "reader: $out"
$reg add list-ids --level land --command true --goal DEL-1 --describe "Given a link-form page, when the tests are listed, then its ids show." --category criterion >/dev/null
out=$(LOOP_PRD_READER="$rd" python3 "$here/skills/workflow-regression/scripts/tests.py" list 2>&1); grep -q "DEL-1" <<<"$out" && ok "tests.py list reads a link-form page's ids" || bad "tests list: $out"
cat >> $P <<'EOF'

## Problem

- Extra prose copied from the PRD.
EOF
edit $P "## Tests

" "## Tests

"; has "^SECTIONS Delivery:" && ok "prose beside the link fails SECTIONS" || bad "prose beside link"
reset

echo "== the source is a docs.tsv setting: page, url or mcp"
cat > $P <<EOF2
<!-- workflow-docs -->
# Delivery

PRD: mcp:notion:delivery-prd

## Tests

EOF2
printf 'Delivery	calc.py	mcp:notion:delivery-prd
Home	README.md
' > .loop/docs.tsv
out=$(check); grep -q "^UNREAD Delivery: .*mcp:notion:delivery-prd" <<<"$out" && ok "an mcp source with no reader is UNREAD" || bad "mcp unread: $out"
LOOP_PRD_READER="$rd" $cri render >/dev/null
out=$(LOOP_PRD_READER="$rd" check); grep -q "^DOCS OK" <<<"$out" && ok "an mcp source read through the reader passes" || bad "mcp reader: $out"
edit $P "PRD: mcp:notion:delivery-prd" "PRD: url:https://example.com/other"
out=$(LOOP_PRD_READER="$rd" check); grep -q "^FORMAT Delivery: DOC-1 the 'PRD: <source>' line" <<<"$out" && ok "a page line that differs from docs.tsv fails" || bad "mismatch: $out"
printf 'Delivery	calc.py	
Home	README.md
' > .loop/docs.tsv
reset

echo "== Home groups rows by topic"
python3 -c "import json; c = json.load(open('.loop/config.json')); c['topics'] = {'Build loop': ['Delivery'], 'Quality': ['Monitoring']}; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
has "^FORMAT Home:.*one table with the header | Topic |" && ok "with topics set a Home without a Topic column fails" || bad "topic header: $(check)"
$cri render >/dev/null
grep -q "^| Topic | Feature |" $H && grep -q "^| Build loop | \[Delivery\]" $H && ok "render adds the Topic column with the page's topic" || bad "regroup: $(cat $H)"
out=$(check); grep -q "^DOCS OK" <<<"$out" && ok "the regrouped Home passes" || bad "regrouped: $out"
edit $H "| Build loop |" "| Quality |"; has "^FORMAT Home:.*Topic cell" && ok "a wrong Topic cell fails" || bad "wrong topic"
reset
echo
[ "$fails" -eq 0 ] && { echo "ALL PASS"; exit 0; } || { echo "$fails FAILED"; exit 1; }
