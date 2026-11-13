#!/usr/bin/env python3
# reads: skills/workflow-health/scripts/report.py dev/toy/matrix-smoke.py
# windows: ok
"""The agent x machine matrix: health's `matrix` rule reads .loop/matrix-runs.tsv, and matrix-smoke.py writes it.
usage: test-matrix.py [rule|record]   (default both). No network, no model."""
import datetime
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "skills", "workflow-health", "scripts"))
import report  # noqa: E402

bad = []


def check(name, cond):
    print("%s: %s" % ("PASS" if cond else "FAIL", name))
    if not cond:
        bad.append(name)


def repo(lines):
    folder = tempfile.mkdtemp(prefix="matrix-test-")
    os.makedirs(os.path.join(folder, ".loop"))
    if lines is not None:
        with open(os.path.join(folder, ".loop", "matrix-runs.tsv"), "w", newline="\n") as handle:
            handle.write("# date\tagent\tos\tmachine\tcommit\tresult\n" + "".join(l + "\n" for l in lines))
    return folder


def day(ago):
    return (datetime.date.today() - datetime.timedelta(days=ago)).isoformat()


def line(ago, agent, os_name, result="pass"):
    return "\t".join((day(ago), agent, os_name, "m1", "abc1234", result))


def states(folder):
    return {(r["state"], r["subject"]) for r in report.matrix(folder)}


def rule():
    check("no matrix-runs.tsv: the rule is off (no rows)", report.matrix(repo(None)) == [])
    got = states(repo([]))
    check("an empty record fails each V1-required cell", {s for s in got if s[0] == "FAIL"} ==
          {("FAIL", "Claude Code on Windows"), ("FAIL", "Claude Code on macOS"), ("FAIL", "CI on Linux")})
    check("an empty record warns not proven for the other cells", ("WARN", "codex on linux") in got and ("WARN", "claude-cli on linux") in got)
    full = [line(1, "claude-cli", "windows"), line(2, "claude-app", "macos"), line(0, "ci", "linux")]
    got = states(repo(full))
    check("a pass in each V1 cell leaves no FAIL", not [s for s in got if s[0] == "FAIL"])
    check("a V1 cell is proven by either Claude Code agent (no WARN for its twin)", ("WARN", "claude-app on windows") not in got)
    check("codex stays WARN while unproven", ("WARN", "codex on windows") in got)
    got = states(repo(full + [line(0, "codex", "windows")]))
    check("a passing codex smoke clears its cell", ("WARN", "codex on windows") not in got)
    got = states(repo([line(8, "claude-cli", "windows")] + full[1:]))
    check("a pass 8 days old no longer proves the cell", ("FAIL", "Claude Code on Windows") in got)
    got = states(repo([line(7, "claude-cli", "windows")] + full[1:]))
    check("a pass 7 days old still proves it", ("FAIL", "Claude Code on Windows") not in got)
    got = states(repo([line(0, "claude-cli", "windows", "fail")] + full[1:]))
    check("a failed smoke proves nothing", ("FAIL", "Claude Code on Windows") in got)
    got = states(repo(["not a record", "x\ty\tz"] + full))
    check("malformed lines are ignored", not [s for s in got if s[0] == "FAIL"])


def record():
    spec = importlib.util.spec_from_file_location("matrix_smoke", os.path.join(HERE, "matrix-smoke.py"))
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    folder = repo(None)
    smoke.ROOT = folder
    smoke.record("codex", "pass")
    smoke.record("ci", "fail")
    with open(os.path.join(folder, ".loop", "matrix-runs.tsv")) as handle:
        rows = [l.rstrip("\n").split("\t") for l in handle if not l.startswith("#")]
    check("record writes one line per run with date, agent, os, machine, commit and result", len(rows) == 2 and all(len(r) == 6 for r in rows))
    check("the date is today's and the agent and result are as given", rows[0][0] == day(0) and rows[0][1] == "codex" and rows[0][5] == "pass" and rows[1][5] == "fail")
    check("the os is one of windows, macos, linux", rows[0][2] in ("windows", "macos", "linux"))
    check("a smoke pass is what the health rule reads as proof", ("WARN", "codex on %s" % rows[0][2]) not in states(folder))
    check("the smoke refuses a step that does not exist", __import__("subprocess").run(
        [sys.executable, os.path.join(HERE, "matrix-smoke.py"), "--only", "nope"], capture_output=True, text=True).returncode == 2)


want = sys.argv[1:] or ["rule", "record"]
for name in want:
    {"rule": rule, "record": record}[name]()
print("ALL PASS" if not bad else "%d FAILED" % len(bad))
sys.exit(1 if bad else 0)
