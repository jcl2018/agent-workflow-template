#!/usr/bin/env python3
"""Govern only (MON-7), kept by a Claude Code PreToolUse hook: the operation session never edits code, commits or pushes;
only merges and the post-merge steps change the repo.

usage: govern_hook.py          the PreToolUse hook: reads the hook's JSON on stdin, prints a deny decision or nothing
       govern_hook.py check    read a Bash command on stdin, print BLOCK with why, or PASS (tests and by hand)

Which session: the operation session only, known by its id in <git common dir>/loop/operation.id (`operate.py claim`
adds its session and keeps the others: several independent operation sessions may run at once) or by the reply hook's record that the session ran
`operate.py run`. A session whose folder is a goal worktree is a worker and is never checked, nor is any other repo.
What it blocks there: Edit, Write and NotebookEdit on a path inside a followed repo (this one, its worktrees, or one in
~/.workflow-loop/repos), so the session's own notes and other files outside every repo pass (issue 2850); and each Bash segment (split on && || ; | and new lines, with
`env X=Y`, `bash -c` and `sh -c` bodies read once more) that runs git, after any -C, -c, --git-dir or --work-tree
options, with commit, push, merge, rebase, reset, cherry-pick, revert, am or pull (a `pull --ff-only` passes, issue 495). Each segment is judged alone, so
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

WRITES = {"commit", "push", "merge", "rebase", "reset", "cherry-pick", "revert", "am", "pull"}
EDITS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
SPLIT = re.compile(r"&&|\|\||;|\||\n|[{}()]")
FIX = ("the operation session only governs (MON-7); a worker builds. Fix: hand the change to the goal's worker "
       "(operate.py send SLUG \"...\") or run the merge and post-merge steps (merge.py, release.py, wiki.py). "
       "Off switch: \"govern_hook\": false in .loop/config.json")


WRAPPERS = ("env", "command", "exec", "sudo", "nohup", "time", "nice", "xargs", "stdbuf", "timeout", "caffeinate",
            "{", "}", "!", "if", "then", "else", "elif", "while", "until", "do", "done", "fi")  # shell keywords run what follows


def strip(words):
    """A segment's words without leading VAR=x assignments, wrappers, their flags and flag values (timeout -s KILL 60,
    sudo -u root, nice -n 5): what is left starts with the command that runs."""
    i, wrapped = 0, False
    while i < len(words):
        word, prev = words[i], words[i - 1] if i else ""
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", word) or os.path.basename(word) in WRAPPERS:
            wrapped = wrapped or os.path.basename(word) in WRAPPERS
        elif not wrapped or not (word.startswith("-") or re.match(r"^[0-9.]+[smhd]?$", word) or re.match(r"^-[a-zA-Z]$", prev)):
            break
        i += 1
    return words[i:]


def safe_pull(args):
    """`git pull --ff-only [-q|-v] [remote [branch ...]]` and nothing else: an allowlist, since git takes the last of
    --ff/--ff-only and a `+src:dst` refspec or -f can force; anything else is refused."""
    names = [a for a in args if not a.startswith("-")]
    return ("--ff-only" in args and all(a in ("--ff-only", "-q", "--quiet", "-v", "--verbose") for a in args if a.startswith("-"))
            and all(re.match(r"^[A-Za-z0-9._/-]+$", a) for a in names))


def git_write(words):
    """The history-writing git subcommand in one segment's words, or ''."""
    configured = any(w.startswith("GIT_CONFIG") for w in words)  # an env config override (a forced fetch refspec)
    words, i = strip(words), 0
    if i < len(words) and os.path.basename(words[i]) in ("bash", "sh", "zsh") and i + 2 < len(words) and words[i + 1] == "-c":
        return verdict(words[i + 2], nested=True)
    if i >= len(words) or os.path.basename(words[i]) != "git":
        return ""
    i += 1
    while i < len(words):
        word = words[i]
        if word == "-c" and i + 1 < len(words) and words[i + 1].startswith("alias."):
            return "alias"  # an alias defined on the command line can be any write
        if word in ("-C", "-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
        elif word.startswith("-"):
            i += 1
        else:
            plain = all(w == "-C" or words[n - 1] == "-C" for n, w in enumerate(words[1:i], 1))  # only -C <dir> before pull
            if word == "pull" and plain and not configured and safe_pull(words[i + 1:]):  # no -c, --config-env or GIT_CONFIG_*
                return ""  # issue 495: a fast-forward-only pull can't rewrite history
            return word if word in WRITES else ""
    return ""


def segments(command):
    """The command's segments as word lists, split on && || ; | & and new lines outside quotes."""
    text = str(command or "").replace("\n", " ; ")
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()")
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:  # an unclosed quote: fall back to a plain split
        return [part.split() for part in SPLIT.split(text)]
    out, words = [], []
    for token in tokens:
        if token and set(token) <= set(";&|()"):
            out.append(words)
            words = []
        else:
            words.append(token)
    return [w for w in out + [words] if w]


def verdict(command, nested=False):
    """The first blocked git write in a command, as 'git <sub>', or ''."""
    for words in segments(command):
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


def claim(payload, common):
    """A session that runs `operate.py run` or `operate.py claim` (not a worker, not in a goal worktree) is the
    operation session: its id from the hook's own input goes into operation.id, so no environment variable is needed."""
    command = str((payload.get("tool_input") or {}).get("command") or "") if payload.get("tool_name") == "Bash" else ""
    session, cwd = str(payload.get("session_id") or ""), os.path.realpath(str(payload.get("cwd") or ""))
    runs = any(os.path.basename(x) == "operate.py" and w[n + 1:n + 2] in (["run"], ["claim"])
               and all(os.path.basename(p).startswith("python") or (k and p.startswith("-")) for k, p in enumerate(w[:n]))
               for w in (strip(words) for words in segments(command)) for n, x in enumerate(w))  # executed, not named
    if not runs or not reply_hook.SESSION.match(session):  # only executing operate.py claims; a grep that names it doesn't
        return
    if os.environ.get("LOOP_ROLE") == "worker" or cwd.startswith(os.path.join(common, "loop", "worktrees") + os.sep):
        return
    old = operation_ids(common)
    if session not in old:
        with open(os.path.join(common, "loop", "operation.id"), "a") as handle:
            handle.write(session + "\n")
        log(common, "added %s to operation.id from its operate.py call" % session)


def log(common, text):
    try:
        with open(os.path.join(common, "loop", "govern-hook.log"), "a") as handle:
            handle.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), " ".join(str(text).split())[:300]))
    except OSError:
        pass


def followed_roots(top, common):
    """Real paths of every followed repo: this checkout, its git common dir's parent and worktrees, and each repo listed in
    ~/.workflow-loop/repos (the board's list)."""
    roots = [top, os.path.dirname(common) if os.path.basename(common) == ".git" else common]
    try:
        with open(os.path.expanduser("~/.workflow-loop/repos")) as handle:
            roots += [line.strip() for line in handle if line.strip()]
    except OSError:
        pass
    return [os.path.normcase(os.path.realpath(r)) for r in roots if r]


def in_followed(given, cwd, top, common):
    """True when an edit tool's target path is inside a followed repo. A path it can't read counts as inside."""
    target = str(given.get("file_path") or given.get("notebook_path") or given.get("path") or "")
    if not target:
        return True
    target = os.path.normcase(os.path.realpath(os.path.join(cwd, os.path.expanduser(target))))
    return any(target == r or target.startswith(r.rstrip(os.sep) + os.sep) for r in followed_roots(top, common))


def decide(payload):
    """The deny reason for one tool call, or '' to let it run."""
    cwd = os.path.realpath(str(payload.get("cwd") or ""))
    if os.environ.get("LOOP_GOVERN_HOOK") == "0" or os.environ.get("LOOP_ROLE") == "worker" or "%sloop%sworktrees%s" % (os.sep, os.sep, os.sep) in cwd:
        return ""  # a worker, cheaply, before any git call: the hook runs on every tool call
    where = reply_hook.repo_of(str(payload.get("cwd") or ""))
    if not where or str(where[2].get("govern_hook", True)).strip().lower() in ("false", "0", "off", "no"):
        return ""
    top, common, _ = where
    try:
        claim(payload, common)
        if not is_operation(payload, common):
            return ""
        tool, given = payload.get("tool_name"), payload.get("tool_input") or {}
        if tool in EDITS:
            if not in_followed(given, str(payload.get("cwd") or ""), top, common):
                return ""  # a file outside every followed repo, such as the agent's memory notes (issue 2850)
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
