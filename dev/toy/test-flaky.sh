#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/flaky.py
# reads: skills/workflow-regression/scripts/lanes.py skills/workflow-regression/scripts/runs.py
# reads: skills/workflow-regression/scripts/tests.py skills/workflow-health/scripts/health.py
# Proves FLAKY (REG-9, flaky.py) on a throwaway repo with a fake gh: a row whose result flips on the same clean commit
# and runner is marked with the raw result kept, the exit following that result, a sticky flag shown by tests.py list
# and health's TESTS block, never reused, and cleared by a later commit's clean pass; a dirty tree, another runner or a
# record from before the fields never marks. No model is called.
# usage: test-flaky.sh [marked|nofalse]   (no argument: both)
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR=$(mktemp -d)
unset GH_TOKEN GITHUB_TOKEN GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID GITHUB_STEP_SUMMARY _LOOP_LANE_LABEL LANES_WIDE
pass=0; fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }
r=$(mktemp -d); export FLIP="$r/flip"; toy_on_exit 'cd /; rm -rf "$r" "$FAKE_GH_DIR"'
cd "$r" && git init -q -b main repo && cd repo && git config user.email t@t && git config user.name t && mkdir .loop
{ printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n'
  printf 'f\tland\t[ "$(cat "$FLIP")" = pass ]\t-\t2026-01-01\tA row whose result the test sets.\tcriterion\t\n'; } > .loop/regression.tsv
git add -A && git commit -qm toy
record() { ls "$(git rev-parse --git-common-dir)"/loop/tests/*.json; }
go() { echo "$1" > "$FLIP"; out=$($reg run f 2>&1); rc=$?; }
flag() { awk -F'\t' '$1 == "f" { print $5 }' .loop/regression-runs.tsv; }
listed() { python3 "$here/skills/workflow-regression/scripts/tests.py" list --root . | grep -c "FLAKY"; }
next() { git commit -q --allow-empty -m "$1"; }
head12() { git rev-parse HEAD | cut -c1-12; }

marked() {
echo "== FAIL, PASS, PASS on one clean commit stays flaky and exits 0"
# Value: protects=a row that failed then passed on the same clean commit and runner is marked FLAKY, with the result kept
#   and exit 0; fails_when=no flip is detected, the result is replaced by FLAKY or the exit fails; why_new=no run compared a
#   row's results; seam=none; no_claim=flips across machines (the runner check is proved in nofalse)
go fail; go pass
grep -qxF "PASS f" <<<"$out" && [ "$rc" = 0 ] && grep -q "^FLAKY f: failed then passed on $(head12) (same clean tree; runner .*, python [0-9.]*)\. Note: the result counts as passed; the row is never reused while flaky$" <<<"$out" \
  && ok "FAIL then PASS prints the FLAKY line, keeps PASS and exits 0" || bad "fail then pass: rc=$rc $out"
# Value: protects=the flag is sticky on its commit and shown everywhere tests are listed (regression-runs.tsv, tests.py
#   list, health's TESTS block); fails_when=a third PASS clears it or a listing drops it; why_new=no listing had a flaky
#   state; seam=none; no_claim=the wiki Tests tables (criteria.py renders tests.py's cells)
go pass
health=$(cd "$here/skills/workflow-health/scripts" && python3 -c "import sys, health; print('\n'.join(health.tests_block(sys.argv[1])))" "$r/repo")
[ "$rc" = 0 ] && grep -q "^FLAKY f: failed then passed" <<<"$out" && [ "$(flag)" = "$(head12)" ] && [ "$(listed)" = 1 ] \
  && grep -q "PASS [0-9-]* FLAKY" <<<"$health" && grep -q '"flaky": "'"$(git rev-parse HEAD)" "$(record)" \
  && ok "a third run's PASS stays flaky: in regression-runs.tsv, tests.py list, health's TESTS block and the lane record" \
  || bad "sticky: rc=$rc flag=$(flag) $(listed) $health"
# Value: protects=a flaky row is never reused; fails_when=run --reuse reuses it from the record; why_new=reuse only
#   looked at PASS/FAIL; seam=none; no_claim=the goal tier (tiers.reason gives it a failure rerun the same way)
out=$($reg run land --reuse 2>&1)
grep -qxF "PASS f" <<<"$out" && ! grep -q "^REUSED" <<<"$out" && ok "run --reuse reruns a flaky row instead of reusing it" \
  || bad "reused a flaky row: $out"
echo "== a later commit's clean pass clears it; PASS, FAIL, FAIL stays flaky and exits 1"
# Value: protects=FLAKY clears when a later commit's clean run passes, and PASS then FAIL marks too with exit 1;
#   fails_when=the flag never clears, PASS-then-FAIL is not marked, or a flaky FAIL exits 0; why_new=E-9's second
#   sequence; seam=none; no_claim=nothing about issues (no live gh)
next two; go pass
[ "$rc" = 0 ] && [ -z "$(flag)" ] && [ "$(listed)" = 0 ] && ! grep -q "^FLAKY" <<<"$out" \
  && ok "a clean pass on a later commit clears the flag" || bad "not cleared: flag=$(flag) $out"
go fail; first=$rc; firstout=$out; go fail
[ "$first" = 1 ] && [ "$rc" = 1 ] && grep -q "^FLAKY f: passed then failed on $(head12) .*Note: the result counts as failed" <<<"$firstout" \
  && grep -qxF "FAIL f" <<<"$out" && grep -q "^FLAKY f: passed then failed" <<<"$out" && [ "$(flag)" = "$(head12)" ] \
  && ok "PASS, FAIL, FAIL stays flaky, keeps FAIL and exits 1" || bad "pass fail fail: $first/$rc $out"
}

nofalse() {
echo "== a dirty tree, another runner or an older record never marks"
# Value: protects=only clean trees count; fails_when=a run with uncommitted changes marks FLAKY; why_new=S6's clean-tree
#   key; seam=none; no_claim=what a dirty run records (nothing in the lane record)
next three; go pass; echo x > scratch.txt; go fail
[ "$rc" = 1 ] && ! grep -q "^FLAKY" <<<"$out" && [ -z "$(flag)" ] && ok "a flip on a dirty tree is not FLAKY" || bad "dirty marked: $out"
rm -f scratch.txt
# Value: protects=results from another runner or python version are not compared (V6); fails_when=a host or python
#   difference is ignored; why_new=no run kept its runner; seam=none; no_claim=a real second machine (the record's host
#   field is rewritten)
next four; go pass
grep -q '"host": ' "$(record)" && grep -q '"python": ' "$(record)" && grep -q '"clean": "yes"' "$(record)" && grep -q '"commit": ' "$(record)" \
  && ok "the lane record keeps commit, clean, runner and python per row" || bad "record fields: $(cat "$(record)")"
python3 - "$(record)" <<'PY'
import json, sys
data = json.load(open(sys.argv[1])); data["rows"]["f"]["host"] = "another-runner"; json.dump(data, open(sys.argv[1], "w"))
PY
go fail
[ "$rc" = 1 ] && ! grep -q "^FLAKY" <<<"$out" && [ -z "$(flag)" ] && ok "a flip from another runner is not FLAKY" || bad "runner marked: $out"
# Value: protects=a record or runs file from before the fields reads as unknown, never flaky (S16); fails_when=missing
#   fields compare equal; why_new=old files exist on every machine; seam=none; no_claim=nothing
next five; go pass
python3 - "$(record)" <<'PY'
import json, sys
data = json.load(open(sys.argv[1])); row = data["rows"]["f"]
for key in ("clean", "host", "python", "flaky"):
    row.pop(key, None)
json.dump(data, open(sys.argv[1], "w"))
PY
printf '# id\tstatus\tdate\trun\nf\tPASS\t2026-11-01\t\n' > .loop/regression-runs.tsv
go fail
[ "$rc" = 1 ] && ! grep -q "^FLAKY" <<<"$out" && [ -z "$(flag)" ] && [ "$(listed)" = 0 ] \
  && ok "an older record and regression-runs.tsv without the fields never mark" || bad "old record marked: $out"
}

case "${1:-}" in marked) marked ;; nofalse) nofalse ;; *) marked; nofalse ;; esac
echo "$pass passed, $fail failed"
[ "$fail" = 0 ] && echo "ALL PASS" || exit 1
