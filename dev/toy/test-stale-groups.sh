#!/bin/bash
# reads: skills/design-guide.md skills/loop-files.md skills/workflow-health/scripts/milestone.py
# Defect test for issue 89: a removed feature group name must not come back. No model is called.
# The groups are the page names in .loop/docs.tsv (minus Home) plus Backlog; Release and Milestones are gone, and the
# docs feature is "Documentation", not "Criteria and tests". usage: test-stale-groups.sh [ROOT]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd); root=${1:-$here}
cd "$root" || exit 1
bad=0
no() { echo "FAIL: $1"; bad=1; }
groups=$(grep -v '^#' .loop/docs.tsv | cut -f1 | grep -vx Home; echo Backlog)
removed="Release Milestones"

# the wiki titles, its headings, and the pages in .loop/docs.tsv
for g in $removed; do
  grep -q "^$g	" .loop/docs.tsv && no "docs.tsv has a $g page"
  [ -e "docs/wiki/$g.md" ] && no "the wiki has a $g page"
  grep -qE "^#+ +$g( |$)" docs/wiki/*.md && no "a wiki heading names the group $g"
done
for f in docs/wiki/*.md; do
  n=$(basename "$f" .md)
  [ "$n" = Home ] || [ "$n" = Tests ] || grep -qx "$n" <<<"$groups" || no "wiki page $n is not a feature group"
done

# the old name of the Documentation group, in the places that list groups
grep -nE "^\| Criteria and tests \|" skills/design-guide.md && no "design-guide.md calls Documentation 'Criteria and tests'"
grep -rnE "Criteria and tests" README.md skills/loop-files.md skills/design-guide.md docs/ROADMAP.md && no "the old name 'Criteria and tests' came back"

# a page list that names the groups must not name a removed one
for g in $removed; do
  grep -nE "pages \(.*\b$g\b" README.md docs/ROADMAP.md skills/design-guide.md skills/loop-files.md && no "a page list names $g"
  grep -nE "^\| $g \|" skills/design-guide.md && no "design-guide.md parts table has $g"
done

# the milestone list and the board, even when the old milestones exist on GitHub
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR=$(mktemp -d); trap 'rm -rf "$FAKE_GH_DIR"' EXIT
out=$(python3 "$here/skills/workflow-health/scripts/milestone.py" features; python3 "$here/skills/workflow-health/scripts/milestone.py" new --all 2>&1)
for g in $removed; do grep -qiE "(^|milestone )$g( |	|$)" <<<"$out" && no "the milestone list has $g"; done
for g in $groups; do grep -q "$g" <<<"$out" || no "the milestone list lacks $g"; done
# the step word and its skill stay: they are not a group
grep -q "workflow-release" .loop/docs.tsv || no "the release step's skill left docs.tsv"
[ $bad = 0 ] && echo "PASS: no removed feature group comes back" || exit 1
