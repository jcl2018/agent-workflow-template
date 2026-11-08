#!/usr/bin/env python3
"""Assign goals in batches. The operation session only adds, starts workers and watches; it never runs a goal.

usage: batch.py <command> [options]

  add NAME --goal GOAL --done LINE [--done LINE] [--slug S] [--touches A,B] [--release ask]
      add a goal line under the heading '## Batch: NAME' in .loop/queue.md
  start NAME [--max N] [--skill-dir DIR]
      start one worker for each goal line (watch.py beside this file does it); each worker runs its own loop to the end
      and reports back by prompt message; otherwise print the command that starts them
  status NAME
      one line for each goal of the batch

Each goal runs the one skill flow in its own worktree, in its own worker. Nothing is merged.
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

SELF = os.path.abspath(sys.argv[0])
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,50}$")
HEAD = re.compile(r"^## Batch: (\S+)\s*$")
STEPS = ("build", "plan", "idea", "review", "qa", "ship", "step", "pr", "record", "run")
REFUSE = "REFUSED: %s is worker work; the operation session only assigns, watches and reports. Use: batch.py start NAME"

def git(*args, cwd=None, check=True):
    done = subprocess.run(["git"] + list(args), cwd=cwd, capture_output=True, text=True)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip() if done.returncode == 0 else ""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def loop_dir(*parts):
    path = os.path.join(os.path.abspath(git("rev-parse", "--git-common-dir")), "loop", *parts)
    os.makedirs(path, exist_ok=True)
    return path


def root():
    return git("rev-parse", "--show-toplevel")




def record_path(slug):
    return os.path.join(loop_dir("runs"), slug + ".json")


def load(slug):
    try:
        with open(record_path(slug)) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None




def queue_path():
    return os.path.join(root(), ".loop", "queue.md")


def read_queue():
    try:
        with open(queue_path()) as handle:
            return handle.read().splitlines()
    except OSError:
        return []


def fields(line):
    out = {}
    for part in line.strip()[2:].split("|"):
        key, _, value = part.partition(":")
        out.setdefault(key.strip(), " ".join(value.split()))
    return out


def batch_items(name):
    """The goal lines under '## Batch: NAME', as (kind, fields)."""
    items, inside = [], False
    for line in read_queue():
        if line.startswith("## "):
            match = HEAD.match(line)
            inside = bool(match and match.group(1) == name)
        elif inside and line.startswith("- slug:"):
            items.append(("goal", fields(line)))
    return items


def taken(slug):
    return any(line.startswith("- slug: %s " % slug) for line in read_queue()) or load(slug)


def put(name, line):
    lines = read_queue()
    at = None
    for index, text in enumerate(lines):
        if text.startswith("## "):
            if at is not None:
                break
            at = index + 1 if (HEAD.match(text) or [0, 0])[1] == name else None
        elif at is not None and text.strip():
            at = index + 1
    if at is None:
        lines += [""] * bool(lines and lines[-1].strip()) + ["## Batch: " + name, line]
    else:
        lines.insert(at, line)
    with open(queue_path(), "w") as handle:
        handle.write("\n".join(lines) + "\n")


def clean(text):
    text = " ".join(str(text).split())
    if "|" in text:
        sys.exit("REFUSED: no | in any text.")
    return text


def cmd_add(args):
    if not SLUG.match(args.name):
        sys.exit("REFUSED: bad batch name (lowercase letters, digits, dashes).")
    if not args.goal or not args.done:
        sys.exit("REFUSED: give --goal GOAL with at least one --done.")
    text = clean(args.goal)
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    slug = args.slug or "-".join(words)[:40].strip("-") or "item"
    if not SLUG.match(slug) or taken(slug):
        sys.exit("REFUSED: %s is a bad slug or already exists. Pick a new --slug." % slug)
    parts = ["slug: " + slug]
    if args.touches:
        parts.append("touches: " + clean(args.touches))
    if args.release:
        parts.append("release: " + args.release)
    parts += ["goal: " + text] + ["done: " + clean(item) for item in args.done]
    line = "- " + " | ".join(parts)
    put(args.name, line)
    print("ADDED %s to batch %s" % (slug, args.name))
    return 0


def cmd_start(args):
    items = batch_items(args.name)
    if not items:
        sys.exit("REFUSED: no goal lines under '## Batch: %s'." % args.name)
    if items:
        flags = (["--max", str(args.max)] if args.max else []) + (["--skill-dir", args.skill_dir] if args.skill_dir else [])
        watch = os.path.join(os.path.dirname(SELF), "watch.py")
        if os.path.exists(watch):
            subprocess.run([sys.executable, watch, "watch", "--once"] + flags, cwd=root())
        else:
            print("NEXT: run watch.py watch --once to start the goal lines.")
    return 0


def cmd_status(args):
    items = batch_items(args.name)
    for kind, item in items:
        slug = item.get("slug")
        state = load(slug)
        print("%s %s: %s" % (kind, slug, state.get("status") if state else "not started"))
    print("%d line(s) in batch %s" % (len(items), args.name)) if items else print("EMPTY batch " + args.name)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("add")
    item.add_argument("name")
    item.add_argument("--goal", default="")
    item.add_argument("--done", action="append", default=[])
    item.add_argument("--slug", default="")
    item.add_argument("--touches", default="")
    item.add_argument("--release", default="", choices=["", "ask"])
    item = sub.add_parser("start")
    item.add_argument("name")
    item.add_argument("--max", type=int, default=0)
    item.add_argument("--skill-dir", default="")
    sub.add_parser("status").add_argument("name")
    if sys.argv[1:2] and sys.argv[1] in STEPS and os.environ.get("LOOP_ROLE") != "worker":
        sys.exit(REFUSE % sys.argv[1])
    args = parser.parse_args()
    return globals()["cmd_" + args.command.lstrip("_")](args)


if __name__ == "__main__":
    sys.exit(main())
