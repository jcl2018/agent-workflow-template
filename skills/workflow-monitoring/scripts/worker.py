#!/usr/bin/env python3
"""A worker runs one goal's own loop to the end, then reports back to the operation session.

usage: worker.py <command> [options]

  loop SLUG -- COMMAND...   run the goal's agent command; when it ends, send the result back (watch.py and mend.py start this)
  report SLUG STATUS [--pr URL] [--words TEXT]
                            send a result back by hand: STATUS is merged, failed or waiting
  met SLUG N [N...]         record that done lines N are met, for the status block's Goals section

A report is a prompt message in the run record's `report`: {"status", "pr", "text", "at"}. The board shows it, and a
failed or waiting one stays at the top of Needs you until the goal moves on. It never merges.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

TOKENS = re.compile(r"(\d[\d,]*) (?:total )?tokens", re.I)


def git(*args):
    done = subprocess.run(["git"] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def base():
    return os.path.join(os.path.abspath(git("rev-parse", "--git-common-dir")), "loop")


def path_of(slug):
    return os.path.join(base(), "runs", slug + ".json")


def load(slug):
    try:
        with open(path_of(slug)) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def save(state, note=None):
    state["updated"] = now()
    if note:
        state.setdefault("log", []).append("%s %s" % (state["updated"], note))
        print("%s %s: %s" % (state["updated"], state["slug"], note))
    temp = path_of(state["slug"]) + ".%d.tmp" % os.getpid()
    with open(temp, "w") as handle:
        json.dump(state, handle, indent=2)
    os.replace(temp, path_of(state["slug"]))


def merged(url):
    try:
        done = subprocess.run(["gh", "pr", "view", url, "--json", "state", "-q", ".state"], capture_output=True, text=True, timeout=20)
        return done.returncode == 0 and done.stdout.strip() == "MERGED"
    except (OSError, subprocess.SubprocessError):
        return False


def message(slug, status, pr, words=""):
    text = "worker %s reports %s" % (slug, status) + (" (%s)" % pr if pr else "") + (": " + words if words else "")
    return {"status": status, "pr": pr or "", "text": text, "at": now()}


def log_since(slug, mark):
    try:
        with open(os.path.join(base(), "logs", slug + ".log"), "rb") as handle:
            handle.seek(mark)
            return handle.read().decode("utf-8", "replace")
    except OSError:
        return ""


def outcome(state, text):
    """What a finished worker sends back, from its run record."""
    status, pr = state.get("status"), state.get("pr", "")
    if status == "done":
        return message(state["slug"], "merged" if pr and merged(pr) else "waiting", pr,
                       "" if pr and merged(pr) else "its pull request waits for review and merge")
    if status == "waiting":
        ask = state.get("waiting") or {}
        return message(state["slug"], "waiting", pr, "%s Type: %s" % (ask.get("ask", ""), " or ".join(ask.get("words") or [])))
    return message(state["slug"], "failed", pr, " ".join((state.get("finding") or text[-200:] or "see its log").split()))


def cmd_loop(args):
    state = load(args.slug)
    if not state or not args.command:
        sys.exit("REFUSED: loop needs a run record and a command after --.")
    mark = os.path.getsize(os.path.join(base(), "logs", args.slug + ".log")) if os.path.exists(os.path.join(base(), "logs", args.slug + ".log")) else 0
    code = subprocess.run(args.command, env=dict(os.environ, LOOP_ROLE="worker")).returncode
    state = load(args.slug) or state
    text = log_since(args.slug, mark)
    if state.get("status") == "running":
        state["status"], state["finding"] = "failed", state.get("finding") or "the agent ended (exit %d) without finishing: %s" % (code, " ".join(text[-200:].split()))
    found = TOKENS.findall(text)
    if found:
        state["tokens"] = dict(state.get("tokens") or {}, total=int(found[-1].replace(",", "")))
    state["report"] = outcome(state, text)
    save(state, state["report"]["text"])
    return 0


def cmd_report(args):
    state = load(args.slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % args.slug)
    state["report"] = message(args.slug, args.status, args.pr or state.get("pr", ""), args.words)
    save(state, state["report"]["text"])
    return 0


def cmd_met(args):
    state = load(args.slug)
    if not state:
        sys.exit("REFUSED: no run named %s." % args.slug)
    state["met"] = sorted(set(state.get("met") or []) | set(args.lines))
    save(state, "done lines met: %s" % ", ".join(map(str, state["met"])))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    item = sub.add_parser("loop")
    item.add_argument("slug")
    item.add_argument("command", nargs=argparse.REMAINDER)
    item = sub.add_parser("report")
    item.add_argument("slug")
    item.add_argument("status", choices=["merged", "failed", "waiting"])
    item.add_argument("--pr", default="")
    item.add_argument("--words", default="")
    item = sub.add_parser("met")
    item.add_argument("slug")
    item.add_argument("lines", nargs="+", type=int)
    args = parser.parse_args()
    if args.cmd == "loop" and args.command[:1] == ["--"]:
        args.command = args.command[1:]
    return globals()["cmd_" + args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
