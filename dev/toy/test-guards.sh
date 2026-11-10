#!/bin/bash
# reads: skills/workflow-delivery/scripts/ skills/workflow-monitoring/scripts/
# reads: skills/workflow-setup/scripts/setup.py
# Proves the loop guards: goals stop only for real failures. A format rule binds only steps started after it (147); a
# refusal that changes nothing costs no try (148); the operation resumes a stopped session goal (149); touches widen
# and a finished goal's finding is only noted (157); the worker refusal says exactly how (121); bind hands over the
# worktree and refuses an outside folder (160, the owner's choice a). No model is called.
# usage: test-guards.sh [DIR] [g1|g2|g3|g4|g5|g6|g7]   (no part: all)
set -u
unset LOOP_ROLE LOOP_SESSION LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # this script acts as the operation unless told
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; part=${2:-all}; rm -rf "${d:?}"; mkdir -p "$d"
export HOME="$d/home"; mkdir -p "$HOME"
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
D="$here/skills/workflow-delivery/scripts"; S="$here/skills/workflow-monitoring/scripts"
goal="python3 $D/goal.py"; F="python3 $D/flow.py"; SE="python3 $S/sessions.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" LOOP_FLOW="$d/flow.json"
cd "$d/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
C=$(cd "$(git rev-parse --git-common-dir)" && pwd); R="$C/loop/runs"; TREE=$(pwd -P)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
want() { [ "$part" = all ] || [ "$part" = "$1" ]; }
field() { python3 -c "import json,sys;d=json.load(open(sys.argv[1]));v=d;exec('for k in sys.argv[2].split(\".\"): v=(v or {}).get(k) if isinstance(v, dict) else None');print(v)" "$R/$1.json" "$2"; }
setf() { python3 - "$R/$1.json" "$2" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s.update(json.loads(sys.argv[2])); json.dump(s, open(sys.argv[1], "w"), indent=2)
PY
}
new() { git switch -q main; LOOP_ROLE=worker $goal new "$1" --here --goal "Goal $1" --done "Line $1" --touches skills/a >/dev/null; }
rec() { printf '%b\n' "$3" > "$d/reply.txt"; LOOP_ROLE=worker $goal record "$1" "$2" --file "$d/reply.txt" --in-session 2>&1; }
cat > "$d/tool.sh" <<'TOOL'
#!/bin/bash
echo "$1 $2 ${3:+$(head -c 120 <<<"$3" | tr '\n' ' ')}" >> "$TOOL_LOG"
[ -n "${TOOL_FAIL:-}" ] && { echo "tool: no route to session" >&2; exit 1; }
[ "$1" = send ] && printf '%s\n' "$3" > "$TOOL_LOG.sent.$2"
[ "$1" = start ] && echo "s-new"
exit 0
TOOL
chmod +x "$d/tool.sh"; export TOOL_LOG="$d/tool.log"; : > "$TOOL_LOG"

if want g1; then
echo "== g1 (147): a format rule binds only steps started after it"
# Value: protects=done line 1; fails_when=a rule added mid-goal fails a step already under way, or its refusal hides the
# rule; why_new=no rule ever carried the steps it binds; seam=rules_at edited by hand; no_claim=a real upgrade of a running
# worktree (simulated by removing the rule id from the step's rules_at)
new g1; $SE bind g1 s1 >/dev/null
check "a new goal's first step starts under every rule known" '[ "$(field g1 rules_at.idea)" = "$(python3 $D/guards.py known | python3 -c "import json,sys;print(json.load(sys.stdin))")" ]'
setf g1 '{"rules_at": {"idea": ["depth-condensed", "full-markers"]}}'
out=$(rec g1 idea 'STEP: done')
check "a step started before the DEPTH rule records without a DEPTH line, and the skip is logged" 'grep -q "^RECORDED idea done in session (depth not stated)" <<<"$out" && grep -q "rule depth-line (v0.12.1) not applied: idea started before it" "$R/g1.json"'
check "the next step starts under the rules known now" 'grep -q depth-line <<<"$(field g1 rules_at.plan)"'
out=$(rec g1 plan 'STEP: done'); rc=$?
check "a step started after the rule is refused, naming the rule and the release that added it, with no try" '[ $rc = 2 ] && grep -q "REFUSED (no try used): plan refused: no DEPTH line (rule depth-line, added in v0.12.1)" <<<"$out" && grep -q "(FORMAT_RULE depth-line)" <<<"$out" && [ "$(field g1 tries)" = 0 ]'
setf g1 '{"rules_at": null}'
out=$(rec g1 plan 'STEP: done')
check "a run record with no rules_at (a goal from before) is held to every rule known, as today" 'grep -q "rule depth-line, added in v0.12.1" <<<"$out"'
out=$(rec g1 plan 'DEPTH: full\nSTEP: done')
check "a record whose rules_at is null still advances, and the next step gets its rules" 'grep -q "^RECORDED plan" <<<"$out" && grep -q depth-line <<<"$(field g1 rules_at.review)"'
python3 - "$d/flow.json" <<'PY2'
import json, sys
s = json.load(open(sys.argv[1])); s["full_markers"] = {"review": "not-a-list"}; json.dump(s, open(sys.argv[1], "w"))
PY2
setf g1 '{"rules_at": {"review": ["depth-line"]}}'
out=$(rec g1 review 'DEPTH: full\nSTEP: done')
check "a malformed marker setting doesn't hold a step that started before the marker rule" 'grep -q "^RECORDED review" <<<"$out" && [ "$(field g1 status)" = running ]'
python3 - "$d/flow.json" <<'PY2'
import json, sys
s = json.load(open(sys.argv[1])); s.pop("full_markers", None); json.dump(s, open(sys.argv[1], "w"))
PY2
fi

if want g2; then
echo "== g2 (148): a refusal that changes nothing costs no try"
# Value: protects=done line 2; fails_when=a format slip or a wrong HEAD burns the shared try budget or stops the goal;
# why_new=format refusals were failed tries; seam=none; no_claim=none beyond protects
new g2; $SE bind g2 s2 >/dev/null; rec g2 idea 'DEPTH: full\nSTEP: done' >/dev/null
out=$(rec g2 plan 'STEP: done')
check "a missing DEPTH line leaves tries 0 and status running, keeps the run marker, and prints NEXT" '[ "$(field g2 tries)" = 0 ] && [ "$(field g2 status)" = running ] && [ -e "$R/g2.plan.ran" ] && grep -q "^NEXT: write .DEPTH: full." <<<"$out"'
for i in 2 3 4 5; do rec g2 plan 'STEP: done' >/dev/null; done
check "the 5th refusal in a row leaves a note the board shows" 'grep -q "5 refused records in a row" <<<"$(field g2 note.text)" && [ "$(field g2 tries)" = 0 ]'
out=$(rec g2 plan 'DEPTH: full\nSTEP: done')
check "a good record clears the count and the note" 'grep -q "^RECORDED plan" <<<"$out" && [ "$(field g2 refusals)" = 0 ] && [ "$(field g2 note)" = None ]'
out=$(rec g2 review 'DEPTH: full\nall good'); rc=$?
check "a session reply with no STEP line is refused with no try" '[ $rc = 2 ] && grep -q "REFUSED (no try used): the review reply has no STEP line" <<<"$out" && grep -q "(NO_STEP_LINE)" <<<"$out" && [ "$(field g2 tries)" = 0 ]'
out=$(LOOP_ROLE=worker $goal record g2 qa --file "$d/reply.txt" 2>&1); rc=$?
check "the qa lane not passed on HEAD (a wrong HEAD) says no try is used, exit 2" '[ $rc = 2 ] && grep -q "^REFUSED (no try used): the qa lane has not passed on .* (LANE_MISSING)" <<<"$out" && [ "$(field g2 tries)" = 0 ]'
for i in 1 2 3 4 5 6 7 8 9; do rec g2 review 'DEPTH: full\nall good' >/dev/null; done
check "10 refused records in a row put the goal in waiting for the owner, still with no try" '[ "$(field g2 status)" = waiting ] && [ "$(field g2 tries)" = 0 ] && grep -q "10 refused records in a row" <<<"$(field g2 waiting.ask)"'
check "a touches path with a comma or a newline is refused" '$goal touches g2 --add "a,b" --why x 2>&1 | grep -q TOUCHES_PATH && $goal touches g2 --add "$(printf "a\nb")" --why x 2>&1 | grep -q TOUCHES_PATH'
new g2h
export FAKE_SKILL_OUT='crashed halfway'; LOOP_ROLE=worker $F g2h idea --wait 5 >/dev/null 2>&1; LOOP_ROLE=worker $F g2h idea --wait 10 >/dev/null 2>&1; unset FAKE_SKILL_OUT
out=$(LOOP_ROLE=worker $goal record g2h idea --file "$R/g2h.idea.txt" 2>&1)
check "a background run's reply with no STEP line still costs a try (it may have crashed)" 'grep -q "TRY 1 OF 3 FAILED: idea gave no STEP line" <<<"$out" && [ "$(field g2h tries)" = 1 ]'
fi

if want g3; then
echo "== g3 (149): the operation resumes a stopped session goal"
# Value: protects=done line 3; fails_when=a stopped session goal needs hand-edited JSON, a worker resets its own budget,
# or resume takes a session serving another goal; why_new=only watch.py resume (headless) existed; seam=a stand-in session
# tool; no_claim=a real app session receiving the message
W3="$d/wt3"; git worktree add -q -b loop/g3 "$W3" main; W3=$(cd "$W3" && pwd -P)  # the goal's own worktree
cd "$W3"; LOOP_ROLE=worker $goal new g3 --here --goal "Goal g3" --done "Line g3" >/dev/null
$SE bind g3 s3 >/dev/null; rec g3 idea 'DEPTH: full\nSTEP: done' >/dev/null; cd "$d/repo"
stop3() { setf g3 '{"status": "stopped", "tries": 3, "refusals": 2, "finding": "Failed 3 tries", "report": {"status": "failed"}, "note": {"text": "x"}}'; }
free3() { python3 - "$C/loop/session-pool.json" "$1" "$2" <<'PY'
import json, sys
p = json.load(open(sys.argv[1])); p["s3"] = {"name": "worker · g3", "slug": sys.argv[3], "state": sys.argv[2]}; json.dump(p, open(sys.argv[1], "w"))
PY
}
stop3; free3 free g3
out=$(LOOP_ROLE=worker $goal resume g3 --why "limit passed" 2>&1)
check "a worker can't resume its own goal" 'grep -q "(WORKER_SELF_REPAIR)" <<<"$out" && [ "$(field g3 status)" = stopped ]'
git switch -q main  # resume runs from the main checkout, not the goal's worktree
out=$(LOOP_SESSION_TOOL="$d/tool.sh" $goal resume g3 --why "limit passed" 2>&1)
check "resume from another checkout revives the goal: running, tries 0, report cleared, who and why logged" 'grep -q "^RESUMED g3 at plan$" <<<"$out" && [ "$(field g3 status)" = running ] && [ "$(field g3 tries)" = 0 ] && [ "$(field g3 report)" = None ] && grep -q "resumed by operation session: limit passed" "$R/g3.json"'
check "resume reserves the session and tells it where to continue, starting no process" 'grep -q "\"slug\": \"g3\"" "$C/loop/session-pool.json" && grep -q "Continue at plan in " "$TOOL_LOG.sent.s3" && [ "$(field g3 pid)" = None ]'
resumed=$(python3 -c "import json;s=json.load(open('$R/g3.json'));print([s.get(k) for k in ('status','tries','refusals','finding','waiting','note','report')])")
out=$($goal resume g3 --why again 2>&1)
check "a running goal doesn't resume" 'grep -q "g3 is running; only a failed or stopped goal resumes (RESUME_STATUS)" <<<"$out"'
stop3; free3 busy other
out=$($goal resume g3 --why "x" 2>&1)
check "a session now serving another goal is refused, and nothing changes" 'grep -q "session s3 now serves goal other.*(SESSION_TAKEN)" <<<"$out" && [ "$(field g3 status)" = stopped ] && grep -q "\"slug\": \"other\"" "$C/loop/session-pool.json"'
free3 free g3; sed -i.bak 's/^1\. Line g3$/1. Line g3 changed/' "$W3/.loop/goals/g3.md"
out=$($goal resume g3 --why "x" 2>&1); rc=$?
check "changed done lines are refused with exit 1 and nothing written" '[ $rc = 1 ] && grep -q "(DONE_LINES_CHANGED)" <<<"$out" && [ "$(field g3 status)" = stopped ]'
mv "$W3/.loop/goals/g3.md.bak" "$W3/.loop/goals/g3.md"
out=$(LOOP_SESSION_TOOL="$d/tool.sh" TOOL_FAIL=1 $goal resume g3 --why "retry" 2>&1)
check "a failed send says the message wasn't delivered and prints the resend command" 'grep -q "^RESUMED g3 at plan (message not delivered)" <<<"$out" && grep -q "^NEXT: python3 .*sessions.py send g3 " <<<"$out"'
stop3; $SE bind g3 s9 >/dev/null
bound=$(python3 -c "import json;s=json.load(open('$R/g3.json'));print([s.get(k) for k in ('status','tries','refusals','finding','waiting','note','report')])")
check "bind and resume leave the same revived fields" '[ "$bound" = "$resumed" ] && grep -q "revived by bind (was stopped)" "$R/g3.json"'
new g3b; setf g3b '{"status": "stopped"}'
out=$($goal resume g3b --why "x" 2>&1)
check "a goal with no session is pointed at bind or watch.py resume" 'grep -q "g3b has no session. Fix: sessions.py bind g3b ID (bind revives it), or watch.py resume g3b .*(RESUME_NO_SESSION)" <<<"$out"'
stop3; setf g3 '{"worktree": "/nonexistent/g3"}'
out=$($goal resume g3 --why "x" 2>&1)
check "a lost worktree is refused" 'grep -q "(RESUME_NO_WORKTREE)" <<<"$out"'
setf g3 "{\"worktree\": \"$W3\"}"
fi

if want g4; then
echo "== g4 (157): touches widen with a reason; a finished goal's finding is only noted"
# Value: protects=done line 4; fails_when=widening needs hand edits, a worker's save erases it, or a finding stops a
# finished goal; why_new=no command existed and finding always stopped; seam=none; no_claim=the operation's planner
# acting on the widened list
new g4; $SE bind g4 s4 >/dev/null
out=$($goal touches g4 --add skills/b --why "needs the b scripts" 2>&1)
check "touches --add writes only the sidecar: the run record and the worktree are unchanged" 'grep -q "^TOUCHES g4 +skills/b$" <<<"$out" && ! grep -q skills/b <<<"$(field g4 touches)" && [ -z "$(git status --porcelain)" ] && grep -q "touches +skills/b: needs the b scripts" "$R/g4.extra.json"'
rec g4 idea 'DEPTH: full\nSTEP: done' >/dev/null
check "a worker's save leaves the widening, and its next record writes the goal file's Touches line" 'grep -q skills/b "$R/g4.extra.json" && grep -q "^- Touches: skills/a, skills/b$" .loop/goals/g4.md'
out=$(rec g4 plan 'DEPTH: full\nSTEP: done')
check "the freeze still holds after the Touches line changed" 'grep -q "^RECORDED plan" <<<"$out"'
git commit -qam "g4 touches" >/dev/null
check "the board lists the widened touches" 'python3 -c "import sys,datetime;sys.path.insert(0,\"$S\");import board;rows=board.collect(\"r\",\".\",\"$C\",datetime.datetime.now(datetime.timezone.utc))[0];print([r[\"touches\"] for r in rows if r[\"slug\"]==\"g4\"][0])" 2>/dev/null | grep -q "skills/b"'
out=$(LOOP_ROLE=worker $goal touches g4 --add skills/c --why x 2>&1)
check "a worker can't widen its own touches" 'grep -q "(WORKER_SELF_REPAIR)" <<<"$out"'
check "an absolute, a .. or a repeated path is refused" '$goal touches g4 --add /etc --why x 2>&1 | grep -q TOUCHES_PATH && $goal touches g4 --add ../x --why x 2>&1 | grep -q TOUCHES_PATH && $goal touches g4 --add skills/b --why x 2>&1 | grep -q "already in the goal.s touches"'
setf g4 '{"status": "done"}'
out=$($goal finding g4 "the board missed a field" 2>&1)
check "a finding on a done goal is noted and the goal stays done" 'grep -q "^FINDING recorded on g4 (goal stays done)" <<<"$out" && [ "$(field g4 status)" = done ] && grep -q "the board missed a field" "$R/g4.extra.json"'
check "the board shows the finished goal's finding" 'python3 -c "import sys,datetime;sys.path.insert(0,\"$S\");import board;rows=board.collect(\"r\",\".\",\"$C\",datetime.datetime.now(datetime.timezone.utc))[0];print([r[\"note\"] for r in rows if r[\"slug\"]==\"g4\"][0])" 2>/dev/null | grep -q "finding after done: the board missed a field"'
new g4r
out=$($goal finding g4r "broken for real" 2>&1)
check "a finding on a running goal still stops it" 'grep -q "^STOPPED g4r" <<<"$out" && [ "$(field g4r status)" = stopped ]'
fi

if want g5; then
echo "== g5 (121): the worker refusal says exactly how"
# Value: protects=done line 5; fails_when=a session is told to run batch.py start instead of setting LOOP_ROLE;
# why_new=the refusal named the operation's command; seam=none; no_claim=the app setting env vars in a session
new g5; out=$($SE bind g5 s5 2>&1)
check "bind prints the worker command form" 'grep -q "^WORKER g5: run goal steps as LOOP_ROLE=worker python3 .*/workflow-delivery/scripts/goal.py" <<<"$out"'
out=$($goal record g5 idea --file x 2>&1)
check "a goal step outside a worker names the bound session, its worktree and the exact command" 'grep -q "REFUSED: record is worker work and LOOP_ROLE is not worker here. Fix: in worker · g5, in .*, run: LOOP_ROLE=worker python3 .*goal.py record g5 idea --file x" <<<"$out" && grep -q "(NOT_WORKER)" <<<"$out"'
new g5b; out=$($goal record g5b idea --file x 2>&1)
check "for an unbound goal it says how to start or bind a worker" 'grep -q "start a worker for g5b (batch.py start NAME), or bind a session (sessions.py bind g5b ID)" <<<"$out"'
out=$(python3 "$D/role.py" lane g5 qa 2>&1)
check "the lane's refusal names the session too" 'grep -q "in worker · g5" <<<"$out"'
fi

if want g6; then
echo "== g6 (160, owner's choice a): bind hands over the worktree and refuses an outside folder"
# Value: protects=done line 6 as the owner chose (a); fails_when=a session works from the wrong folder unnoticed;
# why_new=nothing said where to work at bind; seam=--cwd stands in for the session's folder; no_claim=the desktop app's own
# edit guard (out of the template's reach; #160 stays open)
new g6; out=$($SE bind g6 s6 2>&1)
check "bind prints the goal worktree to work in" 'grep -q "^WORKTREE g6: $TREE$" <<<"$out"'
out=$($SE bind g6 s7 --cwd /tmp 2>&1)
check "a session folder outside the worktree is refused, and the pool is unchanged" 'grep -q "REFUSED: session folder /tmp is outside the goal worktree $TREE.*(CWD_OUTSIDE)" <<<"$out" && ! grep -q "\"s7\"" "$C/loop/session-pool.json"'
check "a folder inside the worktree binds" '$SE bind g6 s7 --cwd "$TREE/.loop" >/dev/null 2>&1 && grep -q "\"s7\"" "$C/loop/session-pool.json"'
git worktree add -q --detach "$d/wt6" main
out=$(cd "$d/wt6" && LOOP_ROLE=worker $SE bind g6 s8 2>&1)
check "a worker binding itself from another worktree is refused" 'grep -q "(CWD_OUTSIDE)" <<<"$out"'
out=$(cd "$d/wt6" && LOOP_ROLE=worker $SE bind g6 s8 --cwd "$TREE" 2>&1)
check "a worker can't pass --cwd to hide where it runs" 'grep -q "session folder $(cd "$d/wt6" && pwd -P) is outside.*(CWD_OUTSIDE)" <<<"$out"'
LOOP_SESSION_TOOL="$d/tool.sh" $SE assign g6 >/dev/null 2>&1
check "assign's message names the worktree and the worker command" 'cat "$TOOL_LOG".sent.* | grep -q "cd $TREE first" && cat "$TOOL_LOG".sent.* | grep -q "^WORKER g6:"'
fi

if want g7; then
echo "== g7: the review's extra guards"
# Value: protects=the plan review's accepted guards (answer, waiting, self-bind, freeze stamp, pool lock, tool errors);
# fails_when=a stopped goal is revived around resume's checks, a waiting goal advances, or two goals take one session;
# why_new=these paths had no check; seam=two processes and a held lock; no_claim=a real app session tool
new g7; $SE bind g7 s70 >/dev/null; setf g7 '{"status": "stopped"}'
out=$($goal answer g7 2>&1)
check "answer refuses a goal that isn't waiting" 'grep -q "(ANSWER_STATUS)" <<<"$out" && [ "$(field g7 status)" = stopped ]'
out=$(LOOP_ROLE=worker $SE bind g7 s71 --cwd "$TREE" 2>&1)
check "a worker binding itself to a stopped goal attaches without reviving it" '[ "$(field g7 status)" = stopped ] && grep -q "NEXT: ask the operation session to resume g7" <<<"$out"'
setf g7 '{"status": "waiting", "waiting": {"ask": "pick one", "words": ["go on g7"]}}'
out=$(rec g7 idea 'DEPTH: full\nSTEP: done'); rc=$?
check "a waiting goal's record is refused with no try, exit 2" '[ $rc = 2 ] && grep -q "g7 waits for the owner: pick one.*(WAITING_OWNER)" <<<"$out" && [ "$(field g7 tries)" = 0 ]'
out=$(LOOP_ROLE=worker $goal pr g7 2>&1); rc=$?
check "a waiting goal's pull request is refused first, with no try" '[ $rc = 2 ] && grep -q "(WAITING_OWNER)" <<<"$out" && [ "$(field g7 tries)" = 0 ]'
$goal answer g7 >/dev/null; out=$(rec g7 idea 'DEPTH: full\nSTEP: done')
check "after the answer the record goes through" 'grep -q "^RECORDED idea" <<<"$out"'
check "watch.py's freeze stamps the rules known" '[ "$(python3 -c "import sys;sys.path.insert(0,\"$S\");import watch;print(watch.known_rules())")" = "$(python3 -c "import sys;sys.path.insert(0,\"$D\");import guards;print(guards.known())")" ] && grep -q "\"rules_at\": {\"idea\": known_rules()}" "$S/watch.py"'
python3 - "$C/loop/session-pool.json" <<'PY'
import json, sys
p = json.load(open(sys.argv[1])); p["sx"] = {"name": "x", "slug": "", "state": "free"}; json.dump(p, open(sys.argv[1], "w"))
PY
python3 -c "import fcntl,sys,time;f=open(sys.argv[1],'w');fcntl.flock(f,fcntl.LOCK_EX);open(sys.argv[2],'w').close();time.sleep(2)" "$C/loop/session-pool.lock" "$d/held" &
while [ ! -e "$d/held" ]; do sleep 0.1; done  # both reservations start while the lock is held, so without it they'd race
($SE reserve ga sx > "$d/ra" 2>&1 &) ; ($SE reserve gb sx > "$d/rb" 2>&1 &); sleep 4
check "two reservations of one free session: exactly one wins" '[ "$(cat "$d/ra" "$d/rb" | grep -c "^RESERVED")" = 1 ] && grep -q "(SESSION_TAKEN)" "$d/ra" "$d/rb"'
errs=$(LOOP_SESSION_TIMEOUT=1 python3 - "$S" <<'PY'
import sys; sys.path.insert(0, sys.argv[1]); import sessions
out = []
for cmd in (["bash", "-c", "echo boom >&2; exit 3"], ["/nonexistent/tool"], ["sleep", "5"]):
    sessions.HUNG[:] = []
    out.append("%s|%s" % (sessions.call(cmd), sessions.LAST_ERROR[0]))
print("\n".join(out))
PY
)
check "the session tool's error is kept: stderr, a missing executable, a timeout" 'grep -q "^None|boom$" <<<"$errs" && grep -q "^None|cannot start /nonexistent/tool" <<<"$errs" && grep -q "^None|timed out after 1 s$" <<<"$errs"'
fi

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
