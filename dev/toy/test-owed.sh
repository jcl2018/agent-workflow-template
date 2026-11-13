#!/bin/bash
# reads: skills/workflow-delivery/scripts/fit.py
# Test that a lane failing only on rows both SKIPPED and UNPROVEN waits for off-platform proof (REG-10). usage: test-owed.sh
here=$(cd "$(dirname "$0")/../.." && pwd)
cd "$here/skills/workflow-delivery/scripts" || exit 1
python3 - <<'PY'
import sys; sys.dont_write_bytecode = True
import fit
t = "SKIPPED w1\nPASS ok\nUNPROVEN w1: never seen failing. Fix: x\n"
assert fit.off_rows(t) == ["w1"]
assert "STEP: pending" in fit.off_reply("LANE qa" + fit.off_line(t)) and "PENDING:" in fit.off_reply("LANE qa" + fit.off_line(t))
print("PASS: a lane that failed only on skipped, unproven rows waits for off-platform proof")
assert fit.off_rows(t + "FAIL z\n") == []
assert fit.off_rows("UNPROVEN w2: never seen failing\n") == []
assert fit.off_reply("LANE qa; LANE_FAIL z") == ""
print("PASS: a real failure, or an unproven row that ran, still costs a try")
PY
python3 - <<'PY'
import sys, types; sys.dont_write_bytecode = True
import fit
log = []
g = types.SimpleNamespace(private=types.SimpleNamespace(pr_result=lambda *a: log.append("result")), root=lambda: ".",
                          config=lambda: {"base": "main"}, failed_try=lambda *a: log.append("try"))
owed = "LANE pr FULL 1/1 in 1s" + fit.off_line("SKIPPED w1\nUNPROVEN w1: never seen failing\n")
assert fit.pr_fail(g, {"branch": "b"}, "h", owed, ["w1"]) == 1 and log == []
print("PASS: pr waits on owed off-platform proof and spends no try")
assert fit.pr_fail(g, {"branch": "b"}, "h", "LANE pr; LANE_FAIL z", ["z"]) == 1 and log == ["result", "try"]
print("PASS: pr still fails a try on a real failure or an unproven row that ran")
PY
