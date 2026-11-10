"""Which feature a finding is about, so file.py puts its issue on that feature's milestone (HLT-4). Read-only.

A feature is a page of .loop/docs.tsv other than Home; its milestone has the page's name. In order:
  a review finding's own feature (only when it names a docs.tsv page)
  a page name (the subject or evidence), such as a stale page
  a path (the subject or evidence): the page whose docs.tsv path is the longest prefix of it, or docs/wiki/<Page>.md
  a requirement id: the page that defines it
  a regression row id: the page of the requirement its row guards
  an issue #N: that issue's milestone, when it is a feature's
Backlog when nothing fits.
"""
import os
import re

import ghcache
from rules_trace import defined, table

BACKLOG = "Backlog"
ID = re.compile(r"^[A-Z]{2,5}-\d+[a-z]?$")


def features(root):
    """{page: [paths]} from .loop/docs.tsv, Home left out."""
    out = {}
    try:
        with open(os.path.join(root, ".loop", "docs.tsv")) as handle:
            for line in handle:
                if line.strip() and not line.startswith("#"):
                    page, _, paths = line.rstrip("\n").partition("\t")
                    if page.strip() and page.strip() != "Home":
                        out[page.strip()] = [p.strip().rstrip("/") for p in paths.split(",") if p.strip()]
    except OSError:
        pass
    return out


def by_path(path, pages):
    path = path.split(":")[0].strip()
    if path.startswith("/workflow-"):  # a command: /workflow-docs init is about skills/workflow-docs
        path = "skills/" + path.split()[0].lstrip("/")
    path = path[2:] if path.startswith("./") else path.lstrip("/")
    best, length = None, -1
    for page, paths in pages.items():
        for prefix in paths + ["docs/wiki/%s.md" % page]:
            if (path == prefix or path.startswith(prefix + "/")) and len(prefix) > length:
                best, length = page, len(prefix)
    return best


def feature_of(root, item, cache=None):
    """The feature (page name) a finding is about, or Backlog."""
    cache = cache if cache is not None else {}
    pages = cache.setdefault("pages", features(root))
    named = item.get("feature")
    if named:
        return named if named in pages else BACKLOG
    known = cache.setdefault("ids", defined(root))
    rows = cache.setdefault("rows", {r["id"]: r for r in table(root)})
    for text in (item.get("subject") or "", item.get("evidence") or ""):
        text = text.strip()
        if not text:
            continue
        if ID.match(text) and text in known:
            page = known[text][0]
            return page if page in pages else BACKLOG
        if text in rows and rows[text]["goal"] in known:
            page = known[rows[text]["goal"]][0]
            return page if page in pages else BACKLOG
        if text.startswith("#") and text[1:].isdigit():
            found, _ = ghcache.issues(root)
            stone = next((i.get("milestone") for i in found or [] if str(i["number"]) == text[1:]), None)
            if stone in pages:
                return stone
            continue
        page = text if text in pages else by_path(text, pages)  # a page-level finding (docs stale) names its page
        if page:
            return page
    return BACKLOG
