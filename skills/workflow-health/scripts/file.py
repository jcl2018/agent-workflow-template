"""File health findings as issues on their feature's milestone, under the owner's control (HLT-4). Used by health.py
preview and file.

plan() works out what each finding does: open, update, reopen, close, link or same. preview prints the plan and has no
write path; file carries it out for the named groups (and --feature) only.
- Each issue goes on the milestone of the feature the finding is about (issues.py), Backlog when that milestone isn't
  there (milestone.py new --all makes them), labelled health and health:<group> (review findings: health:review-<kind>).
- Its marker `<!-- loop-health KEY evidence=H placed=P -->` names the finding, a hash of its stable evidence and where
  file put it. An issue moves to its feature only while it is still on P, so one the owner moved stays. A repeat updates,
  a fix closes (only when that rule itself ran and read its data), a return reopens. A closed health:closed issue (closed
  by triage with the owner's words) stays closed while its evidence hash is unchanged.
- An open non-health issue on that milestone that names the finding's subject (an exact path, requirement id or row id)
  already covers it: it gets one link comment, `<!-- loop-health-link KEY evidence=H -->`, never a duplicate issue.
- Markers from before the twelve groups (criteria:, cost:, size:...:limit) are found and moved to the new key.
It runs gh and nothing else, never edits a tracked page, and stops before any write when gh can't list the issues. When it
can't list the milestones it files by title and moves nothing; a closed milestone is set by number.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.parse

import report as G
import issues as IS
from issues import covering, evidence_of, key_of, legacy, title_of

# No terminal, no waiting: a prompt from gh or the judge must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

MARK = "<!-- loop-health %s evidence=%s placed=%s -->"
LINK = "<!-- loop-health-link %s evidence=%s -->"
FOUND = re.compile(r"<!-- loop-health (.+?)(?: evidence=(\w+))?(?: placed=(\S*))? -->")  # a key may hold spaces (/workflow-x verb)
BACKLOG = IS.BACKLOG
GROUPS = tuple(g for g in G.ORDER if g != "controls") + ("review",)
DEFAULT = tuple(g for g in G.ORDER if g not in ("mine", "controls"))  # a preview with no group names these, never mine
BAD = ("WARN", "FAIL", "UNREAD")
# Shown, never filed: local paths and machine state, the controls, and the check's own clock.
REPORT_ONLY = ("test-time", "worktrees", "local-branches", "idle-sessions", "scan-hook", "check-time", "control",
               "finding-age", "milestone")  # finding-age and milestone (DOC-10) are about issues themselves: filing them would feed itself


def tag_of(group, item=None):
    if group == "review" and item:
        return "health:review-" + item["rule"]
    return "health:" + group


def line_of(item):
    text = "%s %s %s %s: %s" % (item["state"], item["family"], item["subject"], item["rule"], item["detail"])
    return text + (" -> fix: " + item["fix"] if item["fix"] else "")


def body_of(item, placed=BACKLOG):
    # A mine rule's output, fix and settings path are private: the issue names the rule and its state only.
    line = line_of(item) if item["family"] != "mine" else "%s mine %s %s: details stay local; run health.py check --group mine" % (
        item["state"], item["subject"], item["rule"])
    angle = G.ANGLE.get(item["family"], "the reviewer's angle: %s" % item.get("angle", "per feature"))
    return "%s\n\n%s\n\nGroup: %s (%s). Evidence: %s\n\nFiled by health.py file.\n" % (
        MARK % (key_of(item), evidence_of(item), urllib.parse.quote(placed, safe="")), line, G.TITLE.get(item["family"], item["family"]), angle,
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
    """({marker key: issue} of the health issues, why), or (None, why) when gh can't list them."""
    found, _, why = held_all(root)
    return found, why


def held_all(root):
    """({marker key: issue} of the health issues, every issue, why) or (None, None, why) when gh can't list them all."""
    found, why = IS.fetch(root)
    if found is None:
        return None, None, why
    out = {}
    for issue in sorted(found, key=lambda one: one["number"]):
        match = FOUND.search(issue.get("body") or "")
        if match and IS.is_health(issue):
            seen = out.get(match.group(1))
            if seen is None or (seen.get("state") != "open" and issue.get("state") == "open"):  # an open duplicate wins
                home = urllib.parse.unquote(match.group(3)) if match.group(3) is not None else (
                    title_of(issue.get("milestone")) if match.group(2) else BACKLOG)  # no placed=: where it is, or Backlog if old
                out[match.group(1)] = dict(issue, evidence=match.group(2) or "", placed=home)
    return out, found, ""


def plan(rows, issues, groups, extra=(), judged=False, root=".", ran_rules=None, everything=(), only=None):
    """Actions for the named groups (and feature `only`): kind open, update, reopen, close, link or same."""
    found = [item for item in list(rows) + list(extra)
             if item["state"] in BAD and item["family"] in groups and item["rule"] not in REPORT_ONLY]
    cache, out, current = {}, [], set()
    miles = milestones(root) if root and found else {}
    blind = miles is None  # unreadable: keep each home by title and move nothing this run
    for item in found:
        stone = IS.feature_of(root, item, cache)
        if only and stone != only:
            continue
        home = BACKLOG if (not blind and miles and stone not in miles) else stone  # a missing milestone: Backlog
        key, group, mark = key_of(item), item["family"], evidence_of(item)
        if key in current:  # two findings with one identity (same kind and evidence) are one issue
            continue
        current.add(key)
        issue = issues.get(key) or next((issues[k] for k in legacy(item) if k in issues), None)
        current.update(k for k in legacy(item) if k in issues)  # a migrated issue is updated, never closed
        act = {"group": group, "key": key, "body": body_of(item, home), "evidence": mark, "milestone": home, "tag": tag_of(group, item),
               "title": "health: %s %s %s" % (group, item["subject"], item["rule"])}
        if not issue:
            cover = covering(item, everything, stone)
            out.append(dict(act, kind="link", number=str(cover["number"])) if cover else dict(act, kind="open"))
            continue
        act["number"] = str(issue["number"])
        names = [l.get("name") if isinstance(l, dict) else l for l in issue.get("labels") or []]  # gh's dicts or fetch's names
        act["stale"] = [t for t in names if t.startswith("health:") and t not in (act["tag"], "health:closed")]
        closed = issue.get("state", "").lower() != "open"
        if closed and "health:closed" in names and issue.get("evidence") == mark:
            out.append(dict(act, kind="same", why="closed by the owner, evidence unchanged"))
            continue
        if closed:
            out.append(dict(act, kind="reopen", unclose="health:closed" in names))
        now, old = title_of(issue.get("milestone")), issue.get("placed", BACKLOG)
        moving = not blind and now == old and home != now  # still where file put it
        body = act["body"] = body_of(item, home if moving else old)
        if moving:  # if the move fails, the update keeps the old placed= so the next run tries again
            act["keep_body"] = body_of(item, old)
            out.append(dict(act, kind="move"))
        if (issue.get("body") or "") != body or act["tag"] not in names or act["stale"]:
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
                        "tag": tag_of(family), "milestone": title_of(issue.get("milestone")) or BACKLOG})
    return out


def words(act):
    kind, where = act["kind"], act.get("shown") or act["milestone"] or "no milestone"
    if kind == "open":
        return "open issue %r on %s [%s]" % (act["title"], where, act["tag"])
    if kind == "move":
        return "move #%s to %s [%s]" % (act["number"], where, act["tag"])
    if kind == "link":
        return "link #%s (already covers %s, on %s) [%s]" % (act["number"], act["key"], act["milestone"], act["tag"])
    return "%s #%s %s on %s [%s]" % (kind, act["number"], act["key"], act["milestone"], act["tag"]) + (
        ", no longer found" if kind == "close" else "")


def args_of(act):
    n = act.get("number")
    return {"open": ["issue", "create", "--title", act["title"], "--body", act["body"], "--label", "health", "--label", act["tag"],
                     "--milestone", act["milestone"] or BACKLOG],
            "move": ["issue", "edit", n, "--milestone", act["milestone"] or BACKLOG],
            "update": ["issue", "edit", n, "--body", act["body"], "--add-label", act["tag"]]
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


def milestones(root):
    """{title: (number, state)} of every milestone, open or closed; None when gh can't read them."""
    done = run(["api", "--paginate", "--slurp", "repos/{owner}/{repo}/milestones?state=all&per_page=100"], root)
    try:
        data = json.loads(done.stdout) if done.returncode == 0 else None
    except ValueError:
        data = None
    if not isinstance(data, list):
        return None
    flat = [m for page in data for m in (page if isinstance(page, list) else [page])]
    return {m["title"]: (m.get("number"), m.get("state") or "open") for m in flat if isinstance(m, dict) and m.get("title")}


def placed(act, miles):
    """The act with a milestone that exists: its feature's, else Backlog with a NOTE, else none. Returns (act, number of a
    closed milestone to set by REST, or None)."""
    title = act.get("milestone") or BACKLOG
    if miles is None:  # milestones unreadable: let gh place it by title
        return dict(act, milestone=title), None
    if title not in miles:
        fallback = BACKLOG if BACKLOG in miles else ""
        print("NOTE: milestone %s doesn't exist, so the issue goes on %s" % (title, fallback or "no milestone"))
        act = dict(act, milestone=fallback, body=act["body"].replace(" placed=%s " % urllib.parse.quote(title, safe=""),
                                                                     " placed=%s " % urllib.parse.quote(fallback, safe="")))
        title = fallback
    number, state = miles.get(title, (None, ""))
    if title and state == "closed":  # gh's --milestone finds open ones only: set this one by number after the write
        return dict(act, milestone="", shown=title), number
    return act, None


def apply(acts, root, groups):
    """Carry out the plan: labels and the Backlog fallback first, then each issue's writes in plan order (reopen before update)."""
    miles = milestones(root) if any(act["kind"] in ("open", "move") for act in acts) else {}
    if miles is not None and BACKLOG not in miles and any(act["kind"] in ("open", "move") and (act.get("milestone") or BACKLOG)
                                                          not in miles for act in acts):  # the fallback, made once
        made = run(["api", "-X", "POST", "repos/{owner}/{repo}/milestones", "-f", "title=" + BACKLOG], root)
        try:
            miles[BACKLOG] = (json.loads(made.stdout)["number"], "open")
        except (ValueError, KeyError, TypeError):
            pass  # placed() then notes no milestone
    for tag in sorted({act["tag"] for act in acts} | {"health"}):
        run(["label", "create", tag, "--description", "Filed by health.py file", "--force"], root)
    unmoved = set()
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
            closed = None
            if act["kind"] == "update" and act.get("number") in unmoved and act.get("keep_body"):
                act = dict(act, body=act["keep_body"])
            if act["kind"] in ("open", "move"):
                act, closed = placed(act, miles)
            args = args_of(act)
            if act["kind"] in ("open", "move") and not act.get("milestone"):
                args = args[:args.index("--milestone")] + args[args.index("--milestone") + 2:]
            done = run(args, root) if args[:2] != ["issue", "edit"] or len(args) > 3 else subprocess.CompletedProcess(args, 0, "", "")
            if done.returncode and miles is None and act["kind"] == "open" and act.get("milestone") and done.returncode != 127 and "milestone" in done.stderr.lower():
                print("NOTE: milestone %s couldn't be set, so the issue goes on no milestone" % act["milestone"])  # placed by title, unmade
                act = dict(act, milestone="", body=re.sub(r" placed=\S* -->", " placed= -->", act["body"], count=1))
                args = args_of(act)
                done = run(args[:args.index("--milestone")] + args[args.index("--milestone") + 2:], root)
            if not done.returncode and closed:
                number = act.get("number") or (re.findall(r"/issues/(\d+)", done.stdout) or [""])[-1]
                done = run(["api", "-X", "PATCH", "repos/{owner}/{repo}/issues/%s" % number, "-F", "milestone=%s" % closed], root)
                if done.returncode and act["kind"] == "open":  # on no milestone now: placed= empty, so the next run places it
                    run(["issue", "edit", number, "--body", re.sub(r" placed=\S* -->", " placed= -->", act["body"], count=1)], root)
            if done.returncode and act["kind"] == "move":
                unmoved.add(act["number"])
            if act["kind"] == "reopen" and act.get("unclose") and not done.returncode:  # the owner's close no longer holds
                run(["issue", "edit", act["number"], "--remove-label", "health:closed"], root)
        print(("FAILED %s: %s" % (words(act), done.stderr.strip()[:160])) if done.returncode else "DONE " + words(act))
