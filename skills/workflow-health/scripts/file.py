"""File health findings as issues on their feature's milestone, under the owner's control (HLT-4). Used by health.py
preview and file.

plan() works out what each finding does: open, update, reopen, close, link or same. preview prints the plan and has no
write path; file carries it out for the named groups (and --feature) only.
- Each issue goes on the milestone of the feature the finding is about (feature.py), Backlog when none fits, labelled
  health and health:<group> (review findings: health:review-<kind>).
- Its marker `<!-- loop-health KEY evidence=H -->` names the finding and a hash of its stable evidence. A repeat updates,
  a fix closes (only when that rule itself ran and read its data), a return reopens. A closed health:closed issue (closed
  by triage with the owner's words) stays closed while its evidence hash is unchanged.
- An open non-health issue on that milestone that names the finding's subject (an exact path, requirement id or row id)
  already covers it: it gets one link comment, `<!-- loop-health-link KEY evidence=H -->`, never a duplicate issue.
- Markers from before the twelve groups (criteria:, cost:, size:...:limit) are found and moved to the new key.
It runs gh and nothing else, never edits a tracked page, and stops before any write when gh can't list the issues.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

import feature
import ghcache
import groups as G

# No terminal, no waiting: a prompt from gh or the judge must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

MARK = "<!-- loop-health %s evidence=%s -->"
LINK = "<!-- loop-health-link %s evidence=%s -->"
FOUND = re.compile(r"<!-- loop-health (.+?)(?: evidence=(\w+))? -->")  # a key may hold spaces (/workflow-x verb)
BACKLOG = feature.BACKLOG
GROUPS = tuple(g for g in G.ORDER if g != "controls") + ("review",)
DEFAULT = tuple(g for g in G.ORDER if g not in ("mine", "controls"))  # a preview with no group names these, never mine
BAD = ("WARN", "FAIL", "UNREAD")
# Shown, never filed: local paths and machine state, the controls, and the check's own clock.
REPORT_ONLY = ("test-time", "worktrees", "local-branches", "idle-sessions", "scan-hook", "check-time", "control",
               "finding-age", "milestone")  # finding-age and milestone (DOC-10) are about issues themselves: filing them would feed itself
OLD = {"requirements": "criteria", "performance": "cost", "traceability": "criteria", "tests": "criteria"}
OLD_RULE = {"scripts": "limit", "seen-red": "proof", "done": "rows"}


def tag_of(group, item=None):
    if group == "review" and item:
        return "health:review-" + item["rule"]
    return "health:" + group


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


def line_of(item):
    text = "%s %s %s %s: %s" % (item["state"], item["family"], item["subject"], item["rule"], item["detail"])
    return text + (" -> fix: " + item["fix"] if item["fix"] else "")


def body_of(item):
    # A mine rule's output, fix and settings path are private: the issue names the rule and its state only.
    line = line_of(item) if item["family"] != "mine" else "%s mine %s %s: details stay local; run health.py check --group mine" % (
        item["state"], item["subject"], item["rule"])
    angle = G.ANGLE.get(item["family"], "the reviewer's angle: %s" % item.get("angle", "per feature"))
    return "%s\n\n%s\n\nGroup: %s (%s). Evidence: %s\n\nFiled by health.py file.\n" % (
        MARK % (key_of(item), evidence_of(item)), line, G.TITLE.get(item["family"], item["family"]), angle,
        item.get("evidence") or item["subject"])


def run(args, root):
    try:
        return subprocess.run(["gh"] + args, cwd=root, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        return subprocess.CompletedProcess(args, 127, "", str(error))


def saves(root, here, rows):
    """(items, read): the judge's savings as rows, and whether the judge answered. Calls a model, so only on request."""
    sys.path.insert(0, here)
    try:
        import judge
        answer, why = judge.ask(judge.gather(root, here, rows), root)
        found = judge.parse(answer)["SAVES"]
    except Exception:  # advice only: no answer means no savings issues opened or closed
        return [], False
    finally:
        sys.path.pop(0)
    if why or not found:
        return [], False
    items = [{"state": "WARN", "family": "performance", "subject": "judge", "rule": "saves-" + hashlib.sha1(c.encode()).hexdigest()[:8],
              "detail": "%s%% saving: %s" % (p.rstrip("% "), w), "fix": c} for p, w, c in found]
    return items, True


def held(root):
    """({marker key: issue} of the health issues, every issue, why) or (None, None, why) when gh can't list them all."""
    found, why = ghcache.issues(root)
    if found is None:
        return None, None, why
    out = {}
    for issue in sorted(found, key=lambda one: one["number"]):
        match = FOUND.search(issue.get("body") or "")
        if match and ghcache.is_health(issue):
            seen = out.get(match.group(1))
            if seen is None or (seen.get("state") != "open" and issue.get("state") == "open"):  # an open duplicate wins
                out[match.group(1)] = dict(issue, evidence=match.group(2) or "")
    return out, found, ""


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


def plan(rows, issues, groups, extra=(), judged=False, root=".", ran_rules=None, everything=(), only=None):
    """Actions for the named groups (and feature `only`): kind open, update, reopen, close, link or same."""
    found = [item for item in list(rows) + list(extra)
             if item["state"] in BAD and item["family"] in groups and item["rule"] not in REPORT_ONLY]
    cache, out, current = {}, [], set()
    for item in found:
        stone = feature.feature_of(root, item, cache)
        if only and stone != only:
            continue
        key, group, mark = key_of(item), item["family"], evidence_of(item)
        if key in current:  # two findings with one identity (same kind and evidence) are one issue
            continue
        current.add(key)
        issue = issues.get(key) or next((issues[k] for k in legacy(item) if k in issues), None)
        current.update(k for k in legacy(item) if k in issues)  # a migrated issue is updated, never closed
        act = {"group": group, "key": key, "body": body_of(item), "evidence": mark, "milestone": stone, "tag": tag_of(group, item),
               "title": "health: %s %s %s" % (group, item["subject"], item["rule"])}
        if not issue:
            cover = covering(item, everything, stone)
            out.append(dict(act, kind="link", number=str(cover["number"])) if cover else dict(act, kind="open"))
            continue
        act["number"] = str(issue["number"])
        act["stale"] = [t for t in issue.get("labels") or [] if t.startswith("health:") and t not in (act["tag"], "health:closed")]
        closed = issue.get("state", "").lower() != "open"
        if closed and "health:closed" in (issue.get("labels") or []) and issue.get("evidence") == mark:
            out.append(dict(act, kind="same", why="closed by the owner, evidence unchanged"))
            continue
        if closed:
            out.append(dict(act, kind="reopen", unclose="health:closed" in (issue.get("labels") or [])))
        if issue.get("milestone") not in (None, BACKLOG, stone):  # the owner moved it: it stays there
            act["milestone"] = issue["milestone"]
        if (issue.get("body") or "") != act["body"] or act["tag"] not in (issue.get("labels") or []) or \
                issue.get("milestone") != act["milestone"] or act["stale"]:
            out.append(dict(act, kind="update"))
        elif not closed:
            out.append(dict(act, kind="same"))
    for key, issue in sorted(issues.items()):
        family, _, rest = key.partition(":")
        family = G.ALIASES.get(family, family)
        rule = G.rule_of({"family": family, "rule": rest.rsplit(":", 1)[-1], "subject": rest.rsplit(":", 1)[0]})
        if family == "mine":  # a private rule closes only when that same rule ran here
            rule = "mine:" + rest.rsplit(":", 1)[0]
        if key in current or family not in groups or issue.get("state", "").lower() != "open" or only:
            continue
        savings = ":judge:saves-" in key
        whole = {"criteria": {"requirements", "traceability", "tests"}, "cost": {"performance"}}.get(key.partition(":")[0])
        if whole and not whole <= set(groups):  # an old key could mean a rule in a group not run now: leave it
            continue
        if (savings and judged) or (not savings and ran_rules is not None and rule in ran_rules):  # its own rule passed
            out.append({"kind": "close", "group": family, "key": key, "number": str(issue["number"]), "title": "", "body": "",
                        "tag": tag_of(family), "milestone": issue.get("milestone") or BACKLOG})
    return out


def words(act):
    kind = act["kind"]
    if kind == "open":
        return "open issue %r on %s [%s]" % (act["title"], act["milestone"], act["tag"])
    if kind == "link":
        return "link #%s (already covers %s, on %s) [%s]" % (act["number"], act["key"], act["milestone"], act["tag"])
    return "%s #%s %s on %s [%s]" % (kind, act["number"], act["key"], act["milestone"], act["tag"]) + (
        ", no longer found" if kind == "close" else "")


def args_of(act):
    n = act.get("number")
    return {"open": ["issue", "create", "--title", act["title"], "--body", act["body"], "--label", "health", "--label", act["tag"],
                     "--milestone", act["milestone"]],
            "update": ["issue", "edit", n, "--body", act["body"], "--add-label", act["tag"], "--milestone", act["milestone"]]
            + [part for t in act.get("stale") or [] for part in ("--remove-label", t)],
            "reopen": ["issue", "reopen", n],
            "close": ["issue", "close", n, "--comment", "No longer found by health.py file."]}[act["kind"]]


def preview(acts):
    """Print what would happen. Nothing here can write."""
    for act in acts:
        print(("SAME #%s %s [%s]%s" % (act["number"], act["key"], act["tag"], " (%s)" % act["why"] if act.get("why") else ""))
              if act["kind"] == "same" else "WOULD " + words(act))
    return len([act for act in acts if act["kind"] != "same"])


def linked(root, number, act):
    """True when the covering issue already has this finding's link comment."""
    got = run(["issue", "view", number, "--json", "comments"], root)
    try:
        return LINK % (act["key"], act["evidence"]) in json.dumps(json.loads(got.stdout))
    except ValueError:
        return False


def apply(acts, root, groups):
    """Carry out the plan: labels and milestones first, then each issue's writes in plan order (reopen before update)."""
    got = run(["api", "repos/{owner}/{repo}/milestones?state=all&per_page=100"], root)
    try:
        listed = json.loads(got.stdout or "[]") if not got.returncode else None
    except ValueError:
        listed = None
    if not isinstance(listed, list):  # before any write: never file half a plan
        print("REFUSED[gh]: can't list the milestones (%s). Nothing was written." % (got.stderr.strip()[:120] or "no list"))
        return
    have = {item.get("title") for item in listed if isinstance(item, dict)}
    for tag in sorted({act["tag"] for act in acts} | {"health"}):
        run(["label", "create", tag, "--description", "Filed by health.py file", "--force"], root)
    for stone in sorted({act["milestone"] for act in acts} - have):  # a feature's milestone, created before filing on it
        run(["api", "-X", "POST", "repos/{owner}/{repo}/milestones", "-f", "title=" + stone], root)
    for act in acts:
        if act["kind"] == "same":
            print("SAME #%s %s" % (act["number"], act["key"]))
            continue
        if act["kind"] == "link":
            if linked(root, act["number"], act):
                print("SAME #%s %s (already linked)" % (act["number"], act["key"]))
                continue
            done = run(["issue", "comment", act["number"], "--body", "%s\nHealth finds this here: %s" % (
                LINK % (act["key"], act["evidence"]), act["body"].split("\n\n")[1])], root)
        else:
            done = run(args_of(act), root)
            if act["kind"] == "reopen" and act.get("unclose") and not done.returncode:  # the owner's close no longer holds
                run(["issue", "edit", act["number"], "--remove-label", "health:closed"], root)
        print(("FAILED %s: %s" % (words(act), done.stderr.strip()[:160])) if done.returncode else "DONE " + words(act))
