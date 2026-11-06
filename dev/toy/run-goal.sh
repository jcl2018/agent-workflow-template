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
  # codex runs a login shell that resets PATH, so name the fake gh in the prompt
  prompt="$prompt Prefix every goal.py command with PATH=$here/dev/toy/fakegh:\$PATH FAKE_GH_DIR=$FAKE_GH_DIR so the test double of gh is used."
  codex exec --skip-git-repo-check -s workspace-write -c "sandbox_workspace_write.writable_roots=[\"$(cd "$repo" && git rev-parse --absolute-git-dir)\",\"$(cd "$repo" && git remote get-url origin)\"]" -c model_reasoning_effort=low ${MODEL:+-m $MODEL} "$prompt" </dev/null
else
  claude -p --model "${MODEL:-haiku}" --allowedTools "Bash,Read,Write,Edit" --add-dir "$here/skills" <<<"$prompt"
fi
