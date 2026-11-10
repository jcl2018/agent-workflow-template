"""File health findings as issues, by group, under the owner's control. Used by health.py preview and file.

plan() works out what each finding would do to its issue: open, update, close or reopen, each with its health:<group>
tag. preview prints the plan and writes nothing (it has no write path). file --group NAME[,NAME] carries out the plan for
the named groups only: it opens, updates, closes and reopens only those groups' issues, on the Backlog milestone, labelled
health:<group> (and the old plain health label, so older issues are still found). A returning finding reopens its issue,
a fixed one closes it, a rule that could not be read closes none. The judge's savings (performance) are filed only when
performance is named, because the judge calls a model. mine is filed only when named. It runs gh and nothing else.
"""
import hashlib
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from gh or the judge must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

MARK = "<!-- loop-health %s -->"
BACKLOG = "Backlog"
GROUPS = ("size", "criteria", "docs", "hygiene", "cost", "mine", "controls")
TAG = {"cost": "performance"}
DEFAULT = ("size", "criteria", "docs", "hygiene", "cost", "controls")  # a preview with no group names these, never mine
BAD = ("WARN", "FAIL", "UNREAD")
REPORT_ONLY = ("test-time", "worktrees", "local-branches")  # machine-local paths and names: shown by check, never filed


def tag_of(group):
    return "health:" + TAG.get(group, group)


def key_of(item):
    return "%s:%s:%s" % (item["family"], item["subject"], item["rule"])


def line_of(item):
    text = "%s %s %s %s: %s" % (item["state"], item["family"], item["subject"], item["rule"], item["detail"])
    return text + (" -> fix: " + item["fix"] if item["fix"] else "")


def body_of(item):
    # A mine rule's output, fix and settings path are private: the issue names the rule and its state only.
    line = line_of(item) if item["family"] != "mine" else "%s mine %s %s: details stay local; run health.py check --group mine" % (
        item["state"], item["subject"], item["rule"])
    return "%s\n\n%s\n\n%s\n" % (MARK % key_of(item), line,
                                    "Filed by health.py file. Move it to a feature with milestone.py move.")


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
    items = [{"state": "WARN", "family": "cost", "subject": "judge", "rule": "saves-" + hashlib.sha1(c.encode()).hexdigest()[:8],
              "detail": "%s%% saving: %s" % (p.rstrip("% "), w), "fix": c} for p, w, c in found]
    return items, True


def held(root):
    """The existing health issues by marker key, or None when gh cannot be read."""
    got = run(["issue", "list", "--label", "health", "--state", "all", "--limit", "500", "--json", "number,state,body,labels"], root)
    try:
        issues = json.loads(got.stdout)
    except ValueError:
        return None, (got.stderr.strip() or "no answer")[:200]
    found = {}
    for issue in sorted(issues, key=lambda one: one["number"]):
        match = re.search(r"<!-- loop-health (\S+) -->", issue.get("body") or "")
        if match:
            found.setdefault(match.group(1), issue)
    return found, ""


def plan(rows, issues, groups, extra=(), judged=False):
    """Actions for the named groups: dicts with kind (open, update, reopen, close, same), group, key, title, body, number."""
    found = [item for item in list(rows) + list(extra)
             if item["state"] in BAD and item["family"] in groups and item["rule"] not in REPORT_ONLY]
    unread = {item["family"] for item in rows if item["state"] == "UNREAD"}
    # A group whose only rows are INFO (mine with no private rules) did not run, as the report says.
    idle = {g for g in groups if any(i["family"] == g for i in rows) and all(i["state"] == "INFO" for i in rows if i["family"] == g)}
    ran = set(groups) - unread - idle  # a clean group gives no rows, so it ran unless a rule in it could not read
    out, current = [], set()
    for item in found:
        key, group = key_of(item), item["family"]
        current.add(key)
        issue, body = issues.get(key), body_of(item)
        act = {"group": group, "key": key, "body": body, "title": "health: %s %s %s" % (group, item["subject"], item["rule"])}
        if not issue:
            out.append(dict(act, kind="open"))
            continue
        act["number"] = str(issue["number"])
        names = {label.get("name") for label in issue.get("labels") or [] if isinstance(label, dict)}
        if issue["state"].upper() != "OPEN":
            out.append(dict(act, kind="reopen"))
        if (issue.get("body") or "") != body or tag_of(group) not in names:
            out.append(dict(act, kind="update"))
        elif issue["state"].upper() == "OPEN":
            out.append(dict(act, kind="same"))
    for key, issue in sorted(issues.items()):
        group = key.split(":")[0]
        savings = key.startswith("cost:judge:")
        if key in current or group not in groups or issue["state"].upper() != "OPEN":
            continue
        if (savings and judged) or (not savings and group in ran):  # closes only when its rule ran and read its data
            out.append({"kind": "close", "group": group, "key": key, "number": str(issue["number"]), "title": "", "body": ""})
    return out


def words(act):
    tag, kind = tag_of(act["group"]), act["kind"]
    if kind == "open":
        return "open issue %r on %s [%s]" % (act["title"], BACKLOG, tag)
    return "%s #%s %s [%s]" % (kind, act["number"], act["key"], tag) + (", no longer found" if kind == "close" else "")


def args_of(act):
    tag, n = tag_of(act["group"]), act.get("number")
    return {"open": ["issue", "create", "--title", act["title"], "--body", act["body"], "--label", "health", "--label", tag,
                     "--milestone", BACKLOG],
            "update": ["issue", "edit", n, "--body", act["body"], "--add-label", tag],
            "reopen": ["issue", "reopen", n],
            "close": ["issue", "close", n, "--comment", "No longer found by health.py file."]}[act["kind"]]


def preview(acts):
    """Print what would happen. Nothing here can write."""
    for act in acts:
        print(("SAME #%s %s [%s]" % (act["number"], act["key"], tag_of(act["group"]))) if act["kind"] == "same"
              else "WOULD " + words(act))
    return len([act for act in acts if act["kind"] != "same"])


def apply(acts, root, groups):
    """Carry out the plan. The caller has already limited the plan to the named groups."""
    for name in sorted({act["group"] for act in acts} | set(groups)):
        run(["label", "create", tag_of(name), "--description", "Filed by health.py file: the %s group" % TAG.get(name, name), "--force"], root)
    run(["label", "create", "health", "--description", "Filed by health.py file", "--force"], root)
    for act in acts:
        if act["kind"] == "same":
            print("SAME #%s %s" % (act["number"], act["key"]))
            continue
        done = run(args_of(act), root)
        print(("FAILED %s: %s" % (words(act), done.stderr.strip()[:160])) if done.returncode else "DONE " + words(act))
