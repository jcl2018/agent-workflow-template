"""When a requirement with no regression row fails health (HLT-2, REG-1, DOC-1; issue 118).

A requirement with no passing test shows as not enforced. Health warns while it is new and fails only when it stays not
enforced: an Unreviewed requirement warns; a Reviewed one warns for GRACE days after its Reviewed date, then fails.
The date comes from the requirement's own line on its wiki page, so no goal mapping is needed.


The defect-tests rule is here too (defects: closed, guarded, missing): every closed issue or finding needs a regression
row of category defect. A closed issue or finding is one a merged goal says it fixed ("fixes #35", "fixes finding:SLUG"
in .loop/goals/*.md), or a line of .loop/findings.md marked [closed]. A defect row links it: its link holds the issue's
URL or finding:SLUG. Reads files only: health check makes no gh call.
"""
import datetime
import glob
import json
import os
import re

GRACE = 7  # days a Reviewed requirement may stay not enforced (HLT-2: "none stays not enforced over 7 days")


def stamp(root, key):
    """('Reviewed', date), ('Unreviewed', None), or (None, None) when no page holds the requirement."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir", "docs/wiki")
    except (OSError, ValueError):
        folder = "docs/wiki"
    line = re.compile(r"^- %s: \*\*(Unreviewed|Reviewed (\d{4}-\d\d-\d\d))\*\*" % re.escape(key), re.M)
    for page in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
        with open(page) as handle:
            found = line.search(handle.read())
        if found:
            return ("Unreviewed", None) if found.group(1) == "Unreviewed" else ("Reviewed", found.group(2))
    return None, None


def row(root, key, make, today=None):
    """The health row for requirement `key` with no regression row, made with health.py's row()."""
    mark, day = stamp(root, key)
    fix = "add a row with regression.py add"
    if mark == "Unreviewed":
        return make("WARN", "criteria", key, "rows", "not enforced: no regression row yet (Unreviewed)", fix)
    if mark == "Reviewed":
        try:
            age = ((today or datetime.date.today()) - datetime.date.fromisoformat(day)).days
        except ValueError:
            return make("FAIL", "criteria", key, "rows", "Reviewed date %s is not a real date" % day, "fix the date on its line")
        if age <= GRACE:
            return make("WARN", "criteria", key, "rows", "not enforced, %d days since Reviewed %s (fails after %d)"
                        % (age, day, GRACE), fix)
        return make("FAIL", "criteria", key, "rows", "not enforced for %d days since Reviewed %s, over %d" % (age, day, GRACE), fix)
    return make("FAIL", "criteria", key, "rows", "criterion has no regression row", fix)


VERB = r"\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+"
FIXES = re.compile(VERB + r"(?:issue\s+)?#(\d+)|" + VERB + r"finding:([a-z0-9][a-z0-9-]*)", re.I)


def read(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return ""


def closed(root):
    """Ref -> where it was closed: '#N' for an issue, 'finding:SLUG' for a finding."""
    found = {}
    for path in sorted(glob.glob(os.path.join(root, ".loop", "goals", "*.md"))):
        if path.endswith(".design.md"):
            continue
        for number, finding in FIXES.findall(read(path)):
            found.setdefault("#" + number if number else "finding:" + finding.lower(), os.path.basename(path)[:-3])
    for line in read(os.path.join(root, ".loop", "findings.md")).splitlines():
        named = re.match(r"^- ([a-z0-9][a-z0-9-]*):.*\[closed\]", line)
        if named:
            found.setdefault("finding:" + named.group(1), "findings.md")
    return found


def guarded(root):
    """The links of the defect rows, as one text."""
    cells = [line.rstrip("\n").split("\t") + [""] * 8 for line in read(os.path.join(root, ".loop", "regression.tsv")).splitlines()
             if line.strip() and line[0] != "#"]
    return " ".join(c[7] for c in cells if c[6] == "defect")


def missing(root):
    """(ref, source) for each closed issue or finding no defect row links."""
    links = guarded(root)
    out = []
    for ref, source in closed(root).items():
        pattern = r"(?:issues/|#)%s\b" % ref[1:] if ref[0] == "#" else re.escape(ref) + r"(?![\w-])"
        if not re.search(pattern, links):
            out.append((ref, source))
    return out
