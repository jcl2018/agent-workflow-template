"""When a requirement with no regression row fails health (HLT-2, REG-1, DOC-1; issue 118).

A requirement with no passing test shows as not enforced. Health warns while it is new and fails only when it stays not
enforced: an Unreviewed requirement warns; a Reviewed one warns for GRACE days after its Reviewed date, then fails.
The date comes from the requirement's own line on its wiki page, so no goal mapping is needed.
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
        folder = json.load(open(os.path.join(root, ".loop", "config.json"))).get("wiki_dir", "docs/wiki")
    except (OSError, ValueError):
        folder = "docs/wiki"
    line = re.compile(r"^- %s: \*\*(Unreviewed|Reviewed (\d{4}-\d\d-\d\d))\*\*" % re.escape(key), re.M)
    for page in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
        found = line.search(open(page).read())
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
        age = ((today or datetime.date.today()) - datetime.date.fromisoformat(day)).days
        if age <= GRACE:
            return make("WARN", "criteria", key, "rows", "not enforced, %d days since Reviewed %s (fails after %d)"
                        % (age, day, GRACE), fix)
        return make("FAIL", "criteria", key, "rows", "not enforced for %d days since Reviewed %s, over %d" % (age, day, GRACE), fix)
    return make("FAIL", "criteria", key, "rows", "criterion has no regression row", fix)
