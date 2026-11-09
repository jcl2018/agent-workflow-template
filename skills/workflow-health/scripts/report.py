"""The formal health report: pure formatting, no I/O. Used by health.py check and judge.

The report is a header naming every group run and any skipped, each group in a fixed order with every rule it checked
(PASS, WARN, FAIL or UNREAD, a fix on each line that is not a pass), then one verdict. A rule that gave no row is a
pass only when its group ran; a rule that could not read its data is UNREAD, never a pass. The Cost group is shown
as performance. Internal family names (cost) are unchanged: only the display differs.
"""

ORDER = ("size", "criteria", "docs", "hygiene", "cost", "mine")  # the fixed order of the groups in the report
SHOWN = {"cost": "performance", "mine": "Mine"}
LINE = {"cost": "performance"}  # a line names its group; only Cost is renamed
# The rules each group checks. A row's rule label says which of them it speaks for (RULE_OF); a rule with no row passes.
RULES = {"size": ("limit",), "criteria": ("rows", "done-lines", "defect-tests"), "docs": ("check",),
         "hygiene": ("findings", "waiting", "branches"), "cost": ("cost",), "mine": ()}
RULE_OF = {"sync": "rows", "proof": "rows", "stale": "check", "missing": "check", "open": "findings", "run": "waiting",
           "merged": "branches", "branch": "branches", "time": "cost", "tokens": "cost"}


def shown(name):
    return SHOWN.get(name, name)


def rule_of(item):
    if item["family"] == "criteria" and item["subject"] == "done-lines":
        return "done-lines"
    return RULE_OF.get(item["rule"], item["rule"])


def line_of(item):
    text = "%s %s %s %s: %s" % (item["state"], LINE.get(item["family"], item["family"]), item["subject"], item["rule"], item["detail"])
    return text + (" -> fix: " + item["fix"] if item["fix"] else "")


def complete(rows, ran):
    """Rows plus a PASS row for each rule of a group that ran and gave none."""
    out = list(rows)
    for name in ran:
        seen = {rule_of(item) for item in rows if item["family"] == name}
        for rule in RULES[name]:
            if rule not in seen:
                out.append({"state": "PASS", "family": name, "subject": rule, "rule": rule, "detail": "no problem found", "fix": ""})
    return out


def groups(rows, asked):
    """(ran, skipped): groups run in order, and (name, why) for each not run."""
    ran, skipped = [], []
    for name in ORDER:
        mine = [item for item in rows if item["family"] == name]
        if asked and name not in asked:
            skipped.append((name, "not asked"))
        elif name == "mine" and mine and all(item["state"] == "INFO" for item in mine):
            skipped.append((name, "no private rules set"))
        else:
            ran.append(name)
    return ran, skipped


def build(rows, asked=None):
    """(lines, counts, green, verdict, ran, skipped) for the fixed template."""
    ran, skipped = groups(rows, asked)
    rows = complete(rows, [name for name in ran if name != "mine"])
    counts = {state: sum(1 for item in rows if item["state"] == state) for state in ("PASS", "WARN", "FAIL", "UNREAD")}
    green = not counts["FAIL"] and not counts["UNREAD"]
    verdict = "HEALTH: %s (%d pass, %d warn, %d fail, %d unread)" % (
        "green" if green else "not green", counts["PASS"], counts["WARN"], counts["FAIL"], counts["UNREAD"])
    head = "groups run: %s; skipped: %s" % (", ".join(shown(n) for n in ran) or "none",
                                            ", ".join("%s (%s)" % (shown(n), why) for n, why in skipped) or "none")
    out = ["HEALTH REPORT", head]
    for name in ORDER:
        group = [item for item in rows if item["family"] == name]
        if group:
            out.append("== %s%s ==" % (shown(name), " (skipped)" if name not in ran else ""))
            out += [line_of(item) for item in group]
    return out + [verdict], counts, green, verdict, [shown(n) for n in ran], [shown(n) for n, _ in skipped], rows
