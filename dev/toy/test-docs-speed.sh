#!/bin/bash
# reads: skills/workflow-docs/scripts/docs.py skills/workflow-docs/scripts/criteria.py
# reads: skills/workflow-docs/scripts/pageformat.py skills/workflow-docs/scripts/render.py
# Test DOC-12 and DOC-13 on this repo: the docs check finishes in under 30 seconds, and two runs on the same pages and
# rows print the same result. A slow or varying check fails. LIMIT (seconds) may be lowered to prove the failure.
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID  # run cells and rendered Tests never depend on the runner
here=$(cd "$(dirname "$0")/../.." && pwd)
cd "$here" || exit 1
limit=${LIMIT:-30}
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { python3 "$here/skills/workflow-docs/scripts/docs.py" check 2>&1; }
start=$(python3 -c 'import time; print(time.time())')
first=$(check)
took=$(python3 -c "import time; print(round(time.time() - $start, 1))")
python3 -c "import sys; sys.exit(0 if $took < $limit else 1)" && ok "DOC-12 the docs check finishes in under ${limit} seconds on this repo" || bad "slow: ${took}s"
second=$(check)
[ "$first" = "$second" ] && ok "DOC-13 two docs check runs on the same pages and rows print the same result" || bad "the check varies between runs"
[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
