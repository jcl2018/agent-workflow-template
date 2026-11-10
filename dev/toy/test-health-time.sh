#!/bin/bash
# reads: skills/workflow-health/scripts/health.py
# HLT-7 on this repo itself: health.py check without controls finishes in under 60 seconds, and the check-time rule warns
# past 60 seconds. It runs the check from this repo's root, so its row reruns on every change. usage: test-health-time.sh
set -u
unset LOOP_HEALTH_T0 CI GITHUB_ACTIONS
here=$(cd "$(dirname "$0")/../.." && pwd)
H="python3 $here/skills/workflow-health/scripts/health.py"
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
echo "== HLT-7: check without controls in under 60 seconds"
# Value: protects=HLT-7; fails_when=a rule makes check slow (a gh call per issue, a scan of the whole history); why_new=no
# timing check; seam=this repo; no_claim=a much larger repo
cd "$here" || exit 1
t0=$(date +%s); $H check --skip controls >/dev/null 2>&1; t1=$(date +%s)
check "check --skip controls on this repo takes under 60 seconds ($((t1 - t0)) s)" '[ $((t1 - t0)) -lt 60 ]'
check "the check-time rule warns on a fixture past 60 seconds" 'LOOP_HEALTH_T0=1 $H check --group performance 2>&1 | grep -q "^WARN performance check check-time"'

[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
