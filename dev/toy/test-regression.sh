#!/bin/bash
# reads: skills/workflow-docs/scripts/audit.py skills/workflow-docs/scripts/criteria.py
# reads: skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/prd.py
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-setup/scripts/setup.py
# Test workflow-regression on a throwaway toy repo with a fake gh. usage: test-regression.sh [DIR]
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN GITHUB_STEP_SUMMARY GITHUB_ENV GITHUB_OUTPUT GITHUB_PATH GITHUB_STATE  # a toy test never writes to a real run summary (issue 92)
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
calls() { grep -c "$1" "$FAKE_GH_DIR/calls.log" 2>/dev/null; }

echo "== add, and an unproven row blocks"
$reg add check-1 --level land --command "python3 -m unittest discover" >/dev/null
grep -q "^check-1" .loop/regression.tsv && ok "added a row" || bad "add"
git add -A; git commit -qm "Rows"
out=$($reg run land); rc=$?; echo "$out"
[ $rc = 1 ] && grep -q "^UNPROVEN check-1" <<<"$out" && ok "unproven row blocks" || bad "unproven"
grep -q "^WOULD" <<<"$out" && [ ! -e "$FAKE_GH_DIR/calls.log" ] && ok "no token: dry run, no gh call" || bad "dry run"
printf 'dash-1\tland\ttrue\tREG-9\t-\tA row dated with a dash.\tcriterion\t\n' >> .loop/regression.tsv
printf 'text-1\tland\ttrue\tREG-9\tn/a\tA row dated with words.\tcriterion\t\n' >> .loop/regression.tsv
$reg sync | grep -q "^UNPROVEN dash-1" && $reg run dash-1 | grep -q "^UNPROVEN dash-1" && ok "a seen-failing date of - is unproven" || bad "a - date counted as seen failing"
$reg sync | grep -q "^UNPROVEN text-1" && ok "a seen-failing value that is not a date is unproven" || bad "a non-date counted as seen failing"
python3 - "$here/skills/workflow-docs/scripts" <<'PY' && ok "the Tests table shows no for a - or a non-date" || bad "Tests table shows a non-date as seen failing"
import sys; sys.dont_write_bytecode = True; sys.path.insert(0, sys.argv[1]); import render
out = render.tests_page(".").splitlines()
cells = [line.split(" | ")[-1].rstrip(" |") for line in out if 'id="t-dash-1"' in line or 'id="t-text-1"' in line]
assert cells == ["no", "no"], out
PY
sed -i.bak '/^dash-1	/d; /^text-1	/d' .loop/regression.tsv; rm -f .loop/regression.tsv.bak

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
mkdir -p "$(git rev-parse --git-common-dir)/loop/runs"; echo '{"status": "running"}' > "$(git rev-parse --git-common-dir)/loop/runs/add-median.json"  # done lines count while the goal runs (issue 143)
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
# Value: protects=a regression issue goes on Backlog when the repo has that milestone, and carries no flag when it has
#   none; fails_when=the CI block drops the --milestone flag or always adds it; why_new=no test had a Backlog milestone
nomile=$(grep -c -- '--milestone' "$FAKE_GH_DIR/calls.log"); : > "$FAKE_GH_DIR/calls.log"; echo '[{"number": 1, "title": "Backlog", "state": "open"}]' > "$FAKE_GH_DIR/milestones.json"
python3 ci-block.py >/dev/null 2>&1; [ "$nomile" = 0 ] && [ "$(calls '^issue create')" = 1 ] && grep -q -- "--milestone Backlog$" "$FAKE_GH_DIR/calls.log" \
  && ok "the CI block opens a regression issue on Backlog when it exists, with no milestone flag otherwise" || bad "backlog milestone: $nomile"
rm -f "$FAKE_GH_DIR/milestones.json" "$FAKE_GH_DIR/issues.json"
nap="31.$((RANDOM % 9000 + 1000))"  # a sleep no other run on this machine uses
printf 'hang\tland\techo started-hang; sleep %s & sleep %s\t-\t2026-01-01\tA row that hangs.\tcriterion\t\n' "$nap" "$nap" >> .loop/regression.tsv
printf 'own-124\tland\techo own-exit; exit 124\t-\t2026-01-01\tA row that exits 124 itself.\tcriterion\t\n' >> .loop/regression.tsv
printf 'no-token\tland\ttest -z "$GH_TOKEN$GITHUB_TOKEN"\t-\t2026-01-01\tA row checks it cannot see the token.\tcriterion\t\n' >> .loop/regression.tsv
# Generated by /ship coverage audit. Value: protects=a failing row's output cannot close the issue body's code fence early;
#   fails_when=the ``` to ''' replacement is dropped; why_new=no row above prints a fence; seam=none; no_claim=how GitHub renders the body
printf 'fence\tland\techo fence-out$(printf "\\140\\140\\140"); exit 1\t-\t2026-01-01\tA row prints a code fence.\tcriterion\t\n' >> .loop/regression.tsv
: > "$FAKE_GH_DIR/calls.log"
# Generated by /ship coverage audit. Value: protects=rows see neither GH_TOKEN nor GITHUB_TOKEN; fails_when=GITHUB_TOKEN is
#   dropped from the removed names; why_new=the no-token row ran with only GH_TOKEN set; seam=none; no_claim=other secrets in the job env
began=$(date +%s); GH_TOKEN=fake-token GITHUB_TOKEN=fake-token-2 REGRESSION_ROW_SECONDS=2 REGRESSION_RESULTS="$d/results.tsv" python3 ci-block.py >/dev/null 2>&1; took=$(( $(date +%s) - began ))
[ "$took" -lt 25 ] && grep -q "^hang	FAIL$" "$d/results.tsv" && grep -q "timed out after 2 s" "$FAKE_GH_DIR/calls.log" && ok "a row that times out fails alone, and the run goes on" || bad "row timeout (took ${took}s)"
grep -q "started-hang" "$FAKE_GH_DIR/calls.log" && ok "a row that times out keeps what it printed" || bad "a timed-out row lost its output"
sleep 0.5; ! pgrep -f "sleep $nap" >/dev/null && ok "a timed-out row leaves no process behind" || { bad "a timed-out row left a process"; pkill -f "sleep $nap"; }
grep -q "own-exit" "$FAKE_GH_DIR/calls.log" && ! grep -A3 "own-exit" "$FAKE_GH_DIR/calls.log" | grep -q "timed out" && ok "a row that exits 124 itself is not called a timeout" || bad "own exit 124 called a timeout"
grep -q "^no-token	PASS$" "$d/results.tsv" && ok "a row cannot see the job's token" || bad "a row saw the token"
grep -q "fence-out'''" "$FAKE_GH_DIR/calls.log" && ! grep -q 'fence-out```' "$FAKE_GH_DIR/calls.log" && ok "a row's code fence is escaped in the issue body" || bad "a row's code fence reached the issue body"
: > "$d/results2.tsv"
: > "$FAKE_GH_DIR/calls.log"
FAKE_GH_ISSUE_OPEN=1 REGRESSION_JOB_SECONDS=1 REGRESSION_RESULTS="$d/results2.tsv" python3 ci-block.py >/dev/null 2>&1; rc=$?
[ $rc = 1 ] && grep -q "^own-124	SKIPPED$" "$d/results2.tsv" && ! grep -q "	PASS$" "$d/results2.tsv" && grep -q "was skipped" "$FAKE_GH_DIR/calls.log" && ok "rows that would pass the job budget are skipped, fail, and open an issue" || bad "job budget skip"
grep -q "^issue comment 7 --body Skipped: out of job time" "$FAKE_GH_DIR/calls.log" && ! grep -q "Still failing" "$FAKE_GH_DIR/calls.log" && ok "a skipped row with an open issue says it was skipped, not still failing" || bad "a skipped row was called still failing"
grep -A2 "actions/checkout@v4" .github/workflows/regression.yml | grep -q "persist-credentials: false" && ok "the checkout leaves no token in git config" || bad "the checkout keeps the token where a row can read it"
REGRESSION_ROW_SECONDS=zero REGRESSION_JOB_SECONDS=-5 REGRESSION_RESULTS="$d/results3.tsv" timeout 120 python3 -c "exec(open('ci-block.py').read().replace('run(row[2])', '(0, \"\")'))" >/dev/null 2>&1
grep -q "^own-124	PASS$" "$d/results3.tsv" && ok "a bad time setting falls back to the default" || bad "bad time setting"
sed -i.bak '/^hang	/d; /^own-124	/d; /^no-token	/d; /^fence	/d' .loop/regression.tsv; rm -f .loop/regression.tsv.bak
rm -f BROKEN ci-block.py
# Generated by /ship coverage audit. Value: protects=this repo's committed regression.yml is what actions.py writes;
#   fails_when=actions.py or the workflow file is changed without the other; why_new=the toy repo only ever runs a freshly written file;
#   seam=none; no_claim=that GitHub Actions accepts the file (no live run)
python3 - "$here" <<'PY' && ok "the committed regression workflow matches what actions.py writes" || bad "the committed regression workflow is stale"
import json, sys
sys.path.insert(0, sys.argv[1] + "/skills/workflow-regression/scripts"); import actions
cron = json.load(open(sys.argv[1] + "/.loop/config.json")).get("regression_cron") or "17 */4 * * *"
assert actions.render(cron) == open(sys.argv[1] + "/.github/workflows/regression.yml").read()
PY
grep -q 'cron: "17 \*/4 \* \* \*"' .github/workflows/regression.yml && ok "default schedule written" || bad "default cron"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["regression_cron"] = "5 4 * * 1"
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
$reg workflow >/dev/null; grep -q 'cron: "5 4 \* \* 1"' .github/workflows/regression.yml && ! grep -q 'cron: "17 \*/4' .github/workflows/regression.yml && ok "changing regression_cron changes the schedule" || bad "cron setting"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["regression_cron"] = "nightly"
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
$reg workflow >/dev/null 2>&1 && bad "bad cron written" || ok "a setting that is not five cron fields is refused"
echo "== the workflow and a local run do the same (REG-3)"
python3 - <<'PY'
import json
c = json.load(open(".loop/config.json")); c["regression_cron"] = "17 */4 * * *"
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
$reg workflow >/dev/null
python3 - <<'PY'
import re
text = open(".github/workflows/regression.yml").read()
block = re.search(r"python3 - <<'PY'\n(.*?)\n\s+PY\n", text, re.S).group(1)
open("ci-block.py", "w").write("\n".join(line[10:] for line in block.split("\n")))
PY
agree() { # agree NAME: the local run and the workflow's block end the same way and open the same issues
  : > .loop/regression-known.tsv; printf 'known-row\tbroken on purpose\n' >> .loop/regression-known.tsv
  rm -f "$FAKE_GH_DIR/calls.log"; GH_TOKEN=x $reg run nightly >/dev/null; local_rc=$?; local_new=$(calls '^issue create')
  rm -f "$FAKE_GH_DIR/calls.log"; GH_TOKEN=x GITHUB_STEP_SUMMARY=/dev/null python3 ci-block.py >/dev/null; ci_rc=$?; ci_new=$(calls '^issue create')
  [ "$local_rc" = "$ci_rc" ] && [ "${local_new:-0}" = "${ci_new:-0}" ] && ok "$1: same exit ($ci_rc) and same issues opened ($ci_new)" || bad "$1: local $local_rc/$local_new, workflow $ci_rc/$ci_new"
}
row() { printf '%s\t%s\t%s\t-\t2026-01-01\tx\tcriterion\t\n' "$1" nightly "$2" >> .loop/regression.tsv; }
printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
row good-row true; row known-row false
agree "passing and known rows"
row bad-row false
agree "a failing row"
rm -f ci-block.py; git checkout -q .loop/regression.tsv .loop/regression-known.tsv 2>/dev/null; git clean -fdq .loop 2>/dev/null
echo "other" > .github/workflows/regression.yml
$reg workflow >/dev/null 2>&1 && bad "replaced another workflow" || ok "won't replace another workflow"

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
