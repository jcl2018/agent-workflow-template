#!/bin/bash
# reads: skills/workflow-regression/references/commands.md skills/workflow-regression/scripts/
# reads: skills/workflow-delivery/scripts/ skills/workflow-release/scripts/merge.py
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
# Every message code a lane, the regression runner or merge.py prints has a row in references/commands.md with its exit
# and what to do, so the agent reading a line can look it up (DX-18).
# Value: protects=the lane messages table lists every code the scripts print; fails_when=a new code ships without its
# row; why_new=the codes were spread across five scripts with no list; seam=none; no_claim=each row's wording
set -u
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
doc="$here/skills/workflow-regression/references/commands.md"
codes=$(cat "$here"/skills/workflow-regression/scripts/*.py "$here"/skills/workflow-delivery/scripts/*.py "$here/skills/workflow-release/scripts/merge.py" \
  | grep -oE '\b(LANE_[A-Z_]+|UNMAPPED|FULL_TIMEOUT|FLAKY|KILLED|SUITE_TIME|BASE_MOVED|BASE_FETCH|HEAD_MOVED|NO LANE|WAITING)\b' | sort -u)
missing=""
for c in $codes; do grep -q "^| [^|]*$c" "$doc" || missing="$missing $c"; done
[ -n "$codes" ] && [ -z "$missing" ] && ok "every code the scripts print has a row in references/commands.md ($(echo $codes | wc -w | tr -d ' ') codes)" || bad "codes with no row:$missing"
grep -q "^| Code | Printed by | Exit | Meaning | What to do |$" "$doc" && ok "the table has code, printer, exit, meaning and fix columns" || bad "table header"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
