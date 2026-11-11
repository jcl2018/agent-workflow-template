"""Key helpers for file.py: what an older health called a finding, the hash of its evidence, and which open issue
already covers it. Pure functions; no gh."""
import hashlib
import re

import ghcache

OLD = {"requirements": "criteria", "performance": "cost", "traceability": "criteria", "tests": "criteria"}
OLD_RULE = {"scripts": "limit", "seen-red": "proof", "done": "rows"}


def key_of(item):
    return "%s:%s:%s" % (item["family"], item["subject"], item["rule"])


def legacy(item):
    """The keys an older health wrote for this finding."""
    family, rule = OLD.get(item["family"]), OLD_RULE.get(item["rule"], item["rule"])
    out = ["%s:%s:%s" % (family, item["subject"], rule)] if family else []
    if item["family"] == "size":
        out.append("size:%s:limit" % item["subject"])
    return out


def evidence_of(item):
    """sha8 of the finding's identity and stable citations; never details, ages, counts or sizes (review: normalized)."""
    cites = item.get("evidence") or item["subject"]
    if item["family"] == "review":
        cites = ",".join(sorted({re.sub(r":\d+(-\d+)?$", "", c.strip()) for c in cites.split(",") if c.strip()}))
    return hashlib.sha1(("%s|%s" % (key_of(item), cites)).encode()).hexdigest()[:8]


def title_of(stone):
    """A milestone's title from gh's {"title": ...}, ghcache's plain title, or nothing."""
    return (stone.get("title") if isinstance(stone, dict) else stone) or ""


def covering(item, issues, stone):
    """An open non-health issue on the finding's milestone naming its subject as a whole token."""
    subject = (item.get("evidence") or item["subject"]).split(",")[0].strip()
    if not re.search(r"[/.]|^[A-Z]{2,5}-\d+", subject) or len(subject) < 4:  # a path or an id, never a plain word
        return None
    pattern = re.compile(r"(?<![\w./-])%s(?![\w/-])" % re.escape(subject))
    for issue in issues:
        if issue.get("state") == "open" and not ghcache.is_health(issue) and issue.get("milestone") == stone and \
                pattern.search("%s\n%s" % (issue.get("title") or "", issue.get("body") or "")):
            return issue
    return None
