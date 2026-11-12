#!/bin/bash
# reads: skills/workflow-delivery/scripts/owed.py
# Test that a lane failing only on rows both SKIPPED and UNPROVEN waits for off-platform proof (REG-10). usage: test-owed.sh
here=$(cd "$(dirname "$0")/../.." && pwd)
cd "$here/skills/workflow-delivery/scripts" || exit 1
python3 - <<'PY'
import sys; sys.dont_write_bytecode = True
import owed
t = "SKIPPED w1\nPASS ok\nUNPROVEN w1: never seen failing. Fix: x\n"
assert owed.rows(t, []) == ["w1"]
assert "STEP: pending" in owed.reply("LANE qa" + owed.line(t, [])) and "PENDING:" in owed.reply("LANE qa" + owed.line(t, []))
print("PASS: a lane that failed only on skipped, unproven rows waits for off-platform proof")
assert owed.rows(t + "FAIL z\n", []) == []
assert owed.rows("UNPROVEN w2: never seen failing\n", []) == []
assert owed.reply("LANE qa; LANE_FAIL z") == ""
print("PASS: a real failure, or an unproven row that ran, still costs a try")
PY
