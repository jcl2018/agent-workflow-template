#!/bin/bash
# Stops every process a toy test started when the test ends: passed, failed, interrupted or its pipe closed.
# Sourcing it exports TOY_REAP_ID (a fresh marker every child inherits, even one detached with setsid) and
# installs the EXIT, INT, TERM, HUP and PIPE traps; on exit the test's callbacks run, then every own process
# carrying the marker gets TERM, then KILL, up to 5 rounds (dev/toy/reap.py does the finding and the signals).
#
# Every dev/toy/test-*.sh starts with these two lines (test-no-leftovers.sh checks it):
#   here=$(cd "$(dirname "$0")/../.." && pwd)
#   . "$here/dev/toy/reap.sh"
# Never set your own trap; register cleanup instead, run at exit in order, a failing one never stops the rest:
#   toy_on_exit 'rm -rf "$d"'
# Exit code: a test that would exit 0 exits 1 when processes are left after 5 rounds (a REAP: line says which);
# INT exits 130, TERM 143, HUP 129, a closed pipe 141; any other status is kept. A signal sent only to the
# shell is handled after its foreground child returns. A nested toy test reaps its own marker; one killed with
# SIGKILL can't clean up, so its processes are left for:
#   bash dev/toy/reap.sh --sweep-dead [--dry-run]   stop this lane's processes whose test shell is gone
# Functions: toy_on_exit CMD, toy_list VAR VALUE (print matching processes), toy_reap VAR VALUE (stop them).
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
  case "${1:-}" in
    --sweep-dead) shift; exec python3 "$(cd "$(dirname "$0")" && pwd)/reap.py" sweep "$@" ;;
    *) echo "usage: bash dev/toy/reap.sh --sweep-dead [--dry-run]  (or source it from a toy test)" >&2; exit 2 ;;
  esac
fi
[ -z "${_toy_reap_on:-}" ] || return 0
# Native Windows cannot run a test that needs the gh fake (CreateProcess does not launch a script named gh): it says so
# with exit 77, and writes $TOY_SKIP_FILE when a lane set one, since a row's `| grep -q` hides the exit status.
toy_skip() { echo "SKIP: $*"; [ -z "${TOY_SKIP_FILE:-}" ] || echo skip > "$TOY_SKIP_FILE"; exit 77; }
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) grep -q fakegh "$0" && toy_skip "$(basename "$0") needs the gh fake, which native Windows cannot launch";; esac
export LOOP_NO_GIT_HOOKS=1  # a toy never installs git hooks into its repos (the guard-enforce test unsets it)
export LOOP_NO_HEALTH=1 LOOP_NO_ISSUES=1  # setup's two health runs and its issue filing are off in a toy; the setup-adopt rows that test them unset these
_toy_reap_on=1
_toy_reap_py="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/reap.py"
_toy_reap_label=$(basename "$0")
_toy_reap_cbs=""
_toy_reap_done=""
# The lane id (issue 435): 8 hex of the lane's _LOOP_LANE_LABEL, or "hand" outside a lane; nested tests inherit it.
# A sweep only touches markers carrying its own lane id, so one lane never stops another lane's processes.
[ -n "${TOY_REAP_LANE:-}" ] || TOY_REAP_LANE=$( [ -n "${_LOOP_LANE_LABEL:-}" ] && printf %s "$_LOOP_LANE_LABEL" | shasum | cut -c1-8 || echo hand)
TOY_REAP_ID="toy-$$-$(date +%s)-$RANDOM-L$TOY_REAP_LANE"
export TOY_REAP_ID TOY_REAP_LANE
toy_on_exit() { _toy_reap_cbs="${_toy_reap_cbs}${1}
"; }
# The local schedule never touches the real home: its registry, launch agent folder and launchctl are per-test fakes.
_toy_sched=$(mktemp -d); toy_on_exit 'rm -rf "$_toy_sched"'
export LOOP_REPO_VISIBILITY=public  # a toy repo is public unless a test unsets this and uses the fake gh
export LOOP_SCHEDULE_PROGRAM="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/skills/workflow-health/scripts/automation.py"  # install is not refused in a worktree
export LOOP_SCHEDULE_HOME="$_toy_sched/schedule" LOOP_AGENTS_DIR="$_toy_sched/agents" LOOP_LAUNCHCTL="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/fakegh/launchctl"
toy_list() { python3 "$_toy_reap_py" list "$1=$2"; }
toy_reap() { python3 "$_toy_reap_py" reap "$1=$2" --label "$_toy_reap_label"; }
_toy_reap_exit() {
  local rc=$? cb
  trap '' PIPE INT TERM HUP
  [ -z "$_toy_reap_done" ] || return 0
  _toy_reap_done=1
  set +e
  while IFS= read -r cb; do
    [ -z "$cb" ] || eval "$cb" || true
  done <<EOF_TOY_REAP
$_toy_reap_cbs
EOF_TOY_REAP
  toy_reap TOY_REAP_ID "$TOY_REAP_ID" >/dev/null || { [ "$rc" != 0 ] || rc=1; }
  exit "$rc"
}
_toy_reap_sig() { trap '' PIPE INT TERM HUP; exit "$1"; }
trap '_toy_reap_exit' EXIT
trap '_toy_reap_sig 130' INT
trap '_toy_reap_sig 143' TERM
trap '_toy_reap_sig 129' HUP
trap '_toy_reap_sig 141' PIPE

# toy_need_posix WHY: a test that cannot run on native Windows (no /tmp shared with python, backslash paths, fake gh
# on PATH) says so with exit 77, which the regression lane reports as SKIPPED instead of failing the lane.
toy_need_posix() { case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) toy_skip "$@";; esac; }
