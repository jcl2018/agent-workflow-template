"""Suggestions: advisory text, never findings. Pure text matching on the wiki pages: no model, no network.

Criteria are the `- ID: text` lines on the pages mapped in .loop/docs.tsv. Two criteria overlap when their word sets
share at least OVERLAP of the smaller set; they conflict when they overlap and exactly one has a negation word.
Output is the same for the same repo.
"""
import glob
import os
import re

OVERLAP = 0.6
NEGATIONS = {"not", "never", "no", "nothing", "without", "cannot", "isnt", "doesnt", "wont"}
STOP = {"a", "an", "the", "is", "are", "and", "or", "of", "to", "in", "it", "on", "with", "for", "that", "any", "each", "one"}
ORDER = {"FAIL": 0, "UNREAD": 1, "WARN": 2}


def words(text):
    return re.findall(r"[a-z]+", text.lower().replace("'", ""))


def pages(root):
    found, path = [], os.path.join(root, ".loop", "docs.tsv")
    try:
        with open(path) as handle:
            for line in handle:
                name = line.split("\t")[0].strip()
                if name and not line.startswith("#") and name != "Home":
                    found.append(name)
    except OSError:
        pass
    return sorted(found)


def criteria(root, page):
    try:
        with open(os.path.join(root, "docs", "wiki", page + ".md")) as handle:
            text = handle.read()
    except OSError:
        return []
    body = text.split("## Criteria", 1)[-1].split("\n## ", 1)[0] if "## Criteria" in text else ""
    return [(m.group(1), m.group(2)) for m in re.finditer(r"^- ([A-Z]+-\d+[a-z]?): (.*)$", body, re.M)]


def suggestions(root, rows):
    lines, items = [], []
    for page in pages(root):
        found = criteria(root, page)
        if not found:
            lines.append("missing: feature %s has no criterion -> add a Criteria section with at least one line" % page)
        items += found
    pairs = []
    for i, (a_id, a_text) in enumerate(items):
        for b_id, b_text in items[i + 1:]:
            a, b = set(words(a_text)) - STOP, set(words(b_text)) - STOP
            na, nb = bool(a & NEGATIONS), bool(b & NEGATIONS)
            a, b = a - NEGATIONS, b - NEGATIONS
            if a and b and len(a & b) / min(len(a), len(b)) >= OVERLAP:
                pairs.append("%s: %s and %s say much the same%s -> merge or reword one" % (
                    "conflict" if na != nb else "overlap", a_id, b_id, " in opposite ways" if na != nb else ""))
    lines += sorted(pairs)
    worst = sorted((r for r in rows if r["state"] in ORDER), key=lambda r: (ORDER[r["state"]], r["family"], r["subject"]))
    steps = ["next %d: %s %s %s -> %s" % (n, r["state"], r["family"], r["subject"], r["fix"] or "look into it")
             for n, r in enumerate(worst, 1)]
    return lines, steps
