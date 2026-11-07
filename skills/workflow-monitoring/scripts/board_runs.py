#!/usr/bin/env python3
"""Change run records for board.py, which forwards these commands here.

usage: board_runs.py <command> [options]

  note SLUG TEXT        record a session's latest message on its run
  session add NAME --repo R [--branch B] [--waits-on X]
  session update NAME [those flags] [--status S] [--note T] [--next T] [--pr URL] [--eta TIME]
  session remove NAME   follow a session with no goal record
  retire SLUG --reason TEXT
  take SLUG             mark a goal as taken over by a visible session, so nothing mends it
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
STATES = ("running", "waiting", "done", "failed", "stopped")


def clean(value, size=300):
    return " ".join(str(value or "").split())[:size]


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def common():
    done = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True)
    return os.path.abspath(done.stdout.strip()) if done.returncode == 0 else ""


def loop_dir(base, *parts):
    path = os.path.join(base, "loop", *parts)
    os.makedirs(path, exist_ok=True)
    return path


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def write(path, text):
    temp = path + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        handle.write(text)
    os.replace(temp, path)


def session_file(base):
    return os.path.join(base, "loop", "sessions.json")


def run_of(slug):
    path = os.path.join(loop_dir(common(), "runs"), slug + ".json")
    run = read_json(path) if SLUG.match(slug) else None
    if not isinstance(run, dict):
        sys.exit("REFUSED: no run named %s in this repo." % slug)
    run["updated"] = now()
    return path, run


def cmd_note(args):
    path, run = run_of(args.slug)
    run["note"] = {"text": clean(args.text), "at": run["updated"]}
    write(path, json.dumps(run, indent=2))
    print("NOTED %s" % args.slug)
    return 0


def cmd_session(args):
    base = common()
    known = (read_json(session_file(base)) if os.path.exists(session_file(base)) else {})
    item = known.get(args.name)
    if not SLUG.match(args.name):
        sys.exit("REFUSED: bad session name.")
    if args.action != "add" and not item:
        sys.exit("REFUSED: no tracked session named %s." % args.name)
    if args.action == "add":
        if item or os.path.exists(os.path.join(base, "loop", "runs", args.name + ".json")):
            sys.exit("REFUSED: %s already exists." % args.name)
        if not args.repo:
            sys.exit("REFUSED: session add needs --repo.")
        at = now()
        item = known[args.name] = {"slug": args.name, "tracked": True, "external": True, "level": "session", "status": "running",
                                   "log": [at + " tracked"], "waits_on": []}
    if args.action == "remove":
        known.pop(args.name)
    else:
        for field in ("repo", "branch", "status", "next", "pr", "eta"):
            if getattr(args, field) is not None:
                item[field] = clean(getattr(args, field))
        if args.waits_on is not None:
            item["waits_on"] = [x.strip() for x in ",".join(args.waits_on).split(",") if x.strip()]
        item["updated"] = now()
        if args.note is not None:
            item["note"] = {"text": clean(args.note), "at": item["updated"]}
    loop_dir(base)
    write(session_file(base), json.dumps(known, indent=2, sort_keys=True) + "\n")
    print("SESSION %s %s" % (args.action.upper(), args.name))
    return 0


def cmd_retire(args):
    path, run = run_of(args.slug)
    if run.get("status") == "running" and not run.get("external"):
        sys.exit("REFUSED: %s is running. Fix: stop its agent, then run watch --once." % args.slug)
    run["retired"] = {"reason": clean(args.reason), "at": run["updated"]}
    run["status"], run["waiting"] = "retired", None
    run.setdefault("log", []).append("%s retired: %s" % (run["updated"], clean(args.reason)))
    write(path, json.dumps(run, indent=2))
    print("RETIRED %s" % args.slug)
    return 0


def cmd_take(args):
    path, run = run_of(args.slug)
    if run.get("status") == "running" and not run.get("external") and run.get("pid"):
        try:
            os.kill(run["pid"], 0)
            sys.exit("REFUSED: agent pid %s still runs %s. Fix: stop it first." % (run["pid"], args.slug))
        except OSError:
            pass
    run["external"], run["pid"], run["status"] = True, None, "running"
    run.setdefault("log", []).append("%s taken over by a visible session" % run["updated"])
    write(path, json.dumps(run, indent=2))
    print("TAKEN %s" % args.slug)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("note")
    item.add_argument("slug")
    item.add_argument("text")
    item = sub.add_parser("session")
    item.add_argument("action", choices=["add", "update", "remove"])
    item.add_argument("name")
    for flag in ("--repo", "--branch", "--note", "--next", "--pr", "--eta"):
        item.add_argument(flag)
    item.add_argument("--waits-on", action="append")
    item.add_argument("--status", choices=STATES)
    item = sub.add_parser("retire")
    item.add_argument("slug")
    item.add_argument("--reason", required=True)
    sub.add_parser("take").add_argument("slug")
    args = parser.parse_args()
    return globals()["cmd_" + args.command](args)


if __name__ == "__main__":
    sys.exit(main())
