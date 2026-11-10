#!/usr/bin/env python3
"""Govern only (MON-7), kept by a Claude Code PreToolUse hook: the operation session never edits code, commits or pushes;
only merges and the post-merge steps change the repo.

usage: govern_hook.py          the PreToolUse hook: reads the hook's JSON on stdin, prints a deny decision or nothing
       govern_hook.py check    read a Bash command on stdin, print BLOCK with why, or PASS (tests and by hand)

Which session: the operation session only, known by its id in <git common dir>/loop/operation.id (`operate.py claim`
writes it, the last claim wins and says whom it replaced) or by the reply hook's record that the session ran
`operate.py run`. A session whose folder is a goal worktree is a worker and is never checked, nor is any other repo.
What it blocks there: Edit, Write and NotebookEdit; and each Bash segment (split on && || ; | and new lines, with
`env X=Y`, `bash -c` and `sh -c` bodies read once more) that runs git, after any -C, -c, --git-dir or --work-tree
options, with commit, push, merge, rebase, reset, cherry-pick, revert or am. Each segment is judged alone, so
`merge.py X && git push` is blocked. The merge and post-merge steps (merge.py, release.py, autorelease.py, wiki.py,
pool.py return, worker.py cleanup) run their own git inside their own process and pass. It guards the session's own
tool use; command substitution and shell writes such as `sed -i` are outside it.
`govern_hook: false` in .loop/config.json, or LOOP_GOVERN_HOOK=0, turns it off, read at each call. Any error lets the
call through and logs one line in <git common dir>/loop/govern-hook.log. setup.py --govern-hook installs it.
"""
import json
import os
import re
import shlex
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reply_hook  # noqa: E402

WRITES = {"commit", "push", "merge", "rebase", "reset", "cherry-pick", "revert", "am"}
EDITS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
SPLIT = re.compile(r"&&|\|\||;|\||\n")
FIX = ("the operation session only governs (MON-7); a worker builds. Fix: hand the change to the goal's worker "
       "(operate.py send SLUG \"...\") or run the merge and post-merge steps (merge.py, release.py, wiki.py). "
       "Off switch: \"govern_hook\": false in .loop/config.json")


def git_write(words):
    """The history-writing git subcommand in one segment's words, or ''."""
    i = 0
    while i < len(words) and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[i]) or words[i] in ("env", "command", "exec", "sudo")):
        i += 1
    if i < len(words) and os.path.basename(words[i]) in ("bash", "sh", "zsh") and i + 2 < len(words) and words[i + 1] == "-c":
        return verdict(words[i + 2], nested=True)
    if i >= len(words) or os.path.basename(words[i]) != "git":
        return ""
    i += 1
    while i < len(words):
        word = words[i]
        if word in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
        elif word.startswith("-"):
            i += 1
        else:
            return word if word in WRITES else ""
    return ""


def verdict(command, nested=False):
    """The first blocked git write in a command, as 'git <sub>', or ''."""
    for part in SPLIT.split(str(command or "")):
        part = part.strip().lstrip("(").rstrip(")").strip()
        if not part:
            continue
        try:
            words = shlex.split(part)
        except ValueError:
            words = part.split()
        found = git_write(words)
        if found:
            return found if nested or found.startswith("git ") else "git " + found
    return ""


def operation_ids(common):
    try:
        with open(os.path.join(common, "loop", "operation.id")) as handle:
            return {line.strip() for line in handle if line.strip()}
    except OSError:
        return set()


def is_operation(payload, common):
    session, cwd = str(payload.get("session_id") or ""), os.path.realpath(str(payload.get("cwd") or ""))
    if cwd.startswith(os.path.join(common, "loop", "worktrees") + os.sep) or os.environ.get("LOOP_ROLE") == "worker":
        return False
    if session and session in operation_ids(common):
        return True
    if not reply_hook.SESSION.match(session):
        return False
    kind, _ = reply_hook.state(os.path.join(common, "loop", "reply-hook", session))
    return kind == "operation"


def log(common, text):
    try:
        with open(os.path.join(common, "loop", "govern-hook.log"), "a") as handle:
            handle.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), " ".join(str(text).split())[:300]))
    except OSError:
        pass


def decide(payload):
    """The deny reason for one tool call, or '' to let it run."""
    if os.environ.get("LOOP_GOVERN_HOOK") == "0":
        return ""
    where = reply_hook.repo_of(str(payload.get("cwd") or ""))
    if not where or str(where[2].get("govern_hook", True)).strip().lower() in ("false", "0", "off", "no"):
        return ""
    _, common, _ = where
    try:
        if not is_operation(payload, common):
            return ""
        tool, given = payload.get("tool_name"), payload.get("tool_input") or {}
        if tool in EDITS:
            log(common, "blocked %s %s" % (tool, os.path.basename(str(given.get("file_path", "")))))
            return "%s is refused here: %s" % (tool, FIX)
        if tool == "Bash":
            found = verdict(given.get("command"))
            if found:
                log(common, "blocked %s" % found)  # the verb only: a command line can hold a token
                return "%s is refused here: %s" % (found, FIX)
        return ""
    except Exception as error:  # fail open, with a trace
        log(common, "fail-open %s: %s" % (type(error).__name__, error))
        return ""


def health(common):
    """(blocks, fail-opens, last fail-open cause) from the log, for the check-in."""
    try:
        with open(os.path.join(common, "loop", "govern-hook.log")) as handle:
            lines = handle.read().splitlines()[-200:]
    except OSError:
        return 0, 0, ""
    fails = [line for line in lines if " fail-open " in line]
    return sum(" blocked " in line for line in lines), len(fails), fails[-1].split(" fail-open ", 1)[1] if fails else ""


def main(argv):
    if argv[1:2] == ["check"]:
        found = verdict(sys.stdin.read())
        print("BLOCK: %s" % found if found else "PASS")
        return 0
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    reason = decide(payload if isinstance(payload, dict) else {})
    if reason:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": reason}}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
