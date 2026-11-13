"""The owner's own messages, recorded by the operation session for workers to use.

usage: sessions.py owner-words "TEXT" --ids DOC-1,HLT-2

One line per message in <git common dir>/loop/owner-words.tsv, tab separated: id (o1, o2, ...), UTC time, the operation
session's id ($LOOP_OPERATION_SESSION, else "operation"), the exact text as a JSON string (so tabs, quotes and new lines
survive), and the requirement IDs or page names the message covers. Only the operation role writes it: a worker
(LOOP_ROLE=worker) is refused. `criteria.py review|unreview --user --owner-record ID` reads it (workflow-docs).
"""
import datetime
import json
import os
import subprocess
import sys


def path():
    top = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    return os.path.join(os.path.abspath(top), "loop", "owner-words.tsv")


def add(text, ids):
    """Append the message and print OWNER-WORDS <id> <ids>; refuse a worker, an empty message or no ids."""
    if os.environ.get("LOOP_ROLE") == "worker":
        sys.exit("REFUSED: only the operation session records the owner's words; a worker never does. Nothing was written.")
    ids = [item.strip() for item in ids.split(",") if item.strip()]
    if not text.strip() or not ids:
        sys.exit("REFUSED: give the owner's exact message and --ids (requirement IDs or page names it covers). Nothing was written.")
    where = path()
    os.makedirs(os.path.dirname(where), exist_ok=True)
    count = 0
    if os.path.exists(where):
        with open(where, encoding="utf-8") as handle:
            count = sum(1 for line in handle if line.strip())
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(where, "a", encoding="utf-8") as handle:
        handle.write("o%d\t%s\t%s\t%s\t%s\n" % (count + 1, stamp, os.environ.get("LOOP_OPERATION_SESSION") or "operation",
                                              json.dumps(text, ensure_ascii=False), ",".join(ids)))
    print("OWNER-WORDS o%d covers %s" % (count + 1, ",".join(ids)))
    return 0
