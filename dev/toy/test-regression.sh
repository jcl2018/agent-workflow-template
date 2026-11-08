#!/bin/bash
# Test workflow-regression on a throwaway toy repo with a fake gh. usage: test-regression.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
calls() { grep -c "$1" "$FAKE_GH_DIR/calls.log" 2>/dev/null; }

echo "== seed, and an unproven row blocks"
$reg seed
grep -q "^check-1" .loop/regression.tsv && ok "seeded a row" || bad "seed"
git add -A; git commit -qm "Rows"
out=$($reg run land); rc=$?; echo "$out"
[ $rc = 1 ] && grep -q "^UNPROVEN check-1" <<<"$out" && ok "unproven row blocks" || bad "unproven"
grep -q "^WOULD" <<<"$out" && [ ! -e "$FAKE_GH_DIR/calls.log" ] && ok "no token: dry run, no gh call" || bad "dry run"

echo "== red proves a test can fail, on a copy"
sum=$(git status --porcelain calc.py)
$reg red check-1 --break "echo 'import nothing_here' > calc.py" && ok "red recorded" || bad "red"
[ -n "$(awk -F'\t' '$1=="check-1"{print $5}' .loop/regression.tsv)" ] && ok "date in the row" || bad "date"
[ "$(git status --porcelain calc.py)" = "$sum" ] && ok "own checkout untouched" || bad "checkout touched"
$reg add always --level nightly --command "true"
$reg red always --break "true"; [ $? = 1 ] && ok "a test that can't fail stays unproven" || bad "still green"
$reg add always --level covered --command "proved by check-1"

echo "== pass, then fail opens one issue, then pass closes it"
$reg run land | tee "$d/o1"; [ "${PIPESTATUS[0]}" = 0 ] && ok "green run" || bad "green run"
$reg add flag --level land --command "test ! -e BROKEN"
$reg red flag --break "touch BROKEN" >/dev/null && ok "flag proven" || bad "flag proven"
touch BROKEN
$reg run land --live > "$d/o2"; rc=$?; cat "$d/o2"
[ $rc = 1 ] && [ "$(calls '^issue create')" = 1 ] && ok "failure opened an issue" || bad "open"
export FAKE_GH_ISSUE_OPEN=1
$reg run land --live > "$d/o3"; [ "$(calls '^issue create')" = 1 ] && [ "$(calls '^issue comment')" = 1 ] && ok "second failure comments, no new issue" || bad "update"
export FAKE_GH_ISSUE_COMMENTED=1
$reg run land --live > "$d/o3b"; [ "$(calls '^issue comment')" = 1 ] && ok "one comment a day" || bad "one a day"
unset FAKE_GH_ISSUE_COMMENTED
export FAKE_GH_ISSUE_CLOSED=1; unset FAKE_GH_ISSUE_OPEN
$reg run land --live >/dev/null; [ "$(calls '^issue reopen')" = 1 ] && ok "closed issue reopens" || bad "reopen"
unset FAKE_GH_ISSUE_CLOSED; export FAKE_GH_ISSUE_OPEN=1
rm BROKEN
$reg run land --live > "$d/o4"; rc=$?; cat "$d/o4"
[ $rc = 0 ] && [ "$(calls '^issue close')" = 1 ] && ok "pass closed the issue" || bad "close"
unset FAKE_GH_ISSUE_OPEN

echo "== known failure doesn't block, and fixed is reported"
touch BROKEN
printf 'flag\tWaiting on a vendor fix\n' > .loop/regression-known.tsv
before=$(calls '^issue create')
out=$($reg run land --live); rc=$?; echo "$out"
[ $rc = 0 ] && grep -q "^KNOWN flag" <<<"$out" && [ "$(calls '^issue create')" = "$before" ] && ok "known doesn't block or open an issue" || bad "known"
rm BROKEN
$reg run flag | grep -q "^FIXED flag" && ok "fixed reported" || bad "fixed"
rm .loop/regression-known.tsv

echo "== sync finds gaps and drafts rows"
mkdir -p .loop/goals
cat > .loop/goals/add-median.md <<'G'
# Add median

## Done lines

Frozen.

1. median works
2. docs say so

## Plan
G
$reg sync > "$d/o5"; rc=$?; cat "$d/o5"
[ $rc = 1 ] && [ "$(grep -c '^GAP' "$d/o5")" = 2 ] && ok "two gaps" || bad "gaps"
$reg sync --write >/dev/null
grep -q "add-median-1.*draft" .loop/regression.tsv && ok "draft written" || bad "draft"
$reg run nightly | grep -q add-median && bad "ran a draft" || ok "drafts don't run"
$reg add add-median-1 --level land --command "test -e calc.py" --goal add-median:1
$reg add add-median-2 --level covered --command "read by a person" --goal add-median:2
git add -A; git commit -qm "Rows for the goal"
$reg red add-median-1 --break "rm calc.py" >/dev/null
$reg sync | grep -q "^NODESC add-median-1" && ok "sync flags a row with no description" || bad "no-description flag"
$reg add check-1 --level land --command "$(awk -F'\t' '$1=="check-1"{print $3}' .loop/regression.tsv)" --describe "The toy calculator still runs." >/dev/null
$reg add flag --level land --command "test ! -e BROKEN" --describe "No BROKEN file exists." >/dev/null
$reg add add-median-1 --level land --command "test -e calc.py" --goal add-median:1 --describe "calc.py exists." >/dev/null
[ -n "$(awk -F'\t' '$1=="check-1"{print $5}' .loop/regression.tsv)" ] && ok "describing a row keeps its seen-failing date" || bad "date lost"
$reg sync && ok "sync clean" || bad "sync clean"

echo "== the written workflow runs"
$reg workflow
python3 - <<'PY' && ok "workflow keys and inline block are valid" || bad "workflow"
import ast, re
text = open(".github/workflows/regression.yml").read()
assert "issues: write" in text and "workflow_dispatch" in text and text.startswith("# Written by workflow-regression")
block = re.search(r"python3 - <<'PY'\n(.*?)\n\s+PY\n", text, re.S).group(1)
block = "\n".join(line[10:] for line in block.split("\n"))
ast.parse(block)
open("ci-block.py", "w").write(block)
PY
python3 -c 'import yaml; yaml.safe_load(open(".github/workflows/regression.yml")); print("yaml ok")' 2>/dev/null || echo "NOTE: PyYAML not installed, YAML not parsed"
: > "$FAKE_GH_DIR/calls.log"
touch BROKEN; git add -A; git commit -qm "Break it" >/dev/null
python3 ci-block.py; rc=$?
[ $rc = 1 ] && [ "$(calls '^issue create')" = 1 ] && ok "CI block fails and opens an issue" || bad "CI block"
rm -f BROKEN ci-block.py
grep -q 'cron: "17 9 \* \* \*"' .github/workflows/regression.yml && ok "default schedule written" || bad "default cron"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["regression_cron"] = "5 4 * * 1"
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
$reg workflow >/dev/null; grep -q 'cron: "5 4 \* \* 1"' .github/workflows/regression.yml && ! grep -q '17 9' .github/workflows/regression.yml && ok "changing regression_cron changes the schedule" || bad "cron setting"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["regression_cron"] = "nightly"
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
$reg workflow >/dev/null 2>&1 && bad "bad cron written" || ok "a setting that is not five cron fields is refused"
echo "other" > .github/workflows/regression.yml
$reg workflow >/dev/null 2>&1 && bad "replaced another workflow" || ok "won't replace another workflow"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
