#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-regression/scripts/actions.py skills/workflow-regression/scripts/runs.py
# reads: skills/workflow-regression/scripts/regression.py
"""Issue 2614 and the duplicate flood: a failing row keeps exactly one open issue, and no issue is written without --live.

Runs the two writers of regression issues against an in-memory gh: the CI block of the written workflow (actions.py) and the
local runs.sync_issues (regression.py run). No PATH shim, so it runs on Windows too. usage: test-regression-issues.py"""
import contextlib
import io
import json
import os
import re
import runpy
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
real_run = subprocess.run
TAB, NL = chr(9), chr(10)


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


class FakeGh:
    """The few gh calls the two writers make, on a list of issues kept in memory. Every call is kept in self.calls."""

    def __init__(self, issues):
        self.issues, self.calls = issues, []

    def writes(self):
        return [c for c in self.calls if c[:2] in (["issue", "create"], ["issue", "edit"], ["issue", "comment"], ["issue", "close"],
                                                    ["issue", "reopen"], ["label", "create"])]

    def open_for(self, row):
        return sorted(i["number"] for i in self.issues if i["state"] == "OPEN" and "loop-regression %s " % row in i["body"])

    def __call__(self, argv, **kw):
        if not argv or argv[0] != "gh":
            return real_run(argv, **kw)
        args = list(argv[1:])
        self.calls.append(args)
        out = ""
        if args[:1] == ["api"]:  # the CI block's paged read of the open regression issues, as gh --jq gives it
            out = NL.join(json.dumps({"number": i["number"], "state": "OPEN", "body": i["body"], "labels": i["labels"]})
                          for i in self.issues if i["state"] == "OPEN")
        elif args[:2] == ["issue", "list"]:  # the local writer: newest first, at most --limit
            limit = int(args[args.index("--limit") + 1])
            out = json.dumps(sorted(self.issues, key=lambda i: -i["number"])[:limit])
        elif args[:2] == ["issue", "create"]:
            with open(args[args.index("--body-file") + 1], encoding="utf-8") as f:
                body = f.read()
            number = max([i["number"] for i in self.issues] + [0]) + 1
            self.issues.append({"number": number, "state": "OPEN", "body": body, "comments": [], "labels": [{"name": "regression"}, {"name": "defect"}]})
        elif args[:2] in (["issue", "close"], ["issue", "reopen"]):
            for i in self.issues:
                if str(i["number"]) == args[2]:
                    i["state"] = "CLOSED" if args[1] == "close" else "OPEN"
        elif args[:2] == ["issue", "comment"]:
            for i in self.issues:
                if str(i["number"]) == args[2]:
                    i["comments"].append({"body": "x"})
        return subprocess.CompletedProcess(argv, 0, out, "")


def issue(number, row, skipped=False):
    said = "The row `%s` was skipped." % row if skipped else "The row `%s` fails." % row
    return {"number": number, "state": "OPEN", "body": "<!-- loop-regression %s placed= -->%s%s%s" % (row, NL, said, NL),
            "comments": [], "labels": [{"name": "regression"}, {"name": "defect"}]}


def block_source():
    """(does the step pass --live, the CI block of the written workflow cut out the way the bash toys do)."""
    text = actions.render("17 */4 * * *")
    found = re.search(r"python3 - (--live )?<<'PY'\n(.*?)\n\s+PY\n", text, re.S)
    return bool(found.group(1)), NL.join(line[10:] for line in found.group(2).split(NL))


def in_repo(gh, argv, env, action):
    """Run action() with subprocess.run replaced by gh, in a throwaway git repo holding one failing row `red`; its output."""
    out, saved = io.StringIO(), (dict(os.environ), sys.argv, os.getcwd(), list(sys.path))
    with tempfile.TemporaryDirectory() as tmp:
        for cmd in (["init", "-q", "-b", "main", "."], ["config", "user.email", "t@example.test"], ["config", "user.name", "t"]):
            real_run(["git"] + cmd, cwd=tmp, check=True, capture_output=True)
        os.makedirs(os.path.join(tmp, ".loop"))
        with open(os.path.join(tmp, ".loop", "regression.tsv"), "w") as f:
            f.write(NL.join(TAB.join(cells) for cells in (
                ["# id", "level", "command", "goal", "seen_red", "description", "category", "link"],
                ["red", "land", 'python3 -c "raise SystemExit(1)"', "REG-5", "2026-11-13", "A failing row.", "criterion", ""])) + NL)
        with open(os.path.join(tmp, ".loop", "config.json"), "w") as f:
            json.dump({"base": "main"}, f)
        real_run(["git", "add", "-A"], cwd=tmp, check=True, capture_output=True)
        real_run(["git", "commit", "-qm", "rows"], cwd=tmp, check=True, capture_output=True)
        os.environ.update({"GH_TOKEN": "token", "LOOP_ROLE": "worker", "HOME": tmp, "USERPROFILE": tmp,
                           "REGRESSION_TARGET": "land", "REGRESSION_RESULTS": os.path.join(tmp, "res.tsv")})
        sys.argv = argv
        subprocess.run = gh
        os.chdir(tmp)
        try:
            with contextlib.redirect_stdout(out):
                try:
                    action()
                except SystemExit:
                    pass
        finally:
            subprocess.run = real_run
            os.chdir(saved[2])
            os.environ.clear()
            os.environ.update(saved[0])
            sys.argv, sys.path[:] = saved[1], saved[3]
    return out.getvalue()


def ci(gh, outcome, *flags):
    """The CI block once, its one row ending as outcome (pass, fail or skip); the output."""
    source = block_source()[1].replace("run(row[2])", "(%d, 'row output')" % {"pass": 0, "fail": 1, "skip": 77}[outcome])
    return in_repo(gh, ["-"] + list(flags), {}, lambda: exec(compile(source, "ci-block", "exec"), {"__name__": "__main__"}))


def regression_run(gh, *flags):
    """regression.py run red, with a token in the environment; the output."""
    argv = [os.path.join(scripts, "regression.py"), "run", "red"] + list(flags)
    return in_repo(gh, argv, {}, lambda: runpy.run_path(argv[0], run_name="__main__"))


def local(gh, outcome):
    """runs.sync_issues live, for the one row `red` ending as outcome."""
    subprocess.run = gh
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            runs.sync_issues([{"id": "red", "state": outcome, "tail": "row output"}], True, "2026-11-13")
    finally:
        subprocess.run = real_run


check(block_source()[0], "the written workflow starts its issue block with --live")
for label, run_it in (("the CI block", lambda g: ci(g, "fail", "--live")), ("the local run", lambda g: local(g, "FAIL"))):
    gh = FakeGh([issue(3700, "red", True), issue(2596, "red", True), issue(3119, "red", True)])
    run_it(gh)
    check(gh.open_for("red") == [2596], "%s: three open issues for one failing row leave one open, the oldest (open: %s)" % (label, gh.open_for("red")))
    run_it(gh)
    check(gh.open_for("red") == [2596] and not [c for c in gh.writes() if c[:2] == ["issue", "create"]],
          "%s: a repeat run opens no second issue (open: %s)" % (label, gh.open_for("red")))
gh = FakeGh([issue(3700, "red"), issue(2596, "red")])
out = ci(gh, "fail")
check(not gh.writes() and "WOULD" in out and gh.open_for("red") == [2596, 3700],
      "the CI block: a token but no --live writes nothing and says WOULD (writes: %s)" % gh.writes()[:2])
ci(gh, "fail", "--live")
check(gh.open_for("red") == [2596], "the CI block: with --live the same run closes the newer duplicate (open: %s)" % gh.open_for("red"))
gh = FakeGh([])
out = regression_run(gh)
check("WOULD open or update the issue for red" in out and not gh.writes(),
      "regression.py run: a token but no --live writes no issue (writes: %s; %s)" % (gh.writes()[:2], out.strip()[-100:]))
out = regression_run(gh, "--live")
check(any(c[:2] == ["issue", "create"] for c in gh.writes()), "regression.py run --live opens the failing row's issue (%s)" % out.strip()[-100:])
if not failed:
    print("PASS: each failing row keeps one open issue and no issue is written without --live")
sys.exit(1 if failed else 0)
