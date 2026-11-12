#!/usr/bin/env python3
"""The one command that runs the operation session's loop, the same way every time. No model is in the loop.

usage: operate.py <command> [options]

  run [--once] [--poll S] [--max N] [--skill-dir DIR] [--board]
      Each pass: watch.py watch --once (starts every queued goal and batch line whose dependencies are merged, up to
      parallel; mends and resumes if the config allows), board.py board, board_page.py. It prints the check-in every pass, even when nothing changed
      (--board adds the live board and its changes). Then it waits the gap from `board.py cadence`,
      or less: a worker that reports (a run record changes) or a goal added to the queue starts the next pass at once.
      It stops when nothing is queued, running or waiting, or when the cadence is off. --once makes one pass.
      Each pass also runs replan.py (MON-10) and auto.py pass (MON-11), and prints the check-in (checkin.py), not the
      live board: the board prints only for report, dashboard and "where do things stand" (MON-4; --board adds it).
  send SLUG TEXT [--source owner|auto]
      send a worker an answer or a follow-up (worker.py send); the worker's agent sees it the next time it runs goal.py.
      An answer to a waiting question is kept in <git common dir>/loop/answers.jsonl with its source (auto.py reads it)
  claim [--id ID]
      add this session ($CLAUDE_SESSION_ID or --id) to loop/operation.id, for the govern hook (MON-7), in this repo and
      every repo it follows (MON-13); sessions already there stay, so several independent operation sessions may run at
      once and nothing refuses or warns; refused in a worker

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
sys.path.insert(0, HERE)
import graph  # noqa: E402
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


def one_pass(top, common, args):
    flags = (["--max", str(args.max)] if args.max else []) + (["--skill-dir", args.skill_dir] if args.skill_dir else [])
    code, said = script("watch.py", "watch", "--once", *flags, cwd=top)
    if code:
        print(graph.localize(said.strip()))
    folder = os.path.join(common, "loop")
    board, before = os.path.join(folder, "board.json"), os.path.join(folder, "board.before.json")
    since = []
    if os.path.exists(board):
        os.replace(board, before)
        since = ["--since", before]
    _, out = script("board.py", "board", *since, cwd=top)
    delay = next((line.split()[1] for line in out.splitlines() if line.startswith("NEXT_DELAY ")), "none")
    if args.board:  # asked for "where do things stand": the live board and its changes, then the check-in
        print(graph.localize(out.rstrip()))
    script("board_page.py", cwd=top)  # board.html and the dashboard keep the live board; the check-in doesn't print it
    for name, *more in (("replan.py", "plan"), ("auto.py", "pass")):
        code, said = script(name, *more, cwd=top)
        if code:
            print(graph.localize(said.strip()))
    print(graph.localize(script("checkin.py", cwd=top)[1].rstrip()))
    script("board_page.py", "checkin", cwd=top)
    try:
        with open(board) as handle:
            busy = bool(json.load(handle).get("open"))
    except (OSError, ValueError):
        busy = False
    return delay, busy


def cmd_run(args):
    top = git("rev-parse", "--show-toplevel")
    common = os.path.abspath(git("rev-parse", "--git-common-dir"))
    if os.environ.get("CLAUDE_SESSION_ID"):
        cmd_claim(argparse.Namespace(id=""))
    pod = graph.pod_id()
    if pod:
        os.environ.setdefault("LOOP_POD_ID", pod)  # watch, auto, send and merge inherit it
    while True:
        seen = signature(top, common)  # before the pass, so a report that lands during it still starts the next one
        delay, busy = one_pass(top, common, args)
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


def remember(slug, text, source):
    """Keep an answer to a waiting question (slug, its question key, the words, who answered) for auto.py."""
    common = os.path.abspath(git("rev-parse", "--git-common-dir") or ".git")
    try:
        with open(os.path.join(common, "loop", "runs", slug + ".json")) as handle:
            run = json.load(handle)
    except (OSError, ValueError):
        return
    ask = (run.get("waiting") or {}).get("ask") if run.get("status") == "waiting" else ""
    if ask:
        with open(os.path.join(common, "loop", "answers.jsonl"), "a") as handle:
            handle.write(json.dumps({"slug": slug, "key": " ".join(ask.lower().split()), "words": text, "source": source}) + "\n")


def add_id(base, sid):
    """Add sid to <base>/loop/operation.id, keeping the sessions already there; a repo that can't be written is skipped."""
    path = os.path.join(base, "loop", "operation.id")
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path) as handle:
            have = {line.strip() for line in handle}
    except OSError:
        have = set()
    if sid not in have:
        try:
            with open(path, "a") as handle:
                handle.write(sid + "\n")
        except OSError:
            pass


def cmd_claim(args):
    """Two layers per pod (MON-13): this session joins the operation sessions of this repo and every repo it follows; the
    others stay, and nothing refuses, because independent operation sessions may run at once."""
    sid = args.id or os.environ.get("CLAUDE_SESSION_ID", "")
    common = os.path.abspath(git("rev-parse", "--git-common-dir") or ".git")
    if os.environ.get("LOOP_ROLE") == "worker" or os.path.realpath(os.getcwd()).startswith(os.path.join(common, "loop", "worktrees") + os.sep):
        sys.exit("REFUSED: a worker can't claim the operation session. Fix: run claim from the main checkout's operation session.")
    if not sid:
        sys.exit("REFUSED: no session id. Fix: operate.py claim --id <this session's id>.")
    import board as bd
    for base in [common] + [base for _, _, base in bd.followed() if base != common]:
        add_id(base, sid)
    print("CLAIMED operation session %s" % sid)
    print("POD %s: set LOOP_POD_ID=%s to keep this pod if the session restarts" % (sid, sid))
    return 0


def cmd_send(args):
    """The inbox always carries it; a goal in a worker session is also sent it by session message, which wakes it."""
    graph.refuse(graph.load_run(args.slug))  # another pod's goal is not ours to answer
    remember(args.slug, args.text, args.source)
    code, said = script("worker.py", "send", args.slug, args.text)
    print(graph.localize(said.strip()))
    if not code and os.path.exists(os.path.join(HERE, "sessions.py")):
        print(graph.localize(script("sessions.py", "send", args.slug, args.text)[1].strip()))
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
    item.add_argument("--board", action="store_true", help="also print the live board each pass (where do things stand)")
    item = sub.add_parser("send")
    item.add_argument("slug")
    item.add_argument("text")
    item.add_argument("--source", default="owner", choices=["owner", "auto"])
    item = sub.add_parser("claim")
    item.add_argument("--id", default="")
    args = parser.parse_args()
    return globals()["cmd_" + args.command](args)


if __name__ == "__main__":
    sys.exit(main())
