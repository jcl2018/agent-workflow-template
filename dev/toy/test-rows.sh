#!/bin/bash
# One small test for each of several Delivery criteria, so a regression row doesn't run a whole toy script.
# usage: test-rows.sh ID   exits non-zero if the criterion doesn't hold. No model is called.
set -u
unset LOOP_BATCH
here=$(cd "$(dirname "$0")/../.." && pwd); id=${1:?usage: test-rows.sh ID}
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
"$here/dev/toy/make.sh" "$d/toy" >/dev/null || exit 1
export LOOP_FLOW="$d/toy/flow.json"
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
watch="python3 $here/skills/workflow-monitoring/scripts/watch.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
cd "$d/toy/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
no() { echo "FAIL $id: $1"; exit 1; }

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
  DEL-8)
    $goal new nosteps --here --goal "No steps" --done "x" >/dev/null || no "new"
    printf '\n# nosteps\n' >> calc.py; git commit -qam "Change"
    for step in idea plan review qa ship; do F="python3 $here/skills/workflow-delivery/scripts/flow.py"; $F nosteps $step --wait 5 >/dev/null; $F nosteps $step --wait 10 >/dev/null
      $goal record nosteps $step --file "$(git rev-parse --git-common-dir)/loop/runs/nosteps.$step.txt" >/dev/null; done
    $goal check nosteps >/dev/null
    $goal pr nosteps 2>&1 | grep -q "no complete steps under ## Verify by hand" || no "pr opened with no verify steps"
    python3 - <<'PY'
p = ".loop/goals/nosteps.md"; t = open(p).read().replace("## Verify by hand\n", "## Verify by hand\n\n1. Open calc.py.\n", 1); open(p, "w").write(t)
PY
    git commit -qam "A step with no Expect line"; $goal check nosteps >/dev/null
    $goal pr nosteps 2>&1 | grep -q "no complete steps" || no "pr opened with a step that has no Expect line"
    python3 - <<'PY'
p = ".loop/goals/nosteps.md"; t = open(p).read().replace("1. Open calc.py.\n", "1. Open calc.py.\n   Expect: the change.\n", 1); open(p, "w").write(t)
PY
    git commit -qam "Complete step"; $goal check nosteps >/dev/null; $goal pr nosteps | grep -q "^PR " || no "pr refused good verify steps";;
  *) no "no such test";;
esac
echo "PASS $id"
