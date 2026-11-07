#!/bin/bash
# One small test for each Delivery and Release criterion, so a regression row doesn't run a whole toy script.
# usage: test-rows.sh ID   exits non-zero if the criterion doesn't hold. No model is called.
set -u
unset LOOP_BATCH
here=$(cd "$(dirname "$0")/../.." && pwd); id=${1:?usage: test-rows.sh ID}
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
"$here/dev/toy/make.sh" "$d/toy" >/dev/null || exit 1
goal="python3 $here/skills/workflow-delivery/scripts/goal.py"
watch="python3 $here/skills/workflow-monitoring/scripts/watch.py"
rel="python3 $here/skills/workflow-release/scripts/release.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh"
cd "$d/toy/repo" || exit 1
python3 "$here/skills/workflow-setup/scripts/setup.py" >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup; git push -q origin main
no() { echo "FAIL $id: $1"; exit 1; }

finish() { # finish SLUG STEPS: a finished level 0 goal with these verify steps
  $goal new "$1" --here --goal "Add $1" --done "calc has $1" >/dev/null || no "new"
  python3 - "$1" "$2" <<'PY'
import sys
path = ".loop/goals/%s.md" % sys.argv[1]
text = open(path).read().replace("## Verify by hand\n", "## Verify by hand\n\n%s\n" % sys.argv[2], 1)
open(path, "w").write(text)
PY
  printf '\n# %s\n' "$1" >> calc.py; git commit -qam "Add $1 to calc"
  $goal check "$1" >/dev/null && $goal pr "$1" >/dev/null || no "goal did not finish"
}
STEPS=$'1. Open calc.py.\n   Expect: the new line.'

case "$id" in
  DEL-1)
    $goal new nodone --here --goal "No line" 2>&1 | grep -q "no done lines" || no "new started with no done line"
    $watch go "No line" --slug nodone2 2>&1 | grep -q "REFUSED" || no "go started with no done line"
    [ -z "$(ls "$(git rev-parse --git-common-dir)/loop/runs" 2>/dev/null)" ] || no "a run record was written";;
  DEL-2)
    $goal new plain --here --goal "Plain" --done "plain" | grep -q "level=0" || no "default level is not 0";;
  DEL-3)
    $goal new risky --here --goal "CI" --done "ci" --touches ".github/x.yml" | grep -q "level=1" || no "not raised";;
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
