#!/bin/bash
# reads: skills/workflow-monitoring/scripts/ skills/workflow-delivery/scripts/ skills/workflow-setup/scripts/setup.py
# Issue 99: the operate-all toy suite passes 10 of 10 under load. Starts one busy loop per CPU, each of which dies with
# this script even on SIGKILL (it checks its parent), runs dev/toy/test-operate.sh 10 times and requires ALL PASS each
# time. Nightly: about 6 minutes. usage: test-operate-load.sh [RUNS]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
runs=${1:-10}
cpus=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 2)
me=$$
for _ in $(seq "$cpus"); do (while kill -0 "$me" 2>/dev/null; do :; done) & done
trap 'kill $(jobs -p) 2>/dev/null' EXIT
passed=0
for i in $(seq "$runs"); do
  if bash "$here/dev/toy/test-operate.sh" 2>&1 | tail -1 | grep -qx "ALL PASS"; then passed=$((passed + 1)); else echo "run $i FAILED"; fi
done
echo "operate-all under load ($cpus busy loops): $passed of $runs passed"
[ "$passed" = "$runs" ] && echo "ALL PASS" || exit 1
