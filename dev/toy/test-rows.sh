#!/bin/bash
# One small test for each Delivery and Release criterion, so a regression row doesn't run a whole toy script.
# usage: test-rows.sh ID   exits non-zero if the criterion doesn't hold. No model is called.
set -u
export LOOP_ROLE=worker  # goal.py and flow.py run only in a worker
unset LOOP_BATCH
here=$(cd "$(dirname "$0")/../.." && pwd); id=${1:?usage: test-rows.sh ID}
export HOME=$(mktemp -d)  # setup.py writes the private settings under HOME
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
"$here/dev/toy/make.sh" "$d/toy" >/dev/null || exit 1
export LOOP_FLOW="$d/toy/flow.json"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
watch="python3 $here/skills/workflow-monitoring/scripts/watch.py"
rel="python3 $here/skills/workflow-release/scripts/release.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
cd "$d/toy/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
no() { echo "FAIL $id: $1"; exit 1; }

finish() { # finish SLUG STEPS: a finished goal with these verify steps
  $goal new "$1" --here --goal "Add $1" --done "calc has $1" >/dev/null || no "new"
  python3 - "$1" "$2" <<'PY'
import sys
path = ".loop/goals/%s.md" % sys.argv[1]
text = open(path).read().replace("## Verify by hand\n", "## Verify by hand\n\n%s\n" % sys.argv[2], 1)
open(path, "w").write(text)
PY
  printf '\n# %s\n' "$1" >> calc.py; git commit -qam "Add $1 to calc"
  bash "$here/dev/toy/flow-done.sh" "$1" && $goal check "$1" >/dev/null && $goal pr "$1" >/dev/null || no "goal did not finish"
}
STEPS=$'1. Open calc.py.\n   Expect: the new line.'

case "$id" in
  DEL-1)
    $goal new nodone --here --goal "No line" 2>&1 | grep -q "no done lines" || no "new started with no done line"
    $watch go "No line" --slug nodone2 2>&1 | grep -q "REFUSED" || no "go started with no done line"
    [ -z "$(ls "$(git rev-parse --git-common-dir)/loop/runs" 2>/dev/null)" ] || no "a run record was written";;
  DEL-2)
    LOOP_FLOW="$d/none.json" $goal new noflow --here --goal "No flow" --done "x" 2>&1 | grep -q "no skill flow is set. Fix:" || no "started with no flow"
    sed 's/"FAKE_MODE": "unattended"/"FAKE_MODE": "interactive"/' "$LOOP_FLOW" > "$d/interactive.json"
    $goal new plain --here --goal "Plain" --done "plain" >/dev/null || no "new"
    LOOP_FLOW="$d/interactive.json" python3 "$here/skills/workflow-delivery/scripts/flow.py" plain idea 2>&1 | grep -q "wouldn't run unattended" || no "a step ran outside the unattended mode"
    [ ! -e "$(git rev-parse --git-common-dir)/loop/runs/plain.idea.txt" ] || no "a step started anyway";;
  DEL-3)
    $goal new held --here --goal "Held" --done "held" >/dev/null || no "new"
    F="python3 $here/skills/workflow-delivery/scripts/flow.py"; R="$(git rev-parse --git-common-dir)/loop/runs"
    FAKE_SKILL_OUT='PENDING: approve the plan\nSTEP: done' $F held plan --wait 5 >/dev/null; FAKE_SKILL_OUT='x' $F held plan --wait 10 >/dev/null
    $goal record held plan --file "$R/held.plan.txt" | grep -q "^WAITING held" || no "a pending decision didn't wait"
    python3 -c "import json,sys;s=json.load(open(sys.argv[1]));assert s['status']=='waiting' and s['flow']['plan']=='pending'" "$R/held.json" || no "pending was approved"
    $goal check held >/dev/null; $goal pr held 2>&1 | grep -q "the flow hasn't finished: idea, plan" || no "pr went on with a decision pending";;
  DEL-10)
    mkdir -p "$d/bin"
    printf '#!/bin/bash\n[ "$GH_PROMPT_DISABLED" = 1 ] || { read -r _; echo prompted >> "%s/prompted"; }\nexit 1\n' "$d" > "$d/bin/gh"; chmod +x "$d/bin/gh"
    export GH_PROMPT_DISABLED=0 GIT_EDITOR=vim
    ( PATH="$d/bin:$PATH"; python3 -c "
import subprocess, sys; sys.argv = ['x']
sys.path.insert(0, '$here/skills/workflow-release/scripts'); import merge, os
assert os.environ['GIT_EDITOR'] == 'true' and os.environ['GH_PROMPT_DISABLED'] == '1'
subprocess.run(['gh', 'x'], timeout=20)" ) < /dev/null || no "a script left a prompt on"
    [ ! -e "$d/prompted" ] || no "gh was allowed to prompt"
    for s in "$here"/skills/*/scripts/*.py; do
      grep -q "GIT_TERMINAL_PROMPT" "$s" || ! grep -q "^import subprocess\|subprocess\." "$s" || no "$s starts processes without the guard"
    done;;
  REL-1)
    finish none ""
    $rel cut none >/dev/null 2>&1 && no "cut with no verify steps"
    git switch -q main
    finish noexpect "1. Open calc.py."
    $rel cut noexpect >/dev/null 2>&1 && no "cut with a step that has no Expect line"
    git switch -q main
    finish good "$STEPS"
    $rel cut good >/dev/null || no "cut refused good verify steps";;
  REL-2)
    finish good "$STEPS"
    $rel cut good >/dev/null || no "cut failed"
    grep -q "^release create .*--draft" "$FAKE_GH_DIR/calls.log" || no "not created as a draft"
    grep -E "^(pr merge|release edit)" "$FAKE_GH_DIR/calls.log" && no "merged or published"
    git merge-base --is-ancestor loop/good origin/main && no "the branch reached main";;
  REL-3)
    LOOP_BATCH=1 finish batch "$STEPS"
    $rel cut batch >/dev/null 2>&1 && no "batch cut without --user"
    $rel cut batch --user >/dev/null || no "batch cut with --user failed";;
  *) no "no such test";;
esac
echo "PASS $id"
