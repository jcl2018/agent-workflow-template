#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-health/scripts/milestone.py skills/workflow-health/scripts/file.py skills/workflow-health/scripts/rules.py
# reads: skills/workflow-health/scripts/issues.py skills/workflow-setup/scripts/survey.py skills/workflow-delivery/scripts/goal.py
# reads: dev/toy/fakegh/fake.py
"""DOC-10, HLT-4, DEL-14, SET-17: every filing has one home. A defect is an issue labelled defect on no milestone; a backlog item is
an issue labelled backlog on "Backlog: <Feature>" (or "Backlog: Other"); setup makes those milestones, health's Adoption group
checks them, and a ship reply's FILE lines are filed once, behind --live.

Runs the health scripts in this process against the fake gh (dev/toy/fakegh/fake.py, called in place of gh so it needs no PATH shim
and runs on Windows too). usage: test-backlog.py [--break]; --break files every finding as a backlog item, to see the rows red."""
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
health = os.path.join(root, "skills", "workflow-health", "scripts")
setup = os.path.join(root, "skills", "workflow-setup", "scripts")
delivery = os.path.join(root, "skills", "workflow-delivery", "scripts")
fake = os.path.join(here, "fakegh", "fake.py")
breaking = "--break" in sys.argv
real_run = subprocess.run
failed = []
os.environ["GH_TOKEN"] = "toy"  # --live needs a token; the fake gh takes any


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
                args += ["--body", f.read().rstrip(chr(10))]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    kw.pop("capture_output", None)
    kw.pop("text", None)
    return real_run([sys.executable, fake] + args, capture_output=True, text=True, **kw)


def patched(argv, *a, **kw):
    return gh(argv, **kw) if argv and argv[0] == "gh" else real_run(argv, *a, **kw)


def git(*args):
    real_run(("git",) + args, check=True, capture_output=True, text=True)


def script(path, repo, *args):
    """path ARGS in REPO, in this process (so the gh calls reach `patched`); (stdout, exit)."""
    out, code = io.StringIO(), 0
    sys.argv, sys.path[:0] = [path] + list(args), [os.path.dirname(path)]
    for name in ("health", "file", "issues", "report", "defects", "milestone", "rules", "controls"):
        sys.modules.pop(name, None)
    os.chdir(repo)
    with contextlib.redirect_stdout(out):
        try:
            runpy.run_path(path, run_name="__main__")
        except SystemExit as stop:
            code = stop.code or 0
    sys.path.pop(0)
    os.chdir(here)
    return out.getvalue(), code


def issues_of(d):
    try:
        with open(os.path.join(d, "issues.json")) as f:
            return json.load(f)
    except OSError:
        return []


def titles_of(d):
    try:
        with open(os.path.join(d, "milestones.json")) as f:
            return [m["title"] for m in json.load(f)]
    except OSError:
        return []


def labels(issue):
    return sorted(l["name"] if isinstance(l, dict) else l for l in issue.get("labels") or [])


def stone(issue):
    return (issue.get("milestone") or {}).get("title")


subprocess.run = patched
with tempfile.TemporaryDirectory() as tmp:
    repo, d = os.path.join(tmp, "repo"), os.path.join(tmp, "gh")
    os.makedirs(os.path.join(repo, ".loop"))
    os.makedirs(os.path.join(repo, "skills", "x", "scripts"))
    os.makedirs(d)
    os.environ["FAKE_GH_DIR"] = d
    os.environ.pop("LOOP_HEALTH_GH_FIXTURE", None)
    with open(os.path.join(repo, ".loop", "config.json"), "w") as f:
        json.dump({"base": "main"}, f)
    with open(os.path.join(repo, ".loop", "docs.tsv"), "w") as f:
        f.write("Calc\tskills/x\nZed\tskills/z\nHome\tREADME.md\n")
    with open(os.path.join(repo, "skills", "x", "scripts", "near.py"), "w", newline="\n") as f:
        f.write("# pad\n" * 3400)
    git("init", "-q", "-b", "main", repo)
    git("-C", repo, "config", "user.email", "t@example.test")
    git("-C", repo, "config", "user.name", "t")
    git("-C", repo, "config", "core.autocrlf", "false")
    git("-C", repo, "add", "-A")
    git("-C", repo, "commit", "-qm", "A near-limit script")

    # SET-17: the standing milestones, one per feature page (Home is not one) and Other
    out, _ = script(os.path.join(health, "milestone.py"), repo, "backlog")
    check(out.count("WOULD create milestone Backlog: ") == 3 and not titles_of(d), "a dry run names the three milestones and writes none (%s)" % out.strip()[:140])
    out, _ = script(os.path.join(health, "milestone.py"), repo, "backlog", "--live")
    check(titles_of(d) == ["Backlog: Calc", "Backlog: Zed", "Backlog: Other"], "--live makes Backlog: Calc, Zed and Other (%s)" % titles_of(d))
    out, _ = script(os.path.join(health, "milestone.py"), repo, "backlog", "--live")
    check(out.count("EXISTS") == 3 and len(titles_of(d)) == 3, "a second run makes none (%s)" % out.strip()[:100])

    # HLT-4: a finding's home. The pure rule first, then a filed backlog item
    sys.path.insert(0, health)
    import file as F
    if breaking:
        F.home = lambda item, page: ("backlog", "Backlog: " + page if page else "Backlog: Other")
    row = lambda state, family, rule: {"state": state, "family": family, "rule": rule, "subject": "x", "detail": "d", "fix": "f", "evidence": "x"}
    check(F.home(row("FAIL", "traceability", "rows"), "Calc") == ("defect", ""), "a FAIL is a defect on no milestone")
    check(F.home(row("FAIL", "size", "scripts"), "Calc") == ("backlog", "Backlog: Calc"), "a size FAIL is a backlog item on its feature's milestone")
    check(F.home(row("WARN", "docs", "docs-check"), None) == ("backlog", "Backlog: Other"), "a WARN that fits no feature is a backlog item on Backlog: Other")
    check(F.home(row("WARN", "review", "conflict"), "Zed") == ("defect", ""), "a review conflict is a defect")
    check(F.home(row("WARN", "review", "gap"), "Zed") == ("backlog", "Backlog: Zed"), "a review gap is a backlog item")
    sys.path.pop(0)
    out, _ = script(os.path.join(health, "health.py"), repo, "preview", "--group", "size")
    check("as backlog on Backlog: Calc" in out, "the preview says where the issue would go (%s)" % out.strip()[:200])
    out, _ = script(os.path.join(health, "health.py"), repo, "file", "--group", "size")
    got = issues_of(d)
    check(len(got) == 1 and "backlog" in labels(got[0]) and stone(got[0]) == "Backlog: Calc" and "defect" not in labels(got[0]),
          "file opens one size finding labelled backlog on Backlog: Calc (%s)" % [(labels(i), stone(i)) for i in got])
    got[0]["milestone"] = {"title": "v1.0"}  # the owner moved it
    with open(os.path.join(d, "issues.json"), "w") as f:
        json.dump(got, f)
    out, _ = script(os.path.join(health, "health.py"), repo, "file", "--group", "size")
    check(len(issues_of(d)) == 1 and stone(issues_of(d)[0]) == "v1.0", "a repeat opens no second issue and leaves the owner's milestone (%s)" % out.strip()[:120])

    # HLT-4: a defect, end to end through plan and apply
    sys.path.insert(0, health)
    for name in ("file", "issues", "report", "defects", "milestone"):
        sys.modules.pop(name, None)
    import file as F2
    if breaking:
        F2.home = lambda item, page: ("backlog", "Backlog: Other")
    os.chdir(repo)
    with contextlib.redirect_stdout(io.StringIO()):
        acts = F2.plan([row("FAIL", "hygiene", "findings")], {}, ("hygiene",), root=repo)
        F2.apply(acts, repo, ("hygiene",))
    os.chdir(here)
    sys.path.pop(0)
    last = issues_of(d)[-1]
    check("defect" in labels(last) and not stone(last), "a FAIL is filed labelled defect on no milestone (%s, %s)" % (labels(last), stone(last)))

    # HLT-2 / SET-17: the Adoption group warns for a missing milestone, only on a GitHub repo
    git("-C", repo, "remote", "add", "origin", "https://github.com/o/r.git")
    sys.path.insert(0, health)
    for name in ("rules", "issues", "report", "defects", "milestone"):
        sys.modules.pop(name, None)
    import rules as R
    os.environ["LOOP_BACKLOG_MILESTONES"] = json.dumps(["Backlog: Calc", "Backlog: Zed"])
    rows = R.milestones(repo)
    check([r["subject"] for r in rows] == ["Backlog: Other"] and rows[0]["state"] == "WARN", "the Adoption group warns for the one missing milestone (%s)" % [r["subject"] for r in rows])
    os.environ["LOOP_BACKLOG_MILESTONES"] = json.dumps(["Backlog: Calc", "Backlog: Zed", "Backlog: Other"])
    check(R.milestones(repo) == [], "it is silent when all three exist")
    git("-C", repo, "remote", "remove", "origin")
    os.environ["LOOP_BACKLOG_MILESTONES"] = "[]"
    check(R.milestones(repo) == [], "it checks nothing in a repo with no GitHub origin")
    os.environ.pop("LOOP_BACKLOG_MILESTONES")
    sys.path.pop(0)

    # DEL-14: a ship reply's FILE lines, once each, only behind --live
    reply = os.path.join(tmp, "ship.txt")
    with open(reply, "w") as f:
        f.write("All good.\nFILE backlog calc: the size rule could name the largest function\nFILE defect Zed: the page lies about ZED-1\n"
                "FILE backlog Nowhere: an idea that fits no feature\nFILE backlog Zed: mail me at someone@example.test\nSTEP: done\n")
    before = len(issues_of(d))
    out, _ = script(os.path.join(health, "milestone.py"), repo, "leftovers", reply)
    check(out.count("WOULD file") == 3 and len(issues_of(d)) == before and "private value" in out, "without --live it only previews three, and skips the one with an email (%s)" % out.strip()[:200])
    out, _ = script(os.path.join(health, "milestone.py"), repo, "leftovers", reply, "--goal", "toy", "--live")
    new = issues_of(d)[before:]
    pairs = sorted((labels(i)[0], stone(i)) for i in new)
    check(pairs == [("backlog", "Backlog: Calc"), ("backlog", "Backlog: Other"), ("defect", None)] and "FILED" in out,
          "--live files a defect on no milestone and two backlog items, an unknown feature on Backlog: Other (%s)" % pairs)
    out, _ = script(os.path.join(health, "milestone.py"), repo, "leftovers", reply, "--goal", "toy", "--live")
    check(len(issues_of(d)) == before + 3 and out.count("SAME") == 3, "a second ship files nothing again (%s)" % out.strip()[:120])

    # SET-17: setup's issue filing makes the milestones first, and not at all with --no-issues
    sys.path.insert(0, setup)
    sys.modules.pop("survey", None)
    import survey
    calls = []

    def fake_run(argv, *a, **kw):
        calls.append(list(argv))
        out = "https://github.com/o/r.git\n" if argv[:2] == ["git", "-C"] else ""
        return subprocess.CompletedProcess(argv, 0, out, "")

    survey.subprocess.run, survey.shutil.which = fake_run, lambda name: name
    survey.file_issues(repo, False, 0)
    tools = [os.path.basename(c[1]) if c[0] == sys.executable else c[0] for c in calls]
    check("milestone.py" in tools and "health.py" in tools and tools.index("milestone.py") < tools.index("health.py"), "setup runs milestone.py backlog --live before health file (%s)" % tools)
    check(any("--live" in c and "backlog" in c for c in calls), "it passes --live")
    calls.clear()
    survey.file_issues(repo, True, 0)
    check(not [c for c in calls if c[0] == sys.executable], "--no-issues makes no milestone and files no issue")
    survey.subprocess.run = real_run
    sys.path.pop(0)

subprocess.run = real_run
os.chdir(here)
if not failed:
    print("PASS: every filing has one home")  # the one line the regression rows grep
sys.exit(1 if failed else 0)
