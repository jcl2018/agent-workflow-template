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
printf 'leak\tland\t[ -z "$GITHUB_STEP_SUMMARY$GITHUB_ENV$GITHUB_OUTPUT" ] || echo FIXTURE-LEAK | tee -a "$GITHUB_STEP_SUMMARY" "$GITHUB_ENV" "$GITHUB_OUTPUT" >/dev/null\t-\t2026-01-01\tA row like a toy test that writes to the summary.\tcriterion\t\n' >> .loop/regression.tsv
$reg workflow >/dev/null && block
: > summary.md; : > env.txt; : > out.txt
GITHUB_STEP_SUMMARY="$r/summary.md" GITHUB_ENV="$r/env.txt" GITHUB_OUTPUT="$r/out.txt" python3 ci-block.py >/dev/null 2>&1
grep -q "real" summary.md && ! grep -q FIXTURE-LEAK summary.md env.txt out.txt \
  && ok "a row cannot write into the run summary, env or outputs" || bad "a row wrote into the run summary, env or outputs"
cd "$here"; rm -rf "$r"

echo "== $pass passed, $fail failed"
[ "$fail" = 0 ]
