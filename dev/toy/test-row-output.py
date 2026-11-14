#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-regression/scripts/runs.py skills/workflow-regression/scripts/rowtail.py
# reads: skills/workflow-regression/scripts/actions.py skills/workflow-regression/scripts/lanes.py
"""REG-3, defect 3789: a failing row's issue holds the row's last 40 output lines, never an empty block.

Rows like `bash dev/toy/test-X.sh 2>&1 | grep -q "PASS: ..."` print nothing, so their issues (#3133, #3773, #3784) had an empty
block. Checks the Mac tick path (runs.execute) and the workflow's inline block (actions.render, run with gh stubbed)."""
import os
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
scripts = os.path.join(root, "skills", "workflow-regression", "scripts")
sys.path.insert(0, scripts)
import actions  # noqa: E402
import runs  # noqa: E402

failed = []
LOUD = 'seq 1 60 | sed "s/^/line /" 2>&1 | grep -q "PASS: never printed"'  # fails, prints nothing
QUIET = "false"  # fails, prints nothing, and has no grep -q stage to make loud
NOISY = "echo boom 1; echo boom 2; echo boom 3; exit 1"


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def lines_of(tail):
    return tail.splitlines()


with tempfile.TemporaryDirectory() as tmp:
    picked = [{"id": "loud", "command": LOUD}, {"id": "quiet", "command": QUIET}, {"id": "noisy", "command": NOISY}]
    out, _ = runs.execute(tmp, picked, ["loud", "quiet", "noisy"], {}, None, 60, {}, False)
    tails = {r["id"]: r["tail"] for r in out}
    check([r["state"] for r in out] == ["FAIL"] * 3, "the three rows fail")
    check(lines_of(tails["loud"]) == ["line %d" % n for n in range(21, 61)],
          "Mac tick: a silent failing row gives an issue body of its last 40 output lines")
    check(tails["quiet"].strip() != "" and "exited 1" in tails["quiet"], "Mac tick: a row that prints nothing still gives a line, not an empty block")
    check(tails["noisy"] == "boom 1\nboom 2\nboom 3" or tails["noisy"].splitlines() == ["boom 1", "boom 2", "boom 3"],
          "Mac tick: a row that prints keeps its own output")

STUB = """import subprocess as _s, sys, os
_run, _pop, SEEN = _s.run, _s.Popen, []
def _fake(args, *a, **k):
    if args and args[0] == 'gh':
        if '--body-file' in args:
            SEEN.append(open(args[args.index('--body-file') + 1]).read())
        return _s.CompletedProcess(args, 0, '', '')
    return _run(args, *a, **k)
def _popen(cmd, **k):  # a row is a bash line; native Windows would hand it to cmd.exe
    if k.get('shell') and os.name == 'nt':
        k.pop('shell')
        cmd = ['bash', '-c', cmd]
    return _pop(cmd, **k)
_s.run, _s.Popen = _fake, _popen
"""
with tempfile.TemporaryDirectory() as tmp:
    text = actions.render("17 */4 * * *")
    block = text.split("python3 - --live <<'PY'\n", 1)[1].split("\n          PY\n", 1)[0]
    block = "\n".join(line[10:] for line in block.split("\n"))
    marker = "sys.exit(1 if red"
    assert marker in block
    os.makedirs(os.path.join(tmp, ".loop"))
    with open(os.path.join(tmp, ".loop", "regression.tsv"), "w") as handle:
        handle.write("loud\tland\t%s\tMON-1\n" % LOUD)
    code = STUB + block.replace(marker, "open('bodies.txt', 'w').write('=====SPLIT'.join(SEEN)); " + marker)
    done = subprocess.run([sys.executable, "-c", code, "--live"], cwd=tmp, env=dict(os.environ, REGRESSION_TARGET="land"),
                          capture_output=True, text=True)
    path = os.path.join(tmp, "bodies.txt")
    bodies = open(path).read().split("=====SPLIT") if os.path.exists(path) else []
    shown = bodies[0].split("```\n")[1].rstrip("\n").splitlines() if bodies and "```\n" in bodies[0] else None
    check(done.returncode == 1 and len(bodies) == 1, "CI: the failing row opens one issue (exit %s; %s)" % (done.returncode, done.stderr.strip()[-200:]))
    check(shown == ["line %d" % n for n in range(21, 61)], "CI: the issue body holds the last 40 output lines of the row")

sys.exit(1 if failed else 0)
