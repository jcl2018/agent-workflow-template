#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-health/scripts/health.py
# reads: skills/workflow-health/scripts/milestone.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-health/scripts/
# Test feature milestones and health run on a throwaway toy repo with a fake gh. usage: test-milestones.sh [DIR]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
ms="python3 $here/skills/workflow-health/scripts/milestone.py"
health="python3 $here/skills/workflow-health/scripts/health.py"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
printf 'Calc\tcalc.py\nHome\tREADME.md\n' > .loop/docs.tsv
mkdir -p docs/wiki; printf '<!-- workflow-docs -->\n# Calc\n' > docs/wiki/Calc.md
git add -A; git commit -qm "Map the Calc page"; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
calls() { grep -c "$1" "$FAKE_GH_DIR/calls.log" 2>/dev/null || true; }
mkdir -p "$FAKE_GH_DIR"

echo "== milestones: one per feature and a Backlog, created once"
out=$($ms new --all); echo "$out"
grep -q "^WOULD create milestone Calc" <<<"$out" && grep -q "^WOULD create milestone Backlog" <<<"$out" && ! grep -q "Home" <<<"$out" \
  && [ ! -f "$FAKE_GH_DIR/milestones.json" ] && ok "without --live it only prints WOULD lines, and Home is no feature" || bad "dry run"
out=$($ms new --all --live); echo "$out"
[ "$(grep -c '^CREATED' <<<"$out")" = 2 ] && ok "one milestone per feature page, plus Backlog" || bad "created"
out=$($ms new --all --live); echo "$out"
[ "$(grep -c '^EXISTS' <<<"$out")" = 2 ] && ! grep -q '^CREATED' <<<"$out" && [ "$(calls 'milestones -f title')" = 2 ] && ok "running it again creates nothing" || bad "idempotent"
$ms new nothing --live 2>&1 | grep -q "REFUSED: 'nothing' is not a feature" && ok "an unknown feature is refused" || bad "unknown feature"

echo "== attach: a goal's pull request joins its feature's milestone"
$goal new calc-goal --here --goal "Change calc" --done "calc changes" --touches "calc.py" >/dev/null
echo "# change" >> calc.py; git commit -qam "Change calc"
python3 - <<'PYEND'
p = ".loop/goals/calc-goal.md"
t = open(p).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: the change.\n", 1)
open(p, "w").write(t)
PYEND
git commit -qam "Verify steps"
bash "$here/dev/toy/flow-done.sh" calc-goal; out=$($goal pr calc-goal); echo "$out"
grep -q "ATTACHED pull request 1 to milestone Calc" <<<"$out" && [ "$(cat "$FAKE_GH_DIR/pr-milestone-1")" = Calc ] && ok "goal.py pr puts the pull request in the Calc milestone" || bad "attach"
$goal new other-goal --here --goal "Other" --done "x" --touches "elsewhere.txt" >/dev/null 2>&1 || true
out=$($ms attach other-goal 2>&1); grep -q "REFUSED: other-goal has no pull request" <<<"$out" && ok "no pull request, no attach" || bad "attach no pr"

echo "== health file: one issue per finding on the Backlog"
git switch -q main
mkdir -p skills/x/scripts; python3 -c "print('# pad\n' * 3400)" > skills/x/scripts/near.py
git add -A; git commit -qm "A near-limit script"
out=$($health preview --group size); echo "$out"
grep -q "^WOULD open issue 'health: size skills/x/scripts/near.py limit' on Backlog \[health:size\]" <<<"$out" && [ ! -f "$FAKE_GH_DIR/issues.json" ] \
  && ok "preview: only WOULD lines, nothing written" || bad "run dry"
out=$($health file --group size); echo "$out"
python3 - <<'PYEND' && ok "file: one issue on Backlog, labelled, with the hidden marker" || bad "issue created"
import json, os
issues = json.load(open(os.environ["FAKE_GH_DIR"] + "/issues.json"))
assert len(issues) == 1 and issues[0]["milestone"]["title"] == "Backlog"
assert "<!-- loop-health size:skills/x/scripts/near.py:limit placed=Backlog -->" in issues[0]["body"]
PYEND
grep -q -e "--label health --label health:size --milestone Backlog" "$FAKE_GH_DIR/calls.log" && ok "labelled health and health:size" || bad "label"
out=$($health file --group size); echo "$out"
grep -q "^SAME #1" <<<"$out" && [ "$(python3 -c "import json,os;print(len(json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json'))))")" = 1 ] && ok "a repeat opens no second issue" || bad "duplicate"
python3 -c "print('# pad\n' * 3500)" > skills/x/scripts/near.py; git commit -qam "Bigger"
out=$($health file --group size); echo "$out"
grep -q "^DONE update #1" <<<"$out" && ok "a changed finding updates its issue" || bad "update"

echo "== moved issues stay moved"
$ms move 1 calc --live | grep -q "^MOVED issue 1 to milestone Calc" && ok "move puts the issue in the feature's milestone" || bad "move"
python3 -c "print('# pad\n' * 3600)" > skills/x/scripts/near.py; git commit -qam "Bigger again"
out=$($health file --group size); echo "$out"
python3 - <<'PYEND' && ok "a later run updates the issue where it is, and opens no other" || bad "moved"
import json, os
issues = json.load(open(os.environ["FAKE_GH_DIR"] + "/issues.json"))
assert len(issues) == 1 and issues[0]["milestone"]["title"] == "Calc" and "%d bytes" in "%d bytes", issues
PYEND

echo "== fixed closes, returning reopens"
git rm -q skills/x/scripts/near.py; git commit -qm "Remove it"
out=$($health file --group size); echo "$out"
grep -q "^DONE close #1 size:skills/x/scripts/near.py:limit" <<<"$out" && grep -q '"state": "CLOSED"' "$FAKE_GH_DIR/issues.json" && ok "a fixed finding closes its issue" || bad "close"
mkdir -p skills/x/scripts; python3 -c "print('# pad\n' * 3600)" > skills/x/scripts/near.py; git add -A; git commit -qm "Back again"
out=$($health file --group size); echo "$out"
grep -q "^DONE reopen #1" <<<"$out" && grep -q '"state": "OPEN"' "$FAKE_GH_DIR/issues.json" && [ "$(python3 -c "import json,os;print(len(json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json'))))")" = 1 ] \
  && ok "a returning finding reopens the same issue" || bad "reopen"
grep -Eq "^(release |pr merge|api .*-X)|draft=false" "$FAKE_GH_DIR/calls.log" && bad "publish or merge call" || ok "no release or merge call"

echo "== a group run or an unread rule closes nothing it did not check"
out=$($health file --group criteria,docs,hygiene,performance); echo "$out" | grep -c "^DONE" 
open_other=$(python3 -c "import json,os;print(sorted(i['number'] for i in json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json')) if i['state']=='OPEN' and 'size:' not in i['body']))")
[ "$open_other" != "[]" ] && ok "other families have open issues: $open_other" || bad "no other issues to guard"
git rm -q skills/x/scripts/near.py; git commit -qm "Remove it again"
$health file --group size >/dev/null
still=$(python3 -c "import json,os;print(sorted(i['number'] for i in json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json')) if i['state']=='OPEN' and 'size:' not in i['body']))")
[ "$still" = "$open_other" ] && grep -q '"number": 1, .*"state": "CLOSED"' "$FAKE_GH_DIR/issues.json" && ok "file --group size closed only the size issue" || bad "family close: $still"
lone=$(mktemp -d); cp "$here/skills/workflow-health/scripts/health.py" "$lone/"
python3 "$lone/health.py" file --group size,criteria,docs 2>&1 | grep -q "^REFUSED: file.py is not installed" && ok "a lone health.py refuses to file" || bad "lone file"
# Value: protects=a group whose rule cannot read its data closes none of its issues on file; fails_when=plan() stops
#   taking unread groups out of the ones that ran; why_new=the lone health.py above now refuses before plan(), so it no
#   longer reaches the guard; seam=none; no_claim=real GitHub issue state (fake gh; toy repo)
lone="$lone/skills/workflow-health"; mkdir -p "$lone"; cp -R "$here/skills/workflow-health/scripts" "$lone/"  # no sibling skills: criteria and docs cannot read
python3 "$lone/scripts/health.py" file --group size,criteria,docs >/dev/null 2>&1
still=$(python3 -c "import json,os;print(sorted(i['number'] for i in json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json')) if i['state']=='OPEN' and 'size:' not in i['body'] and i['number'] in $open_other))")
[ "$still" = "$open_other" ] && ok "a rule that could not read closes none of its issues" || bad "unread close: $still"

echo "== sizes"
for f in milestone.py health.py; do
  [ "$(wc -c < "$here/skills/workflow-health/scripts/$f")" -lt 20480 ] && ok "$f under 20 KB" || bad "$f size"
done
[ "$(wc -c < "$here/skills/workflow-delivery/scripts/goal.py")" -lt 20480 ] && ok "goal.py under 20 KB" || bad "goal.py size"

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
