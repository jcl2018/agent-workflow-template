#!/usr/bin/env python3
"""The operation session's reply format, kept by a Claude Code Stop hook instead of a prompt rule (MON-5).

usage: reply_hook.py              the Stop hook: reads the hook's JSON on stdin
       reply_hook.py check FILE|-  print what a reply is missing (exit 0 clean, 1 with problems, 2 unreadable)
       reply_hook.py status        say whether the hook is installed and on in this repo, and its recent let-throughs

A check-in reply passes when it has this layout (issue 123): one headline line; then the sections All sessions (a table of
every session across repos), Dependencies (a drawn graph), Needs you (numbered questions with options and a recommended
answer, or "Nothing needs you") and, last, Coming up (the next expected events and what the owner will need to do), each
heading on its own line (Markdown marks and a trailing colon are fine) with something under it.

The hook checks only the operation session: one named in <git common dir>/loop/operation.id, or whose transcript ran 'operate.py run|claim' without a refusal, as its
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

# No terminal, no waiting: a prompt from git must fail, not block. (stdin is the hook's input, so it stays open.)
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

SECTIONS = ("All sessions", "Dependencies", "Needs you", "Coming up")  # the reply's sections, in order; Coming up last
NOTHING = "Nothing needs you"

TRIES = 3  # the third block in a row is let through
KEEP = 200  # log lines kept
TAIL = 4 << 20  # bytes of the transcript read for the final reply
STALE = 14 * 86400  # seconds before a finished session's state files are removed
OPERATORS = {"&&", "||", ";", "|", "&", ";;", "(", ")"}
KNOWN = {"goal.py": {"new", "queue", "step", "record", "wait", "finding", "pr", "answer", "show"}, "operate.py": {"run", "send", "claim"}}
FIRST = 16 << 20  # bytes read on a session's first stop: its recent history is enough to find its kind
SESSION = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
FENCE = re.compile(r"^\s*(```|~~~)")
FENCE_ALONE = re.compile(r"^\s*(```|~~~)[\w+.-]*\s*$")  # a line that opens or closes a fence, not a one-line fence
NUMBERED = re.compile(r"^\s*(?:[-*+]\s+)?\**(?:q\d+[.):]|\d+[.)])(?!\d)", re.I)
COUNT = re.compile(r"\s*\(\s*\d+\s*\)$")
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


def claimed(common):
    """Session ids in <common>/loop/operation.id: the operation session even when it never runs operate.py run."""
    try:
        with open(os.path.join(common, "loop", "operation.id")) as handle:
            return {line.strip() for line in handle if line.strip()}
    except OSError:
        return set()


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
        at = handle.tell()
        data = handle.read()
        cut = data.rfind(b"\n") + 1  # a last line still being written is left for the next read
        end = at + cut
        for raw in data[:cut].split(b"\n"):
            here, at = at, at + len(raw) + 1
            try:
                entry = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(entry, dict) and not entry.get("isSidechain"):
                entry["_at"] = here
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


def refused(text, error=False):
    """Whether a command did not run: its first output line (after an 'Exit code N' line) starts REFUSED, or it is an
    error with no exit code (the user or a rule denied it). One that ran and failed, timed out or was stopped did run."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and re.match(r"^Exit code -?\d+$", lines[0]):
        lines = lines[1:]
    elif error:
        return True
    return bool(lines) and lines[0].startswith("REFUSED")


def runs(found):
    """([(command, refused)] for each Bash call with its result here, byte offset of the first call still waiting)."""
    results = {}
    for entry in found:
        if entry.get("type") == "user":
            for b in blocks(entry):
                if b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = refused(flat(b.get("content")), bool(b.get("is_error")))
    out, waiting = [], None
    for entry in found:
        if entry.get("type") != "assistant":
            continue
        for b in blocks(entry):
            if b.get("type") == "tool_use" and b.get("name") == "Bash":
                if b.get("id") in results:
                    out.append((str((b.get("input") or {}).get("command") or ""), results[b["id"]]))
                elif waiting is None:
                    waiting = entry.get("_at")
    return out, waiting


def words_of(line):
    lex = shlex.shlex(line, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def runner(part, i):
    """Whether part[i], a .py word, is run as a script: by python (only its own flags between), by uv run, or as ./x.py."""
    if i == 0 and (part[i].startswith("./") or "/" in part[i]):
        return True
    before = part[:i]
    for j in range(len(before) - 1, -1, -1):
        if os.path.basename(before[j]).startswith("python"):
            between = before[j + 1:]
            return all(w.startswith("-") and w not in ("-m", "-c") for w in between)
        if not before[j].startswith("-"):
            break
    return before[-2:] == ["uv", "run"]


def calls(command, depth=0):
    """(script basename, subcommand) for each python script a shell command runs; sh -c / bash -c strings are opened."""
    found = []
    for line in command.splitlines():
        try:
            words = words_of(line)
        except ValueError:
            continue
        part = []
        for word in words + [";"]:
            if word not in OPERATORS:
                part.append(word)
                continue
            for i, item in enumerate(part):
                if item in ("-c",) and i and os.path.basename(part[i - 1]) in ("sh", "bash", "zsh") and i + 1 < len(part) and depth < 2:
                    found += calls(part[i + 1], depth + 1)
                    break
                if item.endswith(".py") and runner(part, i):
                    found.append((os.path.basename(item), subcommand(part[i + 1:], KNOWN.get(os.path.basename(item), set()))))
                    break
            part = []
    return found


def subcommand(rest, known):
    """The first word after the script that isn't a flag or a flag's value."""
    skip = False
    for word in rest:
        if word.startswith("-"):
            skip = "=" not in word
            continue
        if skip and word not in known:
            skip = False
            continue
        return word
    return ""


def signal(script, sub):
    """'worker', 'operation' or '' for one script run."""
    if script == "flow.py" or (script == "goal.py" and sub in ("step", "record", "pr")):
        return "worker"
    return "operation" if script == "operate.py" and sub in ("run", "claim") else ""


def kind(found, known=""):
    """(the session's kind after these entries: its latest signal among non-refused commands, else known;
    the byte offset of the first Bash call still waiting for its result, if any)."""
    done, waiting = runs(found)
    for command, no in done:
        if not no:
            for script, sub in calls(command):
                known = signal(script, sub) or known
    return known, waiting


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
    """A line as a heading: Markdown marks, a trailing colon and a trailing count like (2) dropped, case ignored."""
    return COUNT.sub("", bare(line).rstrip(":").strip()).rstrip(":").strip().lower()


def problems(text):
    """What a check-in reply is missing, one plain line each; an empty list means it passes."""
    lines, fenced, inside = [], [], False
    for line in str(text or "").splitlines():
        if FENCE_ALONE.match(line):
            inside = not inside
        elif FENCE.match(line):
            continue
        elif line.strip():
            lines.append(line)
            fenced.append(inside)  # a line inside a code fence is never a heading
    spots, at = {}, -1
    for name in SECTIONS:
        spot = next((i for i in range(at + 1, len(lines)) if not fenced[i] and heading(lines[i]) == name.lower()), None)
        if spot is not None:
            spots[name] = at = spot
    if not spots:
        return ["it is not in the check-in layout; missing all five parts: the headline line, All sessions, Dependencies, "
                "Needs you and Coming up (a one-line reply is never a check-in, issue 321)"]
    found = ["missing section %s%s" % (name, " (or it is out of order)" if any(heading(l) == name.lower() for l in lines) else "")
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
    first = not os.path.exists(base + ".kind")
    if first:
        prune(folder(common))
    path = payload.get("transcript_path")
    new, end = entries(path, FIRST if first else 0, offset) if path and os.path.exists(path) else ([], offset)
    if end < offset:  # a transcript that shrank was replaced: read it again
        new, end = entries(path, FIRST)
    if not known and os.path.realpath(str(payload.get("cwd"))).startswith(os.path.join(common, "loop", "worktrees") + os.sep):
        known = "worker"
    known, waiting = kind(new, known)
    if known != "worker" and session in claimed(common):  # operate.py claim (or the govern hook) named it (issue 321)
        known = "operation"
    keep = end if waiting is None or end - waiting > FIRST else waiting  # a call that never got its result stops holding
    write(base + ".kind", json.dumps({"kind": known, "offset": keep}))
    if known != "operation":
        return None
    found = None if isinstance(payload.get("last_assistant_message"), str) else entries(path, TAIL)[0] if path else []
    text = final_reply(payload, found or [])
    wrong = problems(text) if text is not None else []
    count = 0
    if payload.get("stop_hook_active") and os.path.exists(base + ".count") and time.time() - os.path.getmtime(base + ".count") < 900:
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
        print(__doc__.strip())
        return 0 if argv[0] in ("-h", "--help") else 2
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
