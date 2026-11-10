"""The formal health report: pure formatting, no I/O. Used by health.py check, judge and review.

A header naming every group run and any skipped, then each group in the fixed order (groups.py) under a heading that
states its angle, with every rule it checked (PASS, WARN, FAIL or UNREAD, a fix on each line that is not a pass), then
one verdict. A rule that gave no row passes only when its function ran; a rule whose source could not be read, or whose
function did not run, is UNREAD, never a pass (HLT-3).
"""
import groups as G

ORDER = G.ORDER
RULES = dict(G.RULES_OF)
SOURCE = {"rows": "sync", "proof": "sync", "done": "sync", "seen-red": "sync"}  # rules read from one source


def shown(name):
    return G.TITLE.get(name, name)


def rule_of(item):
    return G.rule_of(item)


def line_of(item):
    text = "%s %s %s %s: %s" % (item["state"], item["family"], item["subject"], item["rule"], item["detail"])
    return text + (" -> fix: " + item["fix"] if item["fix"] else "")


def complete(rows, ran, ran_rules=None):
    """Rows plus one for each rule of a group that ran and gave none: PASS when its function ran, UNREAD when its source
    could not be read or it did not run."""
    out = list(rows)
    blind = {SOURCE[rule_of(item)] for item in rows if item["state"] == "UNREAD" and rule_of(item) in SOURCE}
    for name in ran:
        seen = {rule_of(item) for item in rows if item["family"] == name}
        for rule in RULES.get(name, ()):
            if rule in seen:
                continue
            if SOURCE.get(rule) in blind:
                out.append({"state": "UNREAD", "family": name, "subject": rule, "rule": rule,
                            "detail": "its source could not be read", "fix": "see the UNREAD line above"})
            elif ran_rules is not None and rule not in ran_rules:
                out.append({"state": "UNREAD", "family": name, "subject": rule, "rule": rule,
                            "detail": "the rule did not run", "fix": "see the error above"})
            else:
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


def build(rows, asked=None, ran_rules=None):
    """(lines, counts, green, verdict, ran, skipped, rows) for the fixed template."""
    ran, skipped = groups(rows, asked)
    rows = complete(rows, [name for name in ran if name != "mine"], ran_rules)
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
            out.append(G.heading(name, name not in ran))
            out += [line_of(item) for item in group]
    return out + [verdict], counts, green, verdict, [shown(n) for n in ran], [shown(n) for n, _ in skipped], rows
