"""The owner's words from a record in owner-words.tsv, for criteria.py review|unreview --owner-record ID.

The operation session writes the record (sessions.py owner-words "TEXT" --ids A,B in workflow-monitoring); a worker never
does. A record counts for the IDs and pages it lists, once for review and once for unreview, and the words it gives are
logged in reviews.tsv as "record ID: TEXT".
"""
import json
import os
import sys


def rows(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return [line.rstrip("\n").split("\t") for line in handle]
    except OSError:
        return []


def words(args, git):
    """The record's text, or exit with nothing changed: no such record, an ID or page it does not cover, or a record
    already used for this command."""
    common = os.path.join(os.path.abspath(git("rev-parse", "--git-common-dir")), "loop")
    found = [row for row in rows(os.path.join(common, "owner-words.tsv")) if len(row) == 5 and row[0] == args.owner_record]
    if not found:
        sys.exit("REFUSED: no owner-words record %s. Nothing was changed. Fix: the operation session records the owner's "
                 "message with sessions.py owner-words." % args.owner_record)
    record = found[-1]
    left = sorted(set(args.ids) - set(record[4].split(",")))
    if left:
        sys.exit("REFUSED: record %s does not cover %s (it covers %s). Nothing was changed." % (
            args.owner_record, ", ".join(left), record[4]))
    for row in rows(os.path.join(common, "reviews.tsv")):
        if len(row) > 3 and row[1] == args.command and row[3].startswith("record %s:" % args.owner_record):
            sys.exit("REFUSED: record %s was already used for %s. Nothing was changed. Fix: the operation session "
                     "records the owner's message again." % (args.owner_record, args.command))
    return "record %s: %s" % (args.owner_record, " ".join(json.loads(record[3]).split()))
