"""The twelve health groups (HLT-2) and the formal health report (HLT-3), plus health.py's commands other than check.

Groups: each has the angle its rules take, in report order, plus Mine. Every rule belongs to one group and has one name; a
row's family is its group's slug and its rule label is the rule's name (older labels map through LABELS). Exactly twelve
groups: adding one means retiring one or raising the cap on purpose.

Report (pure formatting, no I/O; used by check, judge and review): a header naming every group run and any skipped, then each
group in the fixed order under a heading that states its angle, with every rule it checked (PASS, WARN, FAIL or UNREAD, a fix
on each line that is not a pass), then one verdict. A rule that gave no row passes only when its function ran; a rule whose
source could not be read, or whose function did not run, is UNREAD, never a pass (HLT-3).

Commands (each takes the health module h): review, judge, preview, file and triage. Refusals print REFUSED[code] and exit 2:
[group] an unknown group (health.py), [file] file with no group, [gh] the issues can't be listed (nothing is written), [review]
a --review FILE that isn't a saved review --json, [why] and [cap] from triage.
"""
import json
import os
import re
import sys


GROUPS = (
    ("requirements", "Requirements", "my angle: is every promise I approved proven?", ("rows", "proof", "done")),
    ("traceability", "Traceability", "an auditor's angle: can I follow any work end to end?",
     ("defect-tests", "row-requirement")),
    ("consistency", "Consistency", "a reader's angle: do the pages agree?", ("ids-unique", "refs", "usage-readme")),
    ("docs", "Docs", "a newcomer's angle: does each page match the template and the code?", ("docs-check",)),
    ("freshness", "Freshness", "my angle when I come back: is anything out of date?", ("nightly", "unreleased", "finding-age")),
    ("tests", "Tests", "a skeptic's angle: do the tests prove anything?", ("seen-red", "skipped", "network")),
    ("performance", "Performance", "my clock's and my wallet's angle: is it fast and cheap enough?",
     ("cost", "test-time", "check-time")),
    ("security", "Security and privacy", "a leak's angle: can anything private escape?",
     ("private", "scan-hook", "hooks", "workflow-permissions")),
    ("size", "Size", "a maintainer's angle: can someone still read this?", ("scripts", "skill-lines", "requirements-per-page")),
    ("hygiene", "Hygiene", "a janitor's angle: is anything left lying around?",
     ("findings", "waiting", "branches", "worktrees", "local-branches", "idle-sessions")),
    ("adoption", "Adoption", "another repo's angle: would this work installed fresh?",
     ("config", "checks-run-tests", "template-version", "scheduled", "no-fit", "agent-tools", "prompt-pointer", "migration", "milestones")),
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


def bare_agent(command):
    """True for a claude or codex command that grants its agent no tools (so it stops at its first permission prompt)."""
    allows = {"claude": ("--allowedtools", "--allowed-tools", "--permission-mode"), "codex": ("-s", "--sandbox", "--full-auto")}
    name = os.path.basename(command[0]) if isinstance(command, list) and command and isinstance(command[0], str) else ""
    return name in allows and not any(str(a).lower().split("=")[0] in allows[name] or str(a).lower().startswith("--dangerous") for a in command[1:])


def agent_tools(root):
    """agent-tools: WARN when the repo's agent_command, or the flow file's command without allowed_tools, grants no tools."""
    from defects import row
    held = lambda path: json.load(open(path)) if os.path.exists(path) else {}
    try:
        repo = held(os.path.join(root, ".loop", "config.json")).get("agent_command")
        flow = held(os.path.expanduser(os.environ.get("LOOP_FLOW") or "~/.workflow-loop/flow.json"))
        named = [n for n, bad in (("agent_command", bare_agent(repo)), ("the flow file's command", bare_agent(flow.get("command")) and not flow.get("allowed_tools"))) if bad]
    except (OSError, ValueError, AttributeError):
        return []
    return [row("WARN", "adoption", "agent_command", "agent-tools", "%s grants no tools, so a background agent stops at its first permission prompt"
                % " and ".join(named), 'set "agent_command" in .loop/config.json to add --allowedTools Bash,Read,Write,Edit (claude) or --full-auto (codex); '
                "the flow file's command and allowed_tools also run agents", "agent_command")] if named else []


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


SOURCE = {"rows": "sync", "proof": "sync", "done": "sync", "seen-red": "sync"}  # rules read from one source


def shown(name):
    return TITLE.get(name, name)


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
        for rule in RULES_OF.get(name, ()):
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
            out.append(heading(name, name not in ran))
            out += [line_of(item) for item in group]
    return out + [verdict], counts, green, verdict, [shown(n) for n in ran], [shown(n) for n, _ in skipped], rows


def refuse(code, text):
    print("REFUSED[%s]: %s" % (code, text))
    sys.exit(2)


def cmd_judge(h, args):
    """The check report, then the judge section. The verdict and exit code are the check's, whatever the judge says."""
    root = h.repo_root()
    rows = h.gather(root, None)
    text, _, green, _, _ = h.report(rows)
    print("\n".join(h.with_tests(text, root)))
    print()
    judge = h.sibling_module("judge")
    if not judge:
        print("JUDGE UNAVAILABLE: judge.py is not installed beside health.py")
        return 0 if green else 1
    try:
        answer, why = judge.ask(judge.gather(root, h.HERE, rows), root)
        found = judge.parse(answer)
        if not why and not any(found.values()):
            why = "the answer had no tagged line"
        steps = judge.suggestions(root, rows)[1]
        print("judge: " + judge.VIA[0])
        print("\n".join(judge.render(found, steps)) if not why else "JUDGE UNAVAILABLE: " + why)
    except Exception as error:  # the judge is advice: nothing it does may change the verdict
        print("JUDGE UNAVAILABLE: %s" % str(error)[:120])
    return 0 if green else 1


def cmd_review(h, args):
    """The per-feature repo review. Writes nothing; exit 0 whatever it finds (it is never part of the verdict)."""
    root = h.repo_root()
    review = h.sibling_module("judge") or refuse("review", "judge.py is not installed beside health.py")
    names = h.sibling_module("issues").features(root)
    if args.feature and args.feature not in names:
        refuse("feature", "unknown feature %s. Features: %s." % (args.feature, ", ".join(sorted(names))))
    found, dropped, why = review.review(root, args.feature)
    if args.json:
        via = getattr(h.sibling_module("judge"), "VIA", [""])[0]
        print(json.dumps({"version": 1, "findings": found, "dropped": dropped, "judge": why or "answered", "via": via}, indent=2))
    else:
        print("\n".join(review.render_review(found, dropped, why)))
    return 0


def plan_for(h, root, asked, with_judge, only=None, saved=None):
    """(file module, acts, groups) for the groups asked; exit 2 when file.py or gh can't be used."""
    filing = h.sibling_module("file") or refuse("file", "file.py is not installed beside health.py")
    groups = list(asked) if asked is not None else list(filing.DEFAULT)
    ran = set()
    checked = [g for g in groups if g in h.ORDER]
    rows = h.gather(root, checked, ran) if checked else []
    if saved:
        found = h.sibling_module("judge").load(saved)
        if found is None:
            refuse("review", "%s is not a saved review --json (version 1). Run: health.py review --json > FILE" % saved)
        rows += h.sibling_module("judge").as_rows(found)
        groups.append("review")
    judged, extra = False, []
    if with_judge and "performance" in groups:
        extra, judged = filing.saves(root, h.HERE, rows)
    issues, everything, why = filing.held_all(root)
    if issues is None:
        refuse("gh", "can't list the issues (%s). Nothing was written." % why)
    return filing, filing.plan(rows, issues, groups, extra, judged, root, ran, everything, only,
                               bool(saved) and bool(h.sibling_module("judge").answered(saved))), groups


def cmd_preview(h, args):
    """What file would do. Writes nothing and never runs Mine's private commands unless mine is named."""
    root = h.repo_root()
    asked = h.groups_of(args.group)
    if args.live:
        print("NOTE: run and preview never write, even with --live. To write, run: health.py file --group NAME", file=sys.stderr)
    filing, acts, _ = plan_for(h, root, asked, bool(asked) and "performance" in asked, args.feature, args.review)
    count = filing.preview(acts)
    print("PREVIEW: %d to write, nothing written. To write, run: health.py file --group %s" % (count, args.group or "NAME"))
    return 0


def cmd_file(h, args):
    root = h.repo_root()
    asked = h.groups_of(args.group)
    if not asked and not args.review:
        refuse("file", "file needs --group NAME[,NAME] (one of %s) or --review FILE. Run preview first." % ", ".join(h.NAMES))
    filing, acts, groups = plan_for(h, root, asked if asked else [], bool(asked) and "performance" in asked, args.feature, args.review)
    filing.apply(filing.only_open(acts) if args.open_only else acts, root, groups)
    return 0


def cmd_triage(h, args):
    triage = h.sibling_module("issues") or refuse("triage", "issues.py is not installed beside health.py")
    root = h.repo_root()
    if args.close:
        if not args.kind and not args.issue:
            refuse("kind", "close needs --kind (a group such as docs, or review-gap) or --issue N")
        return triage.close(root, args.kind, args.why, args.feature, args.older, args.yes, args.max, tuple(args.issue))
    return triage.listing(root, args.feature)


def answer_flag(item):
    """--judge-answer FILE: the reply an in-session subagent gave to the judge prompt (session first; see judge.py)."""
    item.add_argument("--judge-answer", dest="judge_answer", type=saved_answer, help="the session judge's saved reply")


def saved_answer(path):
    import os
    os.environ["LOOP_JUDGE_ANSWER"] = os.path.abspath(path)
    return path


def add(sub, h):
    """Add these commands to health.py's parser."""
    item = sub.add_parser("review", help="the per-feature repo review; writes nothing")
    item.add_argument("--feature")
    item.add_argument("--json", action="store_true")
    answer_flag(item)
    item.set_defaults(func=lambda a: cmd_review(h, a))
    for name in ("judge", "suggest"):
        item = sub.add_parser(name, help="the check report, then a judge section of suggestions")
        answer_flag(item)
        item.set_defaults(func=lambda a: cmd_judge(h, a))
    for name, func in (("preview", cmd_preview), ("run", cmd_preview), ("file", cmd_file)):
        item = sub.add_parser(name, help="file findings as issues" if name == "file" else "list what file would do")
        item.add_argument("--group", "--family", dest="group", help="NAME[,NAME]: " + ", ".join(h.NAMES))
        item.add_argument("--feature", help="only findings about this feature")
        item.add_argument("--review", help="a saved health.py review --json to file too")
        item.add_argument("--live", action="store_true", help="(ignored)")
        item.add_argument("--open-only", action="store_true", help="file: only open or link issues; never close, reopen or update")
        answer_flag(item)
        item.set_defaults(func=lambda a, f=func: f(h, a))
    item = sub.add_parser("triage", help="open findings per feature; --close a batch with the owner's words")
    item.add_argument("--feature")
    item.add_argument("--close", action="store_true")
    item.add_argument("--kind")
    item.add_argument("--issue", type=int, action="append", default=[], help="close only this issue number (repeatable)")
    item.add_argument("--why", default="")
    item.add_argument("--older", type=int, default=0)
    item.add_argument("--yes", action="store_true")
    item.add_argument("--max", type=int, default=20)
    item.set_defaults(func=lambda a: cmd_triage(h, a))
