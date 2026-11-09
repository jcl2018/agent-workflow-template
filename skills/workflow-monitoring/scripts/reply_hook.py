#!/usr/bin/env python3
"""The operation session's reply format, kept by a Claude Code Stop hook instead of a prompt rule (MON-5).

usage: reply_hook.py              the Stop hook: reads the hook's JSON on stdin
       reply_hook.py check FILE|-  print what a reply is missing (exit 0 clean, 1 with problems, 2 unreadable)
       reply_hook.py status        say whether the hook is installed and on in this repo, and its recent let-throughs

A reply passes when it ends with one 'Decisions:' line (or 'Decisions: none') and then the full live board, exactly as
live_board.py prints it: the LIVE BOARD header, the sections Issues, Running goals, Queued goals, Dependencies and Finish
in that order, and one finish line, last. A code fence around the board is fine.

The hook checks only the operation session: a session whose transcript ran 'operate.py run' or 'board.py board' without
a refusal. A worker is never checked: a session whose cwd is in <git common dir>/loop/worktrees/, or that ran a flow step
('flow.py', 'goal.py step|record|pr'). A session in another repo, or in a repo with no .loop/config.json, is never checked.
"reply_hook": false in .loop/config.json, or LOOP_REPLY_HOOK=0, turns it off. A failing reply is blocked with a reason
naming what is missing; the third block in a row is let through and logged in <git common dir>/loop/reply-hook/log.
Any error lets the reply through (fail open) and logs one line. setup.py --reply-hook installs it. It runs git only.
"""
import json
import os
import re
import shlex
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
try:
    from live_board import SECTIONS  # noqa: E402
except Exception:  # the board's own module is the source; this copy keeps the hook alive without it
    SECTIONS = ("Issues", "Running goals", "Queued goals", "Dependencies", "Finish")

TRIES = 3  # the third block in a row is let through
KEEP = 200  # log lines kept
TAIL = 4 << 20  # bytes of the transcript read for the final reply once the session is known
SESSION = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
FENCE = re.compile(r"^\s*(```|~~~)")
MARKS = re.compile(r"[*#`_]")
TEMPLATE = ("End the reply like this: at most 6 report lines (anything waiting on the owner first), then one line "
            "'Decisions: <what the owner must decide>' (or 'Decisions: none'), then the full live board exactly as "
            "live_board.py prints it, in a code fence, last, with nothing after its finish line.")


def git(cwd, *args):
    done = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, timeout=10)
    return done.stdout.strip() if done.returncode == 0 else ""


def repo_of(cwd):
    """(top, common dir, config) of the repo at cwd, both paths absolute, or None outside a repo with a .loop config."""
    if not cwd or not os.path.isdir(cwd):
        return None
    top = git(cwd, "rev-parse", "--show-toplevel")
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not top or not common:
        return None
    try:
        with open(os.path.join(top, ".loop", "config.json")) as handle:
            config = json.load(handle)
    except (OSError, ValueError):
        return None
    return top, os.path.realpath(common), config if isinstance(config, dict) else {}


def folder(common):
    path = os.path.join(common, "loop", "reply-hook")
    os.makedirs(path, exist_ok=True)
    return path


def log(common, text):
    """Append one line; trim to the last KEEP lines once it passes twice that."""
    path = os.path.join(folder(common), "log")
    line = "%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), " ".join(str(text).split())[:400])
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a") as handle:
        handle.write(line)
    with open(path) as handle:
        lines = handle.readlines()
    if len(lines) > 2 * KEEP:
        write(path, "".join(lines[-KEEP:]))


def write(path, text):
    with open(path + ".tmp", "w") as handle:
        handle.write(text)
    os.replace(path + ".tmp", path)


def entries(path, tail=0):
    """The transcript's main-chain entries (subagent sidechains left out); with tail, only its last tail bytes."""
    found = []
    with open(path, "rb") as handle:
        if tail and os.path.getsize(path) > tail:
            handle.seek(-tail, os.SEEK_END)
            handle.readline()  # a partial first line
        for raw in handle.read().decode("utf-8", "replace").splitlines():
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if isinstance(entry, dict) and not entry.get("isSidechain"):
                found.append(entry)
    return found


def blocks(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [b for b in content or [] if isinstance(b, dict)]


def flat(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and b.get("type") == "text")


def runs(found):
    """Each Bash command with whether its result was a refusal: (argv, refused)."""
    results = {}
    for entry in found:
        if entry.get("type") == "user":
            for b in blocks(entry):
                if b.get("type") == "tool_result":
                    text = flat(b.get("content"))
                    results[b.get("tool_use_id")] = bool(b.get("is_error")) or text.lstrip().startswith("Exit code ") \
                        or any(line.lstrip().startswith("REFUSED") for line in text.splitlines())
    out = []
    for entry in found:
        if entry.get("type") != "assistant":
            continue
        for b in blocks(entry):
            if b.get("type") == "tool_use" and b.get("name") == "Bash" and b.get("id") in results:
                command = str((b.get("input") or {}).get("command") or "")
                out.append((command, results[b["id"]]))
    return out


def calls(command):
    """(script basename, subcommand) for each python script the command runs."""
    found = []
    for part in re.split(r"&&|\|\||;|\||\n", command):
        try:
            words = shlex.split(part)
        except ValueError:
            continue
        for i, word in enumerate(words):
            if word.endswith(".py") and i and os.path.basename(words[i - 1]).startswith("python"):
                rest = [w for w in words[i + 1:] if not w.startswith("-")]
                found.append((os.path.basename(word), rest[0] if rest else ""))
    return found


def kind(found, cwd, common):
    """'worker', 'operation' or '' for a session, from its cwd and the commands it ran (the later signal wins)."""
    if os.path.realpath(cwd).startswith(os.path.join(common, "loop", "worktrees") + os.sep):
        return "worker"
    seen = ""
    for command, refused in runs(found):
        if refused:
            continue
        for script, sub in calls(command):
            if script == "flow.py" or (script == "goal.py" and sub in ("step", "record", "pr")):
                seen = "worker"
            elif (script, sub) in (("operate.py", "run"), ("board.py", "board")):
                seen = "operation"
    return seen


def final_reply(payload, found):
    """The final assistant message's text, or None when it can't be confirmed (then the hook passes)."""
    if isinstance(payload.get("last_assistant_message"), str):
        return payload["last_assistant_message"]
    chat = [e for e in found if e.get("type") in ("user", "assistant")]
    if not chat or chat[-1].get("type") != "assistant":
        return None
    last = (chat[-1].get("message") or {}).get("id")
    texts = [b.get("text", "") for e in chat if e.get("type") == "assistant" and (e.get("message") or {}).get("id") == last
             for b in blocks(e) if b.get("type") == "text"]
    return "\n".join(texts) if texts else None


def bare(line):
    return MARKS.sub("", line).strip()


def problems(text):
    """What a reply is missing, one plain line each; an empty list means it passes."""
    lines = str(text or "").splitlines()
    heads = [i for i, line in enumerate(lines) if bare(line).startswith("LIVE BOARD")]
    if not heads:
        return ["it does not end with the live board (no LIVE BOARD header)"]
    head, found, at = heads[-1], [], heads[-1]
    for name in SECTIONS:
        spot = next((i for i in range(at + 1, len(lines)) if bare(lines[i]) == name), None)
        if spot is None:
            found.append("missing section %s" % name)
        else:
            at = spot
    if not found:
        tail = [line for line in lines[at + 1:] if line.strip() and not FENCE.match(line)]
        if not tail:
            found.append("no finish line after Finish")
        elif len(tail) > 1:
            found.append("text after the board's finish line")
    above = [line for line in lines[:head] if line.strip() and not FENCE.match(line)]
    if not above or not bare(above[-1]).startswith("Decisions:"):
        found.append("no 'Decisions:' line right above the board")
    if sum(1 for line in above if bare(line).startswith("Decisions:")) > 1:
        found.append("more than one 'Decisions:' line")
    return found


def hook(payload):
    """The block decision for one stop, or None to let the session stop."""
    session = str(payload.get("session_id") or "")
    if os.environ.get("LOOP_REPLY_HOOK") == "0" or not SESSION.match(session):
        return None
    where = repo_of(str(payload.get("cwd") or ""))
    if not where or where[2].get("reply_hook") is False:
        return None
    _, common, _ = where
    try:
        return decide(payload, session, common)
    except Exception as error:  # fail open, with a trace
        log(common, "fail-open %s: %s: %s" % (session, type(error).__name__, error))
        return None


def decide(payload, session, common):
    base = os.path.join(folder(common), session)
    try:
        with open(base + ".kind") as handle:
            known = handle.read().strip()
    except OSError:
        known = ""
    found = None
    if not known:  # decided once per session, then kept: the transcript is read whole only until then
        found = entries(payload["transcript_path"]) if payload.get("transcript_path") else []
        known = kind(found, str(payload.get("cwd")), common)
        if known:
            write(base + ".kind", known)
    if known != "operation":
        return None
    if found is None and not isinstance(payload.get("last_assistant_message"), str):
        found = entries(payload["transcript_path"], TAIL) if payload.get("transcript_path") else []
    text = final_reply(payload, found or [])
    wrong = problems(text) if text is not None else []
    count = 0
    if payload.get("stop_hook_active"):
        try:
            with open(base + ".count") as handle:
                count = int(handle.read().strip() or 0)
        except (OSError, ValueError):
            count = 0
    if not wrong or count + 1 >= TRIES:
        if wrong:
            log(common, "let-through %s after %d blocks: %s" % (session, count, "; ".join(wrong)))
        if os.path.exists(base + ".count"):
            os.remove(base + ".count")
        return None
    write(base + ".count", str(count + 1))
    return {"decision": "block", "reason": "REPLY FORMAT (MON-5): " + "; ".join(wrong) + ". " + TEMPLATE}


def status(cwd):
    where = repo_of(cwd)
    if not where:
        print("REPLY HOOK: off here (no repo with .loop/config.json)")
        return 0
    top, common, config = where
    try:
        with open(os.path.join(top, ".claude", "settings.local.json")) as handle:
            hooks = json.load(handle).get("hooks", {}).get("Stop", [])
        commands = [h.get("command", "") for group in hooks for h in group.get("hooks", [])]
    except (OSError, ValueError, AttributeError):
        commands = []
    mine = [c for c in commands if "reply_hook.py" in c]
    path = re.search(r"'([^']*reply_hook\.py)'", mine[0]).group(1) if mine and "'" in mine[0] else ""
    try:
        with open(os.path.join(common, "loop", "reply-hook", "log")) as handle:
            lets = sum(1 for line in handle if " let-through " in line)
    except OSError:
        lets = 0
    print("REPLY HOOK: %s, setting %s, script %s, let-throughs logged %d" % (
        "installed" if mine else "not installed (setup.py --reply-hook)", "off" if config.get("reply_hook") is False else "on",
        "found" if path and os.path.exists(path) else "missing" if mine else "-", lets))
    return 0


def main(argv):
    if argv[:1] == ["check"] and len(argv) == 2:
        try:
            text = sys.stdin.read() if argv[1] == "-" else open(argv[1]).read()
        except OSError as error:
            print("REFUSED: cannot read %s (%s). Fix: name a readable file, or - for stdin." % (argv[1], error.strerror))
            return 2
        wrong = problems(text)
        for line in wrong:
            print(line)
        return 1 if wrong else 0
    if argv[:1] == ["status"]:
        return status(os.getcwd())
    if argv:
        print(__doc__.strip().split("\n\n")[1])
        return 2
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        decision = hook(payload) if isinstance(payload, dict) else None
    except Exception:
        decision = None
    if decision:
        sys.stdout.write(json.dumps(decision) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
