#!/bin/bash
# Proves worker sessions with a stand-in session tool: assignment, renaming, the report path, reuse of a finished
# session for the next goal, the background fallback, steps run inside the session, and issue 98 (a goal moved into a
# session shows with its session name and step, never as a failed background worker). No model is called.
# usage: test-session-workers.sh [DIR]
set -u
unset LOOP_ROLE LOOP_SESSION LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # these tests act as the operation session
here=$(cd "$(dirname "$0")/../.." && pwd)
T=${1:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"
S="$here/skills/workflow-monitoring/scripts"
W="python3 $S/watch.py"; SE="python3 $S/sessions.py"; LB="python3 $S/live_board.py"
export HOME="$T/home" FAKE_AGENT="$T/fake" LOOP_BOARD_HEALTH=green; mkdir -p "$HOME" "$FAKE_AGENT"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
export LOOP_FLOW="$T/flow.json"
mkdir -p "$T/bin"; printf '#!/bin/bash\necho "gh: no answer" >&2; exit 1\n' > "$T/bin/gh"; chmod +x "$T/bin/gh"; export PATH="$T/bin:$PATH"
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
C=$(cd "$(git rev-parse --git-common-dir)" && pwd)
field() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]));v=d;exec('for k in sys.argv[2].split(\".\"): v=(v or {}).get(k)');print(v)" "$C/loop/runs/$1.json" "$2"; }
# A stand-in agent for the background fallback, and a stand-in session tool that logs each call and numbers sessions.
printf '#!/bin/bash\nslug=$(grep -oE "Slug: [a-z0-9-]+" <<<"${!#}" | head -1 | cut -d" " -f2)\ntouch "$FAKE_AGENT/agent-$slug"\n' > "$T/agent.sh"
cat > "$T/tool.sh" <<'TOOL'
#!/bin/bash
echo "$1 $2 ${3:+$(head -c 60 <<<"$3" | tr '\n' ' ')}" >> "$TOOL_LOG"
[ -n "${TOOL_FAIL:-}" ] && exit 1
if [ "$1" = start ]; then n=$(( $(cat "$TOOL_LOG.n" 2>/dev/null || echo 0) + 1 )); echo $n > "$TOOL_LOG.n"; echo "s$n"; fi
TOOL
chmod +x "$T/tool.sh"; export TOOL_LOG="$T/tool.log"
python3 - "$T/agent.sh" <<'PY'
import json, sys
c = json.load(open(".loop/config.json")); c["agent_command"] = ["bash", sys.argv[1]]; c["parallel"] = 0; c["mend"] = False
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
git commit -qam "Agent"; git push -q origin main
go() { $W go "Goal $1" --done "Line $1" --slug "$1" >/dev/null 2>&1; }

echo "== assignment and renaming"
LOOP_SESSION_TOOL="$T/tool.sh" go a
check "a ready goal gets a new worker session from the session tool" 'grep -q "^start worker · a" "$TOOL_LOG" && [ "$(field a session.id)" = s1 ]'
check "the session is renamed worker · <goal>" 'grep -q "^rename s1 worker · a" "$TOOL_LOG" && [ "$(field a session.name)" = "worker · a" ]'
check "the session is sent the goal, its worktree and the report rules" 'grep -q "^send s1 You are the worker session for goal a" "$TOOL_LOG" && $SE list | grep -q "^s1  busy  worker · a  a$"'
check "the run record says session, running, with no pid and no background agent" '[ "$(field a worker)" = session ] && [ "$(field a status)" = running ] && [ "$(field a pid)" = None ] && [ ! -e "$FAKE_AGENT/agent-a" ]'

echo "== the report path"
$SE report a --step build >/dev/null
check "a worker's step report is recorded on the run" '[ "$(field a step)" = build ] && python3 -c "import json,sys;assert json.load(open(sys.argv[1]))[\"reports\"][-1][\"text\"]==\"worker · a: step build, running\"" "$C/loop/runs/a.json"'
$LB > "$T/board1"
check "the live board shows the running goal's worker session name and current step" 'grep -q "^    worker: session worker · a$" "$T/board1" && grep -q "\[build\]" "$T/board1"'

echo "== reuse of a finished session"
$SE report a --status merged --pr https://x/pull/1 >/dev/null
check "a merged result is recorded and frees the session" '[ "$(field a report.status)" = merged ] && $SE list | grep -q "^s1  free"'
LOOP_SESSION_TOOL="$T/tool.sh" go b
check "the next ready goal reuses the finished session, renamed again" '[ "$(field b session.id)" = s1 ] && grep -q "^rename s1 worker · b" "$TOOL_LOG" && [ "$(grep -c "^start" "$TOOL_LOG")" = 1 ]'

echo "== the background fallback"
TOOL_FAIL=1 LOOP_SESSION_TOOL="$T/tool.sh" go c
for _ in $(seq 50); do [ -e "$FAKE_AGENT/agent-c" ] && break; sleep 0.1; done
check "a tool that can't start a session falls back to a background process" '[ "$(field c worker)" = background ] && [ -e "$FAKE_AGENT/agent-c" ] && grep -q "could not start" "$C/loop/runs/c.json"'
go d
check "no session tool at all also falls back, and says why" '[ "$(field d worker)" = background ] && grep -q "no session tool is set" "$C/loop/runs/d.json"'
python3 - "$C/loop/runs/c.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["status"] = "running"; json.dump(s, open(sys.argv[1], "w"))
PY
$LB > "$T/board2"
check "the board marks a fallback goal as background" 'grep -q "^    worker: background (the session tool could not start a session)$" "$T/board2"'

echo "== steps run inside the worker session"
R="$C/loop/runs"; (cd "$C/loop/worktrees/b" && LOOP_ROLE=worker python3 "$here/skills/workflow-delivery/scripts/flow.py" b idea > "$T/f1" 2>&1)
check "flow.py starts no headless agent for a session goal and names the skill to run in the session" 'grep -q "^IN SESSION idea: no headless agent" "$T/f1" && [ ! -e "$R/b.idea.job" ]'
printf 'Shaped it.\nSTEP: done\n' > "$R/b.idea.txt"
(cd "$C/loop/worktrees/b" && LOOP_ROLE=worker python3 "$here/skills/workflow-delivery/scripts/flow.py" b idea > "$T/f2" 2>&1 \
  && LOOP_ROLE=worker python3 "$here/skills/workflow-delivery/scripts/goal.py" record b idea --file "$R/b.idea.txt" > "$T/f3" 2>&1)
check "the session's reply is recorded with goal.py record" 'grep -q "^NEXT: goal.py record b idea" "$T/f2" && grep -q "^RECORDED idea done" "$T/f3"'

(cd "$C/loop/worktrees/b" && LOOP_ROLE=worker python3 "$here/skills/workflow-delivery/scripts/flow.py" b idea > "$T/f4" 2>&1)
check "a reply left by an earlier try is never recorded again: the step is asked for afresh" 'grep -q "^IN SESSION idea" "$T/f4" && [ -e "$R/b.idea.txt.last" ] && [ ! -e "$R/b.idea.ran" ]'
python3 - "$C/loop/sessions.json" <<'PY'
import json, sys
p = json.load(open(sys.argv[1])); p["dead"] = {"name": "worker · old", "slug": "old", "state": "free"}; json.dump(p, open(sys.argv[1], "w"))
PY
printf '#!/bin/bash\n[ "$2" = dead ] && exit 1\nexec "%s" "$@"\n' "$T/tool.sh" > "$T/tool2.sh"; chmod +x "$T/tool2.sh"
LOOP_SESSION_TOOL="$T/tool2.sh" go e
check "a free session that can't be reached is skipped for a new one before any fallback" '[ "$(field e worker)" = session ] && [ "$(field e session.id)" = s2 ] && $SE list | grep -q "^dead  unreachable"'

echo "== issue 98: a goal moved into a session"
python3 - "$R/d.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))
s.update(status="failed", pid=None, step="build", finding="the agent ended (exit 1): usage limit reached",
         report={"status": "failed", "text": "worker d reports failed: usage limit reached", "pr": "", "at": "x"})
json.dump(s, open(sys.argv[1], "w"))
PY
$SE bind d local_123 >/dev/null
$SE report d --step review >/dev/null
$LB > "$T/board3"
issues=$(sed -n '/^Issues/,/^Running goals/p' "$T/board3")
check "issue 98: a goal worked in a session shows its session name and current step, never as a failed background worker" \
  'grep -q "^- d " "$T/board3" && grep -q "^    worker: session worker · d$" "$T/board3" && grep -q "\[review\]" "$T/board3" && ! grep -q "d is failed" <<<"$issues" && ! grep -q "usage limit" "$T/board3" && [ "$(field d status)" = running ]'
python3 - "$R/c.json" "$$" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s.update(status="running", pid=int(sys.argv[2])); json.dump(s, open(sys.argv[1], "w"))
PY
check "bind refuses a goal still running as a background process" '$SE bind c x 2>&1 | grep -q "^REFUSED: c is running as background pid"'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
