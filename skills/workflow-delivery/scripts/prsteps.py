#!/usr/bin/env python3
"""What goal.py pr records about the commit its pr lane passed, for merge.py's checks before it merges.

Imported by goal.py. record(state, base) sets state["pr_head"] (the HEAD the pr lane passed) and state["pr_base"]
(the base commit that HEAD was merged with). merge.py then refuses when the pull request head moved since (HEAD_MOVED)
or the base moved in paths the goal's rows reach (BASE_MOVED). docs: Regression#lane-messages.
"""
import subprocess


def git(*args):
    done = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def record(state, base):
    """Note the tested head and its base in the goal state (saved by the caller)."""
    head = git("rev-parse", "HEAD")
    state["pr_head"] = head
    state["pr_base"] = git("merge-base", head, "origin/" + base) or git("rev-parse", "origin/" + base)
