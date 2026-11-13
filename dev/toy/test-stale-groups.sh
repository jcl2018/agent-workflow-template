#!/bin/bash
# reads: skills/loop-files.md
# Defect test for issue 89: a removed feature group name must not come back. No model is called.
# The groups are the page names in .loop/docs.tsv (minus Home); Release and Milestones are gone, and the
# docs feature is "Documentation", not "Criteria and tests". usage: test-stale-groups.sh [ROOT]
set -u
unset LOOP_SESSION_TOOL LOOP_OPERATION_SESSION  # a toy test never reaches a real session tool
here=$(cd "$(dirname "$0")/../.." && pwd); root=${1:-$here}
. "$here/dev/toy/reap.sh"
cd "$root" || exit 1
bad=0
no() { echo "FAIL: $1"; bad=1; }
groups=$(grep -v '^#' .loop/docs.tsv | cut -f1 | grep -vx Home)
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
grep -nE "^\| Criteria and tests \|" skills/loop-files.md && no "loop-files.md calls Documentation 'Criteria and tests'"
grep -rnE "Criteria and tests" README.md skills/loop-files.md docs/ROADMAP.md && no "the old name 'Criteria and tests' came back"

# a page list that names the groups must not name a removed one
for g in $removed; do
  grep -nE "pages \(.*\b$g\b" README.md docs/ROADMAP.md skills/loop-files.md && no "a page list names $g"
  grep -nE "^\| $g \|" skills/loop-files.md && no "loop-files.md parts table has $g"
done

# the step word and its skill stay: they are not a group
grep -q "workflow-release" .loop/docs.tsv || no "the release step's skill left docs.tsv"
[ $bad = 0 ] && echo "PASS: no removed feature group comes back" || exit 1
