#!/usr/bin/env python3
"""Full auto (MON-11): the operation session answers a worker's routine decision with its recommended option.

usage: auto.py pass [--dry-run]  decide each waiting goal's new question once (operate.py runs it every pass)
       auto.py since ISO       the decisions logged after a time (the check-in lists those since the last one)
       auto.py decide-text     read a question on stdin, print AUTO or WAITS with why (for tests and by hand)

`full_auto` in .loop/config.json, on by default, is read at each decision: turning it off applies at the next one.
Only the operation session answers: a worker's `sessions.py report --status waiting --ask Q --words W ... --recommend W
--kind K` just records the question. A decision is answered only when all of these hold, else it waits under Needs
you with its reason (logged once per question):
- its kind is `routine` (destructive, money, security, owner, a missing or an unknown kind all wait);
- it names a recommended answer that is one of its words;
- no risky word appears in the question or the answer (whole words with their endings, case ignored: delete, remove,
  drop, rm, wipe, truncate, discard, reset --hard, git clean, force, overwrite, rename, publish, release, deploy,
  merge, push, pay, purchase, billing, cost, spend, money, permission, access, token, secret, credential, password, key,
  license, migration, schema, auth, security), nor a path matching `risky_paths`;
- the owner hasn't answered that goal before: an owner answer on the goal sends every later question to the owner
  (answers.jsonl, source owner), so full auto never answers over the owner's word.
An answer goes through `operate.py send SLUG WORDS --source auto` (the inbox and the session message, as an owner answer
does); the worker runs goal.py answer as usual. Each decision is appended to <git common dir>/loop/auto.log as
`time | slug | AUTO|WAITS | question | answer | reason`; the run's waiting.auto marks it decided. The check-in lists
each auto answer with the words that revert it: `operate.py send SLUG "<other words>"` before the worker moves on.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import board_status as bs  # noqa: E402
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")  # no prompt ever blocks

KINDS = ("routine", "destructive", "money", "security", "owner")
END = r"(?:e|es|ed|ing|s|ion|ions|al|als)?"  # the endings a risky word may take: delete, deletes, deleted, deleting
WORDS = ["delet", "remov", "drop", "dropp", "rm", "wip", "truncat", "discard", "forc", "overwrit", "overwritten", "renam",
         "publish", "releas", "deploy", "deployment", "merg", "push", "pay", "payment", "purchas", "billing", "cost",
         "spend", "spent", "money", "permission", "access", "token", "secret", "credential", "password", "key", "licens",
         "migrat", "schema", "auth", "authenticat", "authoriz", "secur", "security", "rebas", "amend", "squash", "eras",
         "destroy", "uninstall", "kill", "unlink", "rmdir", "removal", "revert", "rewrit", "rewritten"]
RISKY = re.compile(r"\b(?:%s)%s\b|reset\s+--hard|git\s+clean" % ("|".join(WORDS), END), re.I)


def top():
    return bs.git("rev-parse", "--show-toplevel")


def loop_dir(root):
    common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, capture_output=True, text=True).stdout.strip()
    return os.path.join(os.path.abspath(os.path.join(root, common)), "loop")


def config(root):
    found = bs.read_json(os.path.join(root, ".loop", "config.json"))
    return found if isinstance(found, dict) else {}


def key_of(text):
    return " ".join(str(text or "").lower().split())


def owner_answered(folder, slug):
    try:
        with open(os.path.join(folder, "answers.jsonl")) as handle:
            for line in handle:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if item.get("slug") == slug and item.get("source", "owner") == "owner":
                    return True
    except OSError:
        pass
    return False


def why_not(waiting, cfg, answered=False):
    """'' when full auto may answer this decision, else why it waits."""
    if cfg.get("full_auto", True) is False:
        return "full_auto is off"
    kind, rec = waiting.get("kind") or "", waiting.get("recommend") or ""
    if kind not in KINDS:
        return "no kind given" if not kind else "unknown kind %s" % kind
    if kind != "routine":
        return "a %s decision is the owner's" % kind
    if not rec or rec not in (waiting.get("words") or []):
        return "no recommended answer among its words"
    said = " ".join([str(waiting.get("ask") or ""), rec])
    hit = RISKY.search(said)
    if hit:
        return "it mentions %s" % hit.group(0).lower()
    for pattern in cfg.get("risky_paths") or []:
        try:
            if re.search(pattern, said):
                return "it names a risky path (%s)" % pattern
        except re.error:
            continue
    if answered:
        return "the owner has answered this goal before"
    return ""


def log(folder, slug, verdict, waiting, answer, reason, at):
    line = " | ".join(str(x).replace("|", "/") for x in (at, slug, verdict, key_of(waiting.get("ask"))[:200], answer or "-", reason))
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "auto.log"), "a") as handle:
        handle.write(line.replace("\n", " ") + "\n")
    return line


def decide_all(root=None, now=None, dry=False):
    """One pass: each waiting goal's newest question decided once. Returns the log lines written (dry: would write)."""
    root = root or top()
    folder, cfg = loop_dir(root), config(root)
    at = now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = []
    runs_dir = os.path.join(folder, "runs")
    for name in sorted(os.listdir(runs_dir)) if os.path.isdir(runs_dir) else []:
        path = os.path.join(runs_dir, name)
        run = bs.read_json(path) if name.endswith(".json") else None
        if not isinstance(run, dict) or run.get("status") != "waiting" or not isinstance(run.get("waiting"), dict):
            continue
        waiting = run["waiting"]
        if waiting.get("auto"):
            continue
        reason = why_not(waiting, cfg, owner_answered(folder, run.get("slug")))
        if reason == "full_auto is off":
            continue  # re-read at the next decision; nothing is marked, so turning it on later still answers
        if dry:
            out.append("WOULD %s %s: %s" % ("WAIT" if reason else "ANSWER", run["slug"], reason or waiting["recommend"]))
            continue
        if reason:
            out.append(log(folder, run["slug"], "WAITS", waiting, "", reason, at))
            waiting["auto"] = {"verdict": "waits", "why": reason, "at": at}
        else:
            words = waiting["recommend"]
            sent = subprocess.run([sys.executable, os.path.join(HERE, "operate.py"), "send", run["slug"], words, "--source", "auto"],
                                  cwd=root, capture_output=True, text=True)
            if sent.returncode:
                out.append(log(folder, run["slug"], "WAITS", waiting, "", "the answer could not be sent", at))
                continue  # not marked: the next pass tries again
            out.append(log(folder, run["slug"], "AUTO", waiting, words, "routine, recommended", at))
            waiting["auto"] = {"verdict": "answered", "words": words, "at": at}
        fresh = bs.read_json(path)
        if isinstance(fresh, dict) and fresh.get("status") == "waiting" and key_of((fresh.get("waiting") or {}).get("ask")) == key_of(waiting.get("ask")):
            fresh["waiting"]["auto"] = waiting["auto"]
            tmp = path + ".%d.tmp" % os.getpid()
            with open(tmp, "w") as handle:
                json.dump(fresh, handle, indent=2)
            os.replace(tmp, path)
    return out


def since(root, stamp):
    try:
        with open(os.path.join(loop_dir(root), "auto.log")) as handle:
            return [line.rstrip("\n") for line in handle if line[:20] > stamp]
    except OSError:
        return []


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    item = sub.add_parser("pass")
    item.add_argument("--dry-run", action="store_true", help="print what would be answered or sent to you, change nothing")
    item = sub.add_parser("since")
    item.add_argument("stamp")
    item = sub.add_parser("decide-text")
    item.add_argument("--kind", default="")
    item.add_argument("--recommend", default="")
    item.add_argument("--words", action="append", default=[])
    args = parser.parse_args()
    if args.cmd == "decide-text":
        reason = why_not({"ask": sys.stdin.read(), "kind": args.kind, "recommend": args.recommend,
                          "words": args.words or [args.recommend]}, config(top() or "."))
        print("WAITS: " + reason if reason else "AUTO")
        return 0
    lines = since(top(), args.stamp) if args.cmd == "since" else decide_all(dry=args.dry_run)
    print("\n".join(lines) if lines else "AUTO: nothing to decide")
    return 0


if __name__ == "__main__":
    sys.exit(main())
