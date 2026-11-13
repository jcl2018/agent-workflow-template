#!/bin/bash
# reads: skills/workflow-regression/scripts/actions.py skills/workflow-regression/scripts/actions_summary.py skills/workflow-health/scripts/automation.py .github/workflows/regression.yml docs/wiki/Regression.md docs/wiki/Automation.md
# Test that REG-7, AUT-7 and regression.yml name one regression budget with the suite sharded to fit it, and that the digest never cuts its counts silently.
# usage: test-automation-budgets.sh [budgets|digest|health]   Exits 0 only when every case in the group passes.
set -u
group=${1:-all}
here=$(cd "$(dirname "$0")/../.." && pwd)
pass=0; fail=0
ok() { echo "PASS: $1"; pass=$((pass + 1)); }
bad() { echo "FAIL: $1"; fail=$((fail + 1)); }
want() { [ "$group" = all ] || [ "$group" = "$1" ]; }

if want budgets; then
  out=$(cd "$here" && python3 -B - <<'PY'
import re, sys
sys.path.insert(0, "skills/workflow-regression/scripts")
import actions
yml = open(".github/workflows/regression.yml").read()
reg = open("docs/wiki/Regression.md").read()
aut = open("docs/wiki/Automation.md").read()
b = actions.BUDGET_MINUTES
errs = []
if "timeout-minutes: %d" % b not in yml: errs.append("regression.yml timeout is not %d" % b)
if "(%d - 2) * 60" % b not in yml: errs.append("the job seconds do not come from the budget")
if "shard: %s" % list(range(actions.SHARDS)) not in yml: errs.append("regression.yml has no %d-shard matrix" % actions.SHARDS)
if "REGRESSION_SHARD" not in yml: errs.append("no REGRESSION_SHARD")
req7 = reg[reg.index("- REG-7:"):reg.index("- REG-8:")]
if "under %d minutes" % b not in req7 or "sharded" not in req7: errs.append("REG-7 does not name %d minutes and sharding" % b)
req = aut[aut.index("- AUT-7:"):aut.index("## Non-goals")]
if "45 minutes" not in req or str(b) not in req: errs.append("AUT-7 does not name the 45-minute round of %d plus health" % b)
if 45 - b != 15: errs.append("round budget is not the regression budget plus 15")
print("; ".join(errs) or "OK")
PY
)
  [ "$out" = OK ] && ok "REG-7, AUT-7 and regression.yml name the same regression budget and shard the suite" || bad "budget agreement: $out"
fi

if want digest; then
  out=$(cd "$here" && python3 -B - <<'PY'
import json, os, sys, types
os.getuid = getattr(os, "getuid", lambda: 0)  # native Windows has none; win-posix-calls owns the real fix
sys.path.insert(0, "skills/workflow-health/scripts")
import automation
def fake(n):
    items = [{"number": i, "url": "u%d" % i, "milestone": None, "labels": []} for i in range(1, n + 1)]
    def gh(*args):
        assert str(automation.ISSUE_LIMIT) in args, "the listing is not paged to the limit"
        return types.SimpleNamespace(returncode=0, stdout=json.dumps(items), stderr="")
    return gh
automation.gh = fake(automation.ISSUE_LIMIT)
found, _ = automation.open_issues(())
cut = list(automation.CUT)
del automation.CUT[:]
automation.gh = fake(7)
automation.open_issues(())
print("OK" if cut and not automation.CUT and len(found) else "cut=%s after-small=%s" % (cut, automation.CUT))
PY
)
  [ "$out" = OK ] && ok "a full listing marks the digest TRUNCATED and a short one does not" || bad "digest truncation: $out"
  grep -q 'TRUNCATED: ' "$here/skills/workflow-health/scripts/automation.py" && ok "the digest prints TRUNCATED when a listing is cut" || bad "no TRUNCATED line"
fi
if want health; then
  out=$(cd "$here" && python3 -B - <<'PY'
import json, os, sys, time
os.getuid = getattr(os, "getuid", lambda: 0)
sys.path.insert(0, "skills/workflow-health/scripts")
import workflows
states = ["in_progress", "in_progress", "completed"]
calls = []
workflows.child = lambda argv, cwd, env, sec, log: (calls.append(argv), (0, json.dumps([{"status": states.pop(0)}])))[1]
slept = []
workflows.time.sleep = lambda s: slept.append(s)
said = workflows.wait_regression(".", {}, None, time.time() + 3600)
print("OK" if len(calls) == 3 and len(slept) == 2 and "finished" in said else "calls=%d slept=%d said=%s" % (len(calls), len(slept), said))
PY
)
  [ "$out" = OK ] && ok "health waits for a running regression to complete instead of a fixed offset" || bad "health wait: $out"
fi
echo "passed $pass failed $fail"
[ "$fail" = 0 ] && echo "ALL PASS"
[ "$fail" = 0 ]
