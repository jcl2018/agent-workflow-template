#!/bin/bash
# Test the regression run summary and the one test format on throwaway repos with a fake gh. usage: test-summary.sh
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR=$(mktemp -d)
unset GH_TOKEN GITHUB_TOKEN GITHUB_STEP_SUMMARY GITHUB_ENV GITHUB_OUTPUT GITHUB_PATH GITHUB_STATE
pass=0; fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }
block() {  # the workflow's inline run block, as the regression run would execute it
  python3 - <<'PY'
import re
text = open(".github/workflows/regression.yml").read()
block = re.search(r"python3 - <<'PY'\n(.*?)\n\s+PY\n", text, re.S).group(1)
open("ci-block.py", "w").write("\n".join(line[10:] for line in block.split("\n")))
PY
}

echo "== a row cannot write into the real run summary (issue 92)"
r=$(mktemp -d); cd "$r" && git init -q && mkdir .loop
printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
printf 'real\tland\ttrue\t-\t2026-01-01\tA real row.\tcriterion\t\n' >> .loop/regression.tsv
printf 'leak\tland\t[ -z "$GITHUB_STEP_SUMMARY$GITHUB_ENV$GITHUB_OUTPUT$REGRESSION_RESULTS" ] || echo FIXTURE-LEAK | tee -a "$GITHUB_STEP_SUMMARY" "$GITHUB_ENV" "$GITHUB_OUTPUT" "$REGRESSION_RESULTS" >/dev/null\t-\t2026-01-01\tA row like a toy test that writes to the summary.\tcriterion\t\n' >> .loop/regression.tsv
$reg workflow >/dev/null && block
: > summary.md; : > env.txt; : > out.txt
GITHUB_STEP_SUMMARY="$r/summary.md" GITHUB_ENV="$r/env.txt" GITHUB_OUTPUT="$r/out.txt" REGRESSION_RESULTS="$r/results.tsv" python3 ci-block.py >/dev/null 2>&1
grep -q "^real	PASS$" results.tsv && grep -q "^leak	PASS$" results.tsv && ! grep -q FIXTURE-LEAK summary.md env.txt out.txt results.tsv \
  && ok "a row cannot write into the run summary, env or outputs" || bad "a row wrote into the run summary, env or outputs"
cd "$here"; rm -rf "$r"

echo "== the one test format, grouped by feature (two features, requirement and defect tests)"
tests="python3 -B $here/skills/workflow-regression/scripts/tests.py"
r=$(mktemp -d); cd "$r" && git init -q && mkdir -p .loop docs/wiki
printf '# Alpha\n\n## Requirements\n\n- AAA-1: **Reviewed 2026-11-01** Alpha words. <!-- reviewed 1 -->\n' > docs/wiki/Alpha.md
printf '# Beta\n\n## Requirements\n\n- BBB-1: **Unreviewed** Beta words.\n' > docs/wiki/Beta.md
{ printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n'
  printf 'a1\tland\ttrue\tAAA-1\t2026-11-01\tGiven a, when b, then c.\tcriterion\t\n'
  printf 'a2\tnightly\ttrue\tAAA-1\t2026-11-02\tGiven an issue, when fixed, then it stays fixed.\tdefect\thttps://example.test/o/r/issues/7\n'
  printf 'b1\tland\ttrue\tBBB-1\t-\tChecks a | pipe, a `tick`.\tcriterion\t\n'
  printf 'b2\tcovered\ttrue\tBBB-1\t2026-11-03\tGiven a finding, when fixed, then it stays fixed.\tdefect\tfinding:some-goal\n'
  printf 'b3\tland\ttrue\tBBB-1\t2026-11-03\tGiven a pull request fix, when merged, then it stays fixed.\tdefect\thttps://example.test/o/r/pull/9\n'
  printf 'o1\tland\ttrue\t-\t2026-11-04\tGuards nothing yet.\tcriterion\t\n'
  printf 'd1\tdraft\ttrue\tAAA-1\t-\tA draft.\tcriterion\t\n'; } > .loop/regression.tsv
printf 'a1\tPASS\t2026-11-09\na2\tFAIL\t2026-11-08\n' > .loop/regression-runs.tsv
printf '# link\tstate\tdate\nhttps://example.test/o/r/issues/7\topen\t2026-11-09\n' > .loop/regression-issues.tsv
md=$($tests list --markdown)
order=$(printf '%s\n' "$md" | grep '^### ' | tr '\n' ,)
[ "$order" = "### Alpha,### Beta,### Other," ] && ok "tests are grouped by feature in page order, then Other" || bad "feature groups: $order"
printf '%s\n' "$md" | grep -qxF '| a1 | requirement | AAA-1: Alpha words. | Given a, when b, then c. | both | PASS 2026-11-09 | 2026-11-01 |' \
  && printf '%s\n' "$md" | grep -qxF '| a2 | defect | [#7](https://example.test/o/r/issues/7) open (2026-11-09) | Given an issue, when fixed, then it stays fixed. | nightly | FAIL 2026-11-08 | 2026-11-02 |' \
  && printf '%s\n' "$md" | grep -qF '| b2 | defect | finding some-goal |' && printf '%s\n' "$md" | grep -qF '| by a person | not run |' \
  && printf '%s\n' "$md" | grep -qF '| b3 | defect | [PR 9](https://example.test/o/r/pull/9) state unknown |' \
  && printf '%s\n' "$md" | grep -qF '| o1 | requirement | - |' && ! printf '%s\n' "$md" | grep -q '| d1 |' \
  && ok "each test shows its kind, what it guards, what it checks, when it runs, its last result and seen failing" || bad "test fields"
printf '%s\n' "$md" | grep -qF '| Checks a \| pipe, a `tick`. |' && ok "a | in a description cannot split a column" || bad "escaping"
printf '# started 0\na1\tPASS\nb1\tFAIL\no1\tSKIPPED\na2\tKNOWN\n' > results.tsv
sum=$($tests summary --results results.tsv --took 65)
printf '%s\n' "$sum" | head -1 | grep -qxF '## Regression: 1 passed, 1 failed, 1 known, 1 skipped of 4, in 1m 05s' \
  && [ "$(printf '%s\n' "$sum" | grep -c '^### ')" = 3 ] && printf '%s\n' "$sum" | grep -qxF '| Test | Kind | Guards | Checks | Result |' \
  && printf '%s\n' "$sum" | grep -qxF '| a2 | defect | [#7](https://example.test/o/r/issues/7) open (2026-11-09) | Given an issue, when fixed, then it stays fixed. | KNOWN |' \
  && ok "the run summary has one header with totals and time, then one table per feature" || bad "run summary"
printf 'a1\tMAYBE\n' > bad.tsv
$tests summary --results bad.tsv --took 5 >/dev/null 2>err.txt; rc=$?
[ $rc = 2 ] && grep -q "^REFUSED: bad.tsv:1" err.txt && $tests summary --results results.tsv --took soon >/dev/null 2>&1; [ $? = 2 ] \
  && ok "a malformed results file or run time is refused" || bad "summary refusals"
g=$(mktemp -d); printf '#!/bin/bash\n[ "$1" = auth ] && { [ -n "${GH_BROKEN:-}" ] && { echo "not logged in" >&2; exit 1; }; exit 0; }\n[ "$1" = issue ] && { echo OPEN; exit 0; }\n[ "$1" = pr ] && { echo MERGED; exit 0; }\nexit 1\n' > "$g/gh"; chmod +x "$g/gh"
before=$(cat .loop/regression-issues.tsv)
GH_BROKEN=1 PATH="$g:$PATH" $tests issues --write >/dev/null 2>err.txt; rc=$?
[ $rc = 1 ] && grep -q "^ISSUES: cannot read issues" err.txt && [ "$(cat .loop/regression-issues.tsv)" = "$before" ] \
  && PATH="$g:$PATH" $tests issues --write >/dev/null && grep -q "issues/7	open	" .loop/regression-issues.tsv && grep -q "pull/9	merged	" .loop/regression-issues.tsv \
  && ok "issue and pull request states are recorded, and nothing is written when gh can't read them" || bad "issue states"
$reg workflow >/dev/null
python3 - <<'PY'
t = open(".github/workflows/regression.yml").read()
blk = t.split("- name: Write the run summary, one table per feature", 1)[1].split("run: |\n", 1)[1]
open("step.sh", "w").write("\n".join(l[10:] for l in blk.rstrip("\n").split("\n")) + "\n")
PY
printf '# started %s\na1\tPASS\nb1\tFAIL\n' "$(date +%s)" > run.tsv; : > sum.md
RUNNER_TEMP="$r" REGRESSION_RESULTS="$r/run.tsv" GITHUB_STEP_SUMMARY="$r/sum.md" PATH="$g:$PATH" bash step.sh >/dev/null 2>&1
grep -q '^## Regression: 1 passed, 1 failed, 0 known, 0 skipped of 2, in 0m 0' sum.md && grep -q '^### Alpha' sum.md && grep -q '^### Beta' sum.md \
  && ok "the workflow's summary step writes the grouped summary" || bad "workflow summary step"
printf 'a1\tMAYBE\n' > run.tsv; : > sum.md
RUNNER_TEMP="$r" REGRESSION_RESULTS="$r/run.tsv" GITHUB_STEP_SUMMARY="$r/sum.md" PATH="$g:$PATH" bash step.sh >/dev/null 2>&1
grep -q "could not be written" sum.md && grep -qxF '| a1 | MAYBE |' sum.md && ok "when the grouped summary fails, the plain results still reach the summary" || bad "summary fallback"
out=$(python3 -B "$here/skills/workflow-health/scripts/health.py" check 2>/dev/null)
t=$(awk '/^TESTS$/{t=1; next} t && /^$/{exit} t' <<<"$out")
[ "$(grep '^FEATURE ' <<<"$t" | tr '\n' ,)" = "FEATURE Alpha,FEATURE Beta,FEATURE Other," ] \
  && grep -qxF 'a1 | requirement | AAA-1: Alpha words. | Given a, when b, then c. | both | PASS 2026-11-09 | seen failing 2026-11-01' <<<"$t" \
  && tail -1 <<<"$out" | grep -q '^HEALTH: ' && ok "the health report lists the tests grouped by feature, before its verdict" || bad "health test list"
cd "$here"; rm -rf "$r" "$g"

echo "== $pass passed, $fail failed"
[ "$fail" = 0 ]
