#!/bin/bash
# reads: skills/workflow-monitoring/scripts/
# Issue 159: worker.py's last save rereads the run record, so a merge recorded from outside while gh answers is kept.
# A stand-in merged() records the merge mid-call. No model or network. usage: test-worker-save.sh [DIR]
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
d=${1:-$(mktemp -d)}; rm -rf "${d:?}"; mkdir -p "$d/repo"; cd "$d/repo" || exit 1
git init -q -b main
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
# Value: protects=#159; fails_when=worker.py saves the record it loaded before asking gh; why_new=defect test; seam=a
# stand-in merged(); no_claim=gh's real timing
mkdir -p .git/loop/runs .git/loop/logs
printf '{"slug": "w", "status": "done", "pr": "https://example.test/pull/1", "log": []}' > .git/loop/runs/w.json
out=$(python3 - "$here/skills/workflow-monitoring/scripts" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1]); import worker
def merged(pr):  # while gh answers, the release step records the merge from outside
    s = json.load(open(".git/loop/runs/w.json")); s.update(report={"status": "merged", "pr": pr, "text": "merged from outside", "at": "x"})
    json.dump(s, open(".git/loop/runs/w.json", "w")); return False
worker.merged = merged; worker.release_step = lambda state: None
class A: slug = "w"; command = ["true"]
worker.cmd_loop(A())
print(json.load(open(".git/loop/runs/w.json"))["report"]["status"])
PY
)
check "worker.py's last save keeps a merge recorded from outside while gh answered (issue 159)" '[ "$(tail -1 <<<"$out")" = merged ]'


[ "$fails" = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
