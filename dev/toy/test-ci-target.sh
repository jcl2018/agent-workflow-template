#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/actions.py skills/workflow-regression/scripts/slots.py
# reads: skills/workflow-regression/scripts/tests.py skills/
# Proves the CI dispatch target (C-A1, E-7, F3, S23) in an adopted toy repo that has no skills/ folder: the written
# regression.yml has an optional `target` input on workflow_dispatch; its run step (run as GitHub would, with bash and
# the step's env) runs only the named row for target=ID; a target that is not land, nightly or a row id fails with
# REFUSED (BAD_TARGET) and runs nothing; ci_levels=land rewrites the scheduled target so a run with no target runs land
# rows only. A fake gh answers; no model, no network.
# usage: test-ci-target.sh [input|bad|levels]   (no argument: all three)
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR=$(mktemp -d)
unset GH_TOKEN GITHUB_TOKEN GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID GITHUB_STEP_SUMMARY REGRESSION_TARGET REGRESSION_LEVELS
pass=0; fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }
r=$(mktemp -d); export TOY_LOG="$r/ran.log"; toy_on_exit 'cd /; rm -rf "$r" "$FAKE_GH_DIR"'
cd "$r" && git init -q -b main repo && cd repo && git config user.email t@t && git config user.name t && mkdir .loop
{ printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n'
  printf 'l1\tland\techo l1 >> "$TOY_LOG"\t-\t2026-01-01\tA land row.\tcriterion\t\n'
  printf 'n1\tnightly\techo n1 >> "$TOY_LOG"\t-\t2026-01-01\tA nightly row.\tcriterion\t\n'
  printf 'n2\tnightly\techo n2 >> "$TOY_LOG"\t-\t2026-01-01\tAnother nightly row.\tcriterion\t\n'; } > .loop/regression.tsv
echo '{}' > .loop/config.json
$reg workflow >/dev/null && git add -A && git commit -qm adopted
# step TARGET: run the yml's "Run the rows" step as GitHub would: bash, its literal env values, the dispatch input as
# REGRESSION_TARGET (empty for the schedule); prints its output, returns its exit status.
step() {
  python3 - "$r/step.sh" "$r/step.env" <<'PY'
import re, sys
text = open(".github/workflows/regression.yml").read()
part = text.split("      - name: Run the rows, and keep one issue per failing row\n", 1)[1].split("\n      - ", 1)[0]
env = dict(re.findall(r"^          ([A-Z_]+): \"?([^\"$\n#]*?)\"?\s*(?:#.*)?$", part.split("        run: |\n")[0], re.M))
open(sys.argv[2], "w").write("".join("export %s=%s\n" % (k, v) for k, v in env.items() if v))
open(sys.argv[1], "w").write("\n".join(line[10:] for line in part.split("        run: |\n", 1)[1].split("\n")))
PY
  : > "$TOY_LOG"
  ( . "$r/step.env"; REGRESSION_TARGET="$1" REGRESSION_RESULTS="$r/results.tsv" SUITE_TIME_FILE="$r/suite-time.tsv" bash "$r/step.sh" ) 2>&1
}
ran() { sort "$TOY_LOG" | tr '\n' ' '; }

input() {
echo "== the dispatch target input runs one row in a repo with no skills/ folder"
# Value: protects=a run by hand can name a target (C-A1); fails_when=the input is missing or not optional;
#   why_new=the workflow had no inputs; seam=none; no_claim=GitHub's form rendering (no live run)
python3 - <<'PY' && ok "the written regression.yml has an optional target input on workflow_dispatch" || bad "no target input"
text = open(".github/workflows/regression.yml").read()
part = text.split("  workflow_dispatch:\n", 1)[1].split("permissions:", 1)[0]
assert "    inputs:\n      target:\n" in part and "required: false" in part and 'default: ""' in part, part
assert "REGRESSION_TARGET: ${{ inputs.target }}" in text and "${{ inputs.target }}" not in text.split("        run: |")[2].split("      - ")[0]
PY
# Value: protects=target=ID runs only that row, through the embedded runner (E-7); fails_when=the target is ignored or the
#   step calls regression.py, which an adopting repo lacks; why_new=CI ran every row; seam=none; no_claim=a real runner
[ ! -e skills ] && out=$(step n2); rc=$?
[ "$rc" = 0 ] && [ "$(ran)" = "n2 " ] && grep -qx "PASS n2" <<<"$out" && ! grep -q "^SUITE_TIME" <<<"$out" \
  && ok "target=n2 runs only row n2 in a repo with no skills/ folder, and records no suite time" || bad "target=ID: rc=$rc ran=$(ran) $out"
out=$(step land); [ "$(ran)" = "l1 " ] && ok "target=land runs land rows only" || bad "target=land ran $(ran)"
}

bad_target() {
echo "== a bad target fails with BAD_TARGET and runs nothing"
# Value: protects=the target reaches the runner only as a checked value (F3); fails_when=a value outside land, nightly or
#   a row id runs anything or reaches a shell; why_new=no input existed; seam=none; no_claim=GitHub's own input escaping
rm -f "$FAKE_GH_DIR/calls.log"
for value in 'x;touch HACKED' 'no-such-row' '$(touch HACKED)'; do
  out=$(step "$value"); rc=$?
  if [ "$rc" = 1 ] && [ -z "$(ran)" ] && [ ! -e HACKED ] && [ -z "$(cat "$FAKE_GH_DIR/calls.log" 2>/dev/null)" ] \
     && grep -qxF "REFUSED (BAD_TARGET): bad target \"$value\": use land, nightly or a row id from regression.py list. Fix: rerun the workflow with one of those" <<<"$out"; then
    ok "target '$value' fails with the BAD_TARGET line, exit 1, no row run and no issue touched"
  else bad "target '$value': rc=$rc ran=$(ran) $out"; fi
  rm -f HACKED "$FAKE_GH_DIR/calls.log"
done
}

levels() {
echo "== ci_levels sets the scheduled target"
# Value: protects=ci_levels is written into the yml and decides what the schedule runs (S23); fails_when=the writer
#   ignores ci_levels or the runner ignores the written level; why_new=CI always ran every row; seam=none;
#   no_claim=the cron trigger itself
out=$(step ""); [ "$(ran)" = "l1 n1 n2 " ] && grep -q '^          REGRESSION_LEVELS: "nightly"' .github/workflows/regression.yml \
  && grep -q "^SUITE_TIME [0-9]*$" <<<"$out" && ok "by default the scheduled run (no target) runs every row and records the suite time" \
  || bad "default levels ran $(ran)"
echo '{"ci_levels": "land"}' > .loop/config.json; $reg workflow >/dev/null
out=$(step ""); grep -q '^          REGRESSION_LEVELS: "land"' .github/workflows/regression.yml && [ "$(ran)" = "l1 " ] \
  && ! grep -q "^SUITE_TIME" <<<"$out" && ok "ci_levels=land rewrites the scheduled target: a run with no target runs land rows only" \
  || bad "ci_levels=land ran $(ran): $(grep REGRESSION_LEVELS .github/workflows/regression.yml)"
echo '{"ci_levels": "weekly"}' > .loop/config.json
out=$($reg workflow 2>&1); [ $? = 1 ] && grep -q "^REFUSED: ci_levels is 'weekly', not land or nightly" <<<"$out" \
  && ok "a ci_levels that is not land or nightly is refused" || bad "bad ci_levels: $out"
git checkout -q -- .loop/config.json .github
}

case "${1:-}" in input) input ;; bad) bad_target ;; levels) levels ;; *) input; bad_target; levels ;; esac
echo "$pass passed, $fail failed"
[ "$fail" = 0 ] && echo "ALL PASS" || exit 1
