#!/bin/bash
# reads: skills/workflow-monitoring/scripts/auto.py skills/workflow-monitoring/scripts/board.py
# reads: skills/workflow-monitoring/scripts/board_page.py skills/workflow-monitoring/scripts/board_runs.py
# reads: skills/workflow-monitoring/scripts/board_status.py skills/workflow-monitoring/scripts/checkin.py
# reads: skills/workflow-monitoring/scripts/dep_graph.py skills/workflow-monitoring/scripts/goal_state.py
# reads: skills/workflow-monitoring/scripts/govern_hook.py skills/workflow-monitoring/scripts/graph.py
# reads: skills/workflow-monitoring/scripts/issue_lines.py skills/workflow-monitoring/scripts/live_board.py
# reads: skills/workflow-monitoring/scripts/mend.py skills/workflow-monitoring/scripts/monitor.py
# reads: skills/workflow-monitoring/scripts/operate.py skills/workflow-monitoring/scripts/pool.py
# reads: skills/workflow-monitoring/scripts/prs.py skills/workflow-monitoring/scripts/replan.py
# reads: skills/workflow-monitoring/scripts/reply_hook.py skills/workflow-monitoring/scripts/session_bind.py
# reads: skills/workflow-monitoring/scripts/session_tool.py skills/workflow-monitoring/scripts/sessions.py
# reads: skills/workflow-monitoring/scripts/status_graph.py skills/workflow-monitoring/scripts/watch.py
# reads: skills/workflow-monitoring/scripts/worker.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-setup/scripts/settings.py skills/workflow-setup/scripts/survey.py
# reads: skills/workflow-setup/scripts/seed.py dev/toy/fakegh/gh dev/toy/fakegh/fake.py
# Proves the Monitoring PRD's MON-4 and MON-6..MON-12 and issues 94, 97, 111-115, 122 and 175 with a made-up repo, a
# fake gh and a stand-in session pool. No model is called. usage: test-monitoring-prd.sh [CASE ...] [--dir DIR]
# Cases: mon4 mon6 mon7 mon8 mon9 mon10 mon11 mon12 deps94 issues97 held111 slot112 state113 attempt114 held115
# pool122 merged175 (default: all). Each case prints PASS or FAIL lines; the last line is ALL PASS or N FAILED.
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_ROLE LOOP_SESSION_QUIET LOOP_GOVERN_HOOK CLAUDE_SESSION_ID
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
cases=(); T=""
while [ $# -gt 0 ]; do case "$1" in --dir) T=$2; shift 2;; *) cases+=("$1"); shift;; esac; done
[ ${#cases[@]} -eq 0 ] && cases=(mon4 mon6 mon7 mon8 mon9 mon10 mon11 mon12 deps94 issues97 held111 slot112 state113 attempt114 held115 pool122 merged175)
T=${T:-$(mktemp -d)}; rm -rf "${T:?}"; mkdir -p "$T"; [ -n "${KEEP:-}" ] || toy_on_exit 'rm -rf "$T"'
S="$here/skills/workflow-monitoring/scripts"
export HOME="$T/home" LOOP_BOARD_HEALTH=green PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$T/gh"; mkdir -p "$HOME"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
"$here/dev/toy/make.sh" "$T" >/dev/null || exit 1
cd "$T/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null 2>&1
git switch -q main 2>/dev/null; git merge -q --no-edit workflow-setup 2>/dev/null
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); L="$C/loop"
cfg() { python3 - "$@" <<'PY'
import json, sys
c = json.load(open(".loop/config.json"))
for pair in sys.argv[1:]:
    k, v = pair.split("=", 1)
    c[k] = json.loads(v)
json.dump(c, open(".loop/config.json", "w"), indent=2)
PY
}
cfg parallel=0 mend=false auto_merge=false 'agent_command=["true"]' resume_on_limit=false
git commit -qam "Config" 2>/dev/null
# fresh: an empty loop folder (runs, pool, logs) and an empty queue, before each case
fresh() { rm -rf "$L"; mkdir -p "$L/runs"; printf '# Queue\n' > .loop/queue.md; rm -rf "$T/gh"; }
# run SLUG KEY=JSON ...: write a run record; times are minutes before now, as "-N"
run() { python3 - "$L/runs" "$@" <<'PY'
import datetime, json, os, sys
folder, slug = sys.argv[1], sys.argv[2]
now = datetime.datetime.now(datetime.timezone.utc)
ago = lambda m: (now - datetime.timedelta(minutes=m)).strftime("%Y-%m-%dT%H:%M:%SZ")
rec = {"slug": slug, "goal": "Goal " + slug, "status": "running", "step": "build", "tries": 0, "pr": "", "waits_on": [], "updated": ago(1)}
for pair in sys.argv[3:]:
    k, v = pair.split("=", 1)
    val = json.loads(v)
    rec[k] = ago(int(val[1:])) if isinstance(val, str) and val[:1] == "-" and val[1:].isdigit() else val
json.dump(rec, open(os.path.join(folder, slug + ".json"), "w"))
PY
}
pool() { printf '%s' "$1" > "$L/session-pool.json"; }
field() { python3 -c "import json,sys; d=json.load(open('$L/runs/$1.json')); print(eval(sys.argv[1], {}, {'d': d}))" "$2"; }

case_mon4() {
  fresh; run alpha 'worker="session"' 'session={"id":"s1","name":"worker · alpha"}'
  pool '{"s1": {"name": "worker · alpha", "slug": "alpha", "state": "busy", "since": "2026-01-01T00:00:00Z"}}'
  out=$(python3 "$S/operate.py" run --once 2>&1)
  check "MON-4: a check-in prints the check-in layout, not the live board" \
    'echo "$out" | grep -qx "All sessions" && echo "$out" | grep -qx "Needs you" && echo "$out" | grep -qx "Coming up" && ! echo "$out" | grep -q "LIVE BOARD"'
  echo "$out" | sed -n '/^[0-9]* running/,$p' > "$T/checkin.txt"
  check "MON-5: the check-in passes the reply hook's layout check" 'python3 "$S/reply_hook.py" check "$T/checkin.txt" >/dev/null'
  check "MON-4: report still prints the live board" 'python3 "$S/monitor.py" report 2>&1 | grep -q "LIVE BOARD"'
}

case_mon6() {
  fresh; cfg pool_size=2
  git branch -q loop/gone origin/main; git worktree add -q "$L/worktrees/gone" loop/gone 2>/dev/null
  run gone 'status="running"' 'worker="session"' 'session={"id":"s1","name":"worker · gone"}' "worktree=\"$L/worktrees/gone\""
  pool '{"s1": {"name": "worker · gone", "slug": "gone", "state": "busy"}, "s2": {"name": "w2", "state": "free"}}'
  (cd "$L/worktrees/gone" && FAKE_GH_PR_STATE=MERGED python3 "$S/sessions.py" report gone --status merged --pr https://example.test/pull/1 >"$T/o6" 2>&1)
  check "MON-6: a merged goal's session goes back to the pool" 'grep -q "\"state\": \"free\"" "$L/session-pool.json" && ! grep -q "busy" "$L/session-pool.json"'
  check "MON-6: its worktree and branch are removed, even when reported from inside the worktree" '[ ! -d "$L/worktrees/gone" ] && ! git rev-parse --verify -q refs/heads/loop/gone >/dev/null'
  run edge 'worker="session"'
  pool '{"a": {"slug": "edge", "state": "busy"}, "b": {"state": "free"}, "c": {"state": "free"}}'
  python3 "$S/pool.py" return edge >/dev/null
  check "MON-6: above pool_size the returned session is marked archive" 'python3 -c "import json;assert json.load(open(\"$L/session-pool.json\"))[\"a\"][\"state\"]==\"archive\""'
  pool '{"a": {"slug": "edge", "state": "busy"}, "b": {"state": "free"}}'
  python3 "$S/pool.py" return edge >/dev/null
  check "MON-6: at pool_size the returned session stays in the pool" 'python3 -c "import json;assert json.load(open(\"$L/session-pool.json\"))[\"a\"][\"state\"]==\"free\""'
  cfg pool_size=20
}

hook() { printf '%s' "$1" | python3 "$S/govern_hook.py"; }
case_mon7() {
  fresh; echo op1 > "$L/operation.id"; R=$(pwd -P)
  e='{"session_id":"op1","cwd":"'"$R"'","tool_name":"Edit","tool_input":{"file_path":"x.py"}}'
  b() { printf '{"session_id":"%s","cwd":"%s","tool_name":"Bash","tool_input":{"command":"%s"}}' "$1" "$2" "$3"; }
  check "MON-7: the operation session's Edit is refused" 'hook "$e" | grep -q "\"deny\""'
  check "MON-7: git -C . commit is refused" 'hook "$(b op1 "$R" "git -C . commit -m x")" | grep -q deny'
  check "MON-7: merge.py X && git push is refused segment by segment" 'hook "$(b op1 "$R" "python3 merge.py x && git push origin main")" | grep -q deny'
  check "MON-7: shell keywords don't hide a push" '[ "$(printf "%s" "{ git push; }" | python3 "$S/govern_hook.py" check)" = "BLOCK: git push" ] && [ "$(printf "%s" "if git push; then :; fi" | python3 "$S/govern_hook.py" check)" = "BLOCK: git push" ]'
  check "MON-7: a command that only names git passes" '[ -z "$(hook "$(b op1 "$R" "echo git push")")" ] && [ -z "$(hook "$(b op1 "$R" "grep -rn git commit skills")")" ]'
  check "MON-7: git status and merge.py pass" '[ -z "$(hook "$(b op1 "$R" "git status")")" ] && [ -z "$(hook "$(b op1 "$R" "python3 skills/workflow-release/scripts/merge.py g")")" ]'
  check "MON-7: another session and a worker worktree are never checked" '[ -z "$(hook "$(b w9 "$R" "git commit -m x")")" ] && [ -z "$(hook "$(b op1 "$L/worktrees/x" "git commit -m x")")" ]'
  cfg govern_hook=false
  check "MON-7: govern_hook false turns it off" '[ -z "$(hook "$e")" ]'
  cfg govern_hook=true
  check "MON-7: LOOP_GOVERN_HOOK=0 turns it off for one session" '[ -z "$(printf "%s" "$e" | LOOP_GOVERN_HOOK=0 python3 "$S/govern_hook.py")" ]'
  check "MON-7: the deny names the fix and the off switch" 'hook "$e" | grep -q "govern_hook"'
  hook "$(b dev9 "$R" "grep -rn operate.py.run skills")" >/dev/null; hook "$(b dev9 "$R" "echo python3 operate.py run")" >/dev/null
  check "MON-7: a command that only names operate.py run claims nothing" '[ "$(cat "$L/operation.id")" = op1 ]'
  check "MON-7: wrappers such as timeout and nohup don't hide a push" 'hook "$(b op1 "$R" "timeout -s KILL 60 git push")" | grep -q deny && hook "$(b op1 "$R" "nohup git push")" | grep -q deny'
  hook "$(b op3 "$R" "python3 -u $S/operate.py run --once")" >/dev/null
  check "MON-7: running operate.py run claims the session" '[ "$(cat "$L/operation.id")" = op3 ]'; echo op1 > "$L/operation.id"
  check "MON-7: claim records the session and a worker can't claim" \
    'python3 "$S/operate.py" claim --id op2 | grep -q "replaced op1" && ! LOOP_ROLE=worker python3 "$S/operate.py" claim --id w 2>/dev/null'
}

case_mon8() {
  fresh; run quiet31 'worker="session"' 'updated="-31"' 'session={"id":"s1","name":"worker · quiet31"}'
  run quiet29 'worker="session"' 'updated="-29"' 'session={"id":"s2","name":"worker · quiet29"}'
  pool '{"s1": {"slug": "quiet31", "state": "busy"}, "s2": {"slug": "quiet29", "state": "busy"}}'
  out=$(python3 "$S/checkin.py" 2>&1)
  check "MON-8: a worker silent 31 minutes shows under Needs you" 'echo "$out" | sed -n "/^Needs you/,/^Coming up/p" | grep -q "quiet31: its worker has sent nothing"'
  check "MON-8: a worker silent 29 minutes does not" '! echo "$out" | sed -n "/^Needs you/,/^Coming up/p" | grep -q "quiet29"'
  check "MON-8: the live board names it too" 'python3 "$S/live_board.py" | grep -q "quiet31: its session"'
}

case_mon9() {
  fresh
  for i in $(seq 1 12); do run "pr$i" 'status="done"' 'step="pr"' "pr=\"https://example.test/pull/$i\""; done
  start=$(date +%s); FAKE_GH_SLEEP=2 FAKE_GH_PR_STATE=OPEN python3 "$S/live_board.py" >/dev/null 2>&1; took=$(( $(date +%s) - start ))
  # timing-ok: MON-9 is itself a wall-clock requirement (under 10 s); 12 x 2 s sequential would take 24 s
  check "MON-9: the board for 12 goals builds in under 10 seconds with a slow gh (${took}s)" '[ "$took" -lt 10 ]'
}

case_mon10() {
  fresh
  printf '%s\n' '# Queue' \
    '- slug: qa1 | prd: Mon MON-1 | touches: s/x,s/y | goal: g | done: d' \
    '- slug: qa2 | prd: Mon MON-2 | touches: s/y,s/z | goal: g | done: d' \
    '- slug: big | parts: big-core | goal: g | done: d' \
    '- slug: w1 | depends-on: big | goal: g | done: d' \
    '- slug: w2 | depends-on: big | goal: g | done: d' \
    '- slug: live | goal: g | done: d' > .loop/queue.md
  run live 'status="running"' 'pid=1'
  first=$(python3 "$S/replan.py" plan); second=$(python3 "$S/replan.py" plan)
  check "MON-10: a started goal is logged with its reason" 'echo "$first" | grep -q "start live: started: dependencies met"'
  check "MON-10: same-PRD goals sharing files are proposed merged" 'echo "$first" | grep -q "merge qa1+qa2: same PRD Mon and shared files s/y"'
  check "MON-10: a blocking goal with a ready part is proposed split" 'echo "$first" | grep -q "split big: 2 goals wait on it"'
  check "MON-10: nothing is logged twice" '[ "$second" = "REPLAN: no change" ]'
  check "MON-10: no running goal is stopped" '[ "$(field live "d[\"status\"]")" = running ] && [ "$(field live "d[\"pid\"]")" = 1 ]'
  check "MON-10: the check-in shows the changes with their reasons" 'python3 "$S/checkin.py" --since 0000 | grep -q "merge qa1+qa2: same PRD"'
}

ask() { run "$1" 'status="waiting"' "waiting={\"ask\": \"$2\", \"words\": [\"use a\", \"use b\"], \"recommend\": \"use a\", \"kind\": \"$3\"}"; }
case_mon11() {
  fresh; ask r1 "Which helper name?" routine; ask r2 "Which layout for the keyboard map?" routine
  ask d1 "Pick one" destructive; ask n1 "Pick one" ""; ask k1 "Delete the old cache?" routine; ask o1 "Pick one again" routine
  ask m1 "Pick one" money; ask s1 "Pick one" security; ask w1 "Pick one" owner; ask x1 "Pick one" sideways
  python3 "$S/operate.py" send o1 "use b" >/dev/null 2>&1  # the owner answers o1 through the real path
  python3 "$S/auto.py" pass >/dev/null 2>&1
  check "MON-11: a routine decision is answered with its recommended option and logged" 'grep -q "| r1 | AUTO | which helper name? | use a |" "$L/auto.log"'
  check "MON-11: the answer reaches the worker's inbox" 'grep -q "use a" "$L/inbox/r1.txt"'
  check "MON-11: money, security, owner and unknown kinds wait and send nothing" \
    '( for g in m1 s1 w1 x1; do grep -q "| $g | WAITS |" "$L/auto.log" || exit 1; [ ! -s "$L/inbox/$g.txt" ] || exit 1; done )'
  check "MON-11: keyboard is not a risky word" 'grep -q "| r2 | AUTO |" "$L/auto.log"'
  check "MON-11: destructive, no kind and a risky word wait for the owner" \
    'grep -q "| d1 | WAITS |.*destructive decision is the owner" "$L/auto.log" && grep -q "| n1 | WAITS |.*no kind given" "$L/auto.log" && grep -q "| k1 | WAITS |.*mentions delete" "$L/auto.log"'
  check "MON-11: an owner answer sent with operate.py send is kept, and that goal goes to the owner" \
    'grep -q "\"slug\": \"o1\".*\"source\": \"owner\"" "$L/answers.jsonl" && grep -q "| o1 | WAITS |.*owner has answered" "$L/auto.log"'
  n=$(wc -l < "$L/auto.log"); python3 "$S/auto.py" pass >/dev/null 2>&1
  check "MON-11: each question is decided once" '[ "$(wc -l < "$L/auto.log")" -eq "$n" ]'
  ask r3 "Which name?" routine; cfg full_auto=false; python3 "$S/auto.py" pass >/dev/null 2>&1
  check "MON-11: full_auto off applies at the next decision" '! grep -q "| r3 |" "$L/auto.log"'
  cfg full_auto=true; python3 "$S/auto.py" pass >/dev/null 2>&1
  check "MON-11: turned back on, the same decision is answered" 'grep -q "| r3 | AUTO |" "$L/auto.log"'
  check "MON-11: the check-in lists the auto answer with its revert" 'python3 "$S/checkin.py" --since 0000 | grep -q "r1: .* -> use a; revert"'
}

case_mon12() {
  fresh; cfg pool_size=4
  pool '{"s1": {"slug": "busy1", "state": "busy"}, "s2": {"state": "free"}}'
  printf '%s\n' '# Queue' '- slug: n1 | goal: g | done: d' '- slug: n2 | goal: g | done: d' '- slug: n3 | goal: g | done: d' > .loop/queue.md
  check "MON-12: the pool shows free, busy and total" 'python3 "$S/pool.py" status | grep -q "pool: 1 free, 1 busy, 2 total (target 4)"'
  check "MON-12: when the pool runs low it asks for every missing session" 'python3 "$S/pool.py" need --ready 3 | grep -q "^NEED 2$"'
  check "MON-12: the check-in asks the owner with the one-step fix" 'python3 "$S/checkin.py" | grep -q "session pool is low: 1 free for 3 ready goals; create 2 sessions"'
  check "MON-12: adding the same id twice counts it once" 'python3 "$S/pool.py" add s3 s3 | grep -q "^POOLED 1 session"'
  python3 "$S/pool.py" add s3 s4 >/dev/null
  check "MON-12: pool.py add registers the new sessions as free" 'python3 "$S/pool.py" status | grep -q "3 free, 1 busy, 4 total"'
  check "MON-10/11: a bad since time is refused" '! python3 "$S/auto.py" since notadate 2>/dev/null && ! python3 "$S/replan.py" since notadate 2>/dev/null && ! python3 "$S/checkin.py" --since junk 2>/dev/null'
  pool '{"s1": {"slug": "busy1", "state": "busy"}}'
  python3 "$S/pool.py" decline --ready 3 >/dev/null
  check "MON-12: no pool hides the ask; a ready goal still waits with its fix" \
    'out=$(python3 "$S/pool.py" need --ready 3); echo "$out" | grep -q "declined" && echo "$out" | grep -q "wait for a session"'
  cfg pool_size=1
  check "MON-12: a full pool makes ready goals wait under Needs you" 'python3 "$S/pool.py" need --ready 2 | grep -q "pool full (1 of 1 busy)"'
  cfg pool_size=20
}

case_deps94() {
  fresh; run a 'pid=1'; run b 'pid=1'
  printf '%s\n' '# Queue' '- slug: c | depends-on: a, b | goal: g | done: d' '- slug: dd | depends-on: c | goal: g | done: d' > .loop/queue.md
  out=$(python3 "$S/live_board.py" | sed -n '/^Dependencies/,/^Finish/p')
  check "#94: dependencies are drawn top to bottom with arrows" 'echo "$out" | grep -qx "  v" && echo "$out" | grep -q "\[ \] c <- a, b" && echo "$out" | grep -q "\[ \] dd <- c"'
  check "#94: the graph has its legend" 'echo "$out" | grep -q "\[>\] running \[=\] holding \[ \] queued \[?\] you \[!\] stuck"'
  check "#94: every line fits 60 columns" '! echo "$out" | awk "length > 60" | grep -q .'
}

case_issues97() {
  fresh
  for g in u1 u2 u3 u4; do run "$g" 'status="failed"' "finding=\"API Error: 429 {\\\"type\\\":\\\"error\\\",\\\"error\\\":{\\\"message\\\":\\\"You have hit your weekly usage limit, resets Nov 11 4pm\\\"}} at /srv/me/very/long/path/agent.log line 4000\""; done
  out=$(python3 "$S/live_board.py")
  check "#97: four goals stopped by one usage limit share one Issues line" 'echo "$out" | grep -q "usage limit: 4 goals paused until Nov 11 4pm" && [ "$(echo "$out" | grep -c "usage limit")" -eq 1 ]'
  check "#97: raw agent output is never shown" '! echo "$out" | grep -q "API Error\|429\|agent.log"'
  check "#97: every line fits 60 columns" '! echo "$out" | awk "length > 60" | grep -q .'
  check "#97: while all work is paused the finish says so" 'echo "$out" | sed -n "/^Finish/,\$p" | grep -q "paused until Nov 11 4pm"'
}

case_held111() {
  fresh; run held1 'worker="session"' 'session={"id":"s9","name":"worker · held1"}'
  pool '{"s2": {"name": "worker · fz", "slug": "fz", "state": "busy", "since": "2026-01-01T00:00:00Z"}}'
  printf '%s\n' '# Queue' '- slug: fz | goal: g | done: d' > .loop/queue.md
  out=$(python3 "$S/monitor.py" report 2>&1)
  check "#111: report lists held and freezing goals" 'echo "$out" | sed -n "/^HELD OR FREEZING/,/^QUEUED/p" | grep -q "held1: held" && echo "$out" | sed -n "/^HELD OR FREEZING/,/^QUEUED/p" | grep -q "fz: freezing"'
  python3 "$S/board.py" board >/dev/null 2>&1
  check "#111: the board digest counts held and freezing goals" 'grep -q "1 held, 1 freezing" "$L/board.json"'
}

case_slot112() {
  out=$(cd "$S" && python3 -c '
import graph
run = {"slug": "h", "status": "running", "worker": "session"}
print(graph.holds_slot(run, {}), graph.holds_slot(run, {"h": {"id": "s"}}), graph.holds_slot(run, None))
start, held = graph.ready([{"slug": "q", "depends": [], "done": ["d"], "goal": "g"}], {"h": run}, 1, {}, "")
print([g["slug"] for g in start])')
  check "#112: a held session goal whose session was freed holds no slot" '[ "$(echo "$out" | head -1)" = "False True True" ]'
  check "#112: so a queued goal can start in that slot" '[ "$(echo "$out" | tail -1)" = "['"'"'q'"'"']" ]'
}

case_state113() {
  fresh; run h1 'worker="session"'; run r1 'pid=1'; run w1 'status="waiting"' 'waiting={"ask":"q","words":["a"]}'
  pool '{}'
  out=$(cd "$S" && python3 - "$L" <<'PY'
import json, os, sys, graph, goal_state, live_board
folder = sys.argv[1]
runs = [json.load(open(os.path.join(folder, "runs", f))) for f in sorted(os.listdir(os.path.join(folder, "runs")))]
taken = graph.assigned(graph.read_pool(os.path.join(folder, "session-pool.json"))[0])
print(all(graph.holds_slot(r, taken) == goal_state.holds_slot(r, taken) for r in runs),
      all(live_board.is_held(r, taken) == goal_state.held(r, taken) for r in runs),
      [goal_state.classify(r, taken) for r in runs])
PY
)
  check "#113: graph, live board and goal_state agree on every goal" 'echo "$out" | grep -q "^True True \[.held., .running., .waiting.\]"'
}

case_attempt114() {
  fresh; git branch -q loop/att 2>/dev/null; mkdir -p "$L/worktrees"
  run att 'status="running"' 'step="build"' "worktree=\"$T/repo\""
  python3 "$S/sessions.py" bind att sA >/dev/null 2>&1; python3 "$S/sessions.py" free att >/dev/null 2>&1
  python3 "$S/sessions.py" bind att sB --force >/dev/null 2>&1
  python3 "$S/sessions.py" report att --step qa --attempt 1 >/dev/null 2>&1
  check "#114: a report from an older attempt is recorded, not applied" '[ "$(field att "d[\"step\"]")" = build ] && [ "$(field att "d[\"reports\"][-1][\"status\"]")" = stale ]'
  check "#114: a non-number attempt is refused and changes nothing" '! python3 "$S/sessions.py" report att --step qa --attempt abc >/dev/null 2>&1 && [ "$(field att "d[\"step\"]")" = build ]'
  python3 "$S/sessions.py" report att --step qa --attempt 2 >/dev/null 2>&1
  check "#114: the current attempt's report is applied" '[ "$(field att "d[\"step\"]")" = qa ]'
  python3 "$S/pool.py" return att >/dev/null 2>&1
  check "#114: a freed session keeps who it was freed from" 'python3 -c "import json;assert json.load(open(\"$L/session-pool.json\"))[\"sB\"][\"history\"][-1][\"slug\"]==\"att\""'
}

case_held115() {
  fresh; run h1 'updated="-10"'; pool '{}'
  python3 -c "import json,datetime;json.dump({'h1':(datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')},open('$L/held.json','w'))"
  check "#115: the board shows how long the goal has been held" 'python3 "$S/live_board.py" | grep -q "worker: none (held 3h"'
  rm -f "$L/held.json"; python3 "$S/replan.py" plan >/dev/null
  check "#115: a goal first seen held gets its held time stamped" 'grep -q "\"h1\"" "$L/held.json"'
}

case_pool122() {
  fresh; run old 'status="retired"'
  pool '{"bad": "not an object", "s1": {"name": "w1", "slug": "old", "state": "busy"}, "s2": {"state": "free"}}'
  check "#122: one malformed pool entry no longer blocks the pool" 'python3 "$S/sessions.py" list >/dev/null 2>&1 && python3 "$S/pool.py" status | grep -q "1 free, 1 busy"'
  check "#122: the malformed entry is set aside and named in the check-in" '[ -f "$L/session-pool.bad.json" ] && python3 "$S/checkin.py" | grep -q "set aside in session-pool.bad.json"'
  check "#122: a retired goal's busy session shows under Needs you" 'python3 "$S/checkin.py" | grep -q "old is retired but session w1 is still busy"'
  python3 "$S/pool.py" return old >/dev/null
  check "#122: pool.py return frees it" '! grep -q busy "$L/session-pool.json"'
}

case_merged175() {
  fresh; run donem 'status="done"' 'step="release"' 'pr="https://example.test/pull/9"' 'report={"status":"merged","text":"merged"}'
  pool '{"s1": {"name": "worker · donem", "slug": "donem", "state": "busy"}}'
  out=$(FAKE_GH_PR_STATE=MERGED python3 "$S/sessions.py" report donem --status merged --pr https://example.test/pull/9 2>&1)
  check "#175: a merged report on a done goal frees its session" 'echo "$out" | grep -q KEPT && ! grep -q busy "$L/session-pool.json"'
}

for c in "${cases[@]}"; do "case_$c"; done
[ "$fails" -eq 0 ] && echo "ALL PASS" || echo "$fails FAILED"
[ "$fails" -eq 0 ]
