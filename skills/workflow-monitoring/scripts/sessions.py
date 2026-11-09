#!/usr/bin/env python3
"""Worker sessions: each goal runs in its own app session, named "worker · <goal>", and reports by session message.

usage: sessions.py <command> [options]

  assign SLUG               give a frozen goal to a worker session (watch.py does this for every goal it starts)
  bind SLUG ID [--name N]   record a session the operation session started itself with the app's own tools
  report SLUG [--step S] [--status running|waiting|merged|failed] [--pr URL] [--ask Q --words W...] [--text T]
                            record a worker's session message: each step change, and its result when the goal ends.
                            merged is checked with gh; waiting with --ask is a question for the owner, without it the
                            goal ended with its pull request waiting. A goal that ended frees its session.
  send SLUG TEXT            send a worker session the owner's answer or a follow-up (operate.py send does this)
  list                      the sessions this repo knows, with their goals

A session tool does the talking: the command in `session_command` (.loop/config.json) or $LOOP_SESSION_TOOL, called as
`TOOL start NAME` (prints the new session's id), `TOOL rename ID NAME` and `TOOL send ID TEXT`. With no tool, or one
that fails or takes over 30 seconds, the goal falls back to a background process and the board says "background".
The pool lives in <git common dir>/loop/session-pool.json. Where auto_merge is on, a goal that ends with its pull
request open gets the release step run for it, as worker.py does for a background goal. Nothing else here merges.
"""
import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
SEND = ("You are the worker session for goal {slug}; this replaces any goal you had before. Work only in its worktree: "
        "cd {tree} first, and run every goal.py and flow.py command there with LOOP_ROLE=worker set. Run every flow step "
        "inside this session: flow.py prints IN SESSION and the skill to invoke; run it yourself with the recommended "
        "answer at every question, never push from ship, and record each step with goal.py record. Send the operation "
        "session{to} a session message at each change of step or status, and your result when the goal ends (merged, "
        "failed or waiting, with the pull request).\n\n")
FREE_TRIES = 2  # free sessions tried before a new one: each try can take a minute when the tool hangs


def git(*args):
    done = subprocess.run(["git", *args], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def base():
    return os.path.join(os.path.abspath(git("rev-parse", "--git-common-dir") or ".git"), "loop")


def read(path, empty):
    try:
        with open(path) as handle:
            found = json.load(handle)
        return found if isinstance(found, type(empty)) else empty
    except (OSError, ValueError):
        return empty


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        json.dump(data, handle, indent=2)
    os.replace(temp, path)


def pool():
    return read(os.path.join(base(), "session-pool.json"), {})


def save_pool(found):
    write(os.path.join(base(), "session-pool.json"), found)


def load(slug):
    return read(os.path.join(base(), "runs", slug + ".json"), {}) if SLUG.match(slug or "") else {}


def save(state, note):
    state["updated"] = now()
    state.setdefault("log", []).append("%s %s" % (state["updated"], note))
    write(os.path.join(base(), "runs", state["slug"] + ".json"), state)
    print("%s %s: %s" % (state["updated"], state["slug"], note))


def name_of(slug):
    return "worker · " + slug


def release(slug, found=None):
    """Free every session the pool holds for this goal; the caller saves the pool when it passes one in."""
    held = found if found is not None else pool()
    for item in held.values():
        if item.get("slug") == slug and item.get("state") == "busy":
            item["state"] = "free"
    if found is None:
        save_pool(held)
    return held


def tool(cfg):
    if os.environ.get("LOOP_SESSION_TOOL"):
        return shlex.split(os.environ["LOOP_SESSION_TOOL"])
    found = cfg.get("session_command")
    return [os.path.expanduser(str(part)) for part in found] if isinstance(found, list) and found else []


def call(command, *args):
    """One session tool call: its last output line, or None when it can't start or reach a session."""
    try:
        done = subprocess.run(command + list(args), capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    lines = done.stdout.strip().splitlines()
    return (lines[-1].strip() if lines else "") if done.returncode == 0 else None


def assign(state, prompt, cfg):
    """Give the goal to a free session, or a new one; rename it, send it the goal. False means: start a background process.
    A send that fails may still have arrived; the board names the fallback and its reason, so a second worker shows."""
    command, slug = tool(cfg), state["slug"]
    state["worker"], state["worker_why"] = "background", "no session tool is set (session_command)"
    if not command:
        return False
    found, to = pool(), os.environ.get("LOOP_OPERATION_SESSION", "")
    text = SEND.format(slug=slug, tree=state.get("worktree") or "its worktree", to=" (%s)" % to if to else "") + prompt
    free = sorted(s for s, item in found.items() if item.get("state") == "free")[:FREE_TRIES]
    sid, reused = None, False
    for sid in free + [None]:  # free ones first, then a new one
        reused = sid is not None
        sid = sid or call(command, "start", name_of(slug))
        if not sid:
            state["worker_why"] = "the session tool could not start a session"
            break
        if call(command, "rename", sid, name_of(slug)) is not None and call(command, "send", sid, text) is not None:
            break
        state["worker_why"] = "the session tool could not reach session %s" % sid
        found.setdefault(sid, {"name": name_of(slug), "slug": slug})["state"] = "unreachable"
        save_pool(found)
        sid = None
    if not sid:
        return False
    found[sid] = {"name": name_of(slug), "slug": slug, "state": "busy", "since": now()}
    save_pool(found)
    state.update(worker="session", worker_why="", session={"id": sid, "name": name_of(slug)}, pid=None, status="running")
    save(state, "assigned to session %s (%s)%s" % (sid, name_of(slug), ", reused" if reused else ""))
    return True


def config():
    return read(os.path.join(git("rev-parse", "--show-toplevel"), ".loop", "config.json"), {})


def held(slug):
    state = load(slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % slug)
    return state


def cmd_assign(args):
    state = held(args.slug)
    if not assign(state, args.text, config()):
        print("BACKGROUND %s: %s" % (args.slug, state["worker_why"]))
        return 1
    return 0


def cmd_bind(args):
    state = held(args.slug)
    if state.get("pid") and state.get("status") == "running":
        sys.exit("REFUSED: %s is running as background pid %s; let it end first." % (args.slug, state["pid"]))
    found = pool()
    other = found.get(args.id) or {}
    if other.get("state") == "busy" and other.get("slug") != args.slug:
        sys.exit("REFUSED: session %s is busy with goal %s." % (args.id, other.get("slug")))
    name = args.name or name_of(args.slug)
    release(args.slug, found)  # a session the goal had before goes back to the pool
    found[args.id] = {"name": name, "slug": args.slug, "state": "busy", "since": now()}
    save_pool(found)
    if state.get("status") in ("failed", "stopped", "queued", "", None):
        state.update(status="running", finding="", report=None)
    state.update(worker="session", worker_why="", session={"id": args.id, "name": name}, pid=None)
    save(state, "bound to session %s (%s)" % (args.id, name))
    return 0


def merged(url):
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], capture_output=True, text=True, timeout=20)
        return done.returncode == 0 and done.stdout.strip() == "MERGED"
    except (OSError, subprocess.SubprocessError):
        return False


def release_step(state):
    """Where auto_merge is on, a goal that ended with its pull request open gets merge.py, as worker.py does."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import worker
    except ImportError:
        return
    worker.release_step(state)


def cmd_report(args):
    state = held(args.slug)
    if args.step:
        state["step"] = args.step
    if args.pr:
        state["pr"] = args.pr
    pr, said = state.get("pr", ""), args.status
    ended = said in ("merged", "failed") or (said == "waiting" and not args.ask)
    if said == "waiting" and args.ask:  # a question for the owner: the goal stops until it is answered
        state.update(status="waiting", waiting={"ask": args.ask, "words": args.words or ["go on " + args.slug]})
    elif said == "failed":
        state.update(status="failed", finding=args.text or state.get("finding") or "the worker session reported failed")
    elif said in ("merged", "waiting"):  # the goal ended with a pull request: done, merged or waiting for review
        if not pr:
            sys.exit("REFUSED: %s with no pull request. Fix: pass --pr URL." % said)
        state["status"] = "done"
        if config().get("auto_merge") is True and not merged(pr):
            release_step(state)
            state = load(args.slug) or state
        said = "merged" if merged(pr) else "waiting"
    elif said == "running":
        state["status"] = "running"
    who = (state.get("session") or {}).get("name") or args.slug
    text = args.text or "%s: step %s, %s" % (who, state.get("step") or "-", said or state.get("status"))
    if said == "waiting" and not args.ask:
        text = args.text or "%s reports waiting (%s): its pull request waits for review and merge" % (who, pr)
    state.setdefault("reports", []).append({"at": now(), "step": state.get("step") or "-", "status": said or state.get("status"), "text": text})
    del state["reports"][:-30]
    if said in ("merged", "failed", "waiting"):
        state["report"] = {"status": said, "pr": pr, "text": text, "at": now()}
    if ended:
        release(args.slug)
    save(state, "session report: " + text)
    return 0


def cmd_send(args):
    """Send the owner's answer or a follow-up to the goal's worker session; 1 when it has none or can't be reached."""
    state = held(args.slug)
    sid, command = (state.get("session") or {}).get("id"), tool(config())
    if state.get("worker") != "session" or not sid or not command:
        print("NO SESSION for %s: the inbox carries it" % args.slug)
        return 1
    if call(command, "send", sid, " ".join(args.text.split())) is None:
        print("UNREACHED session %s for %s: the inbox carries it" % (sid, args.slug))
        return 1
    print("SENT to session %s (%s)" % (sid, (state.get("session") or {}).get("name")))
    return 0


def cmd_list(args):
    for sid, item in sorted(pool().items()):
        print("%s  %s  %s  %s" % (sid, item.get("state"), item.get("name"), item.get("slug")))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    item = sub.add_parser("assign")
    item.add_argument("slug")
    item.add_argument("--text", default="")
    item = sub.add_parser("bind")
    item.add_argument("slug")
    item.add_argument("id")
    item.add_argument("--name", default="")
    item = sub.add_parser("report")
    item.add_argument("slug")
    item.add_argument("--status", default="", choices=["", "running", "waiting", "merged", "failed"])
    for flag in ("--step", "--pr", "--text", "--ask"):
        item.add_argument(flag, default="")
    item.add_argument("--words", action="append", default=[])
    item = sub.add_parser("send")
    item.add_argument("slug")
    item.add_argument("text")
    sub.add_parser("list")
    args = parser.parse_args()
    return globals()["cmd_" + args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
