"""File health findings as issues, by group, under the owner's control. Used by health.py preview and file.

plan() works out what each finding would do to its issue: open, update, close, reopen or move, each with its
health:<group> tag. preview prints the plan and writes nothing (it has no write path). file --group NAME[,NAME] carries
out the plan for the named groups only: it opens, updates, closes and reopens only those groups' issues, labelled
health:<group> (and the old plain health label, so older issues are still found), on the milestone of the feature the
finding is about (milestone.page_of: the docs.tsv page whose path is the longest prefix of its subject), Backlog when
none fits. The marker remembers where the automation placed an issue (placed=); it moves an issue only while it is still
there, so an issue the owner moved elsewhere, Backlog included, stays. A returning finding reopens its issue,
a fixed one closes it, a rule that could not be read closes none. The judge's savings (performance) are filed only when
performance is named, because the judge calls a model. mine is filed only when named. It runs gh and nothing else.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse

# No terminal, no waiting: a prompt from gh or the judge must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

MARK = "<!-- loop-health %s placed=%s -->"
FOUND = re.compile(r"<!-- loop-health (\S+?)(?: placed=(\S*))? -->")
BACKLOG = "Backlog"
GROUPS = ("size", "criteria", "docs", "hygiene", "cost", "mine")
TAG = {"cost": "performance"}
DEFAULT = ("size", "criteria", "docs", "hygiene", "cost")  # a preview with no group names these, never mine
BAD = ("WARN", "FAIL", "UNREAD")
REPORT_ONLY = ("test-time", "worktrees", "local-branches", "control")  # local paths and names, and controls: shown, never filed


def tag_of(group):
    return "health:" + TAG.get(group, group)


def key_of(item):
    return "%s:%s:%s" % (item["family"], item["subject"], item["rule"])


def line_of(item):
    text = "%s %s %s %s: %s" % (item["state"], item["family"], item["subject"], item["rule"], item["detail"])
    return text + (" -> fix: " + item["fix"] if item["fix"] else "")


def feature_of(root, item):
    if not root:
        return BACKLOG
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        import milestone
        return milestone.page_of(root, item["subject"]) or BACKLOG
    finally:
        sys.path.pop(0)


def body_of(item, placed=BACKLOG):
    # A mine rule's output, fix and settings path are private: the issue names the rule and its state only.
    line = line_of(item) if item["family"] != "mine" else "%s mine %s %s: details stay local; run health.py check --group mine" % (
        item["state"], item["subject"], item["rule"])
    return "%s\n\n%s\n\n%s\n" % (MARK % (key_of(item), urllib.parse.quote(placed, safe="")), line,
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
    got = run(["issue", "list", "--label", "health", "--state", "all", "--limit", "500", "--json", "number,state,body,labels,milestone"], root)
    try:
        issues = json.loads(got.stdout)
    except ValueError:
        return None, (got.stderr.strip() or "no answer")[:200]
    found = {}
    for issue in sorted(issues, key=lambda one: one["number"]):
        match = FOUND.search(issue.get("body") or "")
        if match:  # an issue filed before placed= was recorded was placed on Backlog
            issue["placed"] = urllib.parse.unquote(match.group(2)) if match.group(2) is not None else BACKLOG
            found.setdefault(match.group(1), issue)
    return found, ""


def plan(rows, issues, groups, extra=(), judged=False, root=None):
    """Actions for the named groups: dicts with kind (open, update, reopen, move, close, same), group, key, title, body,
    number and milestone."""
    found = [item for item in list(rows) + list(extra)
             if item["state"] in BAD and item["family"] in groups and item["rule"] not in REPORT_ONLY]
    unread = {item["family"] for item in rows if item["state"] == "UNREAD" and item["rule"] not in REPORT_ONLY}
    # A group whose only rows are INFO (mine with no private rules) did not run, as the report says.
    idle = {g for g in groups if any(i["family"] == g for i in rows) and all(i["state"] == "INFO" for i in rows if i["family"] == g)}
    ran = set(groups) - unread - idle  # a clean group gives no rows, so it ran unless a rule in it could not read
    out, current = [], set()
    miles = milestones(root) if root and found else {}
    for item in found:
        key, group = key_of(item), item["family"]
        current.add(key)
        issue, home = issues.get(key), feature_of(root, item)
        if miles and home not in miles:  # its milestone isn't there: Backlog, so placed= matches where it really goes
            home = BACKLOG
        act = {"group": group, "key": key, "body": body_of(item, home), "milestone": home,
               "title": "health: %s %s %s" % (group, item["subject"], item["rule"])}
        if not issue:
            out.append(dict(act, kind="open"))
            continue
        act["number"] = str(issue["number"])
        now = (issue.get("milestone") or {}).get("title") or ""
        moving = now == issue.get("placed") and home != now  # still where the automation put it
        body = act["body"] = body_of(item, home if moving else issue.get("placed", BACKLOG))
        if moving:
            out.append(dict(act, kind="move"))
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
        return "open issue %r on %s [%s]" % (act["title"], act.get("milestone") or BACKLOG, tag)
    if kind == "move":
        return "move #%s to %s [%s]" % (act["number"], act["milestone"], tag)
    return "%s #%s %s [%s]" % (kind, act["number"], act["key"], tag) + (", no longer found" if kind == "close" else "")


def args_of(act):
    tag, n = tag_of(act["group"]), act.get("number")
    return {"open": ["issue", "create", "--title", act["title"], "--body", act["body"], "--label", "health", "--label", tag,
                     "--milestone", act.get("milestone") or BACKLOG],
            "move": ["issue", "edit", n, "--milestone", act.get("milestone") or BACKLOG],
            "update": ["issue", "edit", n, "--body", act["body"], "--add-label", tag],
            "reopen": ["issue", "reopen", n],
            "close": ["issue", "close", n, "--comment", "No longer found by health.py file."]}[act["kind"]]


def preview(acts):
    """Print what would happen. Nothing here can write."""
    for act in acts:
        print(("SAME #%s %s [%s]" % (act["number"], act["key"], tag_of(act["group"]))) if act["kind"] == "same"
              else "WOULD " + words(act))
    return len([act for act in acts if act["kind"] != "same"])


def milestones(root):
    """{title: (number, state)} of every milestone, open or closed; {} when gh can't read them."""
    done = run(["api", "--paginate", "--slurp", "repos/{owner}/{repo}/milestones?state=all&per_page=100"], root)
    try:
        data = json.loads(done.stdout) if done.returncode == 0 else []
    except ValueError:
        data = []
    flat = [m for page in data for m in (page if isinstance(page, list) else [page])] if isinstance(data, list) else []
    return {m["title"]: (m.get("number"), m.get("state") or "open") for m in flat if isinstance(m, dict) and m.get("title")}


def placed(act, miles):
    """The act with a milestone that exists: its feature's, else Backlog with a NOTE, else none. Returns (act, number of a
    closed milestone to set by REST, or None)."""
    title = act.get("milestone") or BACKLOG
    if title not in miles:
        fallback = BACKLOG if BACKLOG in miles else ""
        print("NOTE: milestone %s doesn't exist, so the issue goes on %s" % (title, fallback or "no milestone"))
        act = dict(act, milestone=fallback, body=act["body"].replace(" placed=%s " % urllib.parse.quote(title, safe=""),
                                                                     " placed=%s " % urllib.parse.quote(fallback or BACKLOG, safe="")))
        title = fallback
    number, state = miles.get(title, (None, ""))
    if title and state == "closed":  # gh's --milestone finds open ones only: set this one by number after the write
        return dict(act, milestone=""), number
    return act, None


def apply(acts, root, groups):
    """Carry out the plan. The caller has already limited the plan to the named groups."""
    miles = milestones(root) if any(act["kind"] in ("open", "move") for act in acts) else {}
    for name in sorted({act["group"] for act in acts} | set(groups)):
        run(["label", "create", tag_of(name), "--description", "Filed by health.py file: the %s group" % TAG.get(name, name), "--force"], root)
    run(["label", "create", "health", "--description", "Filed by health.py file", "--force"], root)
    for act in acts:
        if act["kind"] == "same":
            print("SAME #%s %s" % (act["number"], act["key"]))
            continue
        closed = None
        if act["kind"] in ("open", "move"):
            act, closed = placed(act, miles)
        args = args_of(act)
        if act["kind"] in ("open", "move") and not act.get("milestone"):
            args = args[:args.index("--milestone")] + args[args.index("--milestone") + 2:]
        done = run(args, root) if args[:2] != ["issue", "edit"] or len(args) > 3 else subprocess.CompletedProcess(args, 0, "", "")
        if not done.returncode and closed:
            number = act.get("number") or (re.findall(r"/issues/(\d+)", done.stdout) or [""])[-1]
            done = run(["api", "-X", "PATCH", "repos/{owner}/{repo}/issues/%s" % number, "-F", "milestone=%s" % closed], root)
        print(("FAILED %s: %s" % (words(act), done.stderr.strip()[:160])) if done.returncode else "DONE " + words(act))
