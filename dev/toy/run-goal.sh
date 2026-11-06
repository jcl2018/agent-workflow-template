#!/bin/bash
# Run one goal on a toy repo with a headless agent. usage: run-goal.sh REPO_DIR LEVEL SLUG "GOAL" "DONE1" ["DONE2"] 
# env: AGENT=claude|codex  MODEL=<model>  EXTRA=<more prompt text>
set -e
here=$(cd "$(dirname "$0")/../.." && pwd); repo=$1; level=$2; slug=$3; goal=$4; shift 4
done_args=""; for d in "$@"; do done_args="$done_args --done \"$d\""; done
prompt="Follow the skill at $here/skills/workflow-delivery/SKILL.md. Its script is $here/skills/workflow-delivery/scripts/goal.py. Run \`go \"$goal\"$done_args --level $level\` in this repo with the slug $slug. Do the whole run to the pull request. $EXTRA"
cd "$repo"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="${FAKE_GH_DIR:-$repo/../gh}" 
if [ "${AGENT:-claude}" = codex ]; then
  codex exec --skip-git-repo-check -s workspace-write ${MODEL:+-m $MODEL} "$prompt"
else
  claude -p --model "${MODEL:-haiku}" --allowedTools "Bash,Read,Write,Edit" --add-dir "$here/skills" <<<"$prompt"
fi
