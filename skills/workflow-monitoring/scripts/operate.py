#!/usr/bin/env python3
"""The one command that runs the operation session's loop, the same way every time. No model is in the loop.

usage: operate.py <command> [options]

  run [--once] [--poll S] [--max N] [--skill-dir DIR]
      Each pass: watch.py watch --once (starts every queued goal and batch line whose dependencies are merged, up to
      parallel; mends and resumes if the config allows), board.py board, board_page.py. It prints the status block and
      the changes when something changed, and one line when nothing did. Then it waits the gap from `board.py cadence`,
      or less: a worker that reports (a run record changes) or a goal added to the queue starts the next pass at once.
      It stops when nothing is queued, running or waiting, or when the cadence is off. --once makes one pass.
  send SLUG TEXT
      send a worker an answer or a follow-up (worker.py send); the worker's agent sees it the next time it runs goal.py

An LLM asked to run the operation session runs `operate.py run` and nothing else. It never merges.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import time

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

HERE = os.path.dirname(os.path.abspath(__file__))
DONE = "NOTHING LEFT TO OPERATE: no goal is queued, running or waiting. Nothing was merged."


def git(*args):
    done = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def script(name, *args, cwd=None):
    done = subprocess.run([sys.executable, os.path.join(HERE, name)] + list(args), capture_output=True, text=True, cwd=cwd)
    return done.returncode, done.stdout + done.stderr


def signature(top, common):
    """What a worker's report or a new queue line changes: the run records, the inbox and the queue file."""
    files = glob.glob(os.path.join(common, "loop", "runs", "*.json")) + [os.path.join(top, ".loop", "queue.md")]
    found = {}
    for path in files:
        try:
            found[path] = os.stat(path).st_mtime_ns
        except OSError:
            pass
    return found


def one_pass(top, common, args, first):
    flags = (["--max", str(args.max)] if args.max else []) + (["--skill-dir", args.skill_dir] if args.skill_dir else [])
    code, said = script("watch.py", "watch", "--once", *flags, cwd=top)
    if code:
        print(said.strip())
    folder = os.path.join(common, "loop")
    board, before = os.path.join(folder, "board.json"), os.path.join(folder, "board.before.json")
    since = []
    first = first and not os.path.exists(board)  # a board from an earlier run is the baseline, so a quiet restart is one line too
    if os.path.exists(board):
        os.replace(board, before)
        since = ["--since", before]
    _, out = script("board.py", "board", *since, cwd=top)
    lines = out.splitlines()
    delay = next((line.split()[1] for line in lines if line.startswith("NEXT_DELAY ")), "none")
    quiet = [line for line in lines if line.startswith("NO_CHANGE")]
    digest = next((line[7:] for line in lines if line.startswith("DIGEST ")), "")
    if "CHANGED no" in lines and not first:
        print(quiet[0].split(" ", 1)[1] if quiet else "Nothing changed. %s." % digest)
    else:
        print(out.rstrip())
        print(script("board_page.py", cwd=top)[1].rstrip())
    try:
        with open(board) as handle:
            busy = bool(json.load(handle).get("open"))
    except (OSError, ValueError):
        busy = False
    return delay, busy


def cmd_run(args):
    top = git("rev-parse", "--show-toplevel")
    common = os.path.abspath(git("rev-parse", "--git-common-dir"))
    first = True
    while True:
        seen = signature(top, common)  # before the pass, so a report that lands during it still starts the next one
        delay, busy = one_pass(top, common, args, first)
        first = False
        if not busy:
            print(DONE)
            return 0
        if args.once:
            return 0
        if delay == "none":
            print("CADENCE OFF: the owner turned the loop off. Stop.")
            return 0
        stop = time.time() + int(delay)
        while time.time() < stop and signature(top, common) == seen:
            time.sleep(args.poll)


def cmd_send(args):
    code, said = script("worker.py", "send", args.slug, args.text)
    print(said.strip())
    return code


def main():
    sys.stdout.reconfigure(line_buffering=True)  # a loop that waits must show each pass at once, even into a file
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("run")
    item.add_argument("--once", action="store_true")
    item.add_argument("--poll", type=float, default=2)
    item.add_argument("--max", type=int, default=0)
    item.add_argument("--skill-dir", default="")
    item = sub.add_parser("send")
    item.add_argument("slug")
    item.add_argument("text")
    args = parser.parse_args()
    return globals()["cmd_" + args.command](args)


if __name__ == "__main__":
    sys.exit(main())
