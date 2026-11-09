#!/usr/bin/env python3
"""Worker sessions: each goal runs in its own app session, named "worker · <goal>", and reports by session message.

usage: sessions.py <command> [options]

  assign SLUG               give a frozen goal to a worker session (watch.py does this for every goal it starts)
  bind SLUG ID [--name N]   record a session the operation session started itself with the app's own tools
  report SLUG [--step S] [--status S] [--pr URL] [--text T]
                            record a worker's session message: each step change, and its result at the end
                            (merged, failed or waiting); a merged or failed goal frees its session for the next goal
  list                      the sessions this repo knows, with their goals

A session tool does the talking: the command in `session_command` (.loop/config.json) or $LOOP_SESSION_TOOL, called as
`TOOL start NAME` (prints the new session's id), `TOOL rename ID NAME` and `TOOL send ID TEXT`. With no tool, or one
that fails or takes over 30 seconds, the goal falls back to a background process and the board says "background".
The pool lives in <git common dir>/loop/session-pool.json. It never merges.
"""
import argparse
import datetime
import json
import os
import shlex
import subprocess
import sys

SEND = ("You are the worker session for goal {slug}. Run every flow step inside this session: flow.py prints IN SESSION "
        "and the skill to invoke; run it yourself with the recommended answer at every question, never push from ship, "
        "and record each step with goal.py record. Send the operation session{to} a session message at each change of "
        "step or status, and your result when the goal ends (merged, failed or waiting, with the pull request).\n\n")
FINAL = {"merged": "done", "failed": "failed", "waiting": "waiting"}


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
    return read(os.path.join(base(), "runs", slug + ".json"), {})


def save(state, note):
    state["updated"] = now()
    state.setdefault("log", []).append("%s %s" % (state["updated"], note))
    write(os.path.join(base(), "runs", state["slug"] + ".json"), state)
    print("%s %s: %s" % (state["updated"], state["slug"], note))


def name_of(slug):
    return "worker · " + slug


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
    """Give the goal to a free session, or a new one; rename it, send it the goal. False means: start a background process."""
    command, slug = tool(cfg), state["slug"]
    state["worker"], state["worker_why"] = "background", "no session tool is set (session_command)"
    if not command:
        return False
    found, to = pool(), os.environ.get("LOOP_OPERATION_SESSION", "")
    text = SEND.format(slug=slug, to=" (%s)" % to if to else "") + prompt
    state["worker_why"] = "the session tool could not start a session"
    for sid in sorted(s for s, item in found.items() if item.get("state") == "free") + [None]:  # free ones first, then a new one
        reused = sid is not None
        sid = sid or call(command, "start", name_of(slug))
        if not sid:
            state["worker_why"] = "the session tool could not start a session"
            break
        if call(command, "rename", sid, name_of(slug)) is not None and call(command, "send", sid, text) is not None:
            break
        state["worker_why"] = "the session tool could not reach session %s" % sid
        found.setdefault(sid, {})["state"] = "unreachable"
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


def cmd_assign(args):
    state = load(args.slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % args.slug)
    if not assign(state, args.text, config()):
        print("BACKGROUND %s: %s" % (args.slug, state["worker_why"]))
        return 1
    return 0


def cmd_bind(args):
    state = load(args.slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % args.slug)
    if state.get("pid") and state.get("status") == "running":
        sys.exit("REFUSED: %s is running as background pid %s; let it end first." % (args.slug, state["pid"]))
    name = args.name or name_of(args.slug)
    found = pool()
    found[args.id] = {"name": name, "slug": args.slug, "state": "busy", "since": now()}
    save_pool(found)
    if state.get("status") in ("failed", "stopped", "queued", "", None):
        state.update(status="running", finding="", report=None)
    state.update(worker="session", worker_why="", session={"id": args.id, "name": name}, pid=None)
    save(state, "bound to session %s (%s)" % (args.id, name))
    return 0


def cmd_report(args):
    state = load(args.slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % args.slug)
    if args.step:
        state["step"] = args.step
    if args.pr:
        state["pr"] = args.pr
    status = FINAL.get(args.status, args.status) if args.status else state.get("status")
    state["status"] = status or "running"
    who = (state.get("session") or {}).get("name") or args.slug
    text = args.text or "%s: step %s, %s" % (who, state.get("step") or "-", args.status or state["status"])
    state.setdefault("reports", []).append({"at": now(), "step": state.get("step") or "-", "status": args.status or state["status"], "text": text})
    del state["reports"][:-30]
    if args.status in FINAL:
        state["report"] = {"status": args.status, "pr": state.get("pr", ""), "text": text, "at": now()}
        sid = (state.get("session") or {}).get("id")
        found = pool()
        if sid in found and args.status in ("merged", "failed"):
            found[sid]["state"] = "free"
            save_pool(found)
    save(state, "session report: " + text)
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
    for flag in ("--step", "--status", "--pr", "--text"):
        item.add_argument(flag, default="")
    sub.add_parser("list")
    args = parser.parse_args()
    return globals()["cmd_" + args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
