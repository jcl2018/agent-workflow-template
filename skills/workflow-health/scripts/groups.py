"""The twelve health groups (HLT-2), each with the angle its rules take, in report order, plus Mine.

Every rule belongs to one group and has one name. A row's family is its group's slug and its rule label is the rule's
name; older labels map through LABELS. Exactly twelve groups: adding one means retiring one or raising the cap on purpose.
"""

GROUPS = (
    ("requirements", "Requirements", "my angle: is every promise I approved proven?", ("rows", "proof", "done")),
    ("traceability", "Traceability", "an auditor's angle: can I follow any work end to end?",
     ("defect-tests", "issue-milestone", "row-requirement")),
    ("consistency", "Consistency", "a reader's angle: do the pages agree?", ("ids-unique", "refs", "usage-readme")),
    ("docs", "Docs", "a newcomer's angle: does each page match the template and the code?", ("docs-check",)),
    ("freshness", "Freshness", "my angle when I come back: is anything out of date?", ("nightly", "unreleased", "finding-age")),
    ("tests", "Tests", "a skeptic's angle: do the tests prove anything?", ("seen-red", "skipped", "network")),
    ("performance", "Performance", "my clock's and my wallet's angle: is it fast and cheap enough?",
     ("cost", "test-time", "check-time")),
    ("security", "Security and privacy", "a leak's angle: can anything private escape?",
     ("private", "scan-hook", "workflow-permissions")),
    ("size", "Size", "a maintainer's angle: can someone still read this?", ("scripts", "skill-lines", "requirements-per-page")),
    ("hygiene", "Hygiene", "a janitor's angle: is anything left lying around?",
     ("findings", "waiting", "branches", "worktrees", "local-branches", "idle-sessions")),
    ("adoption", "Adoption", "another repo's angle: would this work installed fresh?",
     ("config", "checks-run-tests", "template-version", "scheduled")),
    ("controls", "Controls", "the checker's own angle: can each rule fire?", ()),
)
MINE = ("mine", "Mine", "my private angle", ())
MAX_GROUPS = 12
assert len(GROUPS) == MAX_GROUPS, "exactly %d groups: retire one before adding another" % MAX_GROUPS

ORDER = tuple(g[0] for g in GROUPS[:-1]) + ("mine", "controls")  # Mine reports just before Controls
TITLE = {g[0]: g[1] for g in GROUPS + (MINE,)}
ANGLE = {g[0]: g[2] for g in GROUPS + (MINE,)}
RULES_OF = {g[0]: g[3] for g in GROUPS + (MINE,)}
GROUP_OF = {rule: g[0] for g in GROUPS for rule in g[3]}
RULES = tuple(rule for g in GROUPS for rule in g[3])  # every rule; each needs a negative control (controls.py)
ALIASES = {"criteria": "requirements", "cost": "performance"}  # older --group names, kept for one release
# Older row labels -> the rule they speak for, within their group.
LABELS = {"sync": "rows", "done-lines": "done", "open": "findings", "run": "waiting", "merged": "branches",
          "branch": "branches", "time": "cost", "tokens": "cost", "limit": "scripts"}


def heading(slug, skipped=False):
    return "== %s (%s)%s ==" % (TITLE[slug], ANGLE[slug], " (skipped)" if skipped else "")


def rule_of(item):
    """The rule a row speaks for."""
    family, label = item["family"], item["rule"]
    rules = RULES_OF.get(family, ())
    if label in rules:
        return label
    if family == "docs":  # docs.py's kinds (stale, missing, ...) all speak for docs-check
        return "docs-check"
    if family == "requirements" and item.get("subject") == "done-lines":
        return "done"
    return LABELS.get(label, label)
