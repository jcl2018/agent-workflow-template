#!/bin/bash
# reads: skills/workflow-health/scripts/
# reads: dev/toy/fakegh/gh dev/toy/fakegh/fake.py
# Proves the owner-approved Health PRD on throwaway repos with a stand-in for GitHub and stand-in judges: the twelve groups
# and their angles (HLT-2), tagged issues, links and migration (HLT-4), the review and its evidence (HLT-5, HLT-9),
# triage (HLT-8), controls (HLT-6), same answer and no writes (HLT-1), and issues 124, 158
# and 159. No model is called. usage: test-health-prd.sh [DIR] [h1|h2|h4|h5|hj|h6|h8|i124|i158|i159]   (HLT-7: test-health-time.sh)   (no part: all)
set -u
unset CLAUDECODE LOOP_JUDGE_ANSWER  # the judge is the session only where a test asks for it
unset GH_TOKEN GITHUB_TOKEN LOOP_HEALTH_GH_FIXTURE LOOP_HEALTH_T0 CI GITHUB_ACTIONS
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
d=${1:-$(mktemp -d)}; part=${2:-all}; rm -rf "${d:?}"; mkdir -p "$d"
S="$here/skills/workflow-health/scripts"; H="python3 $S/health.py"
export HOME="$d/home" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"; mkdir -p "$HOME" "$FAKE_GH_DIR"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
want() { [ "$part" = all ] || [ "$part" = "$1" ]; }
mkrepo() {  # a repo with one feature (Calc, skills/calc) and a near-limit script in it
  rm -rf "$d/repo"; mkdir -p "$d/repo"; cd "$d/repo" || exit 1
  git init -q -b main; git config user.email t@example.test; git config user.name Toy
  mkdir -p .loop docs/wiki skills/calc/scripts
  echo '{"base": "main", "wiki_dir": "docs/wiki"}' > .loop/config.json
  printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
  printf 'Calc\tskills/calc\n' > .loop/docs.tsv
  printf '# Calc\n\n## Usage\n\n- /workflow-calc add adds.\n\n## Requirements\n\n### Functional\n- CAL-1: **Reviewed 2026-11-10** Calc adds.\n\n### Non-functional\n- CAL-2: **Reviewed 2026-11-10** Calc is fast.\n' > docs/wiki/Calc.md
  printf '# pad\n%.0s' $(seq 1 3400) > skills/calc/scripts/near.py
  echo 'Run /workflow-zzz frob.' > README.md
  git add -A; git commit -qm toy; echo '[]' > "$FAKE_GH_DIR/issues.json"; echo '[{"number": 1, "title": "Backlog", "state": "open"}, {"number": 2, "title": "Calc", "state": "open"}]' > "$FAKE_GH_DIR/milestones.json"
}

fl_on() { python3 -c "import json;c=json.load(open('.loop/config.json'));c['feature_labels']=True;json.dump(c,open('.loop/config.json','w'))"; git commit -qam labels-on; }  # the feature tag is off by default

if want h2; then
echo "== HLT-2: exactly twelve groups, each with its angle, every rule with a control"
# Value: protects=HLT-2; fails_when=a group is added, dropped or loses its angle, or a rule has no firing control;
# why_new=health had seven groups and no angles; seam=none; no_claim=the rules' thresholds on a real repo
mkrepo
out=$($H check 2>&1)
heads=$(grep '^== ' <<<"$out" | sed 's/ (.*//; s/^== //' | tr '\n' '|')
check "check runs exactly the twelve groups in order, plus Mine" '[ "$heads" = "Requirements|Traceability|Consistency|Docs|Freshness|Tests|Performance|Security and privacy|Size|Hygiene|Adoption|Mine|Controls|" ]'
check "each group heading prints its angle" 'grep -q "^== Tests (a skeptic.s angle: do the tests prove anything?) ==" <<<"$out" && grep -q "^== Security and privacy (a leak.s angle: can anything private escape?) ==" <<<"$out"'
n=$(python3 -c "import sys;sys.path.insert(0,'$S');import report;print(len(report.RULES))")
check "every rule has a negative control that fires" '[ "$(grep -c "^PASS controls .* control: fires on its fixture" <<<"$out")" = "$n" ] && [ "$n" -ge 30 ]'
mkdir -p "$d/g13"; sed 's/^GROUPS = (/GROUPS = (("extra", "Extra", "x", ()),/' "$S/report.py" > "$d/g13/report.py"
check "report.py refuses a thirteenth group" 'python3 -c "import sys;sys.path.insert(0,\"$d/g13\");import report" 2>&1 | grep -q "AssertionError: exactly 12 groups"'
fi

if want h4; then
echo "== HLT-4: findings become tagged issues with no milestone; repeat, fix, return; covering issues linked; old markers moved"
# Value: protects=HLT-4; fails_when=a finding is placed on a milestone, a covered finding is duplicated, an old marker is
# closed instead of moved, a fix closes the wrong issue, or the feature tag appears with feature_labels off; why_new=every
# issue used to be placed on its feature's milestone or Backlog; seam=fake gh; no_claim=GitHub's own label and milestone API
mkrepo; f0=$fails
python3 - "$FAKE_GH_DIR/issues.json" <<'PY'
import json, sys
json.dump([{"number": 1, "title": "old size finding", "state": "OPEN", "labels": [{"name": "health"}, {"name": "health:size"}],
            "milestone": {"title": "Backlog"}, "createdAt": "2026-01-01T00:00:00Z",
            "body": "<!-- loop-health size:skills/calc/scripts/near.py:limit -->\nold"}], open(sys.argv[1], "w"))
PY
out=$($H preview --group size,consistency 2>&1)
check "an old marker is moved to the new key, not closed" 'grep -q "^WOULD update #1 size:skills/calc/scripts/near.py:scripts \[health:size\]" <<<"$out" && ! grep -q "close #1" <<<"$out"'
check "a finding is tagged with its group and no milestone is named" 'grep -q "^WOULD open issue .health: consistency /workflow-zzz frob usage-readme. \[health:consistency\]" <<<"$out" && ! grep -qi "milestone\|backlog" <<<"$out"'
pf=$(r=$PWD; cd "$S" && python3 -B -c "import issues; print(issues.feature_of('$r', {'subject': 'Calc', 'evidence': 'Calc'}), issues.feature_of('$r', {'subject': 'nothing/here.py', 'evidence': ''}))" 2>&1)
check "a page-level finding (a stale page) is about that page, one that fits none about none ($pf)" '[ "$pf" = "Calc None" ]'
: > "$FAKE_GH_DIR/calls.log"
$H file --group size,consistency >/dev/null 2>&1
m=$(python3 -c "import json;print([i['milestone']['title'] for i in json.load(open('$FAKE_GH_DIR/issues.json')) if i['number']==1][0])")
check "file leaves an issue the owner put on a milestone where it is, and makes and sets none" '[ "$m" = Backlog ] && ! grep -q -- "milestone" "$FAKE_GH_DIR/calls.log" && ! grep -q "feature:" "$FAKE_GH_DIR/calls.log"'
out=$($H preview --group size,consistency 2>&1)
check "a repeat is SAME, a key with a space (a /workflow command) included" 'grep -q "^SAME #1 " <<<"$out" && grep -q "^SAME #2 consistency:/workflow-zzz frob:usage-readme" <<<"$out" && grep -q "PREVIEW: 0 to write" <<<"$out"'
printf '# small\n' > skills/calc/scripts/near.py; git commit -qam fixed
out=$($H preview --group size 2>&1)
check "a fix closes its issue" 'grep -q "^WOULD close #1 " <<<"$out"'
$H file --group size >/dev/null 2>&1
printf '# pad\n%.0s' $(seq 1 3400) > skills/calc/scripts/near.py; git commit -qam back
check "a return reopens it" '$H preview --group size 2>&1 | grep -q "^WOULD reopen #1 "'
python3 - "$FAKE_GH_DIR/issues.json" <<'PY'
import json, sys
p = sys.argv[1]; s = json.load(open(p))
s.append({"number": 9, "title": "Calc: the docs page lies about CAL-1", "state": "OPEN", "labels": [], "milestone": None,
          "createdAt": "2026-01-01T00:00:00Z", "body": "see CAL-1"})
json.dump(s, open(p, "w"))
PY
out=$($H preview --group requirements 2>&1)
check "an open issue that already names the subject is linked, not duplicated" 'grep -q "^WOULD link #9 (already covers requirements:CAL-1:rows) \[health:requirements\]" <<<"$out" && ! grep -q "open issue .health: requirements CAL-1" <<<"$out"'
$H file --group requirements >/dev/null 2>&1; $H file --group requirements >/dev/null 2>&1
check "the link comment is written once" '[ "$(python3 -c "import json;print(sum(\"loop-health-link requirements:CAL-1:rows\" in c[\"body\"] for i in json.load(open(\"$FAKE_GH_DIR/issues.json\")) for c in i.get(\"comments\") or []))")" = 1 ]'
python3 -c "import json;c=json.load(open('.loop/config.json'));c['feature_labels']=True;json.dump(c,open('.loop/config.json','w'))"; git commit -qam labels-on
out=$($H preview --group size,consistency 2>&1)
check "with feature_labels on, a finding about a feature is also tagged feature:<Page>, one about none is not" 'grep -q "^WOULD update #1 .*\[health:size, feature:Calc\]" <<<"$out" && grep -q "^SAME #2 " <<<"$out" && ! grep -q "feature:" <<<"$(grep consistency <<<"$out")"'
[ "$fails" = "$f0" ] && echo "PASS milestone-freeform:hlt4-feature-milestones"
fi

if want h5; then
echo "== HLT-5 and HLT-9: review per feature, every finding with evidence, unverifiable ones dropped, writes nothing"
# Value: protects=HLT-5, HLT-9; fails_when=a finding without checkable evidence is kept, review writes a file, or a failing
# judge hides its cause; why_new=no review existed; seam=stand-in judges; no_claim=a real model's judgment
mkrepo; fl_on
printf '#!/bin/bash\ncat >/dev/null\necho "FINDING|Calc|conflict|a reader.s angle|CAL-1 and CAL-2 pull apart|CAL-1,docs/wiki/Calc.md:3|merge them"\necho "FINDING|Calc|weak-test|a skeptic.s angle|no test|nowhere/x.py:9|drop"\necho "FINDING|Ghost|gap|x|z|CAL-1,docs/wiki/Calc.md:3|y"\n' > "$d/judge.sh"; chmod +x "$d/judge.sh"
python3 -c "import json;c=json.load(open('.loop/config.json'));c['judge_command']=['$d/judge.sh'];json.dump(c,open('.loop/config.json','w'))"
git commit -qam judge; before=$(git status --porcelain)
out=$($H review 2>&1)
check "review reports per feature with angle, what is wrong and evidence" 'grep -q "^== Calc ==" <<<"$out" && grep -q "^FINDING conflict (a reader.s angle): CAL-1 and CAL-2 pull apart -- evidence: CAL-1, docs/wiki/Calc.md:3" <<<"$out"'
check "a finding whose evidence doesn't exist is dropped and counted" '! grep -q "weak-test" <<<"$out" && grep -q "REVIEW: .* 1 dropped for no evidence" <<<"$out"'
check "a finding for an unknown feature is never shown" '! grep -q "Ghost" <<<"$out"'
check "review writes nothing" '[ "$(git status --porcelain)" = "$before" ]'
$H review --json > "$d/r.json"
printf '#!/bin/bash\ncat >/dev/null\necho "FINDING|Calc|gap|a|first gap|CAL-1,docs/wiki/Calc.md:3|x"\necho "FINDING|Calc|gap|a|second gap|CAL-2,docs/wiki/Calc.md:3|y"\n' > "$d/two.sh"; chmod +x "$d/two.sh"
python3 -c "import json;c=json.load(open('.loop/config.json'));c['judge_command']=['$d/two.sh'];json.dump(c,open('.loop/config.json','w'))"
$H review --json > "$d/two.json"; $H file --review "$d/two.json" >/dev/null 2>&1
check "two findings of one kind on one feature are two issues, and file --review files only review findings" '[ "$(python3 -c "import json;print(sum(1 for i in json.load(open(\"$FAKE_GH_DIR/issues.json\")) if \"review-gap\" in str(i[\"labels\"]) and \"gap\" in i[\"title\"]))")" = 2 ] && ! grep -q "health:size\|health:docs" "$FAKE_GH_DIR/issues.json"'
check "review --json is versioned, and file --review files it as health:review-<kind> on its feature" 'grep -q "\"version\": 1" "$d/r.json" && $H preview --review "$d/r.json" 2>&1 | grep -q "\[health:review-conflict, feature:Calc\]"'
printf '#!/bin/bash\ncat >/dev/null\necho "FINDING|Calc|gap|a|one|CAL-1,docs/wiki/Calc.md:3|same fix"\necho "FINDING|Calc|gap|a|two|CAL-2,docs/wiki/Calc.md:3|same fix"\n' > "$d/same.sh"; chmod +x "$d/same.sh"
python3 -c "import json;c=json.load(open('.loop/config.json'));c['judge_command']=['$d/same.sh'];json.dump(c,open('.loop/config.json','w'))"
check "next steps name each distinct fix once" '$H review 2>&1 | grep -qx "next steps: 1. same fix"'
fi

if want h8; then
echo "== HLT-8: triage per feature; a closed batch keeps the owner's words and is not refiled"
# Value: protects=HLT-8; fails_when=triage writes without --yes, closes more than it listed, or file reopens a finding the
# owner closed with unchanged evidence; why_new=no triage existed; seam=fake gh; no_claim=GitHub's label colors
mkrepo; fl_on
$H file --group size >/dev/null 2>&1
out=$($H triage 2>&1)
check "triage lists open findings per feature by kind and age" 'grep -q "^== Calc: 1 ==" <<<"$out" && grep -q "size .* 1 open, oldest [0-9]* days" <<<"$out"'
out=$($H triage --close --feature Calc --kind size --why "won't fix: generated file" 2>&1)
check "close without --yes lists and writes nothing" 'grep -q "^DRY RUN: 1 would close" <<<"$out" && grep -q "\"OPEN\"" "$FAKE_GH_DIR/issues.json"'
check "close without --why is refused" '$H triage --close --feature Calc --kind size --yes 2>&1 | grep -q "^REFUSED\[why\]"'
$H triage --close --feature Calc --kind size --why "won't fix: generated file" --yes >/dev/null 2>&1
check "--yes closes the batch with the owner's words and health:closed" 'python3 -c "
import json; i=json.load(open(\"$FAKE_GH_DIR/issues.json\"))[0]
assert i[\"state\"]==\"CLOSED\" and {\"name\":\"health:closed\"} in i[\"labels\"] and \"generated file\" in json.dumps(i[\"comments\"])"'
check "the next file leaves it closed while its evidence is the same" '$H preview --group size 2>&1 | grep -q "^SAME #1 .*closed by the owner, evidence unchanged"'
python3 - "$FAKE_GH_DIR/issues.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s[0]["body"] = s[0]["body"].replace("evidence=", "evidence=0"); json.dump(s, open(sys.argv[1], "w"))
PY
$H file --group size >/dev/null 2>&1
check "when the evidence changes it reopens, and the owner's health:closed label comes off" 'python3 -c "
import json; i=json.load(open(\"$FAKE_GH_DIR/issues.json\"))[0]; assert i[\"state\"]==\"OPEN\" and {\"name\":\"health:closed\"} not in i[\"labels\"], i[\"labels\"]"'
fi

if want hj; then
echo "== judge order (owner's rule): the session first, claude -p only with no session"
# Value: protects=the owner's judge rule; fails_when=a session run calls claude -p, the session's reply is ignored, or a
#   run with no session (GitHub Actions) has no judge; why_new=the judge only ran judge_command; seam=stand-in judge;
#   no_claim=a real subagent's answer
mkrepo
printf '#!/bin/bash\ntouch "%s/ran"\ncat >/dev/null\necho "FINDING|Calc|conflict|a reader.s angle|from claude -p|CAL-1,docs/wiki/Calc.md:3|merge"\n' "$d" > "$d/cp.sh"; chmod +x "$d/cp.sh"
python3 -c "import json;c=json.load(open('.loop/config.json'));c['judge_command']=['$d/cp.sh'];json.dump(c,open('.loop/config.json','w'))"
git commit -qam judge; rm -f "$d/ran"
out=$(CLAUDECODE=1 $H review 2>&1); p=$(grep -o "prompt in [^ ]* to an in-session" <<<"$out" | awk '{print $3}')
check "in a session the judge is the session: the report says so, claude -p never runs, the prompt is handed over" 'grep -qx "judge: session" <<<"$out" && [ ! -e "$d/ran" ] && [ -n "$p" ] && grep -q "<<<DATA" "$p"'
printf 'FINDING|Calc|gap|an auditor.s angle|from the session|CAL-1,docs/wiki/Calc.md:3|tie it\n' > "$d/reply.txt"
out=$(CLAUDECODE=1 $H review --judge-answer "$d/reply.txt" 2>&1)
check "the session's saved reply is used, and claude -p still never runs" 'grep -qx "judge: session" <<<"$out" && grep -q "^FINDING gap (an auditor.s angle): from the session" <<<"$out" && [ ! -e "$d/ran" ]'
out=$($H review 2>&1)
check "with no session the fallback is claude -p, logged as such" 'grep -qx "judge: claude -p (no session)" <<<"$out" && grep -q "from claude -p" <<<"$out" && [ -e "$d/ran" ]'
rm -f "$p"
fi

if want h6; then
echo "== HLT-6: controls fire, a slow land run names its slowest rows, stale worktrees and branches with their commands"
# Value: protects=HLT-6; fails_when=a rule loses its control or the lean rules stop naming rows or commands; why_new=the
# lean rules moved groups; seam=none; no_claim=this machine's real worktrees
mkrepo
out=$($H check --group controls 2>&1)
check "every control fires, none UNREAD" '! grep -q "^\(FAIL\|UNREAD\) controls" <<<"$out" && grep -q "^PASS controls test-time control" <<<"$out" && grep -q "^PASS controls worktrees control" <<<"$out"'
git worktree add -q -b loop/gone "$(git rev-parse --git-common-dir)/loop/worktrees/gone" 2>/dev/null
out=$($H check --group hygiene 2>&1)
check "a stale worktree is flagged with the command that removes it, and health runs none" 'grep -q "^WARN hygiene .*worktrees.*git worktree remove" <<<"$out" && [ -d "$(git rev-parse --git-common-dir)/loop/worktrees/gone" ]'
fi

if want h1; then
echo "== HLT-1: the same answer twice, and check changes nothing"
# Value: protects=HLT-1; fails_when=a line carries a time, count drift or temp path, or check writes a file; why_new=the
# new rules read dates and gh; seam=fake gh; no_claim=a repo that changes between the two runs
mkrepo
a=$($H check --skip controls 2>&1); b=$($H check --skip controls 2>&1); s=$(git status --porcelain; ls -la .git | cksum)
check "two checks of an unchanged repo print the same lines" '[ "$a" = "$b" ]'
$H check >/dev/null 2>&1
check "check changes no file" '[ "$(git status --porcelain; ls -la .git | cksum)" = "$s" ]'
fi


if want i124; then
echo "== issue 124: older repos can go green: goals without tokens"
# Value: protects=#124; fails_when=no tokens recorded turns health red;
# why_new=defect test; seam=none; no_claim=none beyond protects
mkrepo
mkdir -p .git/loop/runs; printf '{"slug": "old", "status": "done", "updated": "2026-01-01T03:00:00Z", "log": ["2026-01-01T00:00:00Z queued", "2026-01-01T01:00:00Z build"]}' > .git/loop/runs/old.json
out=$($H check --group performance 2>&1)
check "a finished goal with no tokens recorded is INFO, never UNREAD, and the check stays green" 'grep -q "^INFO performance tokens cost: no tokens recorded" <<<"$out" && ! grep -q "^UNREAD" <<<"$out" && tail -1 <<<"$out" | grep -q "^HEALTH: green"'
fi

if want i158; then
echo "== issue 158: a failing judge names its cause"
# Value: protects=#158; fails_when=JUDGE UNAVAILABLE says only the exit code; why_new=defect test; seam=stand-in judge;
# no_claim=the real claude CLI's wording
mkrepo
printf '#!/bin/bash\ncat >/dev/null\necho "You have hit your weekly limit"\necho "Warning: sign-in ends soon" >&2\nexit 1\n' > "$d/limit.sh"; chmod +x "$d/limit.sh"
python3 -c "import json;c=json.load(open('.loop/config.json'));c['judge_command']=['$d/limit.sh'];json.dump(c,open('.loop/config.json','w'))"
out=$($H review 2>&1)
check "review says JUDGE UNAVAILABLE with the command's last output and stderr lines" 'grep -q "^JUDGE UNAVAILABLE: the judge exited 1: You have hit your weekly limit; stderr: Warning: sign-in ends soon" <<<"$out"'
fi

if want i159; then
echo "== issue 159: the health docs describe today's commands"
# Value: protects=#159; fails_when=the SKILL.md or the commands reference still describe the old run or read-only check;
# why_new=defect test; seam=none; no_claim=prose quality
check "SKILL.md describes review, triage and filing, and the commands reference has no run chart" 'grep -q "review" "$here/skills/workflow-health/SKILL.md" && grep -q "triage" "$here/skills/workflow-health/SKILL.md" && ! grep -q "^#### .run." "$here/skills/workflow-health/references/commands.md" && ! grep -q "Read-only. Use when" "$here/skills/workflow-health/SKILL.md"'
fi

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
