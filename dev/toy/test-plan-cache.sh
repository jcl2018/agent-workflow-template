#!/bin/bash
# reads: dev/toy/plan-fixture.py dev/toy/plan-golden.txt skills/workflow-regression/scripts/ skills/workflow-regression/references/commands.md
# reads: dev/package.py dev/toy/reap.sh
# Proves the lane planner's cost and its row set (issue 710): `golden` the planned rows equal the v0.27.6 planner's on fixture
# repos; `calls` planning git calls and os.walk calls stay flat as rows grow. More modes arrive with the cache (identity,
# key, sizes, seconds). All fixtures are synthetic (dev/toy/plan-fixture.py) and no model is called.
# usage: test-plan-cache.sh golden|calls|identity|key|sizes|seconds|all
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
mode=${1:-all}
S="$here/skills/workflow-regression/scripts"
F="$here/dev/toy/plan-fixture.py"
G="$here/dev/toy/plan-golden.txt"
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN
unset LANES_WIDE LANES_NO_CACHE _LOOP_LANE_LABEL _LOOP_LANE_HELD
export HOME=$(mktemp -d) PYTHONDONTWRITEBYTECODE=1
d=$(mktemp -d)
toy_on_exit 'rm -rf "$d" "$HOME"'
REALGIT=$(command -v git)
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
# fail NAME EXPECTED ACTUAL: the one failure format, with the line that reruns it
fail() { bad "$1"; echo "    expected: $2"; echo "    actual:   $3"; echo "    rerun: bash dev/toy/test-plan-cache.sh ${cur:-$mode}"; }
nocache() { grep -v '^PLAN_CACHE:'; }

m_golden() { cur=golden
  echo "== golden: the planned rows equal the v0.27.6 planner's"
  # Value: protects=a lane's planned row set is the one the v0.27.6 planner chose (done line 2); fails_when=a planner change adds, drops or re-words a selected row on any fixture case; why_new=nothing compared plans across planner versions; seam=none; no_claim=the repo's own rows (they move with HEAD)
  mkdir -p "$d/g"
  local got
  got=$(LANES_NO_CACHE=1 python3 -B "$F" golden "$S" "$d/g" | nocache)
  if [ "$got" = "$(cat "$G")" ]; then ok "every fixture case plans exactly as the committed golden"; else
    fail "golden plans" "plan-golden.txt" "$(diff <(echo "$got") "$G" | head -20)"; fi
  # Value: protects=the committed golden holds no machine path; fails_when=a temp or home path is in plan-golden.txt; why_new=goldens are committed text; seam=none; no_claim=none
  if grep -Eq '/(Users|home|private|var|tmp)/' "$G"; then fail "golden has no machine path" "none" "$(grep -E '/(Users|home|private|var|tmp)/' "$G" | head -3)"; else ok "plan-golden.txt names no machine path"; fi
  # Value: protects=the golden really came from the v0.27.6 planner, never regenerated from new code; fails_when=a fresh run of the v0.27.6 scripts differs from plan-golden.txt; why_new=the identity proof compares new code with old code, not new with new; seam=git history; no_claim=none
  if git -C "$here" cat-file -e '6b0f23c^{commit}' 2>/dev/null; then
    mkdir -p "$d/old" "$d/og"
    git -C "$here" archive 6b0f23c skills/workflow-regression/scripts | tar -x -C "$d/old"
    local was
    was=$(python3 -B "$F" golden "$d/old/skills/workflow-regression/scripts" "$d/og")
    if [ "$was" = "$(cat "$G")" ]; then ok "plan-golden.txt equals a fresh run of the v0.27.6 scripts"; else
      fail "golden is v0.27.6 output" "equal" "$(diff <(echo "$was") "$G" | head -20)"; fi
  else
    echo "SKIP: golden-vs-v0.27.6 proof (6b0f23c absent; run git fetch --unshallow)"
    [ "${STRICT:-}" != 1 ] || bad "golden-vs-v0.27.6 proof skipped under STRICT=1"
  fi
}

# plan_counts ROWS: git calls and os.walk calls of one cold plan (no cache, no record), after the fixture is built
plan_counts() {
  local repo="$d/n$1" log="$d/git$1.log"
  python3 -B "$F" gen "$repo" --rows "$1" --skills 4 --modules 5 --docs 5 --app 6
  mkdir -p "$d/shim"
  printf '#!/bin/sh\necho "$1" >> "$GITLOG"\nexec "%s" "$@"\n' "$REALGIT" > "$d/shim/git"; chmod +x "$d/shim/git"
  : > "$log"
  GITLOG="$log" PATH="$d/shim:$PATH" LANES_NO_CACHE=1 python3 -B "$F" walks "$S" "$repo" > /dev/null 2> "$d/walk$1.txt"
  CALLS=$(wc -l < "$log" | tr -d ' ')
  WALKS=$(awk '/^WALKS/ {print $2}' "$d/walk$1.txt")
  TALLY=$(sort "$log" | uniq -c | sort -rn | awk '{printf "%s=%s ", $2, $1}')
}

m_calls() { cur=calls
  echo "== calls: planning cost stays flat as rows grow"
  plan_counts 20; local c20=$CALLS w20=$WALKS t20=$TALLY
  plan_counts 120; local c120=$CALLS w120=$WALKS t120=$TALLY
  echo "    20 rows: $c20 git calls, $w20 os.walk calls ($t20)"
  echo "    120 rows: $c120 git calls, $w120 os.walk calls ($t120)"
  # Value: protects=planning time does not grow with the number of rows (issue 710: one git diff and git status per row); fails_when=git calls at 120 rows exceed those at 20 by more than 2, or 20 rows take more than 30 calls; why_new=the per-row eager setdefault in tiers.changed was never measured; seam=PATH shim logging every git call; no_claim=wall seconds (they move with load; the nightly seconds row measures them)
  if [ $((c120 - c20)) -le 2 ] && [ "$c20" -le 30 ]; then ok "git calls: $c20 at 20 rows, $c120 at 120 rows"; else
    fail "git calls flat in rows" "calls(120)-calls(20) <= 2 and calls(20) <= 30" "calls(20)=$c20 calls(120)=$c120"; fi
  # Value: protects=a folder shared by many rows is listed once per plan (issue 710 part 2); fails_when=os.walk calls at 120 rows exceed those at 20 by more than 2; why_new=lanes.walk was called per row; seam=os.walk wrapped in the plan driver; no_claim=the number of walks at 20 rows
  if [ $((w120 - w20)) -le 2 ]; then ok "os.walk calls: $w20 at 20 rows, $w120 at 120 rows"; else
    fail "os.walk calls flat in rows" "walks(120)-walks(20) <= 2" "walks(20)=$w20 walks(120)=$w120"; fi
}

case "$mode" in
  golden) m_golden ;;
  calls) m_calls ;;
  all) m_golden; m_calls ;;
  *) echo "usage: test-plan-cache.sh golden|calls|identity|key|sizes|seconds|all"; exit 2 ;;
esac
if [ "$fails" = 0 ]; then echo "ALL PASS"; else echo "FAILED: $fails"; exit 1; fi
