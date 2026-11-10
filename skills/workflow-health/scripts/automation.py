#!/usr/bin/env python3
"""Run the health routine on a schedule in GitHub Actions, and post one digest comment per round.

usage: automation.py workflow            write .github/workflows/health.yml from health_cron in .loop/config.json
       automation.py digest [--owner L]  post this round's comment on the pinned Automation digest issue

The workflow checks the routine (health_cron "off" makes a run write nothing), runs health check into the run summary,
files the groups a runner can read (size, criteria, docs) on the Backlog milestone as health:<group> issues, runs the judge only when
the secret named by judge_env is set, then posts the digest. Nothing in it pushes.
The digest lists what ran (regression's latest run, health's verdict), the new, still-open and fixed issues labelled
regression or health since the last comment, and one request per open issue; it mentions digest_owner (default: the
repo owner). Its state lives in the digest issue's body, so a rerun of the same run posts nothing twice. Outside Actions
with no GH_TOKEN it only prints the comment.
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

CRON = "47 */4 * * *"
KEY_NAME = "ANTHROPIC_API_KEY"  # the name of the Actions secret, not a secret
GROUPS = "size,criteria,docs"  # what a runner can read: cost, Mine and two hygiene checks need this machine's run records
LABELS = ("regression", "health")  # the issues the digest follows: failing tests and health findings
TITLE = "Automation digest"
STATE = re.compile(r"<!-- automation-digest open=([\d,]*) run=(\S*) -->")

WORKFLOW = r"""# Written by workflow-health (automation.py). It reads .loop/config.json.
name: health
on:
@SCHEDULE@  workflow_dispatch:
permissions:
  contents: read
  issues: write
  actions: read
concurrency:
  group: health
  cancel-in-progress: false
jobs:
  health:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Check the routine
        id: routine
        env:
          EVENT: ${{ github.event_name }}
        run: |
          cron=$(python3 -c 'import json; print(json.load(open(".loop/config.json")).get("health_cron") or "")' 2>/dev/null || true)
          if [ "$cron" = off ] && [ "$EVENT" = schedule ]; then  # off stops the schedule; a run started by hand still runs
            echo "on=false" >> "$GITHUB_OUTPUT"
            echo "OFF: health is off in .loop/config.json (health_cron), so this run writes nothing." | tee -a "$GITHUB_STEP_SUMMARY"
            exit 0
          fi
          if [ ! -f skills/workflow-health/scripts/health.py ]; then
            echo "MISSING: the workflow-health skill is not in this repo's checkout, so health ran nothing and wrote nothing. Fix: commit the skills/ folder, or set health_cron to off." | tee -a "$GITHUB_STEP_SUMMARY"
            exit 1
          fi
          echo "on=true" >> "$GITHUB_OUTPUT"
          if [ -n "$cron" ] && [ "$cron" != "@CRON@" ]; then
            said="SCHEDULE: this workflow runs on '@CRON@' but .loop/config.json says '$cron'. Fix: python3 skills/workflow-health/scripts/automation.py workflow"
            echo "::warning::$said"; echo "$said" >> "$GITHUB_STEP_SUMMARY"
          fi
      - name: Health check
        if: steps.routine.outputs.on == 'true'
        env:
          GH_TOKEN: ${{ github.token }}  # the issue-milestone rule reads the open issues
        run: |
          python3 skills/workflow-health/scripts/health.py check --group @GROUPS@ > "$RUNNER_TEMP/health-report.txt" 2>&1 || true
          { echo "## Health"; echo; echo '```'; cat "$RUNNER_TEMP/health-report.txt"; echo '```'; echo
            echo "Not run here: performance (the Cost rule), Mine and hygiene read this machine's run records, branches and private files, which a runner doesn't have."
          } >> "$GITHUB_STEP_SUMMARY"
      - name: File the findings as tagged issues
        if: always() && steps.routine.outputs.on == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          python3 skills/workflow-health/scripts/milestone.py new backlog --live  # findings are filed on Backlog; it may not exist yet
          python3 skills/workflow-health/scripts/health.py file --group @GROUPS@
      - name: Judge, only with the agent key secret
        if: always() && steps.routine.outputs.on == 'true'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.@SECRET@ }}  # the judge reads this name, whatever the secret is called
        run: |
          set -o pipefail
          if [ -z "$ANTHROPIC_API_KEY" ]; then echo "JUDGE: skipped, no @SECRET@ secret is set." | tee -a "$GITHUB_STEP_SUMMARY"; exit 0; fi
          setup=$(python3 -c 'import json; print(json.load(open(".loop/config.json")).get("judge_setup") or "")')
          [ -z "$setup" ] || env -u ANTHROPIC_API_KEY sh -c "$setup"
          prog=$(python3 -c 'import json; c = json.load(open(".loop/config.json")).get("judge_command"); print(c[0] if isinstance(c, list) and c else "")')
          if [ -z "$prog" ] || ! command -v "$prog" >/dev/null; then
            echo "JUDGE: skipped, the runner has no ${prog:-judge_command}; set judge_setup in .loop/config.json." | tee -a "$GITHUB_STEP_SUMMARY"; exit 0
          fi
          { echo "## Judge"; echo; echo '```'; python3 skills/workflow-health/scripts/health.py judge 2>&1 | sed -n '/^JUDGE/,$p' || true; echo '```'; } >> "$GITHUB_STEP_SUMMARY"  # a red verdict is the report's, not the step's
      - name: Post the digest
        if: always() && steps.routine.outputs.on == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
          HEALTH_REPORT: ${{ runner.temp }}/health-report.txt
          DIGEST_RUN: ${{ github.run_id }}
          DIGEST_REPO_OWNER: ${{ github.repository_owner }}
        run: python3 skills/workflow-health/scripts/automation.py digest
"""


def config(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def render(cron, secret):
    schedule = "" if cron == "off" else '  schedule:\n    - cron: "%s"\n' % cron
    return (WORKFLOW.replace("@SCHEDULE@", schedule).replace("@CRON@", cron).replace("@GROUPS@", GROUPS)
            .replace("@SECRET@", secret))


def settings(root):
    """(health_cron, judge_env) from the config, or a REFUSED exit when either can't be written into a workflow."""
    cfg = config(root)
    cron, secret = cfg.get("health_cron") or CRON, cfg.get("judge_env") or KEY_NAME
    if cron != "off" and not (isinstance(cron, str) and re.fullmatch(r"[0-9A-Za-z*/,\- ]+", cron) and len(cron.split()) == 5):
        sys.exit("REFUSED: health_cron is not five cron fields or off. Fix: edit .loop/config.json.")
    if not isinstance(secret, str) or not re.fullmatch(r"[A-Z_][A-Z0-9_]*", secret):
        sys.exit("REFUSED: judge_env %r is not a secret name (capitals, digits, _). Fix: edit .loop/config.json." % secret)
    return cron, secret


def cmd_workflow(args):
    cron, secret = settings(args.root)
    path = os.path.join(args.root, ".github", "workflows", "health.yml")
    if os.path.exists(path):
        with open(path) as handle:
            if not handle.read().startswith("# Written by workflow-health"):
                sys.exit("REFUSED: %s exists, and this tool didn't write it. Fix: merge by hand." % path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(render(cron, secret))
    print("WROTE " + path)
    return 0


def gh(*args):
    try:
        return subprocess.run(("gh",) + args, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as err:
        return subprocess.CompletedProcess(args, 1, "", str(err))


def backlog():
    """['--milestone', 'Backlog'] when the repo has an open Backlog milestone, else []."""
    try:
        miles = json.loads(gh("api", "repos/{owner}/{repo}/milestones?state=open&per_page=100").stdout)
        return ["--milestone", "Backlog"] if "Backlog" in [m.get("title") for m in miles] else []
    except (ValueError, TypeError, AttributeError):
        return []


def loads(done, default):
    try:
        return json.loads(done.stdout) if done.returncode == 0 and done.stdout.strip() else default
    except ValueError:
        return default


def open_issues():
    """{number: url} of the open issues the digest follows; None when gh can't list them."""
    found = {}
    for label in LABELS:
        done = gh("issue", "list", "--label", label, "--state", "open", "--limit", "300", "--json", "number,url")
        if done.returncode:
            return None
        found.update({item["number"]: item["url"] for item in loads(done, [])})
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


def listed(numbers, urls):
    return ", ".join("[#%d](%s)" % (n, urls.get(n, "")) if urls.get(n) else "#%d" % n for n in sorted(numbers)) or "none"


def compose(login, note, ran, now_open, before, run_id):
    """The comment and the new state marker. Issues are named by number and link only: a title is never copied into
    the request an owner pastes into an agent."""
    new, still, fixed = set(now_open) - before, set(now_open) & before, before - set(now_open)
    head = ("@%s " % login if login else "") + "Automation round, %s UTC" % datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    out = [head, ""] + ([note, ""] if note else []) + ["| Routine | Result |", "|---|---|"]
    out += ["| %s | %s |" % (name, said.replace("|", "\\|")) for name, said in ran] + [""]
    out += ["**New** (%d): %s" % (len(new), listed(new, now_open)), "",
            "**Still open** (%d): %s" % (len(still), listed(still, now_open)), "",
            "**Fixed** (%d): %s" % (len(fixed), listed(fixed, {})), ""]
    if now_open:
        out += ["### Ask the agent", ""] + ['- [#%d](%s): `/workflow-delivery go "Fix #%d"`' % (n, now_open[n], n)
                                           for n in sorted(now_open)] + [""]
    marker = "<!-- automation-digest open=%s run=%s -->" % (",".join(str(n) for n in sorted(now_open)), run_id)
    return "\n".join(out + [marker]) + "\n", marker


def digest_issue():
    """(number, body) of the digest issue, or (None, "") when there is none yet; None when gh can't list issues."""
    done = gh("issue", "list", "--label", "automation", "--state", "all", "--limit", "300", "--json", "number,title,body")
    if done.returncode:
        return None
    hits = sorted((item for item in loads(done, []) if item.get("title") == TITLE and STATE.search(item.get("body") or "")),
                  key=lambda item: item["number"])
    return (hits[0]["number"], hits[0]["body"]) if hits else (None, "")  # the oldest: a later look-alike never takes over


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
    found = digest_issue() if live else (None, "")
    if now_open is None or found is None:
        print("DIGEST: gh couldn't read the issues, so nothing was posted.")
        return 1
    number, body = found
    state = STATE.search(body or "")
    before = {int(n) for n in state.group(1).split(",") if n} if state else set()
    run_id = os.environ.get("DIGEST_RUN") or "local"
    if state and run_id != "local" and state.group(2) == run_id:
        print("DIGEST: already posted for run %s" % run_id)
        return 0
    login, note = owner_of(args, cfg) if live else (args.owner or cfg.get("digest_owner") or "", "")
    ran = [("regression", regression_line() if live else "not read (dry run)"),
           ("health", health_line(os.environ.get("HEALTH_REPORT") or ""))]
    comment, marker = compose(login, note, ran, now_open, before, run_id)
    if not live:
        print(comment + "DRY RUN: no GH_TOKEN, so nothing was posted.")
        return 0
    intro = "The Automation routines post one comment here per round. Watch this issue to get them by email.\n\n"
    if number is None:
        gh("label", "create", "automation", "--description", "The Automation digest")  # an existing one keeps its colour
        made = gh("issue", "create", "--title", TITLE, "--label", "automation", "--body",
                  intro + "<!-- automation-digest open= run=none -->", *backlog())  # its state only once its comment is posted
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
    if gh("issue", "edit", str(number), "--body", intro + marker).returncode:  # the state the next round compares with
        print("DIGEST: posted on #%s, but couldn't save its state, so the next round may repeat these issues" % number)
        return 1
    print("DIGEST: posted on #%s (%d open)" % (number, len(now_open)))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("workflow").set_defaults(func=cmd_workflow)
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
