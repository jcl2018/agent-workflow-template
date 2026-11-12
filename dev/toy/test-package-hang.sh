#!/bin/bash
# reads: dev/package.py
# Prove dev/package.py never hangs (goal package-hang): a script whose --help waits on stdin, run under an open stdin
# pipe that never closes (as in a lane), is refused within the child bound; the hard bound stops a run with one TIMEOUT
# line naming what it waited on and leaves no child behind; a looping symlink in a scripts folder is not followed.
# An outside SIGTERM also stops the child. Usage: test-package-hang.sh [stdin|child|bound|loop|term]... (default: all). Free: no network, no model calls.
here=$(cd "$(dirname "$0")/../.." && pwd); T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; bad=0
export HOME="$T/home"; mkdir -p "$HOME"; export LOOP_FLOW="$T/none.json"
pkg() { # a small package whose one script is $1
  rm -rf "$T/p"; mkdir -p "$T/p/skills/demo/scripts"
  printf -- '---\nname: demo\ndescription: a demo skill\n---\n# demo\n' > "$T/p/skills/demo/SKILL.md"
  printf '%s\n' "$1" > "$T/p/skills/demo/scripts/demo.py"
  printf '{"license": "MIT", "summary": "demo", "network": ["none"], "writes": ["nothing"], "commands": []}\n' > "$T/p/listing.json"
  printf '# Demo\n' > "$T/p/README.md"; printf 'MIT\n' > "$T/p/LICENSE"; printf '1.0.0\n' > "$T/p/VERSION"; }
# run package.py with an open stdin pipe that is never closed and a harness limit; prints rc, seconds, output
run() { python3 - "$here/dev/package.py" "$T" "$@" <<'PY'
import subprocess, sys, tempfile, time
script, tmp, limit, extra = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4:]
t = time.time()
with tempfile.TemporaryFile("w+") as log:
    # stdin is a pipe this harness never writes to or closes, as a lane leaves it; communicate() would close it
    p = subprocess.Popen([sys.executable, script, "--root", tmp + "/p", "--out", tmp + "/p.zip"] + extra,
                         stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT, text=True)
    try:
        p.wait(timeout=limit)
        state = "rc=%s secs=%d" % (p.returncode, time.time() - t)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait()
        state = "rc=hung secs=%d" % (time.time() - t)
    p.stdin.close()
    log.seek(0)
    print(state); print(log.read())
PY
}
check() { if eval "$2"; then echo "ok   $1"; else echo "BAD  $1"; echo "$out" | head -5; bad=1; fi; }
case_stdin() {
  pkg 'import json, sys
json.load(sys.stdin)'  # like govern_hook.py: ignores --help and reads its JSON from stdin
  out=$(PACKAGE_CHILD_SECONDS=3 run 60)
  check "a --help that reads stdin finishes under an open stdin pipe" '! grep -q "rc=hung" <<<"$out"'
  check "and is refused by name, since it cannot run alone" 'grep -q "FAIL Scripts: skills/demo/scripts/demo.py does not run alone" <<<"$out"'
}
case_bound() {
  tok="987.1$$$RANDOM"  # this run's own sleeper, so concurrent lanes never see or kill each other's
  pkg "import subprocess, sys, time
subprocess.Popen(['sleep', '$tok'])
open('$T/started', 'w').close()
time.sleep(987)"
  out=$(PACKAGE_CHILD_SECONDS=60 run 40 --timeout 3)
  check "the child and its own child had started" '[ -e "$T/started" ]'
  check "the hard bound stops the run (exit 3)" 'grep -q "^rc=3 " <<<"$out"'
  check "with one TIMEOUT line naming what it waited on" '[ "$(grep -c "^TIMEOUT: package.py stopped after 3 seconds waiting on skills/demo/scripts/demo.py --help$" <<<"$out")" = 1 ]'
  sleep 1
  check "and no child is left holding a slot" '! pgrep -f "sleep $tok" >/dev/null'
  check "and no half ZIP is left at --out" '[ ! -e "$T/p.zip" ] && ! ls "$T"/*.part >/dev/null 2>&1'
  pkill -f "sleep $tok" 2>/dev/null; true
}
case_loop() {
  pkg 'print("ok")'; ln -s .. "$T/p/skills/demo/scripts/up"
  out=$(PACKAGE_CHILD_SECONDS=10 run 60)
  check "a looping symlink in a scripts folder does not hang the run" '! grep -q "rc=hung" <<<"$out"'
  check "nor crash it" '! grep -q Traceback <<<"$out" && grep -Eq "^rc=(0|1) " <<<"$out"'
}
case_child() {
  pkg 'import time
time.sleep(60)'  # blocks on something other than stdin
  out=$(PACKAGE_CHILD_SECONDS=2 run 40)
  check "a --help that never ends is cut at the child bound" '! grep -q "rc=hung" <<<"$out" && grep -q "^rc=1 " <<<"$out"'
  check "and refused by name" 'grep -q "FAIL Scripts: skills/demo/scripts/demo.py --help did not finish in 2 seconds" <<<"$out"'
}
case_term() {
  tok="987.2$$$RANDOM"
  pkg "import subprocess, time
subprocess.Popen(['sleep', '$tok'])
time.sleep(987)"
  PACKAGE_CHILD_SECONDS=60 python3 "$here/dev/package.py" --root "$T/p" --out "$T/p.zip" </dev/null >"$T/term.log" 2>&1 &
  pid=$!; seen=no; for i in $(seq 1 50); do pgrep -f "sleep $tok" >/dev/null && { seen=yes; break; }; sleep 0.2; done
  check "the child's own child was running before the kill" '[ $seen = yes ]'
  kill -TERM $pid; wait $pid; rc=$?; sleep 1; out=$(cat "$T/term.log")
  check "an outside SIGTERM stops the run with one line" '[ $rc = 143 ] && grep -q "^STOPPED: package.py got signal 15 while waiting on skills/demo/scripts/demo.py --help" <<<"$out"'
  check "and leaves no child behind" '! pgrep -f "sleep $tok" >/dev/null'
  pkill -f "sleep $tok" 2>/dev/null; true
}
for c in ${@:-stdin child bound loop term}; do "case_$c"; done
[ $bad = 0 ] && echo "ALL PASS" || { echo "FAILED"; exit 1; }
