#!/bin/bash
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# reads: skills/workflow-delivery/scripts/lanekit.py skills/workflow-regression/scripts/slots.py skills/workflow-delivery/scripts/proctree.py skills/workflow-monitoring/scripts/proctree.py skills/workflow-regression/scripts/proctree.py skills/workflow-delivery/scripts/flow.py skills/workflow-delivery/scripts/lane.py skills/workflow-monitoring/scripts/mend.py skills/workflow-monitoring/scripts/session_bind.py skills/workflow-regression/scripts/lanes.py
# Issue 1396: lanes, slots and step timeouts on native Windows Python as on POSIX. port_base() leases a base with no
# os.getuid or os.O_NOFOLLOW; a stop for a timeout or a mend takes the child's whole tree (killpg on POSIX, taskkill /T
# on Windows), and no stop site calls os.killpg itself. Runs the same on Linux, macOS and Windows.
# Value: protects=lanes get ports and timeouts stop whole trees on Windows (issue 1396); fails_when=a POSIX-only call
# comes back into a lease or a stop; why_new=the lane rows run only where POSIX calls exist; seam=none;
# no_claim=a real lane run on Windows
set -u
export LOOP_LANES_DIR=$(mktemp -d)/lanes
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$(dirname "$LOOP_LANES_DIR")"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
S="$here/skills"
out=$(python3 - "$S/workflow-delivery/scripts" "$S/workflow-regression/scripts" <<'PY' 2>&1
import sys
sys.path.insert(0, sys.argv[1]); import lanekit
sys.path.insert(0, sys.argv[2]); import slots
for mod in (lanekit, slots):
    fd, base = mod.port_base()
    print(mod.__name__, fd is not None and isinstance(base, int) and (base - 20000) % 100 == 0, base)
PY
)
echo "$out" | grep -qx "lanekit True 20000" && echo "$out" | grep -qx "slots True 20100" \
  && ok "lanekit.port_base() and slots.port_base() each lease a port base" || bad "port_base: $(echo "$out" | tail -3)"
for skill in workflow-delivery workflow-monitoring workflow-regression; do
  got=$(python3 - "$S/$skill/scripts" "$d/$skill.pid" <<'PY' 2>&1
import os, subprocess, sys, time
sys.path.insert(0, sys.argv[1]); import proctree
alive = getattr(proctree, "alive", None) or (lambda pid: subprocess.run(["kill", "-0", str(pid)], capture_output=True).returncode == 0)
grand = "import subprocess, sys, time; open(sys.argv[1], 'w').write(str(subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']).pid)); time.sleep(60)"
parent = subprocess.Popen([sys.executable, "-c", grand, sys.argv[2]], start_new_session=True)
for _ in range(100):
    if os.path.exists(sys.argv[2]) and open(sys.argv[2]).read():
        break
    time.sleep(0.1)
child = int(open(sys.argv[2]).read())
before = alive(parent.pid) and alive(child)
proctree.kill(parent.pid)
parent.wait(timeout=10)
for _ in range(50):
    if not alive(child):
        break
    time.sleep(0.1)
print("tree", before, alive(child))
PY
)
  [ "$(echo "$got" | tail -1)" = "tree True False" ] && ok "$skill's proctree.kill stops a child and the process it started" \
    || bad "$skill proctree: $(echo "$got" | tail -2)"
done
cmp -s "$S/workflow-delivery/scripts/proctree.py" "$S/workflow-monitoring/scripts/proctree.py" \
  && cmp -s "$S/workflow-delivery/scripts/proctree.py" "$S/workflow-regression/scripts/proctree.py" \
  && ok "the three proctree.py copies are the same" || bad "proctree.py copies differ"
left=$(cd "$S" && grep -n "os\.killpg\|os\.getpgrp()" workflow-delivery/scripts/flow.py workflow-delivery/scripts/lane.py \
  workflow-delivery/scripts/lanekit.py workflow-monitoring/scripts/mend.py workflow-monitoring/scripts/session_bind.py)
[ -z "$left" ] && ok "no stop site calls os.killpg or os.getpgrp itself" || bad "POSIX-only stops left: $left"
probes=$(cd "$S" && grep -rn "os\.kill([^)]*, 0)" --include=*.py . | grep -v "proctree.py")  # Ctrl+C to the target on Windows
[ -z "$probes" ] && ok "no liveness probe is os.kill(pid, 0), which sends Ctrl+C on Windows" || bad "os.kill probes left: $probes"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "FAILED $fails"; exit 1; }
