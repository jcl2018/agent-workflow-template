#!/bin/bash
# reads: skills/workflow-monitoring/scripts/operate.py skills/workflow-monitoring/scripts/checkin.py skills/workflow-monitoring/scripts/board.py
# reads: skills/workflow-monitoring/scripts/board_lines.py skills/workflow-monitoring/scripts/graph.py skills/workflow-monitoring/scripts/live_board.py
# reads: skills/workflow-monitoring/scripts/reply_hook.py skills/workflow-monitoring/scripts/govern_hook.py docs/wiki/Monitoring.md
# reads: skills/workflow-monitoring/scripts/sessions.py skills/workflow-monitoring/scripts/watch.py skills/workflow-monitoring/scripts/session_bind.py
# reads: skills/workflow-monitoring/scripts/mend.py skills/workflow-monitoring/scripts/auto.py skills/workflow-monitoring/scripts/board_status.py
# reads: skills/workflow-delivery/scripts/goal.py skills/workflow-release/scripts/merge.py dev/package.py
# Pods (MON-13, MON-14, MON-15): two layers per pod with several independent operation sessions, the check-in's per-repo
# dependency blocks, goal ownership by pod and the cross-pod merge lock, on made-up repos (alpha-app, beta-svc, gamma-lib,
# delta-tool, omega-none) and pods (pod-a, pod-b) in a temp HOME. No model, no network.
# usage: test-pods.sh [layers|blocks|owner|lock|twopods|size|docs ...]   (default all; POD_SKILLS=DIR runs another copy of skills/)
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION LOOP_ROLE LOOP_SESSION_QUIET LOOP_GOVERN_HOOK CLAUDE_SESSION_ID LOOP_POD_ID LOOP_MERGE_LOCK_SECONDS
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
SK=${POD_SKILLS:-$here/skills}; SCRIPTS=$SK/workflow-monitoring/scripts; GOAL=$SK/workflow-delivery/scripts/goal.py; MERGE=$SK/workflow-release/scripts/merge.py
cases=("$@"); [ ${#cases[@]} = 0 ] && cases=(layers blocks owner lock twopods size docs)
want() { for c in "${cases[@]}"; do [ "$c" = "$1" ] && return 0; done; return 1; }
T=$(mktemp -d); export HOME="$T/home"; mkdir -p "$HOME/.workflow-loop"
export GIT_CONFIG_GLOBAL="$T/gitconfig" GIT_CONFIG_NOSYSTEM=1 GIT_TERMINAL_PROMPT=0; : > "$GIT_CONFIG_GLOBAL"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; [ -z "${DEBUG:-}" ] || printf "%s\n" "$out" | head -8; fi; }
r() { out=$(eval "$@" 2>&1); rc=$?; }
has() { grep -qF -- "$1" <<<"$out"; }
mk() { git init -q -b main "$T/$1"; git -C "$T/$1" config user.email t@example.test; git -C "$T/$1" config user.name Toy
       echo x > "$T/$1/f"; git -C "$T/$1" add -A; git -C "$T/$1" commit -qm base; mkdir -p "$T/$1/.loop/runs" "$T/$1/.git/loop/runs"; printf "# Queue\n" > "$T/$1/.loop/queue.md"; echo "{}" > "$T/$1/.loop/config.json"; }
queue() { printf '%s\n' "$2" >> "$T/$1/.loop/queue.md"; }   # queue REPO LINE
runrec() { python3 - "$T/$1/.git/loop/runs" "$2" <<'PY'
import datetime, json, os, sys
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump({"slug": sys.argv[2], "goal": "Goal " + sys.argv[2], "status": "running", "step": "build", "tries": 0, "pr": "", "waits_on": [], "updated": now}, open(os.path.join(sys.argv[1], sys.argv[2] + ".json"), "w"))
PY
}
claim() { # claim REPO ID [flags]: run operate.py claim from that repo
  local repo=$1 id=$2; shift 2; r "cd $T/$repo && python3 $SCRIPTS/operate.py claim --id $id $*"; }
own() { # own REPO SLUG POD STATUS [PR]: a run record owned by POD (none when POD is "-")
  python3 - "$T/$1/.git/loop/runs" "$2" "$3" "$4" "${5:-}" <<'PY'
import datetime, json, os, sys
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
rec = {"slug": sys.argv[2], "goal": "Goal " + sys.argv[2], "status": sys.argv[4], "step": "build", "tries": 0, "pr": sys.argv[5], "waits_on": [],
       "updated": now, "branch": "loop/" + sys.argv[2], "log": []}
if sys.argv[3] != "-":
    rec["pod"] = sys.argv[3]
if sys.argv[4] == "waiting":
    rec["waiting"] = {"ask": "Which one?", "words": ["a", "b"], "recommend": "a"}
json.dump(rec, open(os.path.join(sys.argv[1], sys.argv[2] + ".json"), "w"))
PY
}
fp() { md5 -q "$T/$1/.git/loop/runs/$2.json" 2>/dev/null || md5sum "$T/$1/.git/loop/runs/$2.json" | cut -d' ' -f1; }
as() { local pod=$1; shift; r "cd $T/alpha-app && LOOP_POD_ID=$pod $*"; }   # run a command as a pod from alpha-app
shim() { mkdir -p "$T/shim"; cat > "$T/shim/gh" <<SH
#!/bin/sh
echo "in" >> "$T/shim.log"; sleep 1.2; echo "out" >> "$T/shim.log"; echo "{}"; exit 0
SH
chmod +x "$T/shim/gh"; : > "$T/shim.log"; }
depth() { awk '/^in/{d++; if (d>m) m=d} /^out/{d--} END{print m+0}' "$T/shim.log"; }
for n in alpha-app beta-svc gamma-lib delta-tool; do mk $n; done
printf '%s\n' "$T/beta-svc" "$T/gamma-lib" > "$HOME/.workflow-loop/repos"

if want layers; then
echo "== MON-13: several independent operation sessions, nothing refuses or warns"
quiet='! has REFUSED && ! has WARN && ! has already && ! has replaced'
ids() { sort "$T/$1/.git/loop/operation.id" | tr '\n' ' '; }
claim alpha-app s1
check "the first session claims" '[ $rc = 0 ] && has "CLAIMED operation session s1" && '"$quiet"
claim alpha-app s2
check "a second session in the same repo claims with no refusal, warning or replaced note" '[ $rc = 0 ] && has "CLAIMED operation session s2" && '"$quiet"
claim alpha-app s1
check "the same session claiming again leaves two ids" '[ "$(ids alpha-app)" = "s1 s2 " ]'
check "the claim also reached every followed repo, keeping both sessions" '[ "$(ids beta-svc)" = "s1 s2 " ] && [ "$(ids gamma-lib)" = "s1 s2 " ]'
mkdir -p "$T/home2/.workflow-loop"; printf '%s\n' "$T/delta-tool" > "$T/home2/.workflow-loop/repos"
r "cd $T/delta-tool && HOME=$T/home2 python3 $SCRIPTS/operate.py claim --id s3"
check "an independent second pod claims with no refusal and sees only its own repo" '[ $rc = 0 ] && '"$quiet"' && [ "$(ids delta-tool)" = "s3 " ] && [ "$(ids alpha-app)" = "s1 s2 " ]'
claim delta-tool s4
check "a session outside the first pod's repos claims too" '[ $rc = 0 ] && '"$quiet"
r "cd $T/alpha-app && python3 - $SCRIPTS \"$T/alpha-app/.git\" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1]); import govern_hook as g, reply_hook as h
c = os.path.realpath(sys.argv[2]); a = os.getcwd()
yes = lambda s: g.is_operation({'session_id': s, 'cwd': a}, c)
print('IDS', sorted(g.operation_ids(c)), sorted(h.claimed(c)))
print('HOOK', yes('s1'), yes('s2'), yes('s8'), g.is_operation({'session_id': 's1', 'cwd': c + '/loop/worktrees/x'}, c))
PY"
check "the govern and reply hooks know both sessions, not a stranger or a worker" 'has "IDS [\"s1\", \"s2\"]" || has "IDS ['"'"'s1'"'"', '"'"'s2'"'"'] ['"'"'s1'"'"', '"'"'s2'"'"']"'
check "is_operation says True, True, False, False" 'has "HOOK True True False False"'
r "cd $T/gamma-lib && printf '%s' '{\"session_id\":\"s5\",\"cwd\":\"$T/gamma-lib\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"python3 skills/workflow-monitoring/scripts/operate.py claim\"}}' | python3 $SCRIPTS/govern_hook.py"
check "the govern hook's own claim adds its session and keeps the others" 'for i in s1 s2 s5; do grep -qx $i "$T/gamma-lib/.git/loop/operation.id" || exit 1; done && ! grep -qs replaced "$T/gamma-lib/.git/loop/govern-hook.log"'
r "cd $T/alpha-app && LOOP_ROLE=worker python3 $SCRIPTS/operate.py claim --id s6"
check "a worker is still refused" '[ $rc != 0 ] && has "a worker can'"'"'t claim"'
r "cd $T/alpha-app && python3 $SCRIPTS/checkin.py"
check "the check-in runs for the first pod" '[ $rc = 0 ] && has Dependencies && has "Needs you" && ! has Traceback'
r "cd $T/delta-tool && HOME=$T/home2 python3 $SCRIPTS/checkin.py"
check "and for the second pod" '[ $rc = 0 ] && has Dependencies && ! has Traceback'
r "cd $T/beta-svc && CLAUDE_SESSION_ID=s7 python3 $SCRIPTS/operate.py run --once"
check "operate.py run in a repo another session governs is not refused" '! has REFUSED'
fi

if want blocks; then
echo "== MON-14: the check-in groups the dependency map by repo"
runrec alpha-app core; queue alpha-app "- slug: docs | goal: Docs | depends-on: core | done: x"
queue beta-svc "- slug: api | goal: Api | depends-on: alpha-app/core | done: x"
queue beta-svc "- slug: edge | goal: Edge | depends-on: omega-none/x | done: x"
long=a-very-long-repository-name-that-keeps-going-past-sixty-chars-x; mk $long
printf '%s\n' "$T/beta-svc" "$T/gamma-lib" "$T/$long" > "$HOME/.workflow-loop/repos"
r "cd $T/alpha-app && python3 $SCRIPTS/checkin.py"
dep=$(sed -n '/^Dependencies$/,/^Needs you$/p' <<<"$out")
check "the check-in runs" '[ $rc = 0 ]'
check "each repo has one header, in order: own repo first, then the repos file" '[ "$(grep -n "^== " <<<"$dep" | cut -d: -f2- | tr "\n" ,)" = "== alpha-app ==,== beta-svc ==,== gamma-lib ==,== a-very-long-repository-name-that-keeps-going-past-s... ==," ]'
check "each goal sits inside its own repo's block" 'a=$(grep -n "== alpha-app" <<<"$dep" | cut -d: -f1); b=$(grep -n "== beta-svc" <<<"$dep" | cut -d: -f1); g=$(grep -n "== gamma-lib" <<<"$dep" | cut -d: -f1); for x in core docs; do n=$(grep -n "\] $x" <<<"$dep" | head -1 | cut -d: -f1); [ "$n" -gt "$a" ] && [ "$n" -lt "$b" ] || exit 1; done; for x in api edge; do n=$(grep -n "\] $x" <<<"$dep" | head -1 | cut -d: -f1); [ "$n" -gt "$b" ] && [ "$n" -lt "$g" ] || exit 1; done'
check "an empty repo shows (none)" 'grep -A1 "== gamma-lib" <<<"$dep" | grep -q "(none)"'
check "cross-repo dependencies are listed once, between blocks, an unknown one marked unknown" '[ "$(grep -c "^Between repos" <<<"$dep")" = 1 ] && grep -q "beta-svc/api <- alpha-app/core \[.\]" <<<"$out" && has "beta-svc/edge <- omega-none/x (unknown)"'
check "the legend prints once" '[ "$(grep -c "^\[>\] running" <<<"$out")" = 1 ]'
check "no dependency line is over 60 characters" '[ -z "$(awk "length > 60" <<<"$dep")" ]'
check "the table shows each goal with its repo name and the headline counts the pod" 'has "| alpha-app |" && head -1 <<<"$out" | grep -q "1 running, 0 waiting on you, 3 queued"'
printf '%s\n' "$T/beta-svc" > "$HOME/.workflow-loop/repos"; mkdir -p "$T/beta-svc/.git/loop/runs"; printf '{bad' > "$T/beta-svc/.git/loop/runs/broken.json"
r "cd $T/alpha-app && python3 $SCRIPTS/checkin.py"
check "a broken record in a followed repo does not stop the check-in" '[ $rc = 0 ] && ! has Traceback && has "== alpha-app ==" && has "== beta-svc =="'
: > "$HOME/.workflow-loop/repos"
r "cd $T/alpha-app && python3 $SCRIPTS/checkin.py"
check "a pod of one repo prints its one block and no Between repos" '[ "$(grep -c "^== " <<<"$out")" = 1 ] && ! has "Between repos"'
r "cd $T/alpha-app && python3 $SCRIPTS/checkin.py > $T/ci.txt && python3 -c \"
import sys; sys.path.insert(0, '$SCRIPTS'); import reply_hook as h
t = open('$T/ci.txt').read()
print('OK' if all(('## ' + s in ('## ' + t) or s in t) for s in ['All sessions', 'Dependencies', 'Needs you', 'Coming up']) else 'MISSING')\""
check "the layout headings the reply hook looks for are all still there" 'has OK'
fi

if want owner; then
echo "== MON-15: only the owning pod acts on a goal"
echo '{"auto_merge": true}' > "$T/alpha-app/.loop/config.json"
own alpha-app core pod-a failed; own alpha-app mine pod-a done 7; own alpha-app plain - failed; own alpha-app held1 pod-a waiting
line='REFUSED: goal core is owned by pod pod-a.'
for cmdline in "python3 $SCRIPTS/sessions.py send core hi" "python3 $SCRIPTS/sessions.py bind core s9" "python3 $SCRIPTS/sessions.py free core" "python3 $SCRIPTS/worker.py send core hi" "python3 $GOAL resume core --why x" \
               "python3 $SCRIPTS/watch.py resume core" "python3 $SCRIPTS/operate.py send core hi" "python3 $MERGE core"; do
  before=$(fp alpha-app core); [ "${cmdline##* }" = core ] || true
  [ "${cmdline#*merge.py}" != "$cmdline" ] && { own alpha-app core pod-a done 7; before=$(fp alpha-app core); }
  as pod-b "$cmdline"
  check "pod-b is refused with one line naming pod-a, changing nothing: ${cmdline#python3 $SK/}" '[ $rc = 2 ] && [ "$(grep -c REFUSED <<<"$out")" = 1 ] && has "$line" && [ "$(fp alpha-app core)" = "$before" ] && [ ! -e "$T/alpha-app/.git/loop/answers.jsonl" ] && [ ! -e "$T/alpha-app/.git/loop/merge.lock" ]'
done
own alpha-app core pod-a failed
as pod-a "python3 $SCRIPTS/operate.py send core hi"
check "pod-a is not refused on its own goal" '! has "owned by pod"'
as pod-b "python3 $SCRIPTS/operate.py send plain hi"
check "a goal with no recorded pod is open to every pod" '! has "owned by pod"'
r "cd $T/alpha-app && LOOP_ROLE=worker python3 $SCRIPTS/operate.py send core hi"
check "a worker is never refused for ownership" '! has "owned by pod"'
as pod-b "python3 $SCRIPTS/auto.py pass --dry-run"
check "pod-b does not decide another pod's waiting question" '! has held1'
as pod-a "python3 $SCRIPTS/auto.py pass --dry-run"
check "pod-a decides its own" 'has held1'
as pod-b "python3 $SCRIPTS/checkin.py"
check "the check-in as pod-b marks pod-a's goal owned by pod-a, read-only, and numbers no question for it" 'has "core owned by pod-a" && has "held1 asks (owned by pod-a, read-only here)" && ! grep -q "^[0-9]*\. held1" <<<"$out" && [ -z "$(awk "length > 60" <<<"$out" | grep -F "owned by")" ]'
as pod-a "python3 $SCRIPTS/checkin.py"
check "as pod-a the same goals carry no owned-by mark" '! has "owned by"'
as pod-b "python3 $SCRIPTS/board.py board"
check "the board marks it too" 'has "owned by pod-a"'
r "python3 - $SCRIPTS <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1]); import graph
os.environ['LOOP_POD_ID'] = 'pod-a'; a = {'slug': 'x'}; graph.stamp(a)
b = {'slug': 'y', 'pod': 'pod-z'}; graph.stamp(b)
os.environ['LOOP_ROLE'] = 'worker'; c = {'slug': 'z'}; graph.stamp(c)
print('STAMP', a.get('pod'), b.get('pod'), c.get('pod'))
PY"
check "stamping records the caller's pod once, keeps an existing one and records none for a worker" 'has "STAMP pod-a pod-z None"'
r "mkdir -p $T/lonely/skills && cp -R $here/skills/workflow-delivery $here/skills/workflow-release $T/lonely/skills/ && cd $T/alpha-app && python3 $T/lonely/skills/workflow-delivery/scripts/goal.py show plain"
check "goal.py runs without workflow-monitoring beside it" '[ $rc = 0 ] && has plain'
fi

if want lock; then
echo "== MON-15: one merge into a repo's main at a time"
C="$T/alpha-app/.git"; rm -f "$C/loop/merge.lock"
holder() { python3 - "$SCRIPTS" "$C" "$1" "$T/lock.log" <<'PY'
import sys, time
sys.path.insert(0, sys.argv[1]); import graph
graph.merge_lock(sys.argv[2])
open(sys.argv[4], "a").write("in %s %.2f\n" % (sys.argv[3], time.time()))
time.sleep(1.2)
open(sys.argv[4], "a").write("out %s %.2f\n" % (sys.argv[3], time.time()))
PY
}
: > "$T/lock.log"; holder one 2>"$T/e1" & holder two 2>"$T/e2" & wait
check "two concurrent holders do not overlap" '[ "$(cut -d" " -f1 "$T/lock.log" | tr "\n" " ")" = "in out in out " ] && [ "$(cat "$T/lock.log" "$T/e1" "$T/e2" | grep -c "WAITING: another pod")" = 1 ]' 
check "the lock file is gone after both end" '[ ! -e "$C/loop/merge.lock" ]'
echo 999999 > "$C/loop/merge.lock"; : > "$T/lock.log"; holder three 2>/dev/null & holder four 2>/dev/null & wait
check "two waiters finding the same dead lock do not both take it" '[ "$(cut -d" " -f1 "$T/lock.log" | tr "\n" " ")" = "in out in out " ]'; rm -f "$C/loop/merge.lock"
echo 999999 > "$C/loop/merge.lock"; start=$(date +%s)
r "python3 - $SCRIPTS $C <<'PY'
import sys; sys.path.insert(0, sys.argv[1]); import graph; graph.merge_lock(sys.argv[2]); print('TOOK')
PY"
check "a lock held by a dead process is replaced at once" 'has TOOK && ! has WAITING && [ $(( $(date +%s) - start )) -le 3 ]'
sleep 30 & live=$!; echo $live > "$C/loop/merge.lock"; sleep 2
r "LOOP_MERGE_LOCK_SECONDS=1 python3 - $SCRIPTS $C <<'PY'
import sys; sys.path.insert(0, sys.argv[1]); import graph; graph.merge_lock(sys.argv[2]); print('TOOK')
PY"
check "a live holder older than the limit is replaced" 'has TOOK'; kill $live 2>/dev/null
echo "$$" > "$C/loop/merge.lock"
r "timeout 2 python3 - $SCRIPTS $C <<'PY'
import sys; sys.path.insert(0, sys.argv[1]); import graph; graph.merge_lock(sys.argv[2]); print('TOOK')
PY"
check "a live fresh lock blocks, saying who is merging" '[ $rc = 124 ] && has WAITING && ! has TOOK'; rm -f "$C/loop/merge.lock"
r "python3 - $SCRIPTS $C <<'PY'
import sys; sys.path.insert(0, sys.argv[1]); import graph; graph.merge_lock(sys.argv[2]); sys.exit(1)
PY"
check "the lock is released after a failing exit" '[ ! -e "$C/loop/merge.lock" ]'
shim; echo '{"auto_merge": true}' > "$T/alpha-app/.loop/config.json"; own alpha-app m1 - done 5; own alpha-app m2 - done 6
( cd $T/alpha-app && PATH="$T/shim:$PATH" python3 $MERGE m1 >/dev/null 2>&1 & cd $T/alpha-app && PATH="$T/shim:$PATH" python3 $MERGE m2 >/dev/null 2>&1 & wait )
check "two concurrent merge.py runs never call gh at the same time (serialized)" '[ "$(depth)" = 1 ] && [ "$(grep -c "^in" "$T/shim.log")" -ge 2 ]'
check "and the lock is gone after them" '[ ! -e "$C/loop/merge.lock" ]'
echo "$$" > "$C/loop/merge.lock"; own alpha-app core pod-a done 7
start=$(date +%s); as pod-b "python3 $MERGE core"
check "a foreign merge is refused at once even while the lock is held" '[ $rc = 2 ] && has "owned by pod pod-a" && [ $(( $(date +%s) - start )) -le 2 ]'; rm -f "$C/loop/merge.lock"
fi

if want twopods; then
echo "== MON-13 and MON-15: two independent pods on one repo"
mkdir -p "$T/homeA/.workflow-loop" "$T/homeB/.workflow-loop"; printf '%s\n' "$T/beta-svc" > "$T/homeA/.workflow-loop/repos"
echo '{"auto_merge": true}' > "$T/alpha-app/.loop/config.json"; rm -f "$T/alpha-app/.git/loop/operation.id"
r "cd $T/alpha-app && HOME=$T/homeA python3 $SCRIPTS/operate.py claim --id pod-a"; ca=$out; rca=$rc
r "cd $T/alpha-app && HOME=$T/homeB python3 $SCRIPTS/operate.py claim --id pod-b"
check "both pods claim the one repo: nothing refuses or warns, both ids are kept" '[ $rca = 0 ] && [ $rc = 0 ] && ! grep -qiE "REFUSED|WARN|already|replaced" <<<"$ca$out" && grep -qx pod-a "$T/alpha-app/.git/loop/operation.id" && grep -qx pod-b "$T/alpha-app/.git/loop/operation.id"'
own alpha-app api pod-a failed; own alpha-app web pod-b failed; own alpha-app m1 pod-a done 5; own alpha-app m2 pod-b done 6
ra=$(fp alpha-app api); rw=$(fp alpha-app web)
r "cd $T/alpha-app && HOME=$T/homeA LOOP_POD_ID=pod-a python3 $SCRIPTS/checkin.py"
check "pod-a's check-in shows its own goal plain and the other's as owned by pod-b" 'has "web owned by pod-b" && has api && ! has "api owned by"'
r "cd $T/alpha-app && HOME=$T/homeB LOOP_POD_ID=pod-b python3 $SCRIPTS/checkin.py"
check "pod-b's shows the reverse" 'has "api owned by pod-a" && ! has "web owned by"'
as pod-a "python3 $SCRIPTS/operate.py send api hi"; ok1=$rc; o1=$out
as pod-a "python3 $SCRIPTS/operate.py send web hi"
check "each pod can act on its own goal and is refused on the other's" '! grep -q "owned by pod" <<<"$o1" && [ $rc = 2 ] && has "owned by pod pod-b"'
shim; own alpha-app m1 pod-a done 5; own alpha-app m2 pod-b done 6; ma=$(fp alpha-app m1); mb=$(fp alpha-app m2)
( cd $T/alpha-app && LOOP_POD_ID=pod-a PATH="$T/shim:$PATH" python3 $MERGE m1 >"$T/ma.out" 2>&1 & cd $T/alpha-app && LOOP_POD_ID=pod-b PATH="$T/shim:$PATH" python3 $MERGE m2 >"$T/mb.out" 2>&1 & wait )
check "both pods merge their own goals at once: neither is refused, the merges are serialized, the lock is gone" '! grep -q "owned by pod" "$T/ma.out" "$T/mb.out" && [ "$(depth)" = 1 ] && [ ! -e "$T/alpha-app/.git/loop/merge.lock" ]'
check "no pod changed the other's records" '[ "$(fp alpha-app api)" = "$ra" ] && [ "$(fp alpha-app web)" = "$rw" ]'
fi

if want size; then
echo "== done line 6: sizes"
base=$(git -C "$here" merge-base HEAD origin/main 2>/dev/null || git -C "$here" rev-parse HEAD)
over=""
for f in "$here"/skills/*/scripts/*.py; do
  rel=${f#$here/}; now=$(wc -c < "$f"); was=$(git -C "$here" show "$base:$rel" 2>/dev/null | wc -c | tr -d ' ')
  if [ "$now" -ge 20480 ] || { [ "$now" -ge 18432 ] && [ "$was" -lt 18432 ]; }; then over="$over $rel($now)"; fi
done
out="$over"; check "no script reaches 20 KB, and none newly crosses 18 KB" '[ -z "$over" ]'
caps=""; for pair in graph:18300 checkin:12500 operate:10500 goal:20000 sessions:19800 watch:19800 merge:20350 mend:14000 board_lines:17200; do
  n=${pair%%:*}; cap=${pair##*:}; f=$(ls "$here"/skills/*/scripts/$n.py); [ "$(wc -c < "$f")" -le "$cap" ] || caps="$caps $n"; done
out="$caps"; check "the touched scripts stay within their budgets" '[ -z "$caps" ]'
mkdir -p "$T/export" && git -C "$here" archive HEAD | tar -x -C "$T/export"   # a clean export: no __pycache__ from earlier runs
out=$(python3 "$here/dev/package.py" --root "$T/export" --out "$T/pkg.zip" 2>&1); rc=$?
check "the package rules pass, 99 files or fewer (dev/package.py)" '[ $rc = 0 ] && has "PASS: " && has " files, ZIP"'
fi

if want docs; then
echo "== done line 1: MON-13, MON-14 and MON-15 are in the Monitoring page, Reviewed"
out=""
for id in MON-13 MON-14 MON-15; do check "$id is Reviewed with a seal" 'grep -Eq "^- '"$id"': \*\*Reviewed [0-9-]+\*\* .*<!-- reviewed [0-9a-f]{8} -->" "$here/docs/wiki/Monitoring.md"'; done
out=$(python3 "$here/skills/workflow-docs/scripts/docs.py" check 2>&1)
check "the Monitoring page's review lock accepts the three requirements" '! has "LOCKED Monitoring" && ! has "TESTS Monitoring"'
fi
[ "$fails" = 0 ] && echo "ALL PASS" || echo "$fails FAILED"
[ "$fails" = 0 ]
