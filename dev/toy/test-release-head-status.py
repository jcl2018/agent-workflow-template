#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-release/scripts/autorelease.py skills/workflow-release/scripts/merge.py
"""Defect 3870: merge.py posts a failing status on a release head it never tested, then asks the owner for a manual merge.

A release head that only moves the version and changelog carries the goal's passing lane (no lane runs); a head whose lane
could not run gets no status at all; only rows that ran and failed post failure, and the refusal names them."""
import os
import subprocess
import sys
import tempfile
import types

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "workflow-release", "scripts"))
import autorelease  # noqa: E402

failed = []
posted = []
ran = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def git(root, *args):
    return subprocess.run(["git", "-c", "user.email=t@example.test", "-c", "user.name=Toy", "-C", root] + list(args),
                          capture_output=True, text=True, check=True).stdout.strip()


def commit(root, files, message):
    for name, text in files.items():
        path = os.path.join(root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="\n") as handle:
            handle.write(text)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


def pr_result(top, base, head, branch, ok):
    posted.append((head, ok))
    return True


autorelease.LOADED["private"] = types.SimpleNamespace(pr_result=pr_result)


def lane(code, text):
    def fake(top, cfg, sha):
        ran.append(sha)
        return code, text
    return fake


def release(top, sha, state, outcome=None):
    del posted[:], ran[:]
    if outcome:
        autorelease.lane_at = outcome
    autorelease.release_statuses(top, {"base": "main"}, state, "release/v2-g", sha)
    return state


def refusal(state):
    try:
        autorelease.status_held(state, "https://example.test/pull/9", 9)
    except SystemExit as stop:
        return str(stop)
    return ""


with tempfile.TemporaryDirectory() as tmp:
    top = os.path.join(tmp, "repo")
    os.makedirs(top)
    git(top, "init", "-q", "-b", "main")
    commit(top, {"VERSION": "1\n", "CHANGELOG.md": "# x\n", "src/a.txt": "a\n"}, "base")
    bump = commit(top, {"VERSION": "2\n", "CHANGELOG.md": "# x\n## 2\n"}, "Release v2 (g)")
    code = commit(top, {"src/a.txt": "b\n", "VERSION": "3\n"}, "Release v3 (g)")
    state = release(top, bump, {"slug": "g", "statuses": "ok"}, lane(1, "FAIL row-x\n"))
    check(not ran and posted == [(bump, True)] and state["release_status"] == "success",
          "a release head that only moves the version and changelog carries the goal's pass and runs no lane")
    state = release(top, bump, {"slug": "g"}, lane(0, "RESULT 3 passed\n"))
    check(ran == [bump] and posted == [(bump, True)], "with no recorded pass on the goal, the head is tested rather than carried")
    state = release(top, code, {"slug": "g", "statuses": "ok"}, lane(0, "RESULT 3 passed\n"))
    check(ran == [code] and posted == [(code, True)], "a head that moves other files is tested, not carried, even when the goal passed")
    state = release(top, code, {"slug": "g", "statuses": "ok"}, lane(1, "PASS row-a\nFAIL row-b\nFAIL row-c\nRESULT 1 passed, 2 failed\n"))
    held = refusal(state)
    check(posted == [(code, False)] and state["release_status"] == "failure", "rows that ran and failed post failure")
    check("row-b, row-c" in held and "RELEASE_STATUS_FAILED" in held and "gh pr merge" not in held and "owner" in held,
          "the refusal names the failing rows and does not ask for a manual merge")
    state = release(top, code, {"slug": "g", "statuses": "ok"}, lane(None, "the lane could not finish: timed out"))
    held = refusal(state)
    check(not posted and state["release_status"] == "untested", "a lane that could not run posts no status at all")
    check("timed out" in held and "RELEASE_STATUS_UNTESTED" in held and "gh pr merge" not in held, "its refusal names the reason")
    state = release(top, code, {"slug": "g", "statuses": "ok"}, lane(1, "UNPROVEN row-a: never seen failing\nRESULT 3 passed, 0 failed, 1 unproven\n"))
    check(not posted and state["release_status"] == "untested", "a lane that exits 1 with no failed row (unproven rows only) is untested, not a failure")
    state = release(top, code, {"slug": "g", "statuses": "ok", "release_status": "success"}, lane(1, "FAIL row-b\n"))
    check(not ran and not posted, "a head already at success is left alone")

if failed:
    sys.exit("%d check(s) failed" % len(failed))
