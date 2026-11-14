#!/usr/bin/env python3
"""Every setting in one table: where it lives, its default and a one-line explanation.

usage: settings.py reference [--write]   print the settings reference (--write saves references/settings.md)
       settings.py fill-repo [--repo DIR]  add every missing repo setting, with its default, to .loop/config.json
       settings.py fill-private [--file F]  add every missing private setting to the private flow file (mode 0600)
       settings.py show [--repo DIR] [--json]  each value with its layer (default, repo or local) and home

Repo settings live in .loop/config.json (committed). Private settings live outside the repo and are never committed: the flow
file ~/.workflow-loop/flow.json ($LOOP_FLOW), the health rules health.json ($LOOP_HEALTH) and the followed repos file. A value
already set is never overwritten, and every script reads the files fresh, so a change takes effect at once.
"""
import argparse
import functools
import importlib.util
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

REPO, PRIVATE = "repo", "private"
RISKY = ["^\\.github/", "(^|/)auth", "(^|/)migrations?/", "(^|/)(schema|data)\\b"]
# (key, home, default, one-line explanation)
TABLE = [
    ("base", REPO, "main", "The branch goals start from and pull requests target."),
    ("agent_command", REPO, [], "The command that runs a goal in the background; the prompt is its last argument."),
    ("parallel", REPO, 0, "Workers running at once; 0 means unlimited."),
    ("cadence", REPO, "30", "Minutes between check-ins of the operation session, 1 to 60, or off."),
    ("auto_approve", REPO, False, "true approves what a flow step leaves for the owner, logged as auto-approved."),
    ("auto_merge", REPO, False, "true lets the release step merge a goal's pull request and publish its release."),
    ("pr_bumps_version", REPO, False, "true moves the last number of the version file once on a goal's branch."),
    ("version_file", REPO, "VERSION", "The file that holds the version; a release bumps it and writes the changelog."),
    ("routines", REPO, [], "Commands the release step runs on the base branch before it merges."),
    ("regression_cron", REPO, "17 */4 * * *", "Five cron fields: when the full regression runs: in GitHub Actions for a public repo, with each Mac tick for a private one; off turns it off."),
    ("health_cron", REPO, "47 */4 * * *", "Five cron fields (every N hours, or fixed hours): when health with the judge and its digest run on the Mac; off turns it off."),
    ("judge_env", REPO, "ANTHROPIC_API_KEY", "No longer read: the judge runs on the Mac with your own claude login. Kept so old configs stay valid."),
    ("judge_setup", REPO, "", "No longer read: kept so old configs stay valid."),
    ("digest_owner", REPO, "", "Who the digest comment mentions; empty means the repo owner (an organisation notifies no one)."),
    ("digest_mail", REPO, "cloudflare", "How the round's digest is mailed: cloudflare (Email Service), smtp, or off; the address and keys live only in Actions secrets."),
    ("smtp_host", REPO, "smtp.gmail.com", "The SMTP server digest_mail smtp sends through (with DIGEST_SMTP_USER and DIGEST_SMTP_PASSWORD secrets)."),
    ("smtp_port", REPO, 465, "465 (TLS) or 587 (STARTTLS) for digest_mail smtp."),
    ("review_depth", REPO, "full", "full runs the plan and review skills' whole pipeline and refuses a condensed one; condensed allows a shorter run."),
    ("criteria", REPO, True, "true makes docs check enforce the PRD page contract (Problem, Requirements, Non-goals, Success metrics, Tests)."),
    ("criteria_max", REPO, 10, "Most criteria a wiki page may hold, 1 to 50, default 10; docs check and health fail a page over it."),
    ("wiki_dir", REPO, "docs/wiki", "The folder of wiki pages."),
    ("risky_paths", REPO, RISKY, "Regexes for paths whose goals need extra care."),
    ("step_limit", REPO, 0, "Seconds one flow step may run when the flow file sets no limit; 0 means the built-in limit."),
    ("goal_lane_minutes", REPO, 10, "Minutes a goal's regression lane may take before health warns and its LANE line says over."),
    ("goal_levels", REPO, "land", "Row levels a goal lane plans from: land, or nightly for land and nightly rows."),
    ("regression_runs", REPO, "", "Where the full regression runs: actions (a public repo) or mac (with each Mac tick: a private repo, or a public one recorded mac); setup records it from the repo's live visibility, keeps a recorded mac, and unset means it is not known (nothing is written for GitHub)."),
    ("automation", REPO, [], "Routines the Automation table lists: {name, does, cadence, runs: github:FILE, mac:LABEL or claude:TASK}; setup declares the three built-in ones."),
    ("topics", REPO, {}, "Home's Topic column: {topic: [feature pages]}; rows are grouped by topic in this order, unlisted pages sit under Other, and empty means no Topic column."),
    ("ci_levels", REPO, "nightly", "Target of the scheduled and tag regression runs: nightly (every row) or land."),
    ("token_budget", REPO, 0, "Tokens a goal may spend over all steps before no new step starts; 0 means no budget."),
    ("test_budget_minutes", REPO, 15, "Minutes one in-loop test run (qa, ship, pull request) may take, 15 or more; rows past it are left to the scheduled full suite."),
    ("prep_budget_minutes", REPO, 15, "Minutes a lane may spend before its first test row (preparing, planning, waiting for a slot), 15 or more; a lane past it stops and says which part ran long."),
    ("step_budget_minutes", REPO, 30, "Minutes one review or ship step may take, 15 or more; a step at its limit finishes with what it has done and records what it left."),
    ("stale_branch_days", REPO, 14, "Days a local branch on no remote may sit before health lists it with its removal command."),
    ("mend", REPO, False, "true lets watch start a fresh agent for a failed goal."),
    ("mend_wait", REPO, 120, "Seconds a failed goal waits before a mender starts."),
    ("max_tries", REPO, 3, "Failed tries a goal gets before it stops and files a finding."),
    ("resume_on_limit", REPO, False, "true lets watch resume a goal that hit a usage limit."),
    ("limit_wait", REPO, 1800, "Seconds to wait after a usage limit before resuming."),
    ("watch_interval", REPO, 20, "Seconds between rounds of watch."),
    ("agent_files", REPO, ["CLAUDE.md", "AGENTS.md"], "Agent entry files setup wires the workflow-loop block into; [] turns wiring off."),
    ("template_repo", REPO, "", "The template's GitHub repo (owner/name) update reads releases from, when the installed package names none."),
    ("reply_hook", REPO, True, "false turns off the reply-format hook (setup.py --reply-hook installs it) in the operation session."),
    ("govern_hook", REPO, True, "false turns off the govern-only hook (setup.py --govern-hook installs it): edits, commits and pushes refused in the operation session."),
    ("full_auto", REPO, True, "true lets the operation session answer a worker's routine decision with its recommended option, logged; risky ones wait."),
    ("pool_size", REPO, 20, "Idle worker sessions the session pool keeps; when it runs low the operation session asks you to create the missing ones."),
    ("silent_minutes", REPO, 30, "Minutes a worker may send nothing before it shows under Needs you; LOOP_SESSION_QUIET (seconds) overrides it."),
    ("health_script_bytes", REPO, 20480, "Bytes a script may reach before health's Size group fails it (warns at 90%)."),
    ("health_skill_lines", REPO, 150, "Lines a SKILL.md may reach before health's Size group fails it."),
    ("feature_labels", REPO, False, "true makes health file and the regression workflow tag each issue feature:<Page> for its feature, and create that label; off by default, so issues carry their group or regression label only."),
    ("command", PRIVATE, ["claude", "-p"], "Flow file: the agent command that runs each flow step unattended."),
    ("allowed_tools", PRIVATE, [], "Flow file: tools a step's agent may use, passed as --allowedTools; empty adds nothing."),
    ("model", PRIVATE, "", "Flow file: the model a step's agent uses, passed as --model; empty keeps the command's own."),
    ("suite", PRIVATE, {"idea": "built-in", "plan": "built-in", "review": "built-in", "qa": "built-in", "ship": "built-in"},
     "Flow file: the skill for each step; built-in runs delivery's own routine until you name your own."),
    ("steps", PRIVATE, {}, "Flow file: a skill for any one step, replacing the suite's."),
    ("overrides", PRIVATE, {}, "Flow file: per step {skill, model, allowed_tools} that replace the defaults above."),
    ("env", PRIVATE, {}, "Flow file: environment that puts the skills in their unattended mode."),
    ("probe", PRIVATE, [], "Flow file: a command that prints probe_expect when the skills run unattended."),
    ("probe_expect", PRIVATE, "unattended", "Flow file: the word the probe must print."),
    ("leak_prefixes", PRIVATE, [], "Flow file: case-insensitive regexes the package scan blocks in any file or file name, as your leak hook does."),
    ("full_markers", PRIVATE, {}, "Flow file: per step, strings a full plan or review reply must contain, e.g. {\"review\": [\"...\"]}; none checked when empty."),
    ("limit", PRIVATE, 2700, "Flow file: seconds one flow step may run."),
    ("lane_limit", PRIVATE, 2, "Flow file: full regression lanes that may run at once on this machine; more wait their turn (0 is unlimited)."),
    ("rules", PRIVATE, [], "Health file: your own health rules, each {name, command, fix}."),
    ("repos", PRIVATE, [], "Followed repos: one path a line in the repos file, shown on the board."),
]
FLOW_KEYS = ("command", "allowed_tools", "model", "suite", "steps", "overrides", "env", "probe", "probe_expect", "full_markers", "limit")
DEPTHS = ("full", "condensed")


def keys(home):
    return [row for row in TABLE if row[1] == home]


def shown(value):
    return json.dumps(value) if not isinstance(value, str) else value or "(empty)"


def reference():
    out = ["# Settings reference", "",
           "Generated by `settings.py reference --write`; do not edit by hand. Setup writes both halves with these defaults.",
           "", "## Repo settings", "", "In `.loop/config.json`, committed and shared. 0 for `parallel` means unlimited.", "",
           "| Setting | Default | What it does |", "|---|---|---|"]
    out += ["| `%s` | `%s` | %s |" % (k, shown(d), t) for k, _, d, t in keys(REPO)]
    out += ["", "## Private settings", "", "Outside the repo, never committed: `~/.workflow-loop/flow.json` (or `$LOOP_FLOW`), "
            "`~/.workflow-loop/health.json` (or `$LOOP_HEALTH`) and `~/.workflow-loop/repos`.", "",
            "| Setting | Default | What it does |", "|---|---|---|"]
    out += ["| `%s` | `%s` | %s |" % (k, shown(d), t) for k, _, d, t in keys(PRIVATE)]
    return "\n".join(out) + "\n"


def write_json(path, data, mode=None):
    path = os.path.realpath(path)  # a symlinked settings file (dotfiles) is written through, never replaced
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if mode is None and os.path.exists(path):
        mode = os.stat(path).st_mode & 0o777  # keep the file's own mode
    temp = "%s.%d.tmp" % (path, os.getpid())  # a full disk must not leave a truncated settings file
    try:
        with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode or 0o644), "w") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        if mode:
            os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.remove(temp)


def load(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


# What setup leaves in .loop/health-rules.json when the repo has none.
HEALTH_RULES = {"_comment": "rules: [{name, group (a health group or repo), feature, command (words; exit 0 pass, 2 warn, 1 fail), fix, "
                "break (a command that makes it fail)}]. off: {default rule: reason}.", "rules": [], "off": {}}


def repo_defaults():
    return {k: d for k, _, d, _ in keys(REPO)}


def check_depth(held, path):
    """Refuse an unknown review_depth: anything but full or condensed would silently count as full."""
    if "review_depth" in held and held["review_depth"] not in DEPTHS:
        sys.exit("REFUSED: review_depth is %r in %s. Fix: full or condensed." % (held["review_depth"], path))


def repo_help(held):
    """The config's _help map: review_depth's and criteria_max's explanations added when missing, the rest kept."""
    found = held.get("_help") if isinstance(held.get("_help"), dict) else {}
    return dict({k: t for k, _, _, t in TABLE if k in ("review_depth", "criteria_max")}, **found)


def private_path():
    return os.path.expanduser(os.environ.get("LOOP_FLOW") or "~/.workflow-loop/flow.json")


def fill_private(path=None):
    """Add each missing flow-file setting with its default and a one-line explanation. Never overwrites. Returns what was added."""
    path = path or private_path()
    held = load(path)
    added = [k for k in FLOW_KEYS if k not in held]
    help_ = dict(held.get("_help") or {})
    new = dict(held)
    for key, home, default, text in TABLE:
        if key in FLOW_KEYS and key not in new:
            new[key] = default
        if key in FLOW_KEYS and key not in help_:
            help_[key] = text.split(": ", 1)[-1]
    suite = new.get("suite")
    if isinstance(suite, dict) and not any(suite.values()) and not new.get("steps"):  # never configured: the built-in flow
        new["suite"] = dict((key, "built-in") for key in ("idea", "plan", "review", "qa", "ship"))
        added.append("suite")
    new["_help"] = help_
    if new != held:
        write_json(path, new, 0o600)
    home = os.path.expanduser("~/.workflow-loop")
    health = os.environ.get("LOOP_HEALTH") or os.path.join(home, "health.json")
    if not os.path.exists(health):
        write_json(health, {"rules": []}, 0o600)
    repos = os.path.join(home, "repos")
    if not os.path.exists(repos):
        open(repos, "w").close()
        os.chmod(repos, 0o600)
    return added


def health_path():
    return os.path.expanduser(os.environ.get("LOOP_HEALTH") or "~/.workflow-loop/health.json")


@functools.lru_cache(None)
def names():
    """The owner's private-name patterns (workflow-delivery's private.py reads the list); none when absent or unreadable."""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-delivery", "scripts", "private.py")
        spec = importlib.util.spec_from_file_location("private_names", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        state, found, _ = mod.patterns()
        return tuple(p for _, p in found) if state == "on" else ()
    except Exception:
        return ()


def private_value(text):
    """True when text holds the home folder, an email, a token-looking string or a match in the private-name list."""
    text, home = str(text), os.path.expanduser("~")
    return bool((len(home) > 1 and home in text) or any(p.search(text) for p in names())
                or re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+|\b(?:sk-|ghp_|github_pat_|xox[abp]-|AKIA)[\w-]{8,}|\b[A-Za-z0-9]{41,}\b", text))


def resolve(repo):
    """[(setting, value, layer, home)]: default, then repo (.loop/config.json), then local (flow or health file), a later layer
    winning. Each setting has one home today, so a key is its default or its home's value."""
    held, flow, health = load(os.path.join(repo, ".loop", "config.json")), load(private_path()), load(health_path())
    named = lambda var, path: "$" + var if os.environ.get(var) else path.replace(os.path.expanduser("~"), "~")
    homes = {"flow": named("LOOP_FLOW", private_path()), "health": named("LOOP_HEALTH", health_path())}
    rows = []
    for key, home, default, _ in TABLE:
        src = health if key == "rules" else flow
        at = ".loop/config.json" if home == REPO else "~/.workflow-loop/repos" if key == "repos" else homes["health" if key == "rules" else "flow"]
        value, layer = default, "default"
        if home == PRIVATE and key in src:
            value, layer = src[key], "local"
        if key in held:
            value, layer = held[key], "repo" if home == REPO else "repo (local setting in a committed file)"
        rows.append((key, value, layer, at))
    return rows


def show(repo, as_json):
    """Each setting with the layer its value came from; a private value is withheld and env prints its names only."""
    out = []
    for key, value, layer, at in resolve(repo):
        value = sorted(value) if key == "env" and isinstance(value, dict) else value
        out.append((key, "(withheld: holds a private value)" if private_value(json.dumps(value)) else value, layer, at))
    if as_json:
        return print(json.dumps([dict(zip(("setting", "value", "layer", "home"), r)) for r in out], indent=2))
    print("| setting | value | layer | home |\n|---|---|---|---|")
    print("\n".join("| %s | %s | %s | %s |" % (k, v if isinstance(v, str) else shown(v), layer, at) for k, v, layer, at in out))
    print("NOTE: scripts read repo values directly; a local value wins only where its own home is read")


def fill_repo(path):
    """Add each missing repo setting, with its default and _help line, to the config at path; never changes a value set.
    Keeps the config's key order, new keys last. Returns what was added (update's repo half calls it too)."""
    held = load(path)
    if "criteria_max" in held and (isinstance(held["criteria_max"], bool) or not isinstance(held["criteria_max"], int)
                                   or not 1 <= held["criteria_max"] <= 50):
        sys.exit("REFUSED: criteria_max is %r in %s. Fix: a whole number from 1 to 50 (default 10)." % (held["criteria_max"], path))
    check_depth(held, path)
    added = [k for k in repo_defaults() if k not in held]
    merged = dict(held, **{k: v for k, v in repo_defaults().items() if k not in held})
    merged["_help"] = repo_help(held)
    import agents
    merged["automation"] = agents.fill_automation(merged, os.path.dirname(os.path.dirname(os.path.abspath(path))))
    if merged != held:
        write_json(path, merged)
    rules = os.path.join(os.path.dirname(os.path.abspath(path)), "health-rules.json")
    if not os.path.exists(rules):
        write_json(rules, HEALTH_RULES)
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    ref = sub.add_parser("reference")
    ref.add_argument("--write", action="store_true")
    fr = sub.add_parser("fill-repo")
    fr.add_argument("--repo", default=".")
    fp = sub.add_parser("fill-private")
    fp.add_argument("--file", default="")
    sh = sub.add_parser("show")
    sh.add_argument("--repo", default=".")
    sh.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.command == "reference":
        text = reference()
        if args.write:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references", "settings.md")
            with open(path, "w") as handle:
                handle.write(text)
            print("WROTE " + os.path.normpath(path))
        else:
            print(text, end="")
    elif args.command == "show":
        top = subprocess.run(["git", "-C", args.repo, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
        show(top or args.repo, args.json)
    elif args.command == "fill-repo":
        top = subprocess.run(["git", "-C", args.repo, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
        path = os.path.join(top or args.repo, ".loop", "config.json")
        print("FILLED %s: %s" % (path, ", ".join(fill_repo(path)) or "nothing missing"))
    else:
        added = fill_private(args.file or None)
        print("FILLED %s: %s" % (args.file or private_path(), ", ".join(added) or "nothing missing"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
