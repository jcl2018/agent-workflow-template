#!/usr/bin/env python3
"""Run the health routine on a schedule in GitHub Actions, and post one digest comment per round.

usage: automation.py workflow [--check]  write .github/workflows/health.yml and mail-test.yml from .loop/config.json;
                                         --check only says which of them is missing or stale (exit 1)
       automation.py digest [--owner L]  post this round's comment on the pinned Automation digest issue

The workflow checks the routine (health_cron "off" makes a run write nothing), runs health check into the run summary,
files the groups a runner can read (size, criteria, docs) on their feature's milestone as health:<group> issues, runs
the judge only when the secret named by judge_env is set, posts the digest, then mails it (mail.py). Nothing pushes.
The digest lists what ran (regression's latest run, health's verdict, the round's cost, the email), then per milestone
the new, still-open and fixed issues labelled regression or health since the last comment, each open one with its link
and the request to give the agent; it mentions digest_owner (default: the repo owner). Its state lives in the digest
issue's body (rounds.py), so a rerun of the same run posts nothing twice and an older run never overwrites a newer one.
Outside Actions with no GH_TOKEN it only prints the comment.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rounds  # noqa: E402
import workflows  # noqa: E402

CRON = "47 */4 * * *"
KEY_NAME = "ANTHROPIC_API_KEY"  # the name of the Actions secret, not a secret
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


def settings(root):
    """(health_cron, judge_env) from the config, or a REFUSED exit when either can't be written into a workflow."""
    cfg = config(root)
    cron, secret = cfg.get("health_cron") or CRON, cfg.get("judge_env") or KEY_NAME
    if cron != "off" and not (isinstance(cron, str) and re.fullmatch(r"[0-9A-Za-z*/,\- ]+", cron) and len(cron.split()) == 5):
        sys.exit("REFUSED: health_cron is not five cron fields or off. Fix: edit .loop/config.json.")
    if not isinstance(secret, str) or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", secret):
        sys.exit("REFUSED: judge_env %r is not a secret name (capitals, digits, _). Fix: edit .loop/config.json." % secret)
    return cron, secret


def render(cron, secret):
    return workflows.health(cron, secret)


def wanted(root):
    cron, secret = settings(root)
    base = os.path.join(root, ".github", "workflows")
    return [(os.path.join(base, "health.yml"), workflows.health(cron, secret)),
            (os.path.join(base, "mail-test.yml"), workflows.mail_test())]


def cmd_workflow(args):
    status = 0
    for path, text in wanted(args.root):
        rel = os.path.relpath(path, args.root)
        current = open(path).read() if os.path.exists(path) else None
        if current is not None and not current.startswith(workflows.HEADER):
            if args.check:
                print("NOT_OURS: %s was not written by automation.py, so it is never checked or rewritten (NOT_OURS)" % rel)
                continue
            sys.exit("REFUSED: %s exists, and this tool didn't write it. Fix: merge by hand." % path)
        if args.check:
            if current != text:
                print("STALE_WORKFLOW: %s %s what automation.py writes. Fix: python3 skills/workflow-health/scripts/"
                      "automation.py workflow, then commit (STALE_WORKFLOW)" % (rel, "is missing, unlike" if current is None else "differs from"))
                status = 1
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as handle:
            handle.write(text)
        print("WROTE " + path)
    return status


def open_issues():
    """{number: (url, milestone number or 0)} of the open issues the digest follows; None when gh can't list them."""
    found = {}
    for label in LABELS:
        done = gh("issue", "list", "--label", label, "--state", "open", "--limit", "300", "--json", "number,url,milestone")
        if done.returncode:
            return None
        found.update({item["number"]: (item["url"], int((item.get("milestone") or {}).get("number") or 0))
                      for item in loads(done, [])})
    return found


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


def compose(login, note, ran, now_open, before, run_id, titles=None):
    """The comment and its state marker. Issues are named by number and link only: a title is never copied into the
    request an owner pastes into an agent. Milestone titles appear only as section headings."""
    titles = titles or {}
    new, still, fixed = set(now_open) - set(before), set(now_open) & set(before), set(before) - set(now_open)
    head = ("@%s " % login if login else "") + "Automation round, %s UTC" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    out = [head, ""] + ([note, ""] if note else []) + ["| Routine | Result |", "|---|---|"]
    out += ["| %s | %s |" % (name, said.replace("|", "\\|")) for name, said in ran] + [""]
    home = {n: now_open[n][1] for n in now_open}
    home.update({n: before[n] for n in fixed})
    home = {n: m if m in titles else 0 for n, m in home.items()}  # one No milestone section, unknown ones included
    def rank(m):  # features by title, then Backlog, then issues with no (or an unknown) milestone
        title = titles.get(m) if m else None
        return (2, "") if not title else (1, "") if title == "Backlog" else (0, title.lower())
    for milestone in sorted(set(home.values()), key=rank):
        out += ["### %s" % ((titles.get(milestone) if milestone else None) or "No milestone"), ""]
        pick = lambda pool: {n for n in pool if home[n] == milestone}  # noqa: E731
        out += ["**New** (%d): %s" % (len(pick(new)), listed(pick(new), now_open)), "",
                "**Still open** (%d): %s" % (len(pick(still)), listed(pick(still), now_open)), "",
                "**Fixed** (%d): %s" % (len(pick(fixed)), listed(pick(fixed), {})), ""]
        mine = sorted(n for n in now_open if home[n] == milestone)
        out += ['- [#%d](%s): `/workflow-delivery go "Fix #%d"`' % (n, now_open[n][0], n) for n in mine] + ([""] if mine else [])
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
    now_open = open_issues() if live else {}
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
            gh("issue", "edit", str(number), "--body", INTRO + rounds.marker(run_id, earlier["state"]["open"]))
            print("DIGEST: already posted for run %s; state repaired (DIGEST_REPAIRED)" % run_id)
            return 0
    login, note = owner_of(args, cfg) if live else (args.owner or cfg.get("digest_owner") or "", "")
    previous = rounds.run_comment(number, state["run"]) if live and number is not None and state else None
    cost = rounds.round_cost(run_id, state["run"] if state else None) if live and in_actions else None
    ran = [("regression", regression_line() if live else "not read (dry run)"),
           ("health", health_line(os.environ.get("HEALTH_REPORT") or "")),
           ("round cost", rounds.line(cost) if cost else "not read (dry run)" if not live else rounds.line({"error": "only read in Actions"})),
           ("email", email_line(cfg, previous))]
    titles = rounds.milestone_titles() if live else {}
    if titles is None:
        note, titles = (note + " " if note else "") + "Milestones couldn't be read, so issues are listed under No milestone.", {}
    comment, marker = compose(login, note, ran, now_open, before, run_id, titles)
    if cost is not None:
        rounds.summary("## Round\n\n" + rounds.line(cost) + "\n")
        if cost.get("over"):
            print("::warning::" + rounds.line(cost))
    if not live:
        print(comment + "DRY RUN: no GH_TOKEN, so nothing was posted.")
        return 0
    if number is None:
        gh("label", "create", "automation", "--description", "The Automation digest")  # an existing one keeps its colour
        made = gh("issue", "create", "--title", TITLE, "--label", "automation", "--body",
                  INTRO + "<!-- automation-digest open= run=none -->")  # this round's state only once its comment is posted
        number = (re.findall(r"/issues/(\d+)", made.stdout) or [None])[-1]
        if made.returncode or not number:
            print("DIGEST: couldn't create the digest issue: %s" % (made.stderr.strip()[:200] or "no issue number"))
            return 1
        if gh("issue", "pin", number).returncode:
            print("WARNING: couldn't pin issue #%s (a repo pins at most three); the digest still posts there." % number)
    posted = gh("issue", "comment", str(number), "--body", comment)
    if posted.returncode:
        print("DIGEST: couldn't comment on #%s: %s" % (number, posted.stderr.strip()[:200]))
        return 1
    if run_id == "local" and state and state["run"].isdigit():  # a local digest keeps the last Actions run on the issue
        marker = rounds.marker(state["run"], {n: now_open[n][1] for n in now_open})
    if gh("issue", "edit", str(number), "--body", INTRO + marker).returncode:  # the state the next round compares with
        print("DIGEST: posted on #%s, but couldn't save its state; a rerun repairs it from the comment" % number)
        return 1
    print("DIGEST: posted on #%s (%d open)" % (number, len(now_open)))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("workflow")
    item.add_argument("--check", action="store_true", help="say which workflow is missing or stale; write nothing")
    item.set_defaults(func=cmd_workflow)
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
