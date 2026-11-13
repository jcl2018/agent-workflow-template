#!/bin/bash
# reads: skills/workflow-regression/scripts/regression.py skills/workflow-regression/scripts/tiers.py
# reads: skills/workflow-regression/scripts/actions.py skills/workflow-regression/scripts/slots.py skills/workflow-health/scripts/milestone.py
# reads: skills/workflow-health/scripts/automation.py skills/workflow-health/scripts/workflows.py
# Proves the full-suite time (REG-7, S14, S25) on a throwaway repo with a fake gh: only the plain `regression.py run
# nightly` appends `<sha> TAB full TAB <seconds> TAB <date>` to <git common dir>/loop/suite-times.tsv and prints
# SUITE_TIME, never into the worktree; a row id, land, --reuse, --tier or --kind writes nothing; health's milestone.py timing_rows
# reads the line; the written regression.yml keeps the CI run's line as artifact suite-time, and health.yml's fetch
# step (run with a stub gh) adds it with the ci column, or continues when there is no artifact yet. No model.
# usage: test-suite-time.sh
set -u
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
reg="python3 $here/skills/workflow-regression/scripts/regression.py"
export PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR=$(mktemp -d)
unset GH_TOKEN GITHUB_TOKEN GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID _LOOP_LANE_LABEL
pass=0; fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }
r=$(mktemp -d); toy_on_exit 'cd /; rm -rf "$r" "$FAKE_GH_DIR"'
cd "$r" && git init -q -b main repo && cd repo && git config user.email t@t && git config user.name t && mkdir .loop
{ printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n'
  printf 'l1\tland\ttrue\t-\t2026-01-01\tA land row.\tcriterion\t\n'
  printf 'n1\tnightly\tsleep 1\t-\t2026-01-01\tA nightly row.\tcriterion\t\n'; } > .loop/regression.tsv
echo '{}' > .loop/config.json
git add -A && git commit -qm toy
times="$(cd "$(git rev-parse --git-common-dir)" && pwd)/loop/suite-times.tsv"
lines() { [ -f "$times" ] && grep -c . "$times" || echo 0; }
day=$(date -u +%Y-%m-%d)

echo "== only a plain run nightly records the suite time"
# Value: protects=the plain full run records its time where health reads it, outside the worktree (S14, S25);
#   fails_when=no line is written, it lands in the worktree, or SUITE_TIME is not printed; why_new=no run kept its time;
#   seam=none; no_claim=CI's own line (proved below from the written yml)
out=$($reg run nightly 2>&1)
grep -qx "SUITE_TIME [0-9]*" <<<"$out" && [ "$(lines)" = 1 ] && grep -qx "$(git rev-parse HEAD)	full	[0-9]*	$day" "$times" \
  && [ -z "$(git status --porcelain -- . ':!.loop/regression-runs.tsv')" ] && ok "run nightly appends one full line to the git common dir and prints SUITE_TIME" \
  || bad "plain run: $(lines) lines; $out"
# Value: protects=only the plain full run writes (S25); fails_when=a partial run records a full-suite time; why_new=S25;
#   seam=none; no_claim=nothing
for args in "land" "n1" "nightly --kind requirement" "nightly --reuse"; do
  out=$($reg run $args 2>&1)
  [ "$(lines)" = 1 ] && ! grep -q "^SUITE_TIME" <<<"$out" && ok "run $args records no suite time" || bad "run $args wrote: $(cat "$times")"
done
# Value: protects=health reads the local line (REG-7); fails_when=milestone.py timing_rows can't find or parse it; why_new=no writer
#   existed; seam=none; no_claim=the limit warning (test-timing.sh)
python3 - "$here" <<'PY' && ok "health's timing rule reads the local run's suite time" || bad "timing did not read it"
import sys
sys.path.insert(0, sys.argv[1] + "/skills/workflow-health/scripts"); import milestone as cost
found = [r for r in cost.timing_rows(".") if r["subject"] == "full-suite"]
assert found and found[0]["state"] == "PASS" and "from local run" in found[0]["detail"], found
PY

echo "== CI keeps its line as artifact suite-time; the Mac's tick fetches it"
# Value: protects=the CI run's time reaches health (S14): regression.yml uploads suite-time, the local tick downloads the
#   newest one with gh run download and marks it ci; fails_when=either step is missing or the ci column is dropped;
#   why_new=CI times never left the runner; seam=none; no_claim=GitHub's artifact service (a stub gh stands in)
$reg workflow >/dev/null
python3 - <<'PY' && ok "regression.yml uploads the CI run's suite-time file as artifact suite-time" || bad "no upload step"
text = open(".github/workflows/regression.yml").read()
part = text.split("uses: actions/upload-artifact@v4", 1)[1].split("\n      - ", 1)[0]
assert "name: suite-time" in part and "path: ${{ runner.temp }}/suite-time.tsv" in part and "if-no-files-found: ignore" in part
assert "SUITE_TIME_FILE: ${{ runner.temp }}/suite-time.tsv" in text
PY
mkdir -p "$r/stub"; cat > "$r/stub/gh" <<'SH'
#!/bin/bash
case "$1 $2" in
  "run list") printf '12\n11\n' ;;
  "run download") [ "$3" = 11 ] && [ -n "${STUB_ARTIFACT:-}" ] || exit 1
                  shift 3; while [ $# -gt 0 ]; do [ "$1" = --dir ] && printf 'cafe\tfull\t2400\t2026-11-09\n' > "$2/suite-time.tsv"; shift; done ;;
  *) exit 1 ;;
esac
SH
chmod +x "$r/stub/gh"
fetch() { PATH="$r/stub:$PATH" python3 - "$here" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1] + "/skills/workflow-health/scripts"); import rounds, workflows
print(rounds.fetch_suite_time(".", dict(os.environ), open(os.devnull, "w"), workflows.child))
PY
}
out=$(fetch 2>&1); rc=$?
[ "$rc" = 0 ] && grep -q "^NOTE: no suite-time artifact" <<<"$out" && [ "$(lines)" = 1 ] \
  && ok "with no artifact yet the fetch step says so and continues" || bad "no artifact: rc=$rc $out"
out=$(STUB_ARTIFACT=1 fetch 2>&1); rc=$?
[ "$rc" = 0 ] && [ "$(tail -1 "$times")" = "cafe	full	2400	2026-11-09	ci" ] && python3 - "$here" <<'PY' \
  && ok "the newest run's artifact is added with the ci column and health reads it as a CI artifact" || bad "fetch: rc=$rc $out $(cat "$times")"
import sys
sys.path.insert(0, sys.argv[1] + "/skills/workflow-health/scripts"); import milestone as cost
found = [r for r in cost.timing_rows(".") if r["subject"] == "full-suite"]
assert found and found[0]["state"] == "WARN" and "from CI artifact on 2026-11-09" in found[0]["detail"], found
PY

echo "$pass passed, $fail failed"
[ "$fail" = 0 ] && echo "ALL PASS" || exit 1
