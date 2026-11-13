#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-health/scripts/issues.py skills/workflow-health/scripts/report.py
"""HLT-8: triage --close --issue N closes only the numbered open finding, with the owner's words.

Calls issues.close with a stand-in for gh and the open findings: no network, no repo."""
import os
import subprocess
import sys

root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(root, "skills", "workflow-health", "scripts"))
import issues  # noqa: E402

calls, fails = [], 0
issues.open_findings = lambda r, only=None: ([{"number": 1, "title": "a", "labels": ["health:docs"], "created_at": "2026-01-01"},
                                              {"number": 2, "title": "b", "labels": ["health:docs"], "created_at": "2026-01-01"}], "")
issues.subprocess.run = lambda cmd, **kw: (calls.append(cmd), subprocess.CompletedProcess(cmd, 0, "", ""))[1]
issues.features = lambda r: {}


def closed():
    return [c[3] for c in calls if c[:3] == ["gh", "issue", "close"]]


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += not ok


issues.close(root, "", "won't fix: one finding", numbers=(2,), yes=True)
check("--issue 2 closes only #2, with the owner's words", closed() == ["2"] and any("one finding" in " ".join(c) for c in calls))
calls.clear()
issues.close(root, "", "x", numbers=(99,), yes=True)
check("--issue for a number that is not an open finding closes nothing", closed() == [])
calls.clear()
issues.close(root, "", "x", numbers=(1, 2))
check("without --yes --issue only previews", closed() == [])
sys.exit(1 if fails else 0)
