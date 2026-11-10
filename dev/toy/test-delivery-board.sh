#!/bin/bash
# reads: skills/workflow-delivery/scripts/fit.py skills/workflow-delivery/scripts/goal.py
# reads: skills/workflow-health/scripts/cost.py skills/workflow-monitoring/scripts/board_budget.py
# reads: skills/workflow-monitoring/scripts/board_status.py skills/workflow-monitoring/scripts/live_board.py
# reads: skills/workflow-monitoring/scripts/mend.py skills/workflow-monitoring/scripts/session_bind.py
# reads: skills/workflow-monitoring/scripts/sessions.py skills/workflow-monitoring/scripts/worker.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-monitoring/scripts/
# Proves the delivery-prd monitoring half on a made-up repo: the live board's budget line (DEL-8: minutes and tokens,
# OVER flags, none set, one half, a record from before budgets, agreement with health's cost rule), the decided depth
# on the board (DEL-6: by size under condensed, the owner override wins), the missing private-name list under Issues
# (DEL-9), mend's resume prompt (DEL-7: step, next command, uncommitted files, HEAD) and sessions.py bind SLUG self
# (issue 117). No model is called.
# usage: test-delivery-board.sh [budget|depth|issues|mend|bind] [DIR]
set -u
unset LOOP_PRIVATE_NAMES LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_SESSION CLAUDE_CODE_HOST_SESSION_ID
case "${1:-}" in budget|depth|issues|mend|bind) only=$1; shift;; *) only="";; esac
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
d=${1:-$(mktemp -d)}; rm -rf "${d:?}"; mkdir -p "$d"
export HOME="$d/home" LOOP_BOARD_HEALTH=green LOOP_FLOW="$d/flow.json"; mkdir -p "$HOME"
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
S="$here/skills/workflow-monitoring/scripts"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"; SE="python3 $S/sessions.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
want() { [ -z "$only" ] || [ "$only" = "$1" ]; }
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); R="$C/loop/runs"
AT="2026-11-10T10:35:00+00:00"
new() { git switch -q main; LOOP_ROLE=worker $goal new "$1" --here --goal "Goal $1" --done "Line $1" >/dev/null 2>&1 || bad "goal.py new $1"; }
# edit SLUG CODE: run python statements on the run record s (json loaded), then save it.
edit() { python3 - "$R/$1.json" "$2" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); exec(sys.argv[2]); json.dump(s, open(sys.argv[1], "w"))
PY
}
cfg() { python3 - "$@" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
for pair in sys.argv[1:]:
    key, _, value = pair.partition("=")
    c[key] = json.loads(value)
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
}
board() { python3 - "$S" "$AT" > "$d/board" <<'PY'
import datetime, os, sys
sys.path.insert(0, sys.argv[1])
import live_board
print("\n".join(live_board.render(os.getcwd(), datetime.datetime.fromisoformat(sys.argv[2]))))
PY
}
# block SLUG: the goal's lines on the board, wrapped lines joined, spaces squeezed.
block() { awk -v s="- $1 " 'index($0, s) == 1 {on = 1; print; next} on && /^(- |$)/ {on = 0} on' "$d/board" | tr -s ' \n' '  '; }
issues() { sed -n '/^Issues$/,/^Running goals$/p' "$d/board" | tr -s ' \n' '  '; }
LOG='["2026-11-10T10:00:00Z new goal", "2026-11-10T10:20:00Z idea done", "2026-11-10T10:35:00Z plan done"]'
spend() { edit "$1" "s.update(status='running', step='build', pid=None, log=$LOG, tokens={'idea': 150000, 'plan': 250000}); $2"; }

if want budget; then
  echo "== DEL-8: the budget line"
  for g in b1 b2 b3 b4 b5 b6; do new $g; done
  git switch -q main
  cfg 'time_budget_minutes=60' 'token_budget=1000000'
  spend b1 "s['budget'] = {'minutes': 120, 'tokens': 3000000}"
  spend b2 "s['budget'] = {'minutes': 30, 'tokens': 300000}"
  spend b3 "s['budget'] = {'minutes': 0, 'tokens': 0}"
  spend b4 "s['budget'] = {'minutes': 90, 'tokens': 0}"
  spend b5 "s.pop('budget', None)"
  edit b6 "s.update(status='done', step='pr', pid=None, log=['2026-11-10T09:00:00Z new goal', '2026-11-10T09:45:00Z idea done', '2026-11-10T10:15:00Z plan done'], tokens={'idea': 1000000, 'plan': 1500000}); s.pop('budget', None); s.pop('pr', None)"
  board
  check "the board shows budget: with minutes and tokens for a running goal" 'block b1 | grep -q "budget: 35m of 120m, 0.4M of 3.0M tokens" && ! block b1 | grep -q OVER'
  check "a goal past its time and token budget is flagged OVER time and OVER tokens" 'block b2 | grep -q "budget: 35m of 30m, 0.4M of 0.3M tokens, OVER time, OVER tokens"'
  check "a goal carrying a zero budget shows budget: none set even when the repo now sets one" 'block b3 | grep -q "budget: none set"'
  check "only the time half shows when only a time budget is set" 'block b4 | grep -q "budget: 35m of 90m " && ! block b4 | grep -q "tokens"'
  check "a record from before budgets (no budget key) uses the repo settings" 'block b5 | grep -q "budget: 35m of 60m, 0.4M of 1.0M tokens" && ! block b5 | grep -q OVER'
  python3 - "$here" "$(block b6)" > "$d/agree" <<'PY'
import re, sys, os
sys.path.insert(0, os.path.join(sys.argv[1], "skills", "workflow-health", "scripts"))
import cost
rows = {r["rule"]: r["detail"] for r in cost.cost_rows(os.getcwd(), os.path.join(sys.argv[1], "skills", "workflow-health", "scripts")) if r["subject"] == "b6"}
minutes, tokens = int(rows["time"].split(" min")[0]), int(rows["tokens"].split(" tokens")[0])
seen = re.search(r"budget: (\d+)m of \d+m, ([\d.]+M) of", sys.argv[2])
print("health %d %s board %s %s" % (minutes, "%.1fM" % (tokens / 1e6), seen.group(1), seen.group(2)))
PY
  check "the board's minutes and tokens agree with health's cost rule on a finished goal" 'grep -qx "health 75 2.5M board 75 2.5M" "$d/agree"'
fi

if want depth; then
  echo "== DEL-6: the decided depth on the board"
  new dsmall; new dlarge; git switch -q main
  python3 - "$here" "$R" <<'PY'
import json, os, sys
sys.path.insert(0, os.path.join(sys.argv[1], "skills", "workflow-delivery", "scripts"))
import fit
for slug, done, touches in (("dsmall", ["one"], ["src/a.py"]), ("dlarge", ["a", "b", "c", "d"], ["src/a.py", "lib/b/c.py"])):
    path = os.path.join(sys.argv[2], slug + ".json")
    s = json.load(open(path)); s.update(status="running", pid=None, size=fit.size_of(done, touches)); json.dump(s, open(path, "w"))
PY
  cfg 'review_depth="condensed"'
  board
  check "under review_depth condensed a small goal's depth decided is condensed, with why" 'block dsmall | grep -q "depth decided: condensed (small: 1 done line, one area)"'
  check "under review_depth condensed a large goal's depth decided is full, with why" 'block dlarge | grep -q "depth decided: full (large: 4 done lines, 2 areas"'
  echo '{"set": {"depth_override": {"depth": "full", "why": "x"}}}' > "$R/dsmall.extra.json"
  board
  check "the owner's override in the sidecar wins over the size" 'block dsmall | grep -q "depth decided: full (owner override: x)"'
  cfg 'review_depth="full"'
fi

if want issues; then
  echo "== DEL-9: the missing private-name list"
  new i1; git switch -q main
  edit i1 "s.update(finding_error='finding commit holds a private name at commit:abc1234 (list line 2). Fix: remove it, then push the finding commit (FINDING_LOCAL)')"
  board
  check "with no private-name list, Issues says nothing is scanned and how to create one" 'issues | grep -q -- "- no private-name list: nothing is scanned (create \$HOME/.workflow-loop/private-names; a file holding only comments says off on purpose)"'
  check "a finding a scan kept local shows under Issues with its place and fix" 'issues | grep -q -- "- i1: a finding stayed local: finding commit holds a private name at commit:abc1234 (list line 2) fix: remove it, then push the finding commit (FINDING_LOCAL)"'
  mkdir -p "$HOME/.workflow-loop"; printf '# off on purpose\n' > "$HOME/.workflow-loop/private-names"
  board
  check "a private-name list holding only comments hides the issue" '! issues | grep -q "no private-name list"'
  rm -rf "$HOME/.workflow-loop"
  edit i1 "s.update(release_pr_waiting='checks pending on https://example.test/pull/7 (#7)')"
  board
  check "a release pull request waiting on its checks shows under Issues with the merge.py fix" 'issues | grep -q -- "- i1: the release pull request waits: checks pending on https://example.test/pull/7 (#7) fix: run merge.py i1 again"'
  LOOP_PRIVATE_NAMES="$d/names" board
  check "an unset list named by LOOP_PRIVATE_NAMES still shows the issue" 'issues | grep -q "no private-name list"'
fi

if want mend; then
  echo "== DEL-7: mend's resume prompt"
  new m1; git switch -q main
  printf '#!/bin/bash\nprintf "%%s" "${!#}" > "%s/prompt.$$"\n' "$d" > "$d/agent.sh"
  cfg "agent_command=[\"bash\", \"$d/agent.sh\"]" 'mend=false'
  git add -A; git commit -qm "Agent"; echo "half done" > partial.txt
  edit m1 "s.update(status='stopped', pid=None, worktree='$d/repo', branch='main', worker='background', flow={'idea': 'done (depth full)', 'plan': 'done (depth full)'}); s.pop('plan_head', None)"
  waitfor() { for _ in $(seq 50); do eval "$1" && return 0; sleep 0.2; done; return 1; }
  dirty=$(git status --porcelain | grep -c .); head=$(git rev-parse --short HEAD)
  python3 "$S/mend.py" --resume m1 > "$d/m1.out" 2>&1
  waitfor 'ls "$d"/prompt.* >/dev/null 2>&1'; p1=$(ls "$d"/prompt.* 2>/dev/null | head -1)
  check "mend's resume prompt names the step to go on from and the exact next command (no commit since the plan: build)" 'grep -q "Resume at step build; the next command is .goal.py step m1 build, then flow.py m1 review." "$p1"'
  check "mend's resume prompt names the uncommitted file count and HEAD short sha" 'grep -q "The worktree has $dirty uncommitted files* at HEAD $head" "$p1"'
  waitfor '[ "$(python3 -c "import json;print(json.load(open(\"$R/m1.json\"))[\"status\"])")" != running ]'
  edit m1 "s.update(status='stopped', pid=None, plan_head='$(git rev-parse HEAD~1)')"
  rm -f "$d"/prompt.*
  python3 "$S/mend.py" --resume m1 > "$d/m2.out" 2>&1
  waitfor 'ls "$d"/prompt.* >/dev/null 2>&1'; p2=$(ls "$d"/prompt.* 2>/dev/null | head -1)
  check "after a commit landed past the plan record, the prompt resumes at review with flow.py SLUG review" 'grep -q "Resume at step review; the next command is .flow.py m1 review." "$p2"'
  waitfor '[ "$(python3 -c "import json;print(json.load(open(\"$R/m1.json\"))[\"status\"])")" != running ]'
  rm -f partial.txt
fi

if want bind; then
  echo "== issue 117: sessions.py bind SLUG self"
  new s1; git switch -q main
  cp "$R/s1.json" "$d/s1.before"
  env -u CLAUDE_CODE_HOST_SESSION_ID -u LOOP_ROLE $SE bind s1 self > "$d/bind0" 2>&1; rc=$?
  check "bind SLUG self with CLAUDE_CODE_HOST_SESSION_ID unset exits 2 with BIND_SELF_UNSET, naming the variable and the fix" '[ $rc = 2 ] && grep -q "CLAUDE_CODE_HOST_SESSION_ID" "$d/bind0" && grep -q "Fix: sessions.py bind s1 <ID>" "$d/bind0" && grep -q "(BIND_SELF_UNSET)" "$d/bind0" && cmp -s "$R/s1.json" "$d/s1.before" && ! grep -q Traceback "$d/bind0"'
  CLAUDE_CODE_HOST_SESSION_ID=s77 env -u LOOP_ROLE $SE bind s1 self > "$d/bind1" 2>&1
  check "bind SLUG self binds the session named by CLAUDE_CODE_HOST_SESSION_ID" 'grep -q "^BOUND s1 to session s77" "$d/bind1" && [ "$(python3 -c "import json;print(json.load(open(\"$R/s1.json\"))[\"session\"][\"id\"])")" = s77 ]'
fi

if [ -z "$only" ]; then
  echo "== sizes"
  for f in board_budget.py live_board.py mend.py session_bind.py sessions.py; do
    check "$f stays under 20,480 bytes" '[ "$(wc -c < "$S/$f")" -lt 20480 ]'
  done
  check "this test stays under 20,480 bytes" '[ "$(wc -c < "$here/dev/toy/test-delivery-board.sh")" -lt 20480 ]'
fi

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
