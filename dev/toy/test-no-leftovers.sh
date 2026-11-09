#!/bin/bash
# Defect test for issue 100: no toy test leaves a process running after it ends, whether it passes, fails, is
# interrupted or its pipe closes. Each fixture or test runs under its own TOY_OUTER_ID marker; after it ends, any
# process still carrying that marker is a FAIL (found with toy_list, never toy_reap, so a broken reaper can't
# hide it), and is then stopped. No model is called.
# usage: test-no-leftovers.sh [--all]
#   (none)  static check, fixture endings, and the land set: the toy tests that start stand-in agents
#   --all   every dev/toy/test-*.sh instead of the land set, judged on leftovers only (test-govern.sh is skipped)
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
mode=${1:-}
case "$mode" in ""|--all) ;; *) echo "usage: test-no-leftovers.sh [--all]" >&2; exit 2 ;; esac
unset AGENT_TEST LOOP_SESSION_TOOL LOOP_OPERATION_SESSION
export PYTHONDONTWRITEBYTECODE=1
T=$(mktemp -d); R="python3 $here/dev/toy/reap.py"
fails=0 n=0 markers=""
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
mark() { n=$((n + 1)); m="outer-$$-$n"; markers="$markers $m"; }
stop_marker() { $R reap "TOY_OUTER_ID=$1" --label test-no-leftovers.sh >/dev/null 2>&1; }
clean_all() { for x in $markers; do stop_marker "$x"; done; }
toy_on_exit 'clean_all'
toy_on_exit '[ "$fails" != 0 ] || rm -rf "$T"'
gone() {  # a pid that no longer runs (a zombie counts as gone)
  local s; s=$(ps -o stat= -p "$1" 2>/dev/null) || return 0
  case "$s" in Z*|"") return 0 ;; *) return 1 ;; esac
}
waitfor() {  # waitfor FILE|PID SECONDS: until the file exists (or the pid is gone); 1 on timeout
  local i=0 lim=$(($2 * 10))
  while [ "$i" -lt "$lim" ]; do
    case "$1" in */*) [ -e "$1" ] && return 0 ;; *) gone "$1" && return 0 ;; esac
    sleep 0.1; i=$((i + 1))
  done
  return 1
}
# check NAME MARKER [PIDFILE] [quiet]: nothing may carry MARKER now, and no recorded pid may still run
check() {
  local name=$1 out line k=0 bad0=$fails p
  out=$(toy_list TOY_OUTER_ID "$2")
  while IFS= read -r line; do
    case "$line" in
      "") ;;
      UNREADABLE*) bad "cannot read environment of pid $(echo "$line" | cut -d' ' -f2) ($(echo "$line" | cut -d' ' -f3))" ;;
      *) k=$((k + 1)) ;;
    esac
  done <<EOF
$out
EOF
  if [ "$k" != 0 ]; then
    echo "$out" | grep -v '^UNREADABLE' | while IFS= read -r line; do echo "FAIL: $name left $k: $line"; done
    fails=$((fails + 1))
  fi
  if [ -n "${3:-}" ] && [ -s "$3" ]; then
    for p in $(cat "$3"); do gone "$p" || bad "$name: recorded stand-in $p still runs"; kill -9 "$p" 2>/dev/null; done
  fi
  stop_marker "$2"
  [ "$fails" != "$bad0" ] || [ "${4:-}" = quiet ] || ok "$name"
  [ "$fails" = "$bad0" ]
}

# ---- static: every test sources reap.sh and sets no trap of its own
static() {
  python3 - "$@" <<'PY'
import os, re, sys
trap = re.compile(r"(^|[;&|(\s])trap\s+(--\s+)?('[^']*'|\"[^\"]*\"|\S+)\s+(.*)$")
sigs = re.compile(r"(^|\s)(EXIT|0|INT|TERM|HUP|SIGINT|SIGTERM|SIGHUP)(\s|$|;)")
for path in sys.argv[1:]:
    name, lines = os.path.basename(path), open(path).read().split("\n")
    i = next((k for k, l in enumerate(lines) if l.startswith("here=")), None)
    if i is None or i + 1 >= len(lines) or lines[i + 1].strip() != '. "$here/dev/toy/reap.sh"':
        print('FAIL: static: dev/toy/%s does not source reap.sh. Fix: add . "$here/dev/toy/reap.sh" on the line '
              'after here=' % name)
    for k, line in enumerate(lines, 1):
        if line.lstrip().startswith("#"):
            continue
        m = trap.search(line)
        if m and sigs.search(" " + m.group(4)):
            sig = sigs.search(" " + m.group(4)).group(2)
            print("FAIL: static: dev/toy/%s:%d sets its own trap %s. Fix: replace it with toy_on_exit '<cmd>'"
                  % (name, k, sig))
PY
}
echo "== static"
out=$(static "$here"/dev/toy/test-*.sh)
if [ -z "$out" ]; then ok "every dev/toy/test-*.sh sources reap.sh and sets no trap"; else echo "$out"; fails=$((fails + 1)); fi
mkdir -p "$T/st"
printf '#!/bin/bash\nhere=x\necho hi\n' > "$T/st/test-nosrc.sh"
printf '#!/bin/bash\nhere=x\n. "$here/dev/toy/reap.sh"\n# trap old EXIT\ntrap '"'"'x'"'"' EXIT\n' > "$T/st/test-trap.sh"
printf '#!/bin/bash\nhere=x\n. "$here/dev/toy/reap.sh"\ntrap -- "y" SIGHUP\n' > "$T/st/test-trap2.sh"
want1='FAIL: static: dev/toy/test-nosrc.sh does not source reap.sh. Fix: add . "$here/dev/toy/reap.sh" on the line after here='
want2="FAIL: static: dev/toy/test-trap.sh:5 sets its own trap EXIT. Fix: replace it with toy_on_exit '<cmd>'"
[ "$(static "$T/st/test-nosrc.sh")" = "$want1" ] && [ "$(static "$T/st/test-trap.sh")" = "$want2" ] \
  && static "$T/st/test-trap2.sh" | grep -q ":4 sets its own trap SIGHUP" \
  && ok "the static check names the file, the line and the fix" || bad "static check messages"
mkdir -p "$T/brk"; cp "$here/dev/toy/reap.sh" "$here/dev/toy/reap.py" "$T/brk/"
printf 'toy_reap() { return 0; }\n' >> "$T/brk/reap.sh"
bash -c ". '$T/brk/reap.sh'; type toy_reap" 2>/dev/null | grep -q "return 0" \
  && ok "an appended toy_reap stub takes effect (the regression break works)" || bad "appended toy_reap stub is ignored"
want3="REAP: test-x.sh TOY_REAP_ID=toy-1-2-3: 1 left after 5 rounds: 4411 (bash agent.sh). Fix: kill -9 4411, or bash dev/toy/reap.sh --sweep-dead after this test's shell exits."
[ "$($R format test-x.sh TOY_REAP_ID=toy-1-2-3 '4411:bash agent.sh')" = "$want3" ] \
  && ok "a REAP line names the test, marker, pids, commands and the fix" || bad "REAP line format"

# ---- fixtures
cat > "$T/launch.py" <<'PY'
import os, signal, subprocess, sys
for s in (signal.SIGINT, signal.SIGTERM, signal.SIGPIPE, signal.SIGHUP):
    signal.signal(s, signal.SIG_DFL)
args = sys.argv[1:]
if args[0] == "--setsid":
    os.setsid(); args = args[1:]
if args[0] == "--deadline":  # --deadline SECONDS LOG CMD: run CMD with output to LOG; TERM, 5 s, KILL on time out
    secs, log, cmd = float(args[1]), args[2], args[3]
    with open(log, "w") as out:
        p = subprocess.Popen(["bash", "-c", cmd], cwd=os.environ.get("TOY_CWD"), stdout=out, stderr=out, stdin=subprocess.DEVNULL)
        try:
            sys.exit(p.wait(timeout=secs))
        except subprocess.TimeoutExpired:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait()
            sys.exit(124)
os.execvp(args[0], args)
PY
cat > "$T/spawner.sh" <<EOF
#!/bin/bash
# spawner.sh MODE DIR: starts two detached stand-ins, then ends as MODE says
set -eu
here="$here"
EOF
cat >> "$T/spawner.sh" <<'EOF'
. "$here/dev/toy/reap.sh"
toy_on_exit 'false'  # a failing callback never stops the reap
for i in 1 2; do
  python3 -c 'import subprocess, sys
p = subprocess.Popen([sys.executable, "-c", "import time\nwhile 1: time.sleep(0.2)"], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(p.pid)' >> "$2/pids"
done
echo $$ > "$2/shell"; touch "$2/ready"
case "$1" in
  pass) exit 0 ;;
  fail) exit 1 ;;
  wait) while sleep 0.1; do :; done ;;
  block) sleep 60 ;;
  pipe) while :; do echo line; done ;;
esac
EOF
# ending NAME MODE SIGNAL WANT_EXIT [--setsid]: run the spawner, end it, check its marker is empty
ending() {
  local name=$1 dir pid rc
  mark; dir="$T/e$n"; mkdir -p "$dir"
  TOY_OUTER_ID=$m python3 "$T/launch.py" ${5:-} bash "$T/spawner.sh" "$2" "$dir" >"$dir/out" 2>&1 &
  pid=$!
  waitfor "$dir/ready" 10 || bad "$name: the fixture never got ready"
  case "$3" in
    -) ;;
    group) kill -INT -- "-$pid" 2>/dev/null ;;
    *) kill "-$3" "$pid" 2>/dev/null ;;
  esac
  waitfor "$pid" 10 || bad "$name: the fixture did not end"
  wait "$pid" 2>/dev/null; rc=$?
  [ "$rc" = "$4" ] || bad "$name: exit $rc, want $4"
  check "$name" "$m" "$dir/pids" quiet || true
}
echo "== fixture endings"
for spec in "pass pass - 0" "forced fail fail - 1" "SIGINT wait INT 130" "SIGTERM wait TERM 143" "SIGHUP wait HUP 129"; do
  set -- $spec
  if [ "$1" = forced ]; then nm="forced fail"; shift; else nm=$1; fi
  before=$fails; ending "$nm" "$2" "$3" "$4"; [ "$fails" = "$before" ] && ok "$nm ending leaves nothing (exit $4)"
done
before=$fails; ending "INT to the process group while blocked on a foreground child" block group 130 --setsid
[ "$fails" = "$before" ] && ok "INT to the process group while blocked on a foreground child leaves nothing"
mark; dir="$T/e$n"; mkdir -p "$dir"; before=$fails
( TOY_OUTER_ID=$m python3 "$T/launch.py" bash "$T/spawner.sh" pipe "$dir" 2>"$dir/out" | head -1 >/dev/null ) &
pp=$!
waitfor "$dir/ready" 10 && waitfor "$(cat "$dir/shell" 2>/dev/null || echo 1)" 10 || bad "pipe closed: the fixture did not end"
waitfor "$pp" 5; wait "$pp" 2>/dev/null
check "pipe closed early" "$m" "$dir/pids" quiet || true
[ "$fails" = "$before" ] && ok "a closed pipe ending leaves nothing"

echo "== isolation"
mark; m1=$m; d1="$T/e$n"; mark; m2=$m; d2="$T/e$n"; mkdir -p "$d1" "$d2"; before=$fails
TOY_OUTER_ID=$m1 python3 "$T/launch.py" bash "$T/spawner.sh" wait "$d1" >/dev/null 2>&1 & p1=$!
TOY_OUTER_ID=$m2 python3 "$T/launch.py" bash "$T/spawner.sh" wait "$d2" >/dev/null 2>&1 & p2=$!
waitfor "$d1/ready" 10 && waitfor "$d2/ready" 10 || bad "isolation: fixtures never got ready"
kill -TERM "$p1"; waitfor "$p1" 10; wait "$p1" 2>/dev/null
check "first run" "$m1" "$d1/pids" quiet || true
alive=0; for p in $(cat "$d2/pids"); do gone "$p" || alive=$((alive + 1)); done
[ "$alive" = 2 ] && ok "other run untouched" || bad "ending one run stopped $((2 - alive)) of the other run's stand-ins"
kill -TERM "$p2"; waitfor "$p2" 10; wait "$p2" 2>/dev/null
check "second run" "$m2" "$d2/pids" quiet || true
[ "$fails" = "$before" ] && ok "two runs at once each stop only their own"
# a harness killed with TERM still stops every marker it registered
mark; m1=$m; mark; m2=$m; dh="$T/e$n"; mkdir -p "$dh/a" "$dh/b"; before=$fails
cat > "$dh/harness.sh" <<EOF
#!/bin/bash
here="$here"; . "\$here/dev/toy/reap.sh"
toy_on_exit 'for x in $m1 $m2; do python3 "\$here/dev/toy/reap.py" reap TOY_OUTER_ID=\$x >/dev/null 2>&1; done'
TOY_OUTER_ID=$m1 bash "$T/spawner.sh" wait "$dh/a" >/dev/null 2>&1 &
TOY_OUTER_ID=$m2 bash "$T/spawner.sh" wait "$dh/b" >/dev/null 2>&1 &
while [ ! -e "$dh/a/ready" ] || [ ! -e "$dh/b/ready" ]; do sleep 0.1; done; touch "$dh/ready"
while sleep 0.1; do :; done
EOF
python3 "$T/launch.py" bash "$dh/harness.sh" >/dev/null 2>&1 & ph=$!
waitfor "$dh/ready" 10 || bad "harness TERM: never got ready"
kill -TERM "$ph"; waitfor "$ph" 10; wait "$ph" 2>/dev/null
check "harness TERM, first marker" "$m1" "$dh/a/pids" quiet || true
check "harness TERM, second marker" "$m2" "$dh/b/pids" quiet || true
[ "$fails" = "$before" ] && ok "a harness ended with TERM stops both runs it registered"

echo "== markers and the sweep"
sh -c 'exit 0' & dead=$!; wait "$dead"
gone "$dead" || { sh -c 'exit 0' & dead=$!; wait "$dead"; }
mk="toy-$dead-neg-$$"; sl="import time; time.sleep(120)"
python3 -c "$sl" "TOY_REAP_ID=$mk" & a1=$!
env "OTHER=TOY_REAP_ID=$mk" python3 -c "$sl" & a2=$!
sleep 0.3
$R reap "TOY_REAP_ID=$mk" >/dev/null 2>&1; $R sweep --marker "$mk" >/dev/null 2>&1
gone "$a1" || gone "$a2" && bad "a marker in a command line or another variable was matched" \
  || ok "the marker matches only a whole environment entry"
kill -9 "$a1" "$a2" 2>/dev/null; wait "$a1" "$a2" 2>/dev/null
env "TOY_REAP_ID=$mk" python3 -c "$sl" & a3=$!
env "TOY_REAP_ID=toy-$$-live-$$" python3 -c "$sl" & a4=$!
sleep 0.3
dry=$($R sweep --dry-run --marker "$mk")
live=$($R sweep --marker "toy-$$-live-$$")
sw=$($R sweep --marker "$mk")
echo "$dry" | grep -q "WOULD SWEEP $a3 $mk" && echo "$sw" | grep -q "^SWEPT $a3 $mk$" && echo "$sw" | grep -q "^SWEPT 1$" \
  && echo "$live" | grep -q "SKIP $a4 (owner pid alive)" && waitfor "$a3" 5 && ! gone "$a4" \
  && ok "--sweep-dead stops a dead test's process, says SWEPT, and skips a live owner's" \
  || bad "sweep: dry=[$dry] live=[$live] sweep=[$sw]"
kill -9 "$a3" "$a4" 2>/dev/null; wait "$a3" "$a4" 2>/dev/null

# ---- real tests
budget=600 start=$SECONDS
real() {  # real NAME COMMAND: run a toy test under its own marker and a deadline, then check its marker
  local name=$1 rc t0=$SECONDS lim log clean
  mark; log="$T/logs/$(echo "$name" | tr ' /' '__').log"; mkdir -p "$T/logs"
  lim=600; [ -n "$mode" ] || lim=$((budget - (SECONDS - start)))
  if [ "$lim" -lt 30 ]; then bad "$name: no time left in the $budget s budget"; return; fi
  TOY_CWD="$here" TOY_OUTER_ID=$m python3 "$T/launch.py" --deadline "$lim" "$log" "$2"; rc=$?
  [ "$rc" != 124 ] || bad "$name timed out after $lim s"
  if check "$name" "$m" "" quiet; then clean=PASS; else clean=FAIL; echo "  log: $log"; fi
  if [ -n "$mode" ]; then
    echo "$name: cleanup=$clean test_exit=$rc ($((SECONDS - t0)) s)"
  else
    [ "$clean" = FAIL ] || ok "$name leaves nothing ($((SECONDS - t0)) s, exit $rc)"
  fi
}
interrupted() {  # interrupted NAME COMMAND PATTERN: TERM a toy test once two processes matching PATTERN run
  local name=$1 pid i=0 t0=$SECONDS log
  mark; log="$T/logs/interrupted.log"; mkdir -p "$T/logs"
  (cd "$here" && TOY_OUTER_ID=$m exec python3 "$T/launch.py" bash -c "$2") >"$log" 2>&1 &
  pid=$!
  until [ "$(toy_list TOY_OUTER_ID "$m" 2>/dev/null | grep -Ec "$3")" -ge 2 ]; do
    i=$((i + 1)); if [ "$i" -gt 1800 ] || gone "$pid"; then bad "$name: never saw $3"; break; fi; sleep 0.1
  done
  kill -TERM "$pid" 2>/dev/null; waitfor "$pid" 30 || bad "$name: did not end after TERM"; wait "$pid" 2>/dev/null
  if check "$name" "$m" "" quiet; then ok "$name leaves nothing ($((SECONDS - t0)) s)"; else echo "  log: $log"; fi
}
if [ -z "$mode" ]; then
  echo "== land set"
  for t in goal monitoring workers batch operate; do real "test-$t.sh" "bash dev/toy/test-$t.sh"; done
  interrupted "test-operate.sh ended with TERM while its stand-in agents are held" "exec bash dev/toy/test-operate.sh" "agent\.sh"
  real "test-board.sh | grep -q" 'bash dev/toy/test-board.sh 2>&1 | grep -q "PASS: watch records waits_on on the run when the goal starts"'
else
  echo "== every toy test (verdict is cleanup only)"
  for f in "$here"/dev/toy/test-*.sh; do
    t=$(basename "$f")
    case "$t" in
      test-no-leftovers.sh) ;;
      test-govern.sh) echo "SKIP: test-govern.sh calls a real model" ;;
      test-rows.sh)
        for id in $(cut -f3 "$here/.loop/regression.tsv" | sed -n 's/^bash dev\/toy\/test-rows.sh \([^ ]*\).*/\1/p' | sort -u); do
          real "test-rows.sh $id" "bash dev/toy/test-rows.sh $id"
        done ;;
      *) real "$t" "bash dev/toy/$t" ;;
    esac
  done
  echo "(the verdict is cleanup only: each test's own exit is shown, not judged)"
fi
echo; [ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
