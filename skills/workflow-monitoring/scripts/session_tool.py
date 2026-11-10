#!/usr/bin/env python3
"""The session tool: the command that starts, renames and messages the app's worker sessions (`session_command` in
.loop/config.json, or $LOOP_SESSION_TOOL). Used by sessions.py; imported, not run.
"""
import os
import shlex
import signal
import subprocess
import tempfile

# No terminal, no waiting: a prompt from git or gh in the tool must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def tool(cfg):
    if os.environ.get("LOOP_SESSION_TOOL"):
        return shlex.split(os.environ["LOOP_SESSION_TOOL"])
    found = cfg.get("session_command")
    return [os.path.expanduser(str(part)) for part in found] if isinstance(found, list) and found else []


HUNG = []  # set when a call times out: the tool is given up for the rest of this run


def timeout():
    try:
        return max(1.0, float(os.environ.get("LOOP_SESSION_TIMEOUT") or 30))
    except ValueError:
        return 30.0


def call(command, *args):
    """One session tool call: its last output line, or None when it can't start or reach a session. A call past the
    timeout (LOOP_SESSION_TIMEOUT, default 30 s) is killed with its process group, then the tool is given up for the
    run (watch.py clears that each round). Output goes to a file, so a helper the tool leaves running can't hold it."""
    if HUNG:
        return None
    with tempfile.TemporaryFile("w+") as out:
        try:
            child = subprocess.Popen(command + list(args), stdout=out, stderr=subprocess.DEVNULL,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
        except OSError:
            return None
        try:
            child.wait(timeout=timeout())
        except BaseException as error:  # a timeout, or an interrupt: never leave the tool running
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            if not isinstance(error, subprocess.TimeoutExpired):
                raise
            HUNG.append(" ".join(args[:1]))
            return None
        out.seek(0)
        lines = out.read().strip().splitlines()
    return (lines[-1].strip() if lines else "") if child.returncode == 0 else None
