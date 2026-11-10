#!/usr/bin/env python3
"""What goal.py pr does after its pr lane passes, before it pushes: the bookkeeping commit and the record merge.py checks.

Imported by goal.py. record(state, base):
  1. issue states (V5): `tests.py issues --write` once, bounded to 120 s; a failure leaves the file and prints NOTE;
  2. run results (DX-19): the branch's lane record's row results merge into .loop/regression-runs.tsv under the row
     lock, so the rows a goal ran show on the wiki and in health once it merges;
  3. one commit of those two files when they changed, with the wiki Tests tables re-rendered from them, then
  4. state["pr_lane"] (the pull request body's lane part), state["pr_head"] (the head goal.py pr pushes: the lane's commit plus that bookkeeping commit) and state["pr_base"]
     (the base commit it was merged with), for merge.py's HEAD_MOVED and BASE_MOVED checks.
workflow-regression/references/lanes.md.
"""
import datetime
import os
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
REG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-regression", "scripts"))
FILES = (".loop/regression-issues.tsv", ".loop/regression-runs.tsv")


def git(*args):
    done = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def issues(top):
    tests = os.path.join(REG, "tests.py")
    if not os.path.exists(tests) or not os.path.exists(os.path.join(top, ".loop", "regression.tsv")):
        return
    try:
        done = subprocess.run([sys.executable, tests, "issues", "--write", "--root", top], capture_output=True, text=True,
                              timeout=120, stdin=subprocess.DEVNULL)
        why = (done.stderr.strip().splitlines() or [""])[-1] if done.returncode else ""
    except subprocess.TimeoutExpired:
        why = "timed out"
    if why:
        print("NOTE: issue states not refreshed: %s" % why[:200])


def results(top):
    if not os.path.isdir(REG):
        return
    sys.path.insert(0, REG)
    sys.dont_write_bytecode = True  # importing them must not write a cache into the skill folder
    try:
        import lanes
        import runs
        import slots
        record, _ = lanes.load(lanes.record_path(top), top)
        rows = (record or {}).get("rows") or {}
        done = [dict({"id": key, "state": value.get("status")}, **{k: value[k] for k in ("flaky",) if k in value})
                for key, value in sorted(rows.items()) if value.get("status") in ("PASS", "FAIL")]  # flaky: flaky.py
        if done:
            day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
            slots.edit(top, "regression-runs.tsv", lambda: runs.write(top, done, day, git("rev-parse", "HEAD")))
    except (ImportError, OSError, ValueError, SystemExit) as error:
        print("NOTE: lane results not recorded in regression-runs.tsv: %s" % error)
    finally:
        sys.path.remove(REG)


def lane_part(slug):
    """The pull request body's lane part (DX-21): the pr lane's LANE line, and each row with why it ran, folded."""
    common = git("rev-parse", "--git-common-dir")
    base = os.path.join(os.path.abspath(common), "loop", "runs", "%s.pr-lane" % slug) if common and slug else ""
    try:
        with open(base + ".last") as handle:
            line = str(__import__("json").load(handle).get("line", "")).split("\n")[0]
        with open(base + ".txt") as handle:
            rows = [text.rstrip() for text in handle if text.startswith(("SELECTED ", "FULL (", "UNMAPPED "))]
    except (OSError, ValueError):
        return ""
    folded = "\n\n<details><summary>Rows and why they ran</summary>\n\n```\n%s\n```\n</details>" % "\n".join(rows) if rows else ""
    return "\n### Regression lane\n\n%s%s\n" % (line, folded) if line else ""


def record(state, base):
    """Refresh issue states and run results, commit them if they changed, then note the head and base for merge.py."""
    top = git("rev-parse", "--show-toplevel")
    if top:
        issues(top)
        results(top)
        changed = [path for path in FILES if git("status", "--porcelain", "--", path)]
        criteria = os.path.join(os.path.dirname(REG), "..", "workflow-docs", "scripts", "criteria.py")
        if changed and os.path.exists(os.path.join(top, ".loop", "docs.tsv")) and os.path.exists(criteria):
            subprocess.run([sys.executable, criteria, "render"], cwd=top, capture_output=True, text=True, timeout=300)
            status = subprocess.run(["git", "status", "--porcelain"], cwd=top, capture_output=True, text=True).stdout
            changed += [line[3:] for line in status.splitlines()  # the Tests tables it re-rendered (unstripped columns)
                        if line[3:].endswith(".md") and line[:2].strip() in ("M", "??")]
        if changed:  # a new (untracked) file must be added before --only can commit it
            subprocess.run(["git", "add", "--"] + changed, cwd=top, capture_output=True, text=True)
            done = subprocess.run(["git", "commit", "--only", "-q", "-m", "pr: record issue states and the lane's results",
                                   "--"] + changed, cwd=top, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
            if done.returncode:
                print("NOTE: the bookkeeping commit failed: %s" % ((done.stderr or done.stdout).strip().splitlines() or ["?"])[-1])
    state["pr_lane"] = lane_part(state.get("slug", ""))
    head = git("rev-parse", "HEAD")
    state["pr_head"] = head
    state["pr_base"] = git("merge-base", head, "origin/" + base) or git("rev-parse", "origin/" + base)
