#!/bin/bash
# reads: skills/workflow-delivery/scripts/flow.py skills/workflow-delivery/scripts/goal.py
# reads: skills/workflow-delivery/scripts/role.py skills/workflow-regression/scripts/regression.py
# reads: skills/workflow-setup/scripts/setup.py skills/workflow-monitoring/scripts/monitor.py
# reads: skills/workflow-health/scripts/lean.py skills/workflow-regression/scripts/runs.py
# Proves the time budgets: both settings refuse a value under 15 minutes, an in-loop test run stops at its budget and
# lists the rows it left (recorded, so a later lane doesn't rerun them), rows fit the budget by their estimated seconds,
# a review or ship step at its limit finishes with what it has done and the goal goes on, a session-run step is given its
# budget and an overrun is recorded, and the board and health show what hit a budget. No model is called.
set -u
unset GITHUB_SERVER_URL GITHUB_REPOSITORY GITHUB_RUN_ID LOOP_SESSION_TOOL LOOP_OPERATION_SESSION GH_TOKEN GITHUB_TOKEN
here=$(cd "$(dirname "$0")/../.." && pwd)
. "$here/dev/toy/reap.sh"
export HOME=$(mktemp -d)
d=$(mktemp -d); toy_on_exit 'rm -rf "$d" "$HOME"'
"$here/dev/toy/make.sh" "$d" >/dev/null || exit 1
export LOOP_FLOW="$d/flow.json" PATH="$here/dev/toy/fakegh:$PATH" FAKE_GH_DIR="$d/gh" TOY_LOG="$d/ran.log"
S="$here/skills"; reg="python3 $S/workflow-regression/scripts/regression.py"
cd "$d/repo" || exit 1
python3 "$S/workflow-setup/scripts/setup.py" --bare >/dev/null
git switch -q main; git merge -q --no-edit workflow-setup
fails=0
ok() { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }
ran() { sort "$TOY_LOG" 2>/dev/null | tr '\n' ' '; }
cfg() { python3 - "$1" "$2" <<'PY'
import json, sys
p = ".loop/config.json"; c = json.load(open(p)); c[sys.argv[1]] = json.loads(sys.argv[2]); json.dump(c, open(p, "w"))
PY
}
common=$(cd "$(git rev-parse --git-common-dir)" && pwd)

echo "== the two settings refuse a value under 15 minutes"
B="python3 -c 'import sys; sys.path.insert(0, \"$S/workflow-delivery/scripts\"); import budget; print(budget.minutes(json.loads(sys.argv[1]), sys.argv[2]))'"
bm() { python3 -c 'import json, sys; sys.path.insert(0, sys.argv[1]); import budget; print(budget.minutes(json.loads(sys.argv[2]), sys.argv[3]))' "$S/workflow-delivery/scripts" "$@" 2>&1; }
check "step_budget_minutes defaults to 30 and test_budget_minutes to 15" '[ "$(bm "{}" step_budget_minutes)" = 30 ] && [ "$(bm "{}" test_budget_minutes)" = 15 ]'
out=$(bm '{"step_budget_minutes": 10}' step_budget_minutes)
check "a step budget under 15 is refused with a fix line" 'grep -q "^REFUSED: step_budget_minutes is 10 in .loop/config.json, under the 15-minute floor. Fix: set it to 15 or more" <<<"$out"'
out=$(bm '{"test_budget_minutes": 14}' test_budget_minutes)
check "a test budget under 15 is refused with a fix line" 'grep -q "^REFUSED: test_budget_minutes is 14 .*Fix: set it to 15 or more" <<<"$out"'
mkdir -p dev src; printf 'ok\n' > src/a.txt
printf 'echo a >> "$TOY_LOG"\n' > dev/a.sh; printf 'sleep 4; echo b >> "$TOY_LOG"\n' > dev/b.sh; printf 'echo c >> "$TOY_LOG"\n' > dev/c.sh
printf '# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n' > .loop/regression.tsv
for r in a b c; do printf '%s\tland\tbash dev/%s.sh\tX-1\t2026-01-01\t%s works.\tcriterion\t\n' $r $r $r >> .loop/regression.tsv; done
git add -A; git commit -qm "Rows"
cfg test_budget_minutes 5; git commit -qam "Bad budget"
out=$($reg run land --reuse 2>&1); rc=$?
check "a reusing test run refuses a test budget under 15 and runs nothing" '[ $rc != 0 ] && grep -q "under the 15-minute floor" <<<"$out" && [ -z "$(ran)" ]'
git checkout -q HEAD~1 -- .loop/config.json; git commit -qam "Default budget"

echo "== a test run stops at its budget and lists what it left"
: > "$TOY_LOG"; out=$($reg run land --reuse --budget 2 2>&1); rc=$?; echo "$out"
check "rows run in order until the budget, then the rest are left and listed" '[ $rc = 0 ] && grep -q "^BUDGET 0 min: ran 1 of 3 rows; LEFT 2 to the scheduled full suite: b, c$" <<<"$out" && [ "$(ran)" = "a " ]'
check "a left row is not a failure" 'grep -q "^RESULT 1 passed" <<<"$out" && ! grep -q "^FAIL" <<<"$out"'
: > "$TOY_LOG"; out=$($reg run land --reuse 2>&1); echo "$out"
check "the next lane on the same content reuses the left rows and runs none" 'grep -q "^REUSED 3 rows" <<<"$out" && [ -z "$(ran)" ]'
python3 - "$S/workflow-regression/scripts" <<'PY' && ok "rows fit the budget by their estimated seconds, in tier order" || bad "fit"
import sys
sys.path.insert(0, sys.argv[1]); import runs
keep, left = runs.fit(["x", "y", "z"], {"x": 500, "y": 300, "z": 100}, 600)
sys.exit(0 if (keep, left) == (["x", "z"], ["y"]) else 1)
PY

echo "== a lane records the run that hit its budget"
git switch -q -c lb-branch; runs="$common/loop/runs"; mkdir -p "$runs"; printf '{"slug": "lb", "status": "running"}\n' > "$runs/lb.json"
rm -f "$common"/loop/tests/*.json
out=$(python3 - "$S/workflow-delivery/scripts" "$runs" <<'PY'
import json, sys, time
sys.path.insert(0, sys.argv[1]); import budget, role
budget.minutes = lambda cfg, key: 0.05  # 3 seconds: a toy stand-in for a 15 minute budget
while True:
    status, line, ids = role.lane(sys.argv[2], "lb", "qa", {}, {})
    if status != "running":
        break
    time.sleep(1)
print(status); print(line)
PY
)
echo "$out"
check "the lane passes, says what it left, and the goal's run file names the step, the limit and the rows" 'grep -q "^pass" <<<"$out" && grep -q "^BUDGET 0 min: ran .* LEFT" <<<"$out" && python3 -c "
import json, sys
h = json.load(open(sys.argv[1]))[\"budget_hits\"][0]
sys.exit(0 if (h[\"step\"], h[\"kind\"]) == (\"qa\", \"test\") and \"c\" in h[\"left\"] else 1)" "$runs/lb.json"'
git switch -q main

echo "== a review or ship step at its limit finishes with what it has done"
export LOOP_ROLE=worker
goal="python3 $S/workflow-delivery/scripts/goal.py"; F="python3 $S/workflow-delivery/scripts/flow.py"
printf '#!/bin/bash\nsleep 30\n' > "$d/slowskill.sh"
setflow() { python3 - "$d/flow.json" "$1" <<'PY2'
import json, sys
spec = json.load(open(sys.argv[1])); spec.update(json.loads(sys.argv[2])); json.dump(spec, open(sys.argv[1], "w"))
PY2
}
setflow "{\"command\": [\"bash\", \"$d/slowskill.sh\"], \"limit\": 2}"
$goal new bg --here --goal "Budget goal" --done "budgets hold" >/dev/null
python3 - "$runs/bg.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["flow"] = {"idea": "done", "plan": "done"}; s["step"] = "review"; json.dump(s, open(sys.argv[1], "w"))
PY
all=""; for _ in $(seq 12); do out=$($F bg review --wait 3 2>&1); all="$all$out"$'\n'; grep -q "^NEXT:" <<<"$out" && break; done
out=$($goal record bg review --file "$runs/bg.review.txt" 2>&1); echo "$all$out"
check "a review stopped at its limit records done with what it left, never a failed try" 'grep -q "^RECORDED review done: stopped at its" <<<"$out" && grep -q "TRIES\|\"tries\": 0" <(python3 -c "import json,sys;print(json.dumps(json.load(open(sys.argv[1]))))" "$runs/bg.json" | sed "s/\"tries\": 0/TRIES/")'
check "the goal's run file names the step and what it left" 'python3 -c "
import json, sys
h = json.load(open(sys.argv[1]))[\"budget_hits\"][0]
sys.exit(0 if (h[\"step\"], h[\"kind\"]) == (\"review\", \"step\") and h[\"left\"] else 1)" "$runs/bg.json"'

echo "== a session-run step is given its budget, and an overrun is recorded"
setflow '{"limit": 600}'
python3 - "$runs/bg.json" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])); s["worker"] = "session"; s["flow"]["review"] = "done"; s["step"] = "ship"; json.dump(s, open(sys.argv[1], "w"))
PY
out=$($F bg ship 2>&1); echo "$out" | tail -4
check "the step instructions carry the step budget in minutes" 'grep -q "^TIME BUDGET: 30 minutes for this step" <<<"$out"'
touch -t 202601010000 "$runs/bg.ship.asked"
printf 'BUDGET: left: the changelog\nDEPTH: full\nSTEP: done\n' > "$runs/bg.ship.txt"
$F bg ship >/dev/null 2>&1
check "a session step that took longer than its budget is recorded with what it said it left" 'python3 -c "
import json, sys
hits = json.load(open(sys.argv[1]))[\"budget_hits\"]
sys.exit(0 if any(h[\"step\"] == \"ship\" and h[\"kind\"] == \"step\" and h[\"left\"] == \"the changelog\" for h in hits) else 1)" "$runs/bg.json"'

echo "== the board and health show what hit a budget"
unset LOOP_ROLE
out=$(python3 "$S/workflow-monitoring/scripts/monitor.py" report 2>&1); echo "$out" | grep -A3 "BUDGET HITS"
check "the report lists each budget hit with what it left" 'grep -q "^- bg: review step hit its .*-minute budget; left: " <<<"$out" && grep -q "^- bg: ship step hit its 30-minute budget; left: the changelog" <<<"$out"'
out=$(python3 -c "
import sys; sys.path.insert(0, sys.argv[1]); import lean
for r in lean.hit_rows('.'): print(r['state'], r['detail'])" "$S/workflow-health/scripts" 2>&1)
check "health lists them too" 'grep -q "^INFO bg: ship step hit its 30-minute budget; left: the changelog" <<<"$out"'

echo "== health flags a full suite over 30 minutes"
fullrec() { python3 - "$common/loop/tests/full-x.json" "$1" <<'PY'
import json, sys
json.dump({"at": "2026-01-02T00:00:00Z", "command": "regression.py run land", "total_seconds": int(sys.argv[2]),
           "rows": {"a": {"status": "PASS", "seconds": int(sys.argv[2]), "commit": "x"}}}, open(sys.argv[1], "w"))
PY
}
suite() { python3 -c "
import sys; sys.path.insert(0, sys.argv[1]); import lean
for r in lean.suite_rows('.'): print(r['state'], r['detail'])" "$S/workflow-health/scripts" 2>&1; }
mkdir -p "$common/loop/tests"; fullrec 2000; out=$(suite)
check "health warns when the newest full run took over 30 minutes" 'grep -q "^WARN the full suite took 2000 s, over 30 minutes" <<<"$out"'
fullrec 1700; out=$(suite)
check "health stays quiet for a full run within 30 minutes" '[ -z "$out" ]'

[ $fails = 0 ] && echo "ALL PASS" || { echo "$fails FAILED"; exit 1; }
