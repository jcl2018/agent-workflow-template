#!/bin/bash
# reads: skills/
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
printf 'known-row\tland\tfalse\t-\t2026-01-01\tA failure the repo expects.\tcriterion\t\n' >> .loop/regression.tsv
printf 'known-row\texpected\n' > .loop/regression-known.tsv
$reg workflow >/dev/null && block
: > summary.md; : > env.txt; : > out.txt
GITHUB_STEP_SUMMARY="$r/summary.md" GITHUB_ENV="$r/env.txt" GITHUB_OUTPUT="$r/out.txt" REGRESSION_RESULTS="$r/results.tsv" python3 ci-block.py >/dev/null 2>&1
grep -q "^real	PASS$" results.tsv && grep -q "^leak	PASS$" results.tsv && ! grep -q FIXTURE-LEAK summary.md env.txt out.txt results.tsv \
  && ok "a row cannot write into the run summary, env or outputs" || bad "a row wrote into the run summary, env or outputs"
grep -q "^known-row	KNOWN$" results.tsv && ok "a known failure is recorded KNOWN" || bad "known row state"
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
  && $tests summary --results results.tsv --took nan >/dev/null 2>&1; [ $? = 2 ] \
  && ok "a malformed results file or run time is refused" || bad "summary refusals"
g=$(mktemp -d); printf '#!/bin/bash\n[ "$1" = auth ] && { [ -n "${GH_BROKEN:-}" ] && { echo "not logged in" >&2; exit 1; }; exit 0; }\n[ "$1" = issue ] && { echo OPEN; exit 0; }\n[ "$1" = pr ] && { echo MERGED; exit 0; }\nexit 1\n' > "$g/gh"; chmod +x "$g/gh"
before=$(cat .loop/regression-issues.tsv)
GH_BROKEN=1 PATH="$g:$PATH" $tests issues --write >/dev/null 2>err.txt; rc=$?
[ $rc = 1 ] && grep -q "^ISSUES: cannot read issues" err.txt && [ "$(cat .loop/regression-issues.tsv)" = "$before" ] \
  && PATH="$g:$PATH" $tests issues --write >/dev/null && grep -q "issues/7	open	" .loop/regression-issues.tsv && grep -q "pull/9	merged	" .loop/regression-issues.tsv \
  && ok "issue and pull request states are recorded, and nothing is written when gh can't read them" || bad "issue states"
printf '#!/bin/bash\n[ "$1" = auth ] && exit 0\nexit 1\n' > "$g/gh-down"; mkdir -p "$g/down"; cp "$g/gh-down" "$g/down/gh"; chmod +x "$g/down/gh"
PATH="$g/down:$PATH" $tests issues --write >/dev/null && grep -q "issues/7	open	" .loop/regression-issues.tsv \
  && ok "a link gh can't read keeps its last recorded state" || bad "lost issue state"
$reg workflow >/dev/null
python3 - <<'PY'
t = open(".github/workflows/regression.yml").read()
blk = t.split("- name: Write the run summary, one table per feature", 1)[1].split("run: |\n", 1)[1]
open("step.sh", "w").write("\n".join(l[10:] for l in blk.rstrip("\n").split("\n")) + "\n")
PY
printf '# started %s\na1\tPASS\nb1\tFAIL\n' "$(date +%s)" > run.tsv; : > sum.md
RUNNER_TEMP="$r" REGRESSION_RESULTS="$r/run.tsv" GITHUB_STEP_SUMMARY="$r/sum.md" PATH="$g:$PATH" bash -e step.sh >/dev/null 2>&1
grep -q '^## Regression: 1 passed, 1 failed, 0 known, 0 skipped of 2, in 0m 0' sum.md && grep -q '^### Alpha' sum.md && grep -q '^### Beta' sum.md \
  && ok "the workflow's summary step writes the grouped summary" || bad "workflow summary step"
printf 'a1\tMAYBE\n' > run.tsv; : > sum.md
RUNNER_TEMP="$r" REGRESSION_RESULTS="$r/run.tsv" GITHUB_STEP_SUMMARY="$r/sum.md" PATH="$g:$PATH" bash -e step.sh >/dev/null 2>&1
grep -q "could not be written" sum.md && grep -qxF '| a1 | MAYBE |' sum.md && ok "when the grouped summary fails, the plain results still reach the summary" || bad "summary fallback"
rm run.tsv; : > sum.md
RUNNER_TEMP="$r" REGRESSION_RESULTS="$r/run.tsv" GITHUB_STEP_SUMMARY="$r/sum.md" PATH="$g:$PATH" bash -e step.sh >/dev/null 2>&1
grep -q "could not be written" sum.md && ok "with no results file at all, the summary still says so" || bad "summary with no results"
c=$(mktemp -d); cp -R "$here/skills" "$c/"; echo '# ${{ github.token }}' >> "$c/skills/workflow-regression/scripts/tests.py"
python3 -B -c "import sys; sys.path.insert(0, '$c/skills/workflow-regression/scripts'); import actions; actions.render('17 9 * * *')" 2>err.txt; rc=$?
[ $rc != 0 ] && grep -q "^REFUSED: tests.py contains \${{" err.txt && ok "the workflow refuses to carry a tests.py Actions would read" || bad "render guard"
rm "$c/skills/workflow-regression/scripts/tests.py"
out=$(python3 -B "$c/skills/workflow-health/scripts/health.py" check 2>/dev/null)
python3 -B -c "import sys; sys.path.insert(0, '$c/skills/workflow-docs/scripts'); import criteria; assert criteria.tests_format() is None" 2>err.txt
awk '/^TESTS$/{t=1; next} t && /^$/{exit} t' <<<"$out" | grep -q "^NOTE: the test list is unavailable" && tail -1 <<<"$out" | grep -q '^HEALTH: ' \
  && grep -q "^NOTE: .*tests.py not found or broken (FileNotFoundError); Tests lines use the old shape" err.txt && ok "without tests.py, health and the wiki say so and keep working" || bad "missing tests.py"
rm -rf "$c"
out=$(python3 -B "$here/skills/workflow-health/scripts/health.py" check 2>/dev/null)
t=$(awk '/^TESTS$/{t=1; next} t && /^$/{exit} t' <<<"$out")
[ "$(grep '^FEATURE ' <<<"$t" | tr '\n' ,)" = "FEATURE Alpha,FEATURE Beta,FEATURE Other," ] \
  && grep -qxF 'a1 | requirement | AAA-1: Alpha words. | Given a, when b, then c. | both | PASS 2026-11-09 | seen failing 2026-11-01' <<<"$t" \
  && tail -1 <<<"$out" | grep -q '^HEALTH: ' && ok "the health report lists the tests grouped by feature, before its verdict" || bad "health test list"
# Value: protects=list --tsv keeps a raw | and leads with the feature; fails_when=--tsv escapes | or drops the feature column;
#   why_new=only --markdown escaping was checked; seam=none; no_claim=none beyond protects
t=$($tests list --tsv)
grep -qxF "$(printf 'Beta\tb1\trequirement\tBBB-1: Beta words.\tChecks a | pipe, a `tick`.\tboth\tnot run\tno')" <<<"$t" \
  && [ "$(cut -f1 <<<"$t" | sort -u | tr '\n' ,)" = "Alpha,Beta,Other," ] && ok "list --tsv keeps a raw | and puts the feature first" || bad "list --tsv: $t"
# Value: protects=a results id with no regression.tsv row is still shown, under Other; fails_when=unknown ids are dropped or
#   crash the summary; why_new=summary was checked with known ids only; seam=none; no_claim=none beyond protects
printf 'a1\tPASS\nzz-gone\tFAIL\n' > stray.tsv
sum=$($tests summary --results stray.tsv --took 1)
awk '/^### Other$/{o=1; next} /^### /{o=0} o' <<<"$sum" | grep -q '^| zz-gone | ' && printf '%s\n' "$sum" | head -1 | grep -q '1 failed' \
  && ok "a result whose test is not in regression.tsv lands under Other" || bad "stray result: $sum"
# Value: protects=health check prints tests.py's own error as a NOTE and keeps the verdict last; --group prints no TESTS;
#   fails_when=a failing tests.py breaks the report or hides its stderr, or a group run lists tests; why_new=only a missing
#   tests.py was checked; seam=none; no_claim=real tests.py failure modes (a stub script stands in)
c=$(mktemp -d); cp -R "$here/skills" "$c/"
printf '#!/usr/bin/env python3\nimport sys\nsys.stderr.write("STUB-BROKEN: cannot read regression.tsv\\n")\nsys.exit(3)\n' > "$c/skills/workflow-regression/scripts/tests.py"
out=$(python3 -B "$c/skills/workflow-health/scripts/health.py" check 2>/dev/null)
awk '/^TESTS$/{t=1; next} t && /^$/{exit} t' <<<"$out" | grep -qxF "NOTE: the test list is unavailable (STUB-BROKEN: cannot read regression.tsv)" \
  && tail -1 <<<"$out" | grep -q '^HEALTH: ' && ok "when tests.py fails, health shows its error in the TESTS block and the verdict stays last" || bad "failing tests.py: $out"
out=$(python3 -B "$c/skills/workflow-health/scripts/health.py" check --group size 2>/dev/null)
! grep -qx 'TESTS' <<<"$out" && tail -1 <<<"$out" | grep -q '^HEALTH: ' && ok "a health check of one group prints no TESTS block" || bad "group TESTS: $out"
rm -rf "$c"
cd "$here"; rm -rf "$r" "$g"

echo "== an empty repo, an empty regression.tsv, and a local run's environment"
# Value: protects=list on a repo with no rows prints NO TESTS; fails_when=it prints nothing or crashes; why_new=no empty-repo
#   check; seam=none; no_claim=none beyond protects
r=$(mktemp -d); cd "$r" && git init -q
[ "$($tests list)" = "NO TESTS" ] && [ "$($tests list --tsv)" = "NO TESTS" ] && ok "a repo with no tests lists NO TESTS" || bad "empty list"
# Value: protects=issues --write with no rows keeps the recorded states byte for byte; fails_when=the "and rows" guard is
#   removed and the file is wiped; why_new=only the gh-auth failure was checked; seam=none; no_claim=none beyond protects
mkdir .loop; printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
printf '# link\tstate\tdate\nhttps://example.test/o/r/issues/7\topen\t2026-11-09\n' > .loop/regression-issues.tsv
cp .loop/regression-issues.tsv keep.tsv
g=$(mktemp -d); printf '#!/bin/bash\n[ "$1" = auth ] && exit 0\necho OPEN\n' > "$g/gh"; chmod +x "$g/gh"
PATH="$g:$PATH" $tests issues --write >/dev/null 2>&1 && cmp -s keep.tsv .loop/regression-issues.tsv \
  && ok "issues --write with no rows leaves the recorded issue states unchanged" || bad "empty issues write"
# Value: protects=a local regression.py run hides runner files and GH_TOKEN from rows; fails_when=cmd_run drops env=row_env();
#   why_new=only the CI block was checked; seam=none; no_claim=gh calls a live run makes (fake gh stands in)
printf 'leak\tland\t[ -z "$GITHUB_STEP_SUMMARY" ] || echo FIXTURE-LEAK >> "$GITHUB_STEP_SUMMARY"\t-\t2026-01-01\tWrites to the summary.\tcriterion\t\n' >> .loop/regression.tsv
printf 'token\tland\t[ -z "$GH_TOKEN" ]\t-\t2026-01-01\tSees no token.\tcriterion\t\n' >> .loop/regression.tsv
git add -A && git -c user.name=t -c user.email=t@t commit -qm rows
: > "$g/summary.md"
GITHUB_STEP_SUMMARY="$g/summary.md" GH_TOKEN=fixture-token $reg run leak >/dev/null 2>&1
GITHUB_STEP_SUMMARY="$g/summary.md" GH_TOKEN=fixture-token $reg run token > run.txt 2>&1; rc=$?
[ ! -s "$g/summary.md" ] && [ $rc = 0 ] && ! grep -q "FAIL" run.txt \
  && ok "a local run gives a row neither the run summary file nor GH_TOKEN" || bad "local run env (rc $rc): $(cat run.txt)"
cd "$here"; rm -rf "$r" "$g"

echo "== $pass passed, $fail failed"
[ "$fail" = 0 ]
