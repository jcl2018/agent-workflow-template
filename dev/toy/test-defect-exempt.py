#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-health/scripts/health.py skills/workflow-health/scripts/defects.py
"""HLT-2 Traceability: a closed issue labelled health or backlog is exempt from the defect-test rule; a closed bug is not.

Stands in for the issue listing and the closed refs: no repo, no network."""
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(root, "skills", "workflow-health", "scripts"))
sys.argv = ["health.py"]
import health  # noqa: E402
import defects  # noqa: E402
import issues  # noqa: E402

defects.missing = lambda r: [("#815", "grd-goal"), ("#900", "bug-goal"), ("finding:x", "findings.md")]
issues.fetch = lambda r, scope="open": ([{"number": 815, "labels": ["health"]}, {"number": 900, "labels": ["defect"]}], "")
refs = [row["subject"] for row in health.defect_rows(root)]
fails = 0
for name, ok in (("a closed health finding needs no defect test", "#815" not in refs),
                 ("a closed bug without a defect test still fails", "#900" in refs and "finding:x" in refs)):
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += not ok
issues.fetch = lambda r, scope="open": (None, "offline")
check = [row["subject"] for row in health.defect_rows(root)]
ok = "#815" in check
print(("PASS: " if ok else "FAIL: ") + "when the issues can't be read nothing is exempted")
fails += not ok
sys.exit(1 if fails else 0)
