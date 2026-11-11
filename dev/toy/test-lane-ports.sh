#!/bin/bash
# reads: skills/workflow-delivery/scripts/lane.py skills/workflow-regression/scripts/slots.py skills/workflow-regression/scripts/
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# REG-8: lanes running side by side never share ports or temp files. Each lane child leases its own port base from
# the pool (20000 + 100 x N for the first free port-N file, held while it lives) and gets its own TMPDIR; with all
# 100 leases held it runs without one and its note says so.
# Value: protects=two lanes never share a port range or a temp folder (REG-8); fails_when=the base comes from a pid or
# a shared default, or a held lease is handed out again; why_new=lanes had no ports or TMPDIR of their own; seam=none;
# no_claim=real port binding (rows only read the variable)
set -u
export HOME=$(mktemp -d) LOOP_LANES_DIR=$(mktemp -d)/lanes
export LOOP_LANE_PORT_BASE=20700  # as inside a lane (this test is a row): a nested lane with no lease must not inherit it
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME" "$(dirname "$LOOP_LANES_DIR")"'
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
L="$here/skills/workflow-delivery/scripts/lane.py"
run_lane() {  # NAME: a lane child whose "lane" writes its port base and TMPDIR, then waits 2 s
  mkdir -p "$d/$1.tmp"
  TMPDIR="$d/$1.tmp" python3 "$L" lane-exec "$d/$1.rc" 60 "$d/$1.last" a-1 "$LOOP_LANES_DIR" -- \
    sh -c 'echo "$LOOP_LANE_PORT_BASE $TMPDIR" > "'"$d"'/$0.out"; echo x > "$TMPDIR/x"; sleep 2' "$1" >/dev/null 2>&1
}
run_lane a & run_lane b & wait
pa=$(cut -d' ' -f1 "$d/a.out" 2>/dev/null); pb=$(cut -d' ' -f1 "$d/b.out" 2>/dev/null)
[ -n "$pa" ] && [ -n "$pb" ] && [ "$pa" != "$pb" ] && [ $(( (pa - 20000) % 100 )) = 0 ] \
  && ok "two lanes at once get different port bases from the pool ($pa, $pb)" || bad "port bases: [$pa] [$pb]"
[ "$(cut -d' ' -f2 "$d/a.out")" != "$(cut -d' ' -f2 "$d/b.out")" ] && [ -f "$d/a.tmp/x" ] && [ -f "$d/b.tmp/x" ] \
  && ok "each lane writes in its own TMPDIR and both finish" || bad "TMPDIR shared or missing"
out=$(python3 - "$here/skills/workflow-regression/scripts" <<'PY'
import sys
sys.path.insert(0, sys.argv[1]); import slots
got = [slots.port_base() for _ in range(20)]
bases = [b for fd, b in got if fd is not None]
print(len(set(bases)), len(bases))
PY
)
[ "$out" = "20 20" ] && ok "20 leases held at once get 20 distinct bases" || bad "leases: $out"
python3 - "$here/skills/workflow-regression/scripts" "$d/holder.ready" <<'PY' &
import os, sys, time
sys.path.insert(0, sys.argv[1]); import slots
parent = os.getppid()
held = [slots.port_base() for _ in range(100)]
open(sys.argv[2], "w").write(str(sum(fd is not None for fd, _ in held)))
while os.getppid() == parent: time.sleep(0.2)  # held as long as this test lives, however slow a busy machine starts lane c
PY
hp=$!; for _ in $(seq 1200); do [ -s "$d/holder.ready" ] && break; sleep 0.1; done
run_lane c; kill $hp 2>/dev/null
[ "$(cat "$d/holder.ready")" = 100 ] && grep -q "^Note: no port lease free (100 in use); LOOP_LANE_PORT_BASE unset" "$d/c.rc.note" \
  && [ "$(cut -d' ' -f1 "$d/c.out")" = "" ] && ok "with all 100 leases held a lane runs without one and its note says so" || bad "all held: $(cat "$d/c.rc.note" 2>/dev/null)"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
