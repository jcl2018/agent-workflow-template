#!/usr/bin/env python3
"""The operation session's reply format, kept by a Claude Code Stop hook instead of a prompt rule (MON-5).

usage: reply_hook.py              the Stop hook: reads the hook's JSON on stdin
       reply_hook.py check FILE|-  print what a reply is missing (exit 0 clean, 1 with problems, 2 unreadable)
       reply_hook.py status        say whether the hook is installed and on in this repo, and its recent let-throughs

A check-in reply passes when it has this layout (issue 123): one headline line; then the sections All sessions (a table of
every session across repos), Dependencies (a drawn graph), Needs you (numbered questions with options and a recommended
answer, or "Nothing needs you") and, last, Coming up (the next expected events and what the owner will need to do), each
heading on its own line (Markdown marks and a trailing colon are fine) with something under it.

The hook checks only the operation session: a session whose transcript ran 'operate.py run' without a refusal, as its
latest signal. A worker is never checked: a session that ran a flow step ('flow.py', 'goal.py step|record|pr') after that,
or whose cwd is in <git common dir>/loop/worktrees/ before any signal. A session in another repo, or in a repo with no
.loop/config.json, is never checked. Each stop reads only the transcript bytes added since the last one.
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

SECTIONS = ("All sessions", "Dependencies", "Needs you", "Coming up")  # the reply's sections, in order; Coming up last
NOTHING = "Nothing needs you"

TRIES = 3  # the third block in a row is let through
KEEP = 200  # log lines kept
TAIL = 4 << 20  # bytes of the transcript read for the final reply
STALE = 14 * 86400  # seconds before a finished session's state files are removed
OPERATORS = {"&&", "||", ";", "|", "&", ";;", "(", ")"}
WORKER = {"flow.py": None, "goal.py": {"step", "record", "pr"}}
SESSION = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
FENCE = re.compile(r"^\s*(```|~~~)")
NUMBERED = re.compile(r"^\s*\**\d+[.)]")
MARKS = re.compile(r"[*#`_]")
TEMPLATE = ("Write the check-in reply in this layout: one headline line; All sessions (one table: session, repo, what it "
            "is for, status, progress, time left, tokens left, latest); Dependencies (the drawn graph); Needs you (each "
            "question numbered with its options and a recommended answer, or 'Nothing needs you'); and last, Coming up "
            "(the next expected events and what the owner will need to do).")


def git(cwd, *args):
    done = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True, timeout=10)
    return done.stdout.strip() if done.returncode == 0 else ""


def repo_of(cwd):
    """(top, common dir, config) of the repo at cwd, both paths absolute, or None outside a repo with a .loop config."""
    if not cwd or not os.path.isdir(cwd):
        return None
    top = git(cwd, "rev-parse", "--show-toplevel")
    common = git(cwd, "rev-parse", "--git-common-dir")
    if not top or not common:
        return None
    common = os.path.join(cwd, common)  # a relative answer is relative to cwd; an absolute one stays as it is
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
    tmp = "%s.%d.tmp" % (path, os.getpid())  # one per process, so two sessions never share it
    with open(tmp, "w") as handle:
        handle.write(text)
    os.replace(tmp, path)


def off(config):
    return str(config.get("reply_hook", True)).strip().lower() in ("false", "0", "off", "no")


def entries(path, tail=0, start=0):
    """(main-chain entries, end offset) of the transcript: from byte start, or only its last tail bytes. Subagent
    sidechains are left out; a last line still being written is left for the next read."""
    found = []
    with open(path, "rb") as handle:
        size = os.path.getsize(path)
        if tail and size - start > tail:
            handle.seek(-tail, os.SEEK_END)
            handle.readline()  # a partial first line
        else:
            handle.seek(min(start, size))
        data = handle.read()
        end = handle.tell()
        if data and not data.endswith(b"\n"):
            cut = data.rfind(b"\n") + 1
            end -= len(data) - cut
            data = data[:cut]
        for raw in data.decode("utf-8", "replace").splitlines():
            try:
                entry = json.loads(raw)
            except ValueError:
                continue
            if isinstance(entry, dict) and not entry.get("isSidechain"):
                found.append(entry)
    return found, end


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
    """(script basename, its words after it) for each python script a shell command runs."""
    found = []
    for line in command.splitlines():
        try:
            lex = shlex.shlex(line, posix=True, punctuation_chars=True)
            lex.whitespace_split = True
            words = list(lex)
        except ValueError:
            continue
        part = []
        for word in words + [";"]:
            if word not in OPERATORS:
                part.append(word)
                continue
            for i, item in enumerate(part):
                if item.endswith(".py") and (any(os.path.basename(w).startswith("python") for w in part[:i])
                                             or i == 0 or item.startswith("./")):
                    found.append((os.path.basename(item), [w for w in part[i + 1:] if not w.startswith("-")]))
                    break
            part = []
    return found


def signal(script, rest):
    """'worker', 'operation' or '' for one script run."""
    if script in WORKER and (WORKER[script] is None or WORKER[script] & set(rest[:3])):
        return "worker"
    return "operation" if script == "operate.py" and "run" in rest[:3] else ""


def kind(found, known=""):
    """The session's kind after these entries: the latest signal among its non-refused commands, else known."""
    for command, refused in runs(found):
        if not refused:
            for script, rest in calls(command):
                known = signal(script, rest) or known
    return known


def final_reply(payload, found):
    """The final assistant message's text, or None when it can't be confirmed (then the hook passes)."""
    if isinstance(payload.get("last_assistant_message"), str):
        return payload["last_assistant_message"] or None
    chat = [e for e in found if e.get("type") in ("user", "assistant")]
    if not chat or chat[-1].get("type") != "assistant":
        return None
    last = chat[-1]
    if last.get("isApiErrorMessage") or (last.get("message") or {}).get("model") == "<synthetic>":
        return None  # an API error or usage-limit notice, not a reply
    mine = [e for e in chat if e.get("type") == "assistant" and (e.get("message") or {}).get("id") == (last.get("message") or {}).get("id")]
    if any(b.get("type") == "tool_use" for e in mine for b in blocks(e)):
        return None  # the turn's last message still calls a tool: the reply is not written yet
    texts = [b.get("text", "") for e in mine for b in blocks(e) if b.get("type") == "text"]
    return "\n".join(texts) if texts else None


def bare(line):
    return MARKS.sub("", line).strip()


def heading(line):
    return bare(line).rstrip(":").strip()


def problems(text):
    """What a check-in reply is missing, one plain line each; an empty list means it passes."""
    lines = [line for line in str(text or "").splitlines() if line.strip() and not FENCE.match(line)]
    spots, at = {}, -1
    for name in SECTIONS:
        spot = next((i for i in range(at + 1, len(lines)) if heading(lines[i]) == name), None)
        if spot is not None:
            spots[name] = at = spot
    if not spots:
        return ["it is not in the check-in layout (no All sessions, Dependencies, Needs you or Coming up section)"]
    found = ["missing section %s%s" % (name, " (or it is out of order)" if any(heading(l) == name for l in lines) else "")
             for name in SECTIONS if name not in spots]
    first = min(spots.values())
    if first == 0:
        found.append("no headline line before the first section")
    elif first > 1:
        found.append("more than one line before the first section; the headline is one line")
    names = [n for n in SECTIONS if n in spots]
    for name, after in zip(names, names[1:] + [None]):
        body = lines[spots[name] + 1:spots[after] if after else len(lines)]
        if not body:
            found.append("section %s is empty" % name)
        elif name == "Needs you" and not any(NUMBERED.match(l) or NOTHING.lower() in l.lower() for l in body):
            found.append("Needs you has no numbered question and does not say '%s'" % NOTHING)
    return found


def hook(payload):
    """The block decision for one stop, or None to let the session stop."""
    session = str(payload.get("session_id") or "")
    if os.environ.get("LOOP_REPLY_HOOK") == "0" or not SESSION.match(session):
        return None
    where = repo_of(str(payload.get("cwd") or ""))
    if not where or off(where[2]):
        return None
    _, common, _ = where
    try:
        return decide(payload, session, common)
    except Exception as error:  # fail open, with a trace
        log(common, "fail-open %s: %s: %s" % (session, type(error).__name__, error))
        return None


def state(base):
    try:
        with open(base + ".kind") as handle:
            held = json.load(handle)
        return str(held.get("kind", "")), int(held.get("offset", 0))
    except (OSError, ValueError, AttributeError, TypeError):
        return "", 0


def prune(where):
    """Remove state files of sessions not seen for STALE seconds."""
    now = time.time()
    for name in os.listdir(where):
        path = os.path.join(where, name)
        if name.endswith((".kind", ".count", ".tmp")) and now - os.path.getmtime(path) > STALE:
            os.remove(path)


def decide(payload, session, common):
    base = os.path.join(folder(common), session)
    known, offset = state(base)
    if not os.path.exists(base + ".kind"):
        prune(folder(common))
    path = payload.get("transcript_path")
    new, end = entries(path, start=offset) if path and os.path.exists(path) else ([], offset)
    if end < offset:  # a transcript that shrank was replaced: read it again from the start
        new, end = entries(path)
    if not known and os.path.realpath(str(payload.get("cwd"))).startswith(os.path.join(common, "loop", "worktrees") + os.sep):
        known = "worker"
    known = kind(new, known)
    write(base + ".kind", json.dumps({"kind": known, "offset": end}))
    if known != "operation":
        return None
    found = None if isinstance(payload.get("last_assistant_message"), str) else entries(path, TAIL)[0] if path else []
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
        "installed" if mine else "not installed (setup.py --reply-hook)", "off" if off(config) else "on",
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
