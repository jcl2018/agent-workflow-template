#!/usr/bin/env python3
"""Post one digest comment per round, and run the local schedule that makes the rounds.

usage: automation.py local install [--load] | uninstall | status [--json] | plist | tick [--scheduled] [--dry-run] [--repo P]
                                         the one launch agent on this Mac (workflows.py); install registers this repo and writes
                                         the agent, printing the launchctl line that loads it (--load runs it); the tick runs
                                         health with the judge for every repo and the full regression for a private repo
       automation.py digest [--owner L]  post this round's comment on the pinned Automation digest issue
       automation.py workflow            removed: health no longer runs in GitHub Actions (exit 2)

The digest lists what ran (regression's latest run, health's verdict, the round's cost, the email, when the schedule last ran and
a MISSED line after a gap), then per feature the new, still-open and fixed issues labelled regression or health since the last comment,
each open one with its link (and its milestone, when it has one) and the request to give the agent; it mentions digest_owner (default:
the repo owner). Its state lives in the digest issue's body (rounds.py), so a rerun of the same run posts nothing twice and an older run
never overwrites a newer one. Outside a tick with no GH_TOKEN it only prints the comment.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rounds  # noqa: E402
from issues import NO_FEATURE, feature_group, features  # noqa: E402
import workflows  # noqa: E402

ISSUE_LIMIT = 1000  # a label with this many open issues may have more: the digest then says TRUNCATED
CUT = []  # the labels whose listing reached ISSUE_LIMIT, set by open_issues
LABELS = ("regression", "health")  # the issues the digest follows: failing tests and health findings
TITLE = rounds.TITLE
INTRO = "The Automation routines post one comment here per round, and mail it when the mail secrets are set.\n\n"
gh, loads = rounds.gh, rounds.loads


def config(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def local_status(as_json=False):
    data = workflows.load()
    checks = {"plist": (os.path.exists(workflows.plist_path()), "automation.py local install"),
              "loaded": (workflows.launchctl("print", workflows.UID + "/" + workflows.LABEL) == 0, "launchctl bootstrap %s %s" % (workflows.UID, workflows.plist_path())),
              "program": (os.path.exists(workflows.program()), "run local install again (PROGRAM_MISSING)"),
              "gh": (bool(shutil.which("gh")) and subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0, "gh auth login"),
              "claude": (bool(shutil.which("claude")), "install claude and log in once in a terminal")}
    if as_json:
        print(json.dumps({"repos": data["repos"], "checks": {n: v[0] for n, v in checks.items()}}, indent=1))
        return 0
    for key, e in sorted(data["repos"].items()):
        sl, here = workflows.slots(e.get("cron")), os.path.isdir(e["path"])
        print("%s: last_run %s, last_ok %s%s%s%s%s%s" % (key, e.get("last_run") or "never", e.get("last_ok"), " MISSING (path gone)" * (not here),
              " OVERDUE" * bool(sl and (workflows.now() - (workflows.when(e.get("last_run")) or workflows.now())).total_seconds() > 2 * sl[1] * 3600),
              " ORIGIN_CHANGED: run local install again (ORIGIN_CHANGED)" * (here and workflows.origin_of(e["path"]) != e["origin"]),
              " SKIPPED_OFFLINE %d ticks in a row (%s)" % (e.get("skips", 0), e.get("cause")) * bool(e.get("skips")),
              " JUDGE_SKIPPED %d ticks (JUDGE_SKIPPED)" % e.get("judge_skipped", 0) * bool(e.get("judge_skipped"))))
    print("\n".join("OK " + n if ok else "FIX %s: %s" % (n, fix) for n, (ok, fix) in checks.items()))
    return 0


def cmd_local(args):
    if args.action == "tick":
        return workflows.tick(args.scheduled, args.dry_run, args.repo)
    if args.action == "status":
        return local_status(args.json)
    if args.action == "plist":
        print(workflows.agent_text(workflows.load()), end="")
        return 0
    return workflows.uninstall(args.root) if args.action == "uninstall" else workflows.install(args.root, config(args.root), args.load)


def cmd_workflow(args):
    print("REMOVED: health runs on the Mac now; run automation.py local install (SCHEDULE_REMOVED_WORKFLOW)")
    return 2


def open_issues(pages=()):
    """({number: (url, milestone number or 0)}, {number: feature}) of the open issues the digest follows; (None, {}) when
    gh can't list them. A feature is the issue's feature label, else a milestone named like a page, else No feature."""
    found, group = {}, {}
    for label in LABELS:
        done = gh("issue", "list", "--label", label, "--state", "open", "--limit", str(ISSUE_LIMIT), "--json", "number,url,milestone,labels")
        if done.returncode:
            return None, {}
        listed = loads(done, [])
        if len(listed) >= ISSUE_LIMIT and label not in CUT:
            CUT.append(label)
        for item in listed:
            stone = item.get("milestone") or {}
            found[item["number"]] = (item["url"], int(stone.get("number") or 0))
            group[item["number"]] = feature_group({"labels": [l.get("name") for l in item.get("labels") or []],
                                                   "milestone": stone.get("title")}, pages)
    return found, group


def owner_of(args, cfg):
    """(the login to mention, a note): digest_owner, else the repo owner; an organisation notifies no one."""
    login = args.owner or cfg.get("digest_owner") or os.environ.get("DIGEST_REPO_OWNER") or ""
    if not login:
        login = gh("repo", "view", "--json", "owner", "-q", ".owner.login").stdout.strip()
    if not isinstance(login, str) or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", login):
        return "", "No owner to mention: set digest_owner in .loop/config.json."
    kind = gh("api", "users/" + login, "-q", ".type").stdout.strip()
    if kind == "Organization":
        return "", "@%s is an organisation, so no one is notified: set digest_owner in .loop/config.json." % login
    return login, ""


def regression_line():
    if os.environ.get("DIGEST_REGRESSION"):  # the Mac's tick ran it
        return os.environ["DIGEST_REGRESSION"]
    runs = loads(gh("run", "list", "--workflow", "regression.yml", "--limit", "1", "--json", "status,conclusion,createdAt,url"), [])
    if not runs:
        return "no run found"
    run = runs[0]
    said = run.get("conclusion") or run.get("status") or "unknown"
    if run.get("status") not in (None, "completed"):
        said = "still running"
    return "%s, %s ([run](%s))" % (said, (run.get("createdAt") or "")[:16].replace("T", " "), run.get("url") or "")


def health_line(path):
    try:
        with open(path) as handle:
            lines = [line.strip() for line in handle if line.startswith("HEALTH:")]
    except OSError:
        lines = []
    return lines[-1] if lines else "no report"


def email_line(cfg, previous):
    """The email row: off, not set up, or the previous round's mail outcome (read from that round's comment)."""
    mode = cfg.get("digest_mail") or "cloudflare"
    if mode == "off":
        return "off (digest_mail in .loop/config.json)"
    if os.environ.get("DIGEST_MAIL_NOTE"):
        return "not set up (%s)" % os.environ["DIGEST_MAIL_NOTE"]
    ready = os.environ.get("MAIL_ADDR_SET") == "true" and os.environ.get(
        "MAIL_SMTP_SET" if mode == "smtp" else "MAIL_CF_SET") == "true"
    if "MAIL_ADDR_SET" in os.environ and not ready:
        names = "DIGEST_SMTP_USER, DIGEST_SMTP_PASSWORD" if mode == "smtp" else "CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_EMAIL_TOKEN"
        return "not set up (add the DIGEST_TO, DIGEST_FROM, %s secrets)" % names
    if previous is False:
        return "previous round: not read (gh couldn't read the comments)"
    if previous is None:
        return "previous round: none yet"
    flags = previous["state"]["flags"]
    said = "sent" if "mailed" in flags else "may have been sent" if "mailing" in flags else "not sent"
    return "previous round: " + said


def listed(numbers, urls):
    return ", ".join("[#%d](%s)" % (n, urls[n][0]) if n in urls else "#%d" % n for n in sorted(numbers)) or "none"


def compose(login, note, ran, now_open, before, run_id, titles=None, groups=None, pages=()):
    """The comment and its state marker. Issues are named by number and link only: a title is never copied into the
    request an owner pastes into an agent. Sections are features; a milestone title shows only as a suffix on a request."""
    titles, groups = titles or {}, groups or {}
    new, still, fixed = set(now_open) - set(before), set(now_open) & set(before), set(before) - set(now_open)
    head = ("@%s " % login if login else "") + "Automation round, %s UTC" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    out = [head, ""] + ([note, ""] if note else [])
    if "DIGEST_LAST" in os.environ:  # the Mac's tick: when it last ran, and whether a gap went unserved
        at, prev = rounds.created(run_id) or datetime.datetime.now(datetime.timezone.utc), workflows.when(os.environ["DIGEST_LAST"])
        gap = (at - prev).total_seconds() / 3600 if prev else 0
        out += ["Last ran: %s, previous run %s%s" % (at.strftime("%Y-%m-%d %H:%M"), prev.strftime("%Y-%m-%d %H:%M") if prev else "none",
                                                       " (%d hours earlier)" % gap if prev else ""), ""]
        out += ["MISSED: no run for %d hours (Mac asleep or offline)" % gap, ""] * bool(prev and gap > float(os.environ.get("DIGEST_INTERVAL") or 24) + 1)
        out += [os.environ[k] for k in ("DIGEST_DRIFT", "DIGEST_JUDGE") if os.environ.get(k)] + [""] * bool(os.environ.get("DIGEST_DRIFT") or os.environ.get("DIGEST_JUDGE"))
    out += ["| Routine | Result |", "|---|---|"]
    out += ["| %s | %s |" % (name, said.replace("|", "\\|")) for name, said in ran] + [""]
    home = {n: groups.get(n) or (titles.get(now_open[n][1]) if titles.get(now_open[n][1]) in pages else NO_FEATURE) for n in now_open}
    home.update({n: titles.get(before[n]) if titles.get(before[n]) in pages else NO_FEATURE for n in fixed})
    for feature in sorted(set(home.values()), key=lambda f: (f == NO_FEATURE, f.lower())):  # features by name, then No feature
        out += ["### %s" % feature, ""]
        pick = lambda pool: {n for n in pool if home[n] == feature}  # noqa: E731
        out += ["**New** (%d): %s" % (len(pick(new)), listed(pick(new), now_open)), "",
                "**Still open** (%d): %s" % (len(pick(still)), listed(pick(still), now_open)), "",
                "**Fixed** (%d): %s" % (len(pick(fixed)), listed(pick(fixed), {})), ""]
        mine = sorted(n for n in now_open if home[n] == feature)
        out += ['- [#%d](%s): `/workflow-delivery go "Fix #%d"`%s' % (n, now_open[n][0], n, " (milestone %s)" % titles[now_open[n][1]]
                if titles.get(now_open[n][1]) else "") for n in mine] + ([""] if mine else [])
    marker = rounds.marker(run_id, {n: now_open[n][1] for n in now_open})
    return "\n".join(out + [marker]) + "\n", marker


def cmd_digest(args):
    cfg, in_actions = config(args.root), os.environ.get("GITHUB_ACTIONS") == "true"
    live = bool(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")) or args.live
    if in_actions and not live:
        print("DIGEST: no GH_TOKEN in this step, so nothing was posted. Fix: give the step GH_TOKEN: the job's token.")
        return 1
    if live:
        for label in LABELS + ("automation",):  # a label that doesn't exist yet would make its listing fail
            gh("label", "create", label)
    pages = features(args.root)
    now_open, groups = open_issues(pages) if live else ({}, {})
    found = rounds.digest_issue() if live else (None, "")
    if now_open is None or found is None:
        print("DIGEST: gh couldn't read the issues, so nothing was posted.")
        return 1
    number, body = found
    state = rounds.parse(body)
    before = state["open"] if state else {}
    run_id = os.environ.get("DIGEST_RUN") or "local"
    if state and run_id != "local":
        if state["run"] == run_id:
            print("DIGEST: already posted for run %s (DIGEST_ALREADY)" % run_id)
            return 0
        if rounds.order(state["run"]) > rounds.order(run_id):
            print("DIGEST: run %s is older than the round on the issue (run %s); nothing posted (DIGEST_STALE)" % (run_id, state["run"]))
            return 0
    if number is not None and run_id != "local":
        earlier = rounds.run_comment(number, run_id)
        if earlier is False:
            print("DIGEST: gh couldn't read the digest comments, so nothing was posted.")
            return 1
        if earlier:  # an earlier attempt posted it but couldn't save the body: repair, never post twice
            gh("issue", "edit", str(number), body=INTRO + rounds.marker(run_id, earlier["state"]["open"]))
            print("DIGEST: already posted for run %s; state repaired (DIGEST_REPAIRED)" % run_id)
            return 0
    login, note = owner_of(args, cfg) if live else (args.owner or cfg.get("digest_owner") or "", "")
    previous = rounds.run_comment(number, state["run"]) if live and number is not None and state else None
    cost = rounds.round_cost(run_id, state["run"] if state else None) if live and (in_actions or rounds.is_local(run_id)) else None
    ran = [("regression", regression_line() if live else "not read (dry run)"),
           ("health", health_line(os.environ.get("HEALTH_REPORT") or "")),
           ("round cost", rounds.line(cost) if cost else "not read (dry run)" if not live else rounds.line({"error": "only read in Actions"})),
           ("email", email_line(cfg, previous))]
    if CUT:
        ran.append(("issues", "TRUNCATED: %s listed %d open issues, so the counts below may be cut off (TRUNCATED)" % (", ".join(CUT), ISSUE_LIMIT)))
    titles = (rounds.milestone_titles() if live else {}) or {}  # unreadable titles show nowhere: no note, no failure
    comment, marker = compose(login, note, ran, now_open, before, run_id, titles, groups, pages)
    if cost is not None:
        rounds.summary("## Round\n\n" + rounds.line(cost) + "\n")
        if cost.get("over"):
            print("::warning::" + rounds.line(cost))
    if not live:
        print(comment + "DRY RUN: no GH_TOKEN, so nothing was posted.")
        return 0
    if number is None:
        gh("label", "create", "automation", "--description", "The Automation digest")  # an existing one keeps its colour
        made = gh("issue", "create", "--title", TITLE, "--label", "automation",
                  body=INTRO + "<!-- automation-digest open= run=none -->")  # no milestone; its state only once its comment is posted
        number = (re.findall(r"/issues/(\d+)", made.stdout) or [None])[-1]
        if made.returncode or not number:
            print("DIGEST: couldn't create the digest issue: %s" % (made.stderr.strip()[:200] or "no issue number"))
            return 1
        if gh("issue", "pin", number).returncode:
            print("WARNING: couldn't pin issue #%s (a repo pins at most three); the digest still posts there." % number)
    posted = gh("issue", "comment", str(number), body=comment)
    if posted.returncode:
        print("DIGEST: couldn't comment on #%s: %s" % (number, posted.stderr.strip()[:200]))
        return 1
    if run_id == "local" and state and state["run"].isdigit():  # a local digest keeps the last Actions run on the issue
        marker = rounds.marker(state["run"], {n: now_open[n][1] for n in now_open})
    if gh("issue", "edit", str(number), body=INTRO + marker).returncode:  # the state the next round compares with
        print("DIGEST: posted on #%s, but couldn't save its state; a rerun repairs it from the comment" % number)
        return 1
    print("DIGEST: posted on #%s (%d open)" % (number, len(now_open)))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("workflow")
    item.add_argument("--check", action="store_true")
    item.set_defaults(func=cmd_workflow)
    item = sub.add_parser("local")
    item.add_argument("action", choices=("install", "uninstall", "status", "plist", "tick"))
    item.add_argument("--load", action="store_true")
    item.add_argument("--json", action="store_true")
    item.add_argument("--scheduled", action="store_true")
    item.add_argument("--dry-run", action="store_true")
    item.add_argument("--repo", default="")
    item.set_defaults(func=cmd_local)
    item = sub.add_parser("digest")
    item.add_argument("--owner", default="")
    item.add_argument("--live", action="store_true", help="post with your own gh login")
    item.set_defaults(func=cmd_digest)
    for each in sub.choices.values():
        each.add_argument("--root", default="")
    args = parser.parse_args()
    if not args.root:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        args.root = top.stdout.strip() or os.getcwd()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
