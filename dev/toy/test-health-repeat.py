#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-health/scripts/health.py skills/workflow-health/scripts/file.py skills/workflow-health/scripts/issues.py
# reads: dev/toy/fakegh/fake.py
"""HLT-4, issue 3784: a repeated health finding updates its one issue and opens no second, with feature_labels on or off.

Runs health.py file twice in a throwaway repo against the fake gh (dev/toy/fakegh/fake.py, called in place of gh so it
needs no PATH shim and runs on Windows too), once with feature_labels off and once on. The fake reads a --body-file as the
bash fake does ($(cat) drops the last newline), which is what once turned every repeat into an update (issue 3784). usage: test-health-repeat.py [--break]
--break makes the dedupe fail (the issue list comes back empty), to see the row red."""
import contextlib
import io
import json
import os
import runpy
import subprocess
import sys
import tempfile

here = os.path.dirname(os.path.abspath(__file__))
root = os.path.abspath(os.path.join(here, "..", ".."))
scripts = os.path.join(root, "skills", "workflow-health", "scripts")
fake = os.path.join(here, "fakegh", "fake.py")
breaking = "--break" in sys.argv
failed = []
real_run = subprocess.run
calls = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def gh(argv, **kw):
    """Stands in for subprocess.run(["gh", ...]): the fake gh, with --body-file read as --body as dev/toy/fakegh/gh does."""
    args, i = [], 1
    while i < len(argv):
        if argv[i] == "--body-file":
            with open(argv[i + 1], encoding="utf-8") as f:
                args += ["--body", f.read().rstrip(chr(10))]  # bash $(cat) drops trailing newlines
            i += 2
        else:
            args.append(argv[i])
            i += 1
    calls.append(" ".join(args))
    kw.pop("capture_output", None)
    kw.pop("text", None)
    return real_run([sys.executable, fake] + args, capture_output=True, text=True, **kw)


def patched(argv, *a, **kw):
    return gh(argv, **kw) if argv and argv[0] == "gh" else real_run(argv, *a, **kw)


def git(*args):
    real_run(("git",) + args, check=True, capture_output=True, text=True)


def health(repo, *args):
    """health.py ARGS in REPO, in this process (so the gh calls reach `patched`); (stdout, exit)."""
    out, code = io.StringIO(), 0
    sys.argv, sys.path[:0] = [os.path.join(scripts, "health.py")] + list(args), [scripts]
    for name in ("health", "file", "issues", "report", "defects", "groups"):
        sys.modules.pop(name, None)
    os.chdir(repo)
    with contextlib.redirect_stdout(out):
        try:
            runpy.run_path(sys.argv[0], run_name="__main__")
        except SystemExit as stop:
            code = stop.code or 0
    sys.path.pop(0)
    os.chdir(here)  # never leave the cwd inside a directory about to be removed (Windows can't)
    return out.getvalue(), code


def issues_of(d):
    with open(os.path.join(d, "issues.json")) as f:
        return json.load(f)


subprocess.run = patched
for labels in (False, True):
    with tempfile.TemporaryDirectory() as tmp:
        repo, d = os.path.join(tmp, "repo"), os.path.join(tmp, "gh")
        os.makedirs(os.path.join(repo, ".loop"))
        os.makedirs(os.path.join(repo, "skills", "x", "scripts"))
        os.makedirs(d)
        os.environ["FAKE_GH_DIR"] = d
        os.environ.pop("LOOP_HEALTH_GH_FIXTURE", None)
        with open(os.path.join(repo, ".loop", "config.json"), "w") as f:
            json.dump({"base": "main", "feature_labels": labels}, f)
        with open(os.path.join(repo, ".loop", "docs.tsv"), "w") as f:
            f.write("Calc\tskills/x\nHome\tREADME.md\n")
        with open(os.path.join(repo, "skills", "x", "scripts", "near.py"), "w", newline="\n") as f:
            f.write("# pad\n" * 3400)
        git("init", "-q", "-b", "main", repo)
        git("-C", repo, "config", "user.email", "t@example.test")
        git("-C", repo, "config", "user.name", "t")
        git("-C", repo, "config", "core.autocrlf", "false")
        git("-C", repo, "add", "-A")
        git("-C", repo, "commit", "-qm", "A near-limit script")
        name = "feature_labels %s" % ("on" if labels else "off")
        out, code = health(repo, "file", "--group", "size")
        print(out)
        check("DONE open" in out and len(issues_of(d)) == 1, "%s: the first file opens one issue (%s)" % (name, out.strip()[:120]))
        if breaking:  # the dedupe broken: the issue list comes back empty
            os.environ["LOOP_HEALTH_GH_FIXTURE"] = os.path.join(tmp, "empty.json")
            with open(os.environ["LOOP_HEALTH_GH_FIXTURE"], "w") as f:
                f.write("[]")
        out, code = health(repo, "file", "--group", "size")
        print(out)
        os.chdir(here)
        check("SAME #1" in out and len(issues_of(d)) == 1, "%s: a repeat prints SAME #1 and opens no second issue (%s)" % (name, out.strip()[:160]))
os.chdir(here)
subprocess.run = real_run
if not failed:
    print("PASS: a repeat opens no second issue")  # the one line the regression row greps
sys.exit(1 if failed else 0)
