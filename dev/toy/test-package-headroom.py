#!/usr/bin/env python3
# windows: ok
# reads: dev/package.py skills/workflow-health/scripts/rules.py skills/workflow-health/scripts/report.py skills/workflow-delivery/scripts/lane.py skills/workflow-delivery/scripts/goal.py skills/workflow-regression/scripts/actions.py
"""Headroom under dev/package.py's caps: five scripts at 19,000 bytes or less, and no more than 98 shipped files.

The files are counted the way package.py counts them: the ones git tracks, never __pycache__ or other loose files."""
import importlib.util
import os

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIVE = ("workflow-health/scripts/rules.py", "workflow-health/scripts/report.py", "workflow-delivery/scripts/lane.py",
        "workflow-delivery/scripts/goal.py", "workflow-regression/scripts/actions.py")
fails = 0
for name in FIVE:
    with open(os.path.join(root, "skills", name), "rb") as handle:
        size = len(handle.read().replace(b"\r\n", b"\n"))
    ok = size <= 19000
    print("%s: %s is %d bytes (at most 19,000)" % ("PASS" if ok else "FAIL", name, size))
    fails += not ok
spec = importlib.util.spec_from_file_location("package", os.path.join(root, "dev", "package.py"))
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)
files = len(package.walk(root))
print("%s: the package holds %d files (at most 98)" % ("PASS" if files <= 98 else "FAIL", files))
fails += files > 98
raise SystemExit(1 if fails else 0)
