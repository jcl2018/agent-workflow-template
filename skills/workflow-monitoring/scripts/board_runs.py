#!/usr/bin/env python3
"""Change run records for board.py, which forwards these commands here.

usage: board_runs.py <command> [options]

  note SLUG TEXT        record a worker's latest message on its run
  retire SLUG --reason TEXT
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


def cmd_retire(args):
    path, run = run_of(args.slug)
    if run.get("status") == "running":
        sys.exit("REFUSED: %s is running. Fix: stop its agent, then run watch --once." % args.slug)
    run["retired"] = {"reason": clean(args.reason), "at": run["updated"]}
    run["status"], run["waiting"] = "retired", None
    run.setdefault("log", []).append("%s retired: %s" % (run["updated"], clean(args.reason)))
    write(path, json.dumps(run, indent=2))
    print("RETIRED %s" % args.slug)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("note")
    item.add_argument("slug")
    item.add_argument("text")
    item = sub.add_parser("retire")
    item.add_argument("slug")
    item.add_argument("--reason", required=True)
    args = parser.parse_args()
    return globals()["cmd_" + args.command](args)


if __name__ == "__main__":
    sys.exit(main())
