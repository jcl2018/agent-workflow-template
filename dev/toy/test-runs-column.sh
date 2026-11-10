#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/runs.py
# reads: skills/workflow-regression/scripts/lanes.py skills/workflow-regression/scripts/actions.py
# Proves the run column of .loop/regression-runs.tsv on a throwaway repo with a fake gh: empty outside CI, so two
# branches write identical lines, the Actions run URL when all three GITHUB_* vars are set, a 3-column file upgraded,
# a row not rerun kept, and the flaky column (5th) empty unless a row flipped (flaky.py).
# usage: test-runs-column.sh
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR=$(mktemp -d)
unset GH_TOKEN GITHUB_TOKEN GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID GITHUB_STEP_SUMMARY GITHUB_ENV GITHUB_OUTPUT
pass=0; fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }
r=$(mktemp -d); toy_on_exit 'cd /; rm -rf "$r" "$FAKE_GH_DIR"'
cd "$r" && git init -q && git config user.email t@t && git config user.name t && mkdir .loop
{ printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n'
  printf 'a1\tland\ttrue\t-\t2026-01-01\tA passing row.\tcriterion\t\n'
  printf 'b1\tland\tfalse\t-\t2026-01-01\tA failing row.\tcriterion\t\n'; } > .loop/regression.tsv
git add -A && git commit -qm toy
day=$(date -u +%Y-%m-%d)
url=https://github.example/o/r/actions/runs/42

echo "== outside CI the run column is empty"
$reg run a1 >/dev/null 2>&1
head -1 .loop/regression-runs.tsv | grep -qxF "# id	status	date	run	flaky" && grep -qxF "a1	PASS	$day		" .loop/regression-runs.tsv \
  && ok "the 4th column is empty outside CI" || bad "empty column: $(cat .loop/regression-runs.tsv)"

echo "== in CI the run column is the Actions run URL"
GITHUB_SERVER_URL=https://github.example GITHUB_REPOSITORY=o/r GITHUB_RUN_ID=42 $reg run b1 >/dev/null 2>&1
grep -qxF "b1	FAIL	$day	$url	" .loop/regression-runs.tsv && ok "with all three GITHUB_* vars set the Actions URL is written" \
  || bad "url column: $(cat .loop/regression-runs.tsv)"
grep -qxF "a1	PASS	$day		" .loop/regression-runs.tsv && ok "a row not rerun keeps its run cell" || bad "kept cell: $(cat .loop/regression-runs.tsv)"

echo "== with only some GITHUB_* vars set the run column is empty"
GITHUB_SERVER_URL=https://github.example GITHUB_RUN_ID=42 $reg run b1 >/dev/null 2>&1
grep -qxF "b1	FAIL	$day		" .loop/regression-runs.tsv && ok "with only some GITHUB_* vars set the cell is empty" \
  || bad "partial vars: $(cat .loop/regression-runs.tsv)"

echo "== two branches running the same rows on the same day write identical files"
git switch -qc other && git commit -q --allow-empty -m other && $reg run >/dev/null 2>&1; cp .loop/regression-runs.tsv "$r.other"
git switch -q - && $reg run >/dev/null 2>&1
cmp -s .loop/regression-runs.tsv "$r.other" && ok "two branches running the same rows on one day write identical run files" \
  || bad "branches differ: $(diff .loop/regression-runs.tsv "$r.other")"; rm -f "$r.other"

echo "== a 3-column file is read and upgraded"
printf '# id\tstatus\tdate\na1\tPASS\t2026-11-01\nold\tFAIL\t2026-11-02\n' > .loop/regression-runs.tsv
$reg run b1 >/dev/null 2>&1
head -1 .loop/regression-runs.tsv | grep -qxF "# id	status	date	run	flaky" && grep -qxF "a1	PASS	2026-11-01		" .loop/regression-runs.tsv \
  && grep -qxF "old	FAIL	2026-11-02		" .loop/regression-runs.tsv && grep -qxF "b1	FAIL	$day		" .loop/regression-runs.tsv \
  && [ "$(awk -F'\t' '!/^#/ && NF != 5' .loop/regression-runs.tsv | wc -l | tr -d ' ')" = 0 ] \
  && ok "a 3-column file is read and upgraded to 5 columns" || bad "upgrade: $(cat .loop/regression-runs.tsv)"

echo "$pass passed, $fail failed"
[ "$fail" = 0 ] && echo "ALL PASS" || exit 1
