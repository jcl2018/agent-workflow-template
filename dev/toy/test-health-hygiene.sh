#!/bin/bash
# reads: skills/
# Test HLT-6 on a toy repo: negative controls, test time, stale worktrees and branches. usage: test-health-hygiene.sh [DIR]
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=${1:-$(mktemp -d)}; rm -rf "$d"; mkdir -p "$d"
"$here/dev/toy/make.sh" "$d" || exit 1
export LOOP_FLOW="$d/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
unset GH_TOKEN GITHUB_TOKEN
S="$here/skills/workflow-health/scripts"
health="python3 $S/health.py"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
export LOOP_HEALTH="$d/none.json"
mkdir -p "$FAKE_GH_DIR"; : > "$FAKE_GH_DIR/calls.log"
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
field() { python3 -c "import json,sys;d=json.load(sys.stdin);print([r for r in d['rows'] if r['rule']==sys.argv[1]][0][sys.argv[2]])" "$@"; }

echo "== negative controls"
out=$($health check --group controls); echo "$out"
[ "$(grep -c '^PASS controls .* control: fires on its fixture' <<<"$out")" = 12 ] && ok "every rule's control fires" || bad "controls fire"
grep -q "/tmp\|/var/\|health-control-" <<<"$out" && bad "a control row shows a temp path" || ok "control rows carry no temp path"
[ "$($health check --group controls)" = "$out" ] && ok "controls print the same lines twice" || bad "controls differ"
# Value: protects=a rule that silently stops matching is reported as unable to fire; fails_when=controls only check
#   that a rule ran, not that it reported; why_new=no test breaks a rule; seam=none; no_claim=none beyond protects
broken="$d/broken/skills/workflow-health"; mkdir -p "$broken"; cp -R "$here/skills/workflow-health/scripts" "$broken/"
for s in workflow-docs workflow-regression workflow-monitoring; do ln -s "$here/skills/$s" "$d/broken/skills/$s"; done
sed -i.b 's/^LIMIT = 20 \* 1024$/LIMIT = 20 * 1024 * 1000/' "$broken/scripts/health.py" && rm "$broken/scripts/health.py.b"
out=$(python3 "$broken/scripts/health.py" check --group controls); rc=$?
grep -q "^FAIL controls size control: cannot fire" <<<"$out" && grep -q "controls.py run size --keep" <<<"$out" && [ $rc = 1 ] \
  && ok "a broken rule is reported as unable to fire, with how to look" || bad "cannot fire"
grep -q "^PASS controls findings control" <<<"$out" && ok "the other rules' controls still fire" || bad "other controls"
# Value: protects=a new rule cannot be added without its control; fails_when=the load check is dropped; why_new=new;
#   seam=none; no_claim=none beyond protects
sed -i.b 's/^         "test-time", "worktrees", "local-branches")$/         "test-time", "worktrees", "local-branches", "new-rule")/; s/^MAX_RULES = 12 /MAX_RULES = 13 /' "$broken/scripts/health.py" && rm "$broken/scripts/health.py.b"
out=$(python3 "$broken/scripts/health.py" check 2>&1); rc=$?
grep -q '^REFUSED: rule new-rule has no negative control. Fix: add CONTROLS\["new-rule"\] in controls.py' <<<"$out" && [ $rc = 2 ] \
  && ! grep -q "^HEALTH" <<<"$out" && ok "a rule without a control is refused before any report" || bad "refused"
out=$($health check --skip controls); ! grep -q "^== controls" <<<"$out" && grep -q "skipped: .*controls (not asked)" <<<"$out" \
  && ok "check --skip controls leaves the group out" || bad "skip"
out=$($health check --skip size,criteria,docs,hygiene,performance,mine,controls); rc=$?
grep -q "^REFUSED: --skip leaves no group to check" <<<"$out" && [ $rc = 2 ] && ok "a --skip that leaves nothing is refused" || bad "skip all"
# Value: protects=a control that crashes or whose rule cannot read is UNREAD, never a crash or a false "cannot fire";
#   fails_when=one control's exception stops the check; why_new=review finding; seam=none; no_claim=none beyond protects
crash="$d/crash/skills/workflow-health"; mkdir -p "$crash"; cp -R "$here/skills/workflow-health/scripts" "$crash/"
for s in workflow-docs workflow-regression workflow-monitoring; do ln -s "$here/skills/$s" "$d/crash/skills/$s"; done
printf '\ndef f_findings(root):\n    raise RuntimeError("boom")\nCONTROLS["findings"] = ("hygiene", "findings", f_findings)\n' >> "$crash/scripts/controls.py"
out=$(python3 "$crash/scripts/health.py" check --group controls 2>&1)
grep -q "^UNREAD controls findings control: the control stopped with RuntimeError" <<<"$out" && grep -q "^PASS controls waiting control" <<<"$out" \
  && ok "a control that crashes is UNREAD and the others still run" || bad "control crash"
rm "$crash/../workflow-docs"
# Value: protects=running the controls leaves the no-prompt setting in place for what runs after them; fails_when=the
#   restore drops GIT_TERMINAL_PROMPT; why_new=ship review finding; seam=none; no_claim=none beyond protects
GIT_TERMINAL_PROMPT=0 python3 -c "
import os, sys; sys.argv = ['$S/health.py']; sys.path.insert(0, '$S'); import health
health.controls_rows('.'); sys.exit(0 if os.environ.get('GIT_TERMINAL_PROMPT') == '0' else 1)" && ok "the controls keep GIT_TERMINAL_PROMPT for what runs after them" || bad "prompt env lost"
out=$(python3 "$crash/scripts/health.py" check --group controls 2>&1)
grep -q "^UNREAD controls docs-check control: its rule could not read its data" <<<"$out" && ok "a rule that cannot read on its fixture is UNREAD, not cannot fire" || bad "control blind"

echo "== test time"
out=$($health check --group hygiene)
grep -q "^INFO hygiene lane test-time: no lane record yet" <<<"$out" && ok "no lane record is INFO, never a pass" || bad "no record"
python3 - <<'PY'
import json
open(".loop/regression.tsv", "a").write("".join("slow-%d\tland\tbash dev/toy/test-a.sh\tX-1\t2026-01-01\n" % n for n in range(3))
                                         + "quick\tland\tbash dev/toy/test-b.sh\tX-1\t2026-01-01\nnight\tnightly\tbash dev/toy/test-c.sh\n")
PY
git add -A; git commit -qm "rows"
mkdir -p "$C/loop/tests"
OWN="$C/loop/tests/main-$(printf main | shasum | cut -c1-8).json"
python3 - "$OWN" <<'PY'
import json, sys
rows = {"slow-%d" % n: {"status": "PASS", "seconds": 300 + n, "commit": "x"} for n in range(3)}
rows.update({"quick": {"status": "PASS", "seconds": 5, "commit": "x"}, "night": {"status": "PASS", "seconds": 900, "commit": "x"},
             "gone-row": {"status": "PASS", "seconds": 999, "commit": "x"}})
json.dump({"at": "2026-01-02T00:00:00Z", "rows": rows}, open(sys.argv[1], "w"))
PY
# Value: protects=a slow land lane is named with its slowest rows; fails_when=nightly or deleted rows are counted, or
#   no WARN; why_new=new; seam=none; no_claim=real lane timings (a stand-in record)
out=$($health check --group hygiene); echo "$out" | grep test-time
grep -q "^WARN hygiene lane test-time: the land lane takes 908 s, over test_budget_seconds=600 .*slowest rows: slow-2 302s, slow-1 301s, slow-0 300s, quick 5s; slowest scripts: dev/toy/test-a.sh 903s" <<<"$out" \
  && ok "a land lane over its budget warns, naming the slowest rows and scripts (nightly and deleted rows left out)" || bad "test-time warn"
python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['test_budget_seconds']=1000;json.dump(d,open(p,'w'))"
$health check --group hygiene | grep -q "^PASS hygiene lane test-time: the land lane takes 908 s, within test_budget_seconds=1000" \
  && ok "a lane within its budget stays quiet" || bad "test-time quiet"
# Value: protects=another branch's record is never this branch's verdict, and a damaged own record is UNREAD;
#   fails_when=a borrowed record passes or a damaged one is skipped; why_new=review finding; seam=none; no_claim=none
mv "$OWN" "$C/loop/tests/other-abcdef12.json"
$health check --group hygiene | grep -q "^INFO hygiene lane test-time: the land lane takes 908 s, within test_budget_seconds=1000 (from another branch's record, other-abcdef12.json)" \
  && ok "another branch's record is INFO and named" || bad "borrowed record"
git checkout -q -- .loop/config.json
$health check --group hygiene | grep -q "^INFO hygiene lane test-time: the land lane takes 908 s, over test_budget_seconds=600 .*(from another branch's record, other-abcdef12.json)" \
  && ok "another branch's record over budget is INFO, never a warning" || bad "borrowed warn"
echo '{"at": "x", "rows": {"a": {"seconds": "slow"}}}' > "$OWN"
$health check --group hygiene | grep -q "^UNREAD hygiene lane test-time: this branch's lane record cannot be read" && ok "a damaged lane record of this branch is UNREAD" || bad "damaged record"
echo '{"at": "x", "rows": {"slow-0": {"seconds": NaN}}}' > "$OWN"
out=$($health check --group hygiene 2>&1); grep -q "^UNREAD hygiene lane test-time: this branch's lane record cannot be read" <<<"$out" && ! grep -q Traceback <<<"$out" \
  && ok "a lane record with a NaN time is UNREAD, not a crash" || bad "nan record"
cp .loop/config.json "$d/config.keep"; echo '[1]' > .loop/config.json
out=$($health check --group hygiene 2>&1); ! grep -q Traceback <<<"$out" && grep -q "^HEALTH" <<<"$out" && ok "a config.json that is not an object never crashes the check" || bad "config list"
cp "$d/config.keep" .loop/config.json
mv "$C/loop/tests/other-abcdef12.json" "$OWN"
git checkout -q -- .loop/config.json
python3 -c "
import sys; sys.path.insert(0, '$S'); import lean
print(lean.facts('.')[0])" | grep -q "land lane: 4 rows, 908 s (budget 600 s); slowest: slow-2 302s" && ok "the judge's facts carry test time" || bad "judge facts"
python3 -c "
import sys; sys.path.insert(0, '$S'); import judge
print(judge.gather('.', '$S', []))" | grep -q "^## Test time (the land lane)" && ok "the judge input has a test time section" || bad "judge input"
# lanes.save records the total
python3 "$here/skills/workflow-regression/scripts/regression.py" add tiny --level land --command "true" --describe "Given nothing, when it runs, then it passes" >/dev/null
git add -A; git commit -qm "tiny"
python3 "$here/skills/workflow-regression/scripts/regression.py" run tiny --reuse >/dev/null 2>&1
python3 -c "import json,sys;d=json.load(open(sys.argv[1]));sys.exit(0 if 'total_seconds' in d else 1)" "$OWN" && ok "each regression run records its total time and each row's time" || bad "total_seconds"
rm -f "$OWN"

echo "== stale worktrees and branches"
mkdir -p "$C/loop/worktrees"
git worktree add -q -b loop/old-goal "$C/loop/worktrees/old-goal"
git worktree add -q -b loop/live-goal "$C/loop/worktrees/live-goal"
mkdir -p "$C/loop/runs"
printf '{"slug":"live-goal","status":"running","worktree":"%s"}' "$C/loop/worktrees/live-goal" > "$C/loop/runs/live-goal.json"
git checkout -q -b "odd\$name"; echo x > odd.txt; git add odd.txt
GIT_COMMITTER_DATE="2026-01-01T00:00:00+0000" git commit -qm "only here"
git checkout -q main
git checkout -q -b fresh; echo y > fresh.txt; git add fresh.txt; git commit -qm "new"; git checkout -q main
git checkout -q -b loop/held; echo z > held.txt; git add held.txt; GIT_COMMITTER_DATE="2026-01-01T00:00:00+0000" git commit -qm "held"; git checkout -q main
for s in queued waiting failed stopped; do git worktree add -q -b "loop/s-$s" "$C/loop/worktrees/s-$s"; printf '{"status":"%s"}' "$s" > "$C/loop/runs/s-$s.json"; done
git worktree add -q -b loop/s-open "$C/loop/worktrees/s-open"; printf '{"status":"done","release":"ask"}' > "$C/loop/runs/s-open.json"
git worktree add -q -b loop/s-landed "$C/loop/worktrees/s-landed"; printf '{"status":"done","release":"merged"}' > "$C/loop/runs/s-landed.json"
printf '{"status":"queued"}' > "$C/loop/runs/held.json"
out=$($health check --group hygiene --json)
wt=$(field worktrees detail <<<"$out"); br=$(field local-branches detail <<<"$out"); echo "$wt"; echo "$br"
# Value: protects=a worktree no live goal names is listed with its removal command, a live one is not; fails_when=liveness
#   ignores run records or the command is missing; why_new=new; seam=none; no_claim=none beyond protects
grep -q "2 stale loop worktrees: old-goal (no live goal): git worktree remove .*/loop/worktrees/old-goal; s-landed (no live goal)" <<<"$wt" && ! grep -qE "live-goal|s-(queued|waiting|failed|stopped|open)" <<<"$wt" \
  && ok "a worktree with no live goal is listed with its removal command; queued, waiting, failed, stopped and unreleased goals' are not" || bad "worktrees"
! grep -q "loop/held" <<<"$br" && ok "a live goal's branch with no worktree is not listed" || bad "held branch"
for s in queued waiting failed stopped open landed; do git worktree remove --force "$C/loop/worktrees/s-$s"; git branch -q -D "loop/s-$s"; rm "$C/loop/runs/s-$s.json"; done
git branch -q -D loop/held; rm "$C/loop/runs/held.json"
# Value: protects=a damaged run record never makes a live goal's worktree look stale; fails_when=it is skipped and the
#   worktree listed; why_new=ship review finding; seam=none; no_claim=none beyond protects
echo '{broken' > "$C/loop/runs/broken.json"
blind=$($health check --group hygiene)
grep -q "^UNREAD hygiene worktrees worktrees: run record broken.json cannot be read" <<<"$blind" && grep -q "^UNREAD hygiene local-branches local-branches: run record broken.json" <<<"$blind" \
  && ! grep -q "git worktree remove" <<<"$blind" && ok "an unreadable run record makes the worktree and branch rows UNREAD, listing nothing to remove" || bad "broken run record"
rm "$C/loop/runs/broken.json"
[ -d "$C/loop/worktrees/old-goal" ] && git rev-parse -q --verify "odd\$name" >/dev/null && ok "health removes nothing itself" || bad "something removed"
# Value: protects=an old branch on no remote is listed with a quoted, warned delete; a young one is not; fails_when=the age,
#   upstream or quoting is wrong; why_new=new; seam=none; no_claim=none beyond protects
grep -Eq "1 stale local branches: odd\\\$name \([0-9]+ commits exist only on this machine; push it first to keep them\): git branch -D 'odd\\\$name'" <<<"$br" \
  && ! grep -q "fresh" <<<"$br" && ok "an old branch on no remote is listed with a quoted delete and a data-loss warning; a young one is not" || bad "branches"
python3 -c "import json,sys;d=json.load(sys.stdin);r=[r for r in d['rows'] if r['rule']=='worktrees'][0];sys.exit(0 if r['items'][0]['name']=='old-goal' else 1)" <<<"$out" \
  && ok "the full list is in --json" || bad "json items"
# Value: protects=the base comes from .loop/config.json and a missing one is UNREAD, never "not merged";
#   fails_when=main is assumed; why_new=review finding; seam=none; no_claim=none beyond protects
python3 -c "import json;p='.loop/config.json';d=json.load(open(p));d['base']='trunk';json.dump(d,open(p,'w'))"
$health check --group hygiene | grep -q "^UNREAD hygiene local-branches local-branches: the base branch trunk cannot be found" \
  && ok "a configured base that does not exist is UNREAD" || bad "base unread"
git checkout -q -- .loop/config.json
git worktree remove "$C/loop/worktrees/old-goal"; git branch -q -D "odd\$name"
out=$($health check --group hygiene); grep -E "worktrees|local-branches" <<<"$out"
[ "$(grep -cE "^PASS hygiene (worktrees|local-branches)" <<<"$out")" = 2 ] && ok "a clean repo stays quiet" || bad "clean quiet"
# Value: protects=machine-local rows never become GitHub issues; fails_when=file.py files them; why_new=new; seam=none;
#   no_claim=none beyond protects
git worktree add -q -b loop/old2 "$C/loop/worktrees/old2"
out=$($health preview --group hygiene)
grep -qE "worktrees|local-branches|test-time" <<<"$out" && bad "preview would file a local row" || ok "test time, worktree and branch rows are never filed"
python3 -c "
import sys; sys.path.insert(0, '$S'); import file
rows = [{'state': 'UNREAD', 'family': 'hygiene', 'subject': 'lane', 'rule': 'test-time', 'detail': 'x', 'fix': ''}]
print([a['kind'] for a in file.plan(rows, {'hygiene:x:findings': {'number': 7, 'state': 'OPEN'}}, ['hygiene'])])" | grep -qx "\['close'\]" \
  && ok "an UNREAD report-only row never holds back closing a hygiene issue" || bad "report-only unread"
python3 -c "
import sys; sys.path.insert(0, '$S'); import file
rows = [{'state': 'FAIL', 'family': 'controls', 'subject': 'size', 'rule': 'control', 'detail': 'cannot fire', 'fix': ''}]
print(file.plan(rows, {}, ['controls']))" | grep -qx "\[\]" && ok "a controls row is never filed" || bad "controls filed"

echo "repo: $d/repo"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
