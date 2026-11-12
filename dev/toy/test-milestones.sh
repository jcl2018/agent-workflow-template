#!/bin/bash
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-health/scripts/health.py
# reads: skills/workflow-health/scripts/milestone.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-health/scripts/
# Test that milestones are optional and free form (owner commands, none per feature, none on a pull request or an issue
# health files), the feature tag behind its switch, and that setup asks for none, on a toy repo with a fake gh. usage: test-milestones.sh [DIR]
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
setup_out=$(python3 "$here/skills/workflow-setup/scripts/setup.py" --bare 2>&1)
git switch -q main; git merge -q --no-edit workflow-setup
printf 'Calc\tskills/x\nHome\tREADME.md\n' > .loop/docs.tsv
mkdir -p docs/wiki; printf '<!-- workflow-docs -->\n# Calc\n' > docs/wiki/Calc.md
git add -A; git commit -qm "Map the Calc page"; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
calls() { grep -c "$1" "$FAKE_GH_DIR/calls.log" 2>/dev/null || true; }
mkdir -p "$FAKE_GH_DIR"

echo "== setup asks for no milestone"
f0=$fails
! grep -qi "milestone" <<<"$setup_out" && ! git ls-files | xargs grep -li "milestone" 2>/dev/null | grep -q . && ok "setup's plan, NEXT line and files mention no milestone" || bad "setup mentions a milestone: $setup_out"
grep -q "^NEXT: review the branch, then merge it into main$" <<<"$setup_out" && ok "setup's NEXT line is only to review and merge" || bad "setup NEXT: $setup_out"
[ "$fails" = "$f0" ] && echo "PASS milestone-freeform:setup-no-milestone-step"

echo "== milestone.py: free form, named by the owner, created once"
f0=$fails
out=$($ms new v1.0); echo "$out"
[ "$out" = "WOULD create milestone v1.0 (dry run; add --live)" ] && [ ! -f "$FAKE_GH_DIR/milestones.json" ] && ok "without --live it only prints the WOULD line" || bad "dry run"
out=$($ms new v1.0 --live); echo "$out"
[ "$out" = "CREATED v1.0" ] && ok "new v1.0 --live creates it" || bad "created"
out=$($ms new v1.0 --live); echo "$out"
[ "$out" = "EXISTS v1.0" ] && [ "$(calls 'milestones -f title')" = 1 ] && ok "running it again creates nothing" || bad "idempotent"
[ "$($ms new backlog --live)" = "CREATED backlog" ] && [ "$($ms new Calc --live)" = "CREATED Calc" ] && ok "backlog and a page name are ordinary titles, nothing is refused as not a feature" || bad "ordinary titles"
out=$(FAKE_GH_NO_AUTH=1 $ms new v2.0 --live 2>&1); rc=$?
[ $rc = 1 ] && grep -q "^REFUSED: no GitHub token, nothing created. Fix: set GH_TOKEN or run gh auth login, or drop --live to preview.$" <<<"$out" && ! grep -q "title=v2.0" "$FAKE_GH_DIR/calls.log" && ok "--live with no token refuses with the fix and creates nothing" || bad "no token: $out"
for removed in "new --all" "features" "attach calc-goal"; do
  out=$($ms $removed 2>&1); rc=$?
  [ $rc = 1 ] && [ "$(wc -l <<<"$out" | tr -d ' ')" = 1 ] && grep -q "^REFUSED: .* was removed, milestones are free form. Fix: drop the call.$" <<<"$out" || bad "removed: $removed -> $out"
done
ok "the removed new --all, features and attach each refuse in one line, never a traceback"
out=$(bash -c "$ms new --all --live || echo '::warning::an old workflow step'" 2>&1); rc=$?
[ $rc = 0 ] && grep -q "REFUSED" <<<"$out" && ok "an older workflow's step (milestone.py new --all --live || echo warning) still exits 0" || bad "stale step"
[ "$fails" = "$f0" ] && echo "PASS milestone-freeform:milestones-once"

echo "== v1.0 works as before: an issue on it, grouped by feature, never made a feature by the milestone"
f0=$fails
gh issue create --title "Plan a thing" --label health --body "x" >/dev/null
out=$($ms move 1 v1.0); echo "$out"
grep -q "^WOULD move issue 1 to milestone v1.0 (dry run; add --live)$" <<<"$out" && ok "move without --live only prints" || bad "move dry"
out=$($ms move 1 v1.0 --live); echo "$out"
[ "$out" = "MOVED issue 1 to milestone v1.0" ] && [ "$(python3 -c "import json,os;print(json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json'))[0]['milestone']['title'])")" = v1.0 ] && ok "move puts the issue on the milestone" || bad "move"
out=$($ms move 1 v9 --live 2>&1); rc=$?
[ $rc = 1 ] && grep -q "^REFUSED: no milestone v9 (issue 1 unchanged). Fix: milestone.py new v9 --live$" <<<"$out" && ok "an unknown title refuses, the issue unchanged" || bad "move unknown: $out"
out=$($ms move 1 none --live); [ "$out" = "MOVED issue 1 to no milestone" ] && [ "$(python3 -c "import json,os;print(json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json'))[0]['milestone'])")" = None ] && ok "move to none clears it" || bad "move none"
$ms move 1 v1.0 --live >/dev/null
got=$(python3 - "$here" <<'PY'
import os, sys
sys.path.insert(0, os.path.join(sys.argv[1], "skills", "workflow-health", "scripts"))
import issues as I
pages = {"Calc": ["skills/x"]}
print(I.feature_group({"labels": [], "milestone": "v1.0"}, pages), I.feature_group({"labels": [], "milestone": "Backlog"}, pages),
      I.feature_group({"labels": [], "milestone": None}, pages), I.feature_group({"labels": [], "milestone": "Calc"}, pages),
      I.feature_group({"labels": ["feature:calc"], "milestone": "v1.0"}, pages), I.feature_group({"labels": ["feature:" + "x" * 42], "milestone": None}, {"x" * 50: [], "x" * 49: []}))
PY
)
[ "$got" = "No feature No feature No feature Calc Calc No feature" ] && ok "an issue on v1.0, on Backlog or on none is No feature; a page-named milestone or a feature label groups as that page; two pages sharing a label are No feature" || bad "grouping: $got"
python3 -c "
import sys; sys.path.insert(0, '$here/skills/workflow-health/scripts'); import issues as I
f = lambda n: I.feature_label('p' * n)
assert len(f(42)) == 50 and len(f(43)) == 50 and f(42) == f(43), (len(f(42)), len(f(43)))
assert I.feature_label('A,b\nc\x00d') == 'feature:Abcd'" && ok "a feature label cuts the page name at 42 characters (the whole label at most 50) and drops commas and control characters" || bad "label length"
out=$($health triage); echo "$out"
grep -q "^== No feature: 1 ==" <<<"$out" && ok "triage lists the issue on v1.0 under No feature, with no complaint about a milestone" || bad "triage: $out"
[ "$fails" = "$f0" ] && echo "PASS milestone-freeform:milestone-v1-free-form"

echo "== goal.py pr puts the pull request in no milestone"
f0=$fails
$goal new calc-goal --here --goal "Change calc" --done "calc changes" --touches "calc.py" >/dev/null
echo "# change" >> calc.py; git commit -qam "Change calc"
python3 - <<'PYEND'
p = ".loop/goals/calc-goal.md"
t = open(p).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n   Expect: the change.\n", 1)
open(p, "w").write(t)
PYEND
git commit -qam "Verify steps"
: > "$FAKE_GH_DIR/calls.log"
bash "$here/dev/toy/flow-done.sh" calc-goal; out=$($goal pr calc-goal 2>&1); echo "$out"
grep -q "^PR https://example.test/pull/1$" <<<"$out" && ok "goal.py pr opens the pull request" || bad "pr: $out"
! grep -qi "milestone" "$FAKE_GH_DIR/calls.log" && ! grep -q "^pr edit" "$FAKE_GH_DIR/calls.log" && [ ! -f "$FAKE_GH_DIR/pr-milestone-1" ] && ! grep -qi "milestone" <<<"$out" \
  && ok "no milestone is read, made or set for the pull request" || bad "pr milestone: $(cat "$FAKE_GH_DIR/calls.log")"
[ "$fails" = "$f0" ] && echo "PASS milestone-freeform:pr-no-milestone"

echo "== health file: one tagged issue per finding, on no milestone"
rm -f "$FAKE_GH_DIR/issues.json"; f0=$fails; git switch -q main
mkdir -p skills/x/scripts; python3 -c "print('# pad\n' * 3400)" > skills/x/scripts/near.py
git add -A; git commit -qm "A near-limit script"
out=$($health preview --group size); echo "$out"
grep -q "^WOULD open issue 'health: size skills/x/scripts/near.py scripts' \[health:size\]$" <<<"$out" && [ ! -f "$FAKE_GH_DIR/issues.json" ] \
  && ok "preview: only WOULD lines, nothing written" || bad "run dry"
: > "$FAKE_GH_DIR/calls.log"; out=$($health file --group size); echo "$out"
[ -s "$FAKE_GH_DIR/calls.log" ] || bad "FAIL milestone-freeform:health-file: calls.log absent, real gh may have run. Fix: put dev/toy/fakegh first on PATH"
python3 - <<'PYEND' && ok "file: one issue on no milestone, labelled, with the hidden marker" || bad "issue created"
import json, os, re
issues = json.load(open(os.environ["FAKE_GH_DIR"] + "/issues.json"))
assert len(issues) == 1 and not issues[0]["milestone"]
assert re.search(r"<!-- loop-health size:skills/x/scripts/near.py:scripts evidence=[0-9a-f]{8} placed= -->", issues[0]["body"])
PYEND
grep -q -e "--label health --label health:size$" "$FAKE_GH_DIR/calls.log" && ! grep -qi "milestone\|backlog\|feature:" "$FAKE_GH_DIR/calls.log" && ok "labelled health and health:size only: no milestone made or set, no feature label while feature_labels is off" || bad "label: $(cat "$FAKE_GH_DIR/calls.log")"
out=$($health file --group size); echo "$out"
grep -q "^SAME #1" <<<"$out" && [ "$(python3 -c "import json,os;print(len(json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json'))))")" = 1 ] && ok "a repeat opens no second issue" || bad "duplicate"
python3 -c "print('# pad\n' * 3500)" > skills/x/scripts/near.py; git commit -qam "Bigger"
out=$($health file --group size); echo "$out"
grep -q "^DONE update #1" <<<"$out" && ok "a changed finding updates its issue" || bad "update"
python3 - <<'PYEND'
import json, os, re
p = os.environ["FAKE_GH_DIR"] + "/issues.json"; issues = json.load(open(p))
issues[0]["body"] = re.sub(r"<!-- loop-health \S+ evidence=\w+ placed=\S* -->", "<!-- loop-health size:skills/x/scripts/near.py:limit -->", issues[0]["body"])
json.dump(issues, open(p, "w"))
PYEND
out=$($health file --group size); echo "$out"
python3 - <<'PYEND' && grep -q "^DONE update #1 size:skills/x/scripts/near.py:scripts" <<<"$out" && ! grep -q "^DONE \(open\|close\)" <<<"$out" && ok "an old size:...:limit marker is moved to the new key, not closed or duplicated" || bad "marker migrate"
import json, os
issues = json.load(open(os.environ["FAKE_GH_DIR"] + "/issues.json"))
assert len(issues) == 1 and issues[0]["state"] == "OPEN" and "size:skills/x/scripts/near.py:scripts evidence=" in issues[0]["body"], issues
PYEND

echo "== an issue the owner put on a milestone stays there"
$ms new Sprint --live >/dev/null; $ms move 1 Sprint --live | grep -q "^MOVED issue 1 to milestone Sprint" && ok "the owner moves the issue to a milestone of their own" || bad "move"
python3 -c "print('# pad\n' * 3600)" > skills/x/scripts/near.py; git commit -qam "Bigger again"
: > "$FAKE_GH_DIR/calls.log"; out=$($health file --group size); echo "$out"
python3 - <<'PYEND' && ! grep -q "milestone" "$FAKE_GH_DIR/calls.log" && ok "a later run updates the issue where the owner put it, touches no milestone, and opens no other" || bad "moved"
import json, os
issues = json.load(open(os.environ["FAKE_GH_DIR"] + "/issues.json"))
assert len(issues) == 1 and issues[0]["milestone"]["title"] == "Sprint", issues
PYEND

echo "== the feature tag: off by default, on when feature_labels is true"
: > "$FAKE_GH_DIR/calls.log"; out=$($health preview --group size); ! grep -q "feature:" <<<"$out" && ok "with the switch off a preview shows no feature tag" || bad "tag shown off"
python3 -c "import json; c = json.load(open('.loop/config.json')); c['feature_labels'] = True; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
out=$($health preview --group size); echo "$out"
grep -q "^WOULD update #1 .*\[health:size, feature:Calc\]" <<<"$out" && ok "with the switch on a preview shows the feature tag for a finding about a page" || bad "tag shown on"
: > "$FAKE_GH_DIR/calls.log"; out=$($health file --group size); echo "$out"
grep -q "^label create feature:Calc --description Filed by health.py file --force" "$FAKE_GH_DIR/calls.log" && grep -q -- "--add-label feature:Calc" "$FAKE_GH_DIR/calls.log" \
  && grep -q '"name": "feature:Calc"' "$FAKE_GH_DIR/issues.json" && ok "the label is made first, and a repeat run adds it to the old issue" || bad "backfill: $(cat "$FAKE_GH_DIR/calls.log")"
python3 -c "import json; c = json.load(open('.loop/config.json')); c['feature_labels'] = False; json.dump(c, open('.loop/config.json', 'w'), indent=2)"
: > "$FAKE_GH_DIR/calls.log"; out=$($health file --group size); echo "$out"
! grep -q "feature:" "$FAKE_GH_DIR/calls.log" && ok "with the switch off again no feature label call is made" || bad "off again"

echo "== fixed closes, returning reopens"
git rm -q skills/x/scripts/near.py; git commit -qm "Remove it"
out=$($health file --group size); echo "$out"
grep -q "^DONE close #1 size:skills/x/scripts/near.py:scripts" <<<"$out" && grep -q '"state": "CLOSED"' "$FAKE_GH_DIR/issues.json" && ok "a fixed finding closes its issue" || bad "close"
mkdir -p skills/x/scripts; python3 -c "print('# pad\n' * 3600)" > skills/x/scripts/near.py; git add -A; git commit -qm "Back again"
out=$($health file --group size); echo "$out"
grep -q "^DONE reopen #1" <<<"$out" && grep -q '"state": "OPEN"' "$FAKE_GH_DIR/issues.json" && [ "$(python3 -c "import json,os;print(len(json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json'))))")" = 1 ] \
  && ok "a returning finding reopens the same issue" || bad "reopen"
grep -Eq "^(release |pr merge|api .*-X)|draft=false" "$FAKE_GH_DIR/calls.log" && bad "publish or merge call" || ok "no release or merge call"

[ "$fails" = "$f0" ] && echo "PASS milestone-freeform:health-file-no-milestone"

echo "== a group run or an unread rule closes nothing it did not check"
out=$($health file --group criteria,docs,hygiene,performance); echo "$out" | grep -c "^DONE" 
open_other=$(python3 -c "import json,os;print(sorted(i['number'] for i in json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json')) if i['state']=='OPEN' and 'size:' not in i['body']))")
[ "$open_other" != "[]" ] && ok "other families have open issues: $open_other" || bad "no other issues to guard"
git rm -q skills/x/scripts/near.py; git commit -qm "Remove it again"
$health file --group size >/dev/null
still=$(python3 -c "import json,os;print(sorted(i['number'] for i in json.load(open(os.environ['FAKE_GH_DIR']+'/issues.json')) if i['state']=='OPEN' and 'size:' not in i['body']))")
[ "$still" = "$open_other" ] && grep -q '"number": 1, .*"state": "CLOSED"' "$FAKE_GH_DIR/issues.json" && ok "file --group size closed only the size issue" || bad "family close: $still"
lone=$(mktemp -d); cp "$here/skills/workflow-health/scripts/health.py" "$lone/"
n=$(wc -l < "$FAKE_GH_DIR/calls.log")
python3 "$lone/health.py" file --group size,criteria,docs >/dev/null 2>&1; rc=$?
[ $rc = 2 ] && [ "$(wc -l < "$FAKE_GH_DIR/calls.log")" = "$n" ] && ok "a lone health.py has no file command and calls no gh" || bad "lone file"
nofile=$(mktemp -d); cp -R "$here/skills/workflow-health/scripts/." "$nofile/"; rm -f "$nofile/file.py"
out=$(python3 "$nofile/health.py" file --group size,criteria,docs 2>&1); rc=$?
grep -q "^REFUSED\[file\]: file.py is not installed" <<<"$out" && [ $rc = 2 ] && [ "$(wc -l < "$FAKE_GH_DIR/calls.log")" = "$n" ] && ok "health.py without file.py refuses to file, writes nothing" || bad "no file.py"
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
