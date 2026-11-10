#!/bin/bash
# reads: skills/
# reads: skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py
# reads: skills/workflow-docs/scripts/pageformat.py skills/workflow-docs/scripts/render.py
# reads: skills/workflow-docs/scripts/prd.py skills/workflow-docs/scripts/counting.py
# reads: skills/workflow-docs/references/template.md skills/workflow-health/scripts/judge.py
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tests.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-setup/scripts/settings.py
# Test the page format (DOC-4..DOC-10): for each rule a bad page fails naming the page, section and rule and a good
# page passes; sub-bullets and the two requirement groups; the generated Tests page; the runs file's run column; the
# cap default; the format key. usage: test-docs-format.sh [DIR]
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
has() { check | grep -q "$1"; }

echo "== the good pages pass"
out=$(check); grep -q "^DOCS OK" <<<"$out" && ok "pages in the format pass the docs check" || bad "good pages: $out"

echo "== DOC-4 Home"
edit $H "## Features" "Welcome to the toy.

## Features"; has "^FORMAT Home:[0-9]*: Features: DOC-4 a line outside the features table (got 'Welcome to the toy.')" && ok "DOC-4 a Home line outside the table fails naming Home, Features and DOC-4" || bad "home stray"; reset
edit $H "What it does" "Description"; has "^FORMAT Home:[0-9]*: Features: DOC-4 one table with the header" && ok "DOC-4 a Home table with other columns fails" || bad "home header"; reset
edit $H "#how-to-use-delivery" "#how-to-use-nothing"; has "^FORMAT Home:[0-9]*: Features: DOC-4 How to use links the README's '### How to use Delivery' section" && ok "DOC-4 a How to use link to no README anchor fails" || bad "home anchor"; reset
edit $H "https://github.com/toy/repo/milestone/1" "soon"; has "^FORMAT Home:[0-9]*: Features: DOC-4 Milestone links the feature's milestone (got 'soon')" && ok "DOC-4 a Milestone cell with no milestone link fails" || bad "home milestone"; reset
python3 - $H <<'PY'
import sys; p = sys.argv[1]; kept = [l for l in open(p) if not l.startswith("| [Delivery]")]; open(p, "w").write("".join(kept))
PY
has "^FORMAT Home:[0-9]*: Features: DOC-4 one row per feature page (got 0 rows for Delivery)" && ok "DOC-4 a feature page with no Home row fails" || bad "home row"; reset
check | grep -q "^FORMAT Home" && bad "good Home" || ok "DOC-4 a Home of one features table passes"

echo "== DOC-5 README front door"
edit README.md '"What is the median of 1 2 3?"' '`/toy median 1 2 3`'; has "^FORMAT README:[0-9]*: How to use Delivery: DOC-5 You say is a quoted phrase, not a command" && ok "DOC-5 a backtick command in You say fails naming README, the section and DOC-5" || bad "front backtick"; reset
edit README.md '"What is the median of 1 2 3?"' '"/toy median 1 2 3"'; has "^FORMAT README:[0-9]*: How to use Delivery: DOC-5 You say is a quoted phrase" && ok "DOC-5 a quoted slash command in You say fails" || bad "front slash"; reset
edit README.md "### How to use Delivery" "### Delivery"; has "^FORMAT README:[0-9]*: How to use: DOC-5 one '### How to use Delivery' section" && ok "DOC-5 a feature with no How to use section fails" || bad "front missing"; reset
edit README.md "Say these to the agent:" "Say these to the agent:
And a second intro line."; has "^FORMAT README:[0-9]*: How to use: DOC-5 only one intro line per section" && ok "DOC-5 a second intro line fails" || bad "front intro"; reset
check | grep -q "^FORMAT README" && bad "good README" || ok "DOC-5 a front door of quoted phrases passes"

echo "== DOC-6 Usage"
edit $P " and prints it (\`MEDIAN 2\`). Refuses an empty list (exit 1, \`REFUSED: no numbers\`)." "."; has "^FORMAT Delivery:[0-9]*: Usage: DOC-6 each entry says what it prints" && ok "DOC-6 a Usage entry that says nothing printed fails naming the page, Usage and DOC-6" || bad "usage prints"; reset
edit $P "Refuses an empty list" "Refuses an empty list
It works out the median"; has "^FORMAT Delivery:[0-9]*: Usage: DOC-6 only .- .syntax. — what it does. entries" && ok "DOC-6 a prose line in Usage fails" || bad "usage prose"; reset
edit $P '- `/toy median LIST`' '- `/toy mode LIST`'; has "^FORMAT Delivery:[0-9]*: Usage: DOC-6 the command is in its skill's Command map (got '/toy mode LIST')" && ok "DOC-6 a command missing from the Command map fails" || bad "usage map"; reset
edit $P '- `/toy median LIST`' '- `calc.py median LIST`'; check | grep -q "^FORMAT Delivery:[0-9]*: Usage" && bad "usage routine" || ok "DOC-6 a routine named in the Command map passes"; reset
check | grep -q "^FORMAT Delivery:[0-9]*: Usage" && bad "good usage" || ok "DOC-6 Usage of API entries passes"
edit $P '- `/toy median LIST`' '- `   `'; out=$(check); grep -q "^FORMAT Delivery:[0-9]*: Usage: DOC-6 the command is in its skill's Command map" <<<"$out" && ! grep -q Traceback <<<"$out" && ok "DOC-6 a Usage entry whose backticks hold only spaces fails without a crash" || bad "usage blank: $out"; reset

echo "== DOC-7 Requirements: sub-bullets"
edit $P "  - The median of the numbers given is printed.
" ""; has "^FORMAT Delivery:[0-9]*: Requirements: DOC-7 DEL-1 has at least one sub-bullet" && ok "DOC-7 a requirement with no sub-bullet fails naming the page, Requirements and DOC-7" || bad "no sub-bullet"; reset
edit $P "The calculator prints a median." "The calculator prints a median $(printf 'and more %.0s' $(seq 9))."; has "^FORMAT Delivery:[0-9]*: Requirements: DOC-7 an Unreviewed requirement line is at most 20 words" && ok "DOC-7 an Unreviewed line over 20 words fails" || bad "long line"; reset
edit $P "### Functional
" "### Functional

  - An orphan bullet.
"; has "^FORMAT Delivery:[0-9]*: Requirements: DOC-7 a sub-bullet is '  - ' (two spaces) right under a requirement line (got '- An orphan bullet.')" && ok "DOC-7 an orphan sub-bullet is refused" || bad "orphan"; reset
edit $P "  - The median of the numbers given is printed." "  - The median of the numbers given is printed.
    - A deeper bullet."; has "^FORMAT Delivery:[0-9]*: Requirements: DOC-7 a sub-bullet is '  - ' (two spaces)" && ok "DOC-7 a deeper-nested sub-bullet is refused" || bad "nested"; reset
out=$(check); ! grep -q "^CRITERION" <<<"$out" && ! grep -q "Requirements: DOC-7" <<<"$out" && ok "DOC-7 sub-bullets are not read as requirements" || bad "sub-bullets read: $out"

echo "== DOC-7 Requirements: the Functional and Non-functional groups"
edit $P "### Non-functional
" ""; has "^FORMAT Delivery:[0-9]*: Requirements: DOC-7 Requirements is '### Functional' then '### Non-functional' (got 'Functional')" && ok "DOC-7 a missing group heading fails" || bad "group missing"; reset
python3 - $P <<'PY'
import sys; p = sys.argv[1]; t = open(p).read()
a, b, c = t.index("### Functional"), t.index("### Non-functional"), t.index("## Non-goals")
open(p, "w").write(t[:a] + t[b:c].rstrip("\n") + "\n\n" + t[a:b] + t[c:])
PY
has "^FORMAT Delivery:[0-9]*: Requirements: DOC-7 Requirements is '### Functional' then '### Non-functional' (got 'Non-functional, Functional')" && ok "DOC-7 groups in the wrong order fail" || bad "group order"; reset
edit $P "### Functional
" "Some words first.

### Functional
"; has "^FORMAT Delivery:[0-9]*: Requirements: DOC-7 only requirement lines, their sub-bullets or 'None'" && ok "DOC-7 a stray line in Requirements fails" || bad "stray"; reset
edit $P "- DEL-2: **Unreviewed** It answers quickly.
  - It prints within a second for a short list." "None"
edit $P "  - The median of the numbers given is printed." "  - The median of the numbers given is printed.
- DEL-2: **Unreviewed** It answers quickly.
  - It prints within a second for a short list."
out=$(check); grep -q "^DOCS OK" <<<"$out" && ok "DOC-7 a group holding only None passes" || bad "none: $out"
edit $P "None" "None
- DEL-3: **Unreviewed** Also this.
  - It holds."; has "^FORMAT Delivery:[0-9]*: Requirements: DOC-7 a group holds requirements or the single line 'None'" && ok "DOC-7 None beside a requirement fails" || bad "none plus"; reset
$cri review DEL-1 DEL-2 --user >/dev/null
edit $P "  - It prints within a second for a short list." "  - It prints within a second for a short list.
  - A long list takes longer."
edit $P "  - The median of the numbers given is printed." "  - The median of the numbers given is printed.
  - An even list prints the mean of the middle two."
out=$(check); grep -q "^- DEL-2: \*\*Reviewed $day\*\*" $P && grep -q "^LOCKED Delivery: DEL-1 was reviewed and its wording or sub-bullets changed" <<<"$out" && grep -q "^LOCKED Delivery: DEL-2 was reviewed" <<<"$out" && ! grep -q "^CRITERION" <<<"$out" && ok "DOC-7 a requirement under either group is read, and adding a sub-bullet to a reviewed one is LOCKED" || bad "stamp: $out"
$cri unreview DEL-1 DEL-2 --user | grep -c "^UNREVIEWED DEL-" | grep -q 2 && grep -q "^- DEL-2: \*\*Unreviewed\*\* It answers quickly.$" $P && grep -q "^  - A long list takes longer.$" $P && ok "DOC-7 review and unreview work on a page with sub-bullets and keep them" || bad "unreview"; reset
$cri review Delivery --user >/dev/null; edit $P "  - It prints within a second for a short list." "  - It prints within two seconds for a short list."
has "^LOCKED Delivery: the reviewed PRD changed in Requirements" && ok "DOC-7 a sub-bullet change on a reviewed PRD is LOCKED by its fingerprint" || bad "prd seal"; reset

echo "== DOC-7 every reader skips sub-bullets, group headings and None"
edit $P "- No charts." "- No charts.
- This page has 3 criteria."; has "^COUNT docs/wiki/Delivery.md: says 3 criteria, the repo has 2$" && ok "DOC-7 the counts reader counts both groups' requirements and nothing else" || bad "counting"; reset
ids=$(python3 - "$here" <<'PY'
import os, sys
here = sys.argv[1]
for sub in ("workflow-regression", "workflow-health", "workflow-docs"):
    sys.path.insert(0, os.path.join(here, "skills", sub, "scripts"))
import tests, judge, criteria, audit
want = ["DEL-1", "DEL-2"]
parts = dict(criteria.sections(open("docs/wiki/Delivery.md").read()))
got = [sorted(tests.features(".")[1]), sorted(i for i, _ in judge.criteria(".", "Delivery")),
       sorted(m.group(1) for _, m in criteria.criteria_of(parts["Requirements"]) if m)]
print(all(g == want for g in got) and not [l for l, m in criteria.criteria_of(parts["Requirements"]) if not m], got)
PY
)
grep -q "^True" <<<"$ids" && ok "DOC-7 tests, judge and the page parser read the same two requirements" || bad "readers: $ids"
$prd new Billing "Owners want cards charged once a month." --paths calc.py >/dev/null
grep -q "^### Functional$" docs/wiki/Billing.md && grep -q "^### Non-functional$" docs/wiki/Billing.md && grep -q "^None$" docs/wiki/Billing.md && grep -q "^  - " docs/wiki/Billing.md && ok "DOC-7 prd new drafts both groups and a sub-bullet" || bad "prd new: $(cat docs/wiki/Billing.md)"; reset

echo "== DOC-8 Problem"
for pair in "script|a script word" "/usr/local/|a path" "calc.py|a file extension" "\`median\`|a backtick"; do
  IFS='|' read -r word name <<<"$pair"
  edit $P "without working it out by hand." "without working it out by hand, via $word."
  has "^FORMAT Delivery:[0-9]*: Problem: DOC-8 the problem is said without code internals" && ok "DOC-8 a Problem with $name fails naming the page, Problem and DOC-8" || bad "problem $name"; reset
done
edit $P "- I want the median of my numbers" "- Owners want the median of their numbers"; has "^FORMAT Delivery:[0-9]*: Problem: DOC-8 at least one bullet in the first person" && ok "DOC-8 a Problem not in the first person fails" || bad "problem person"; reset
edit $P "without working it out by hand." "without working it out by hand.
- Two.
- Three.
- Four."; has "^FORMAT Delivery:[0-9]*: Problem: DOC-8 1 to 3 bullets (got 4 lines)" && ok "DOC-8 a Problem over problem_lines bullets fails" || bad "problem lines"; reset
check | grep -q "Problem: DOC-8" && bad "good problem" || ok "DOC-8 a first-person Problem with no code passes"
python3 -X dev -W always::ResourceWarning "$here/skills/workflow-docs/scripts/docs.py" check 2>&1 | grep -q ResourceWarning && bad "unclosed files" || ok "docs check closes every file it opens"
edit $P "without working it out by hand." "without working it out by hand, via scripts."; has "^FORMAT Delivery:[0-9]*: Problem: DOC-8 the problem is said without code internals (got 'script')" && ok "DOC-8 a Problem with a banned word in the plural fails" || bad "problem plural"; reset
edit $P "<!-- workflow-docs -->" "<!-- workflow-docs -->
<!-- workflow-docs guide -->"; has "^FORMAT Delivery: DOC-1 a guide page holds no requirement or Review line (got 'Review: " && ok "DOC-1 the guide marker on a page with requirement or Review lines is refused naming the page" || bad "guide marker: $(check)"; reset

echo "== DOC-9 Tests table"
grep -qxF "| [del-1a](Tests#t-del-1a) | requirement | DEL-1 | Given 1 2 3, when the median is asked, then it prints 2. | PASS $day |" $P && head -n 99 $P | grep -qxF "| Test | Kind | Guards | Checks | Last result |" && ok "DOC-9 render writes one Tests table with the test link, kind, guards, checks and last result" || bad "table: $(sed -n '/^## Tests/,$p' $P)"
edit $P "| PASS $day |" "| FAIL $day |"; has "^TESTS Delivery:[0-9]*: Tests: DOC-9 the table differs from a fresh render (got .*). Fix: /workflow-docs render" && ok "DOC-9 a hand-edited Tests table fails naming the page, Tests and DOC-9" || bad "tests stale"; reset
printf 'dup.x\tland\ttrue\tDEL-1\t\tGiven a, when b, then c.\tcriterion\t\ndup-x\tland\ttrue\tDEL-1\t\tGiven a, when b, then c.\tcriterion\t\n' >> .loop/regression.tsv
$cri render 2>&1 | grep -q "^REFUSED: two rows would share one Tests anchor: dup.x and dup-x share t-dup-x" && has "^FORMAT Tests:1: Tests: DOC-9 one anchor per row" && ok "DOC-9 two rows sharing an anchor are refused" || bad "dup slug"; reset

echo "== DOC-10 the full Tests page"
head -2 $T | tr '\n' '~' | grep -q "^<!-- workflow-docs -->~# Tests~$" && grep -qxF "## Delivery" $T && grep -qxF "| Test | Kind | Guards | Result | Date | Run | Seen failing |" $T && ok "DOC-10 render writes the full Tests page grouped by feature" || bad "tests page: $(cat $T)"
grep -q '^| <a id="t-del-1a"></a>del-1a | requirement | DEL-1 | PASS | '"$day"' | ' $T && grep -q "(Tests#t-del-1a)" $P && ok "DOC-10 each feature's Tests row links an anchor on the full Tests page" || bad "anchor"
check | grep -q "^UNMAPPED Tests\|^STALE Tests" && bad "fresh tests page" || ok "DOC-10 a fresh Tests page is neither unmapped nor stale"
edit $T "## Delivery" "## Delivered"; has "^STALE Tests: line [0-9]* is '## Delivered', a fresh render has '## Delivery'. Fix: /workflow-docs render" && ok "DOC-10 a stale Tests page is reported with its first differing line" || bad "tests page stale"; reset
rm $T; has "^STALE Tests: no docs/wiki/Tests.md. Fix: /workflow-docs render" && ok "DOC-10 a missing Tests page is reported" || bad "tests page missing"
out=$($cri render); grep -qxF "WROTE docs/wiki/Tests.md" <<<"$out" && [ "$($cri render)" = "TABLES OK" ] && [ -z "$(git status --porcelain docs)" ] && ok "DOC-10 render writes each file with WROTE and a second render changes nothing" || bad "idempotent: $out"
printf '# id\tstatus\tdate\ndel-1a\tPASS\t%s\ndel-2a\tPASS\t%s\n' "$day" "$day" > .loop/regression-runs.tsv; $cri render >/dev/null
grep -q '^| <a id="t-del-1a"></a>del-1a | .* | local | ' $T && ok "DOC-10 a 3-column runs file shows the run as local" || bad "3 columns: $(grep del-1a $T)"
printf '# id\tstatus\tdate\trun\ndel-1a\tPASS\t%s\thttps://github.com/toy/repo/actions/runs/42\ndel-2a\tPASS\t%s\t\n' "$day" "$day" > .loop/regression-runs.tsv
git remote set-url origin https://github.com/toy/repo.git; $cri render >/dev/null; git remote set-url origin "$d/origin.git"
grep -qF "| [run](https://github.com/toy/repo/actions/runs/42) |" $T && grep -qF "| [CI $day](https://github.com/toy/repo/actions/workflows/regression.yml?query=created%3A$day) |" $T && ok "DOC-10 a 4-column runs file links the Actions run, or for an empty cell that day's CI runs" || bad "4 columns: $(grep 'del-' $T)"; reset

echo "== DOC-1 the cap default is 10 in criteria and setup"
python3 - "$here" <<'PY' && ok "DOC-1 the cap default of 10 is the same in criteria and setup" || bad "cap default"
import os, sys
sys.path[:0] = [os.path.join(sys.argv[1], "skills", s, "scripts") for s in ("workflow-docs", "workflow-setup")]
import criteria, settings
setup = next(default for key, _, default, _ in settings.TABLE if key == "criteria_max")
assert criteria.CRITERIA_MAX_DEFAULT == setup == 10 == criteria.criteria_max("."), (criteria.CRITERIA_MAX_DEFAULT, setup)
PY

echo "== the format key in the rules block chooses the checks"
mkdir -p "$d/sk"; cp -R "$here/skills" "$d/sk/"; sk="python3 $d/sk/skills/workflow-docs/scripts/docs.py"
sed -i.bak 's/^format: .*/format: home, frontdoor, usage, bullets, tests/' "$d/sk/skills/workflow-docs/references/template.md"
edit $P "- I want the median of my numbers" "- Owners want the median of their numbers"
$docs check | grep -q "Problem: DOC-8" && ! $sk check | grep -q "Problem: DOC-8" && ok "the format key without problem turns DOC-8 off" || bad "format key"; reset
sed -i.bak 's/^format: .*/format: home, nosuch/' "$d/sk/skills/workflow-docs/references/template.md"
$sk check 2>&1 | grep -q "REFUSED: the rules block" && ok "an unknown name in the format key refuses" || bad "format unknown"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
