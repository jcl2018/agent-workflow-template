"""Traceability and Consistency rules (groups.py), and the page reader the other rule modules share. Read-only.

  issue-milestone  an open issue with no milestone (WARN; INFO when gh is not available here)
  row-requirement  a regression row whose goal names no requirement on any page and is not a done line slug:N (FAIL)
  ids-unique       a requirement id defined on two pages (FAIL)
  refs             a page naming an id of a known prefix (HLT-12 when HLT ids exist) that no page defines (FAIL)
  usage-readme     a /workflow-<skill> <verb> in the README that no page's Usage names (WARN)
Each rule's negative control is in CONTROLS (controls.py runs it). Rows carry an evidence field of stable citations.
"""
import glob
import json
import os
import re

import ghcache

LINE = re.compile(r"^- ([A-Z]{2,5}-\d+[a-z]?): ", re.M)
SLUG_N = re.compile(r"^[a-z0-9][a-z0-9-]*:\d+$")
COMMAND = re.compile(r"/workflow-[a-z]+ [a-z][a-z-]*")


def row(state, family, subject, rule, detail, fix="", evidence=""):
    return {"state": state, "family": family, "subject": subject, "rule": rule, "detail": detail, "fix": fix,
            "evidence": evidence or subject}


def wiki(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir") or "docs/wiki"
    except (OSError, ValueError, AttributeError):
        folder = "docs/wiki"
    return os.path.join(root, folder)


def pages(root):
    """{page name: text} of the wiki pages."""
    out = {}
    for path in sorted(glob.glob(os.path.join(wiki(root), "*.md"))):
        with open(path, errors="replace") as handle:
            out[os.path.basename(path)[:-3]] = handle.read()
    return out


def defined(root):
    """{requirement id: [pages that define it]}."""
    out = {}
    for name, text in pages(root).items():
        for key in LINE.findall(text):
            out.setdefault(key, []).append(name)
    return out


def table(root):
    """Regression rows as dicts (id, level, command, goal, ...)."""
    names = ("id", "level", "command", "goal", "seen_red", "description", "category", "link")
    try:
        with open(os.path.join(root, ".loop", "regression.tsv")) as handle:
            lines = [line.rstrip("\n").split("\t") for line in handle if line.strip() and not line.startswith("#")]
    except OSError:
        return []
    return [dict(zip(names, cells + [""] * (8 - len(cells)))) for cells in lines]


def section(text, title):
    part = re.split(r"^## %s\s*$" % re.escape(title), text, maxsplit=1, flags=re.M)
    return part[1].split("\n## ", 1)[0] if len(part) > 1 else ""


def issue_milestone(root):
    found, why = ghcache.issues(root)
    if found is None:
        return [row("INFO", "traceability", "issues", "issue-milestone", why)]
    return [row("WARN", "traceability", "#%d" % i["number"], "issue-milestone", "open issue with no milestone: %s" % (i["title"] or "")[:80],
                "move it to its feature's milestone (milestone.py move)", "#%d" % i["number"])
            for i in found if i.get("state") == "open" and not i.get("milestone")]


def row_requirement(root):
    known = defined(root)
    out = []
    for item in table(root):
        goal = item["goal"].strip()
        if goal and goal != "-" and not SLUG_N.match(goal) and goal not in known:
            out.append(row("FAIL", "traceability", item["id"], "row-requirement", "row guards %s, which no page defines" % goal,
                           "fix the row's goal, or add the requirement", item["id"]))
    return out


def ids_unique(root):
    return [row("FAIL", "consistency", key, "ids-unique", "defined on %s" % ", ".join(names), "give each requirement one page", key)
            for key, names in sorted(defined(root).items()) if len(names) > 1]


def refs(root):
    known = defined(root)
    prefixes = {key.split("-")[0] for key in known}
    out, seen = [], set()
    for name, text in pages(root).items():
        for key in re.findall(r"\b([A-Z]{2,5}-\d+[a-z]?)\b", text):
            if key.split("-")[0] in prefixes and key not in known and (name, key) not in seen:
                seen.add((name, key))
                out.append(row("FAIL", "consistency", key, "refs", "page %s names %s, which no page defines" % (name, key),
                               "fix the reference or add the requirement", "%s:%s" % (name, key)))
    return out


def usage_readme(root):
    try:
        with open(os.path.join(root, "README.md"), errors="replace") as handle:
            readme = handle.read()
    except OSError:
        return []
    usage = "\n".join(section(text, "Usage") for text in pages(root).values())
    return [row("WARN", "consistency", command, "usage-readme", "the README names %s and no page's Usage does" % command,
                "add it to its page's Usage, or drop it from the README", command)
            for command in sorted(set(COMMAND.findall(readme))) if command not in usage]


FUNCTIONS = {"issue-milestone": issue_milestone, "row-requirement": row_requirement, "ids-unique": ids_unique,
             "refs": refs, "usage-readme": usage_readme}


def _c():
    import controls
    return controls


def f_issue_milestone(root):
    c = _c(); c.repo(root)
    c.write(root, ".gh.json", json.dumps([{"number": 7, "title": "loose", "state": "open", "labels": [], "milestone": None}]))
    os.environ["LOOP_HEALTH_GH_FIXTURE"] = os.path.join(root, ".gh.json")
    ghcache.CACHE.clear()


def f_row_requirement(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\tgoal\nr1\tland\ttrue\tZZZ-9\n")


def f_ids_unique(root):
    c = _c(); c.repo(root)
    for name in ("One", "Two"):
        c.write(root, "docs/wiki/%s.md" % name, "# %s\n\n## Requirements\n\n- AB-1: **Unreviewed** x.\n" % name)


def f_refs(root):
    c = _c(); c.repo(root)
    c.write(root, "docs/wiki/One.md", "# One\n\n## Requirements\n\n- AB-1: **Unreviewed** see AB-9.\n")


def f_usage_readme(root):
    c = _c(); c.repo(root)
    c.write(root, "README.md", "Run /workflow-toy frob to frob.\n")
    c.write(root, "docs/wiki/One.md", "# One\n\n## Usage\n\n- nothing here\n")


CONTROLS = {"issue-milestone": ("traceability", "issue-milestone", f_issue_milestone),
            "row-requirement": ("traceability", "row-requirement", f_row_requirement),
            "ids-unique": ("consistency", "ids-unique", f_ids_unique), "refs": ("consistency", "refs", f_refs),
            "usage-readme": ("consistency", "usage-readme", f_usage_readme)}
