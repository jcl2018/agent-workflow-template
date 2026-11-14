"""When a requirement with no regression row fails health (HLT-2, REG-1, DOC-1; issue 118).

A requirement with no passing test shows as not enforced. Health warns while it is new and fails only when it stays not
enforced: an Unreviewed requirement warns; a Reviewed one warns for GRACE days after its Reviewed date, then fails.
The date comes from the requirement's own line on its wiki page, so no goal mapping is needed.
"""
import datetime
import glob
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

from defects import PROTOCOLS, SKILLS, clean, mod, read, table, tool

GRACE = 7  # days a Reviewed requirement may stay not enforced (HLT-2: "none stays not enforced over 7 days")


def stamp(root, key):
    """('Reviewed', date), ('Unreviewed', None), or (None, None) when no page holds the requirement."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir", "docs/wiki")
    except (OSError, ValueError):
        folder = "docs/wiki"
    line = re.compile(r"^- %s: \*\*(Unreviewed|Reviewed (\d{4}-\d\d-\d\d))\*\*" % re.escape(key), re.M)
    for page in sorted(glob.glob(os.path.join(root, folder, "*.md"))):
        with open(page) as handle:
            found = line.search(handle.read())
        if found:
            return ("Unreviewed", None) if found.group(1) == "Unreviewed" else ("Reviewed", found.group(2))
    return None, None


def row(root, key, make, today=None):
    """The health row for requirement `key` with no regression row, made with health.py's row()."""
    mark, day = stamp(root, key)
    fix = "add a row with regression.py add"
    if mark == "Unreviewed":
        return make("WARN", "criteria", key, "rows", "not enforced: no regression row yet (Unreviewed)", fix)
    if mark == "Reviewed":
        try:
            age = ((today or datetime.date.today()) - datetime.date.fromisoformat(day)).days
        except ValueError:
            return make("FAIL", "criteria", key, "rows", "Reviewed date %s is not a real date" % day, "fix the date on its line")
        if age <= GRACE:
            return make("WARN", "criteria", key, "rows", "not enforced, %d days since Reviewed %s (fails after %d)"
                        % (age, day, GRACE), fix)
        return make("FAIL", "criteria", key, "rows", "not enforced for %d days since Reviewed %s, over %d" % (age, day, GRACE), fix)
    return make("FAIL", "criteria", key, "rows", "criterion has no regression row", fix)


# The Mine group (health.py reads it through sibling_module("enforce")): The Mine group: the owner's own rules, named in a private file outside the repo.
# 
# ~/.workflow-loop/health.json (or the file LOOP_HEALTH names):
#   {"rules": [{"name": "lint", "command": ["make", "lint"], "fix": "run make lint"}]}
# Each command runs in the repo. Exit 0 is PASS, 2 is WARN, 1 is FAIL; any other exit, a missing command, a timeout
# or an unreadable setting is UNREAD, never a pass. Rules run the owner's commands, so Mine is outside the
# "changes nothing" and "same answer twice" promises of the fixed rules.
# No terminal, no waiting: a prompt from git or gh must fail, not block. health.py sets the same.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

GROUP = "mine"


def setting_path():
    return os.environ.get("LOOP_HEALTH") or os.path.join(os.path.expanduser("~"), ".workflow-loop", "health.json")


def mine_row(state, subject, detail, fix="", family=GROUP, rule="mine", **more):
    return dict({"state": state, "family": family, "subject": subject, "rule": rule, "detail": detail, "fix": fix}, **more)


def words(command):
    return isinstance(command, list) and bool(command) and all(isinstance(part, str) for part in command)


def run_rule(root, rule, name, family=GROUP, label="mine", **more):
    """One rule's row: its command run in root (exit 0 PASS, 2 WARN, 1 FAIL, else UNREAD)."""
    row = lambda state, detail, fix="": mine_row(state, name, detail, fix, family, label, **more)
    command = rule.get("command") if isinstance(rule, dict) else None
    if not words(command):
        return row("UNREAD", "the rule has no command list", "give the rule a command as a list of words")
    fix = str(rule.get("fix") or "run: " + " ".join(command))
    try:
        done = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=int(rule.get("timeout") or 120))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return row("UNREAD", "could not run: %s" % str(error)[:100], fix)
    out = ((done.stdout or "").strip().splitlines() or (done.stderr or "").strip().splitlines() or [""])[-1][:100]
    state = {0: "PASS", 1: "FAIL", 2: "WARN"}.get(done.returncode)
    if state is None:
        return row("UNREAD", "exited %d, not 0, 1 or 2" % done.returncode, fix)
    return row(state, out or "exit %d" % done.returncode, "" if state == "PASS" else fix)


def mine_rows(root):
    path = setting_path()
    if not os.path.exists(path):
        return [mine_row("INFO", "setting", "no private rules set (%s)" % path)]
    try:
        with open(path) as handle:
            rules = json.load(handle)["rules"]
        assert isinstance(rules, list)
    except (OSError, ValueError, KeyError, AssertionError):
        return [mine_row("UNREAD", "setting", "cannot read the private rules at %s" % path, "fix the file: a JSON object with a rules list")]
    rows = []
    for number, rule in enumerate(rules, 1):
        name = rule.get("name") if isinstance(rule, dict) else None
        rows.append(run_rule(root, rule, str(name or "rule-%d" % number)))
    return rows or [mine_row("INFO", "setting", "the private file lists no rules")]


# The repo layer: .loop/health-rules.json, committed. {"rules": [{"name", "group" (one of the twelve, or "repo"), "feature",
# "command", "fix", "break"}], "off": {"<default rule>": "<reason>"}}. A command runs as Mine's does. "break" is a command that
# makes it fail, which the Controls group runs on a copy of the repo. They are the repo's own commands, with the repo's own trust.
REPO_FILE = os.path.join(".loop", "health-rules.json")


def repo_load(root):
    """(rules, off, problems, rows): the valid rules and the off map (empty when the file is absent or unreadable); problems
    are refusal lines (health.py exits 2); rows are the repo group's own INFO and UNREAD rows."""
    note = lambda state, detail, fix="": [mine_row(state, REPO_FILE, detail, fix, "repo", "repo")]
    if not os.path.exists(os.path.join(root, REPO_FILE)):
        return [], {}, [], []
    try:
        with open(os.path.join(root, REPO_FILE)) as handle:
            data = json.load(handle)
        rules, off = data.get("rules", []), data.get("off", {})
        assert isinstance(rules, list) and isinstance(off, dict)
    except (OSError, ValueError, AttributeError, AssertionError):
        return [], {}, [], note("UNREAD", "cannot read the repo rules", "fix the file: a JSON object with a rules list and an off map")
    import report as G
    problems, good, seen, rows = [], [], set(G.RULES), []
    for number, rule in enumerate(rules, 1):
        name = str(rule.get("name") or "rule-%d" % number) if isinstance(rule, dict) else "rule-%d" % number
        group = rule.get("group") if isinstance(rule, dict) else None
        bad = ("is not an object" if not isinstance(rule, dict) else "repeats a name or is a default rule" if name in seen
               else "has no known group (one of the twelve, or repo)" if group not in G.ORDER or group in ("mine", "controls")
               else "has no break command" if not words(rule.get("break")) else "has no command list" if not words(rule.get("command")) else "")
        seen.add(name)
        if bad:
            problems.append("repo rule %s %s. Fix: edit %s" % (name, bad, REPO_FILE))
        else:
            good.append(dict(rule, name=name))
    for key, why in off.items():
        if key not in G.RULES or not (isinstance(why, str) and why.strip()):
            rows += [mine_row("UNREAD", key, "cannot be turned off: %s" % ("not a default rule" if key not in G.RULES else "it needs a reason"),
                              "name a default rule and give a reason in off", "repo", "repo")]
    off = {k: v.strip() for k, v in off.items() if k in G.RULES and isinstance(v, str) and v.strip()}
    return good, off, problems, rows


def repo_rows(root):
    """The repo rules' rows, each in its own group with its feature, then the repo group's own rows."""
    rules, _, _, rows = repo_load(root)
    return [run_rule(root, rule, rule["name"], rule["group"], rule["name"], feature=str(rule.get("feature") or ""), evidence=rule["name"])
            for rule in rules] + rows


def repo_merge(root, rows, asked):
    """rows without the rules the repo turned off, plus the repo's own rows in the groups asked."""
    import report as G
    off = {item["rule"] for item in off_rows(root)}
    return [item for item in rows if G.rule_of(item) not in off] + [item for item in repo_rows(root) + off_rows(root) if item["family"] in asked]


def off_rows(root):
    """One INFO row, in its own group, for each default rule the repo turned off: the reason is printed."""
    import report as G
    return [mine_row("INFO", rule, "turned off: %s" % why, "", G.GROUP_OF[rule], rule) for rule, why in sorted(repo_load(root)[1].items())]


# --- migration-check: the routine, task and check gaps, then the docs check and the published wiki (the engine is defects.py)
def automation_gaps(root, cfg, g, info):
    wf = mod("workflow-health", "workflows")
    label, items = wf.task_name(root), cfg.get("automation")
    items = items if isinstance(items, list) else []
    off = {"health": cfg.get("health_cron") == "off", "regression": cfg.get("regression_cron") == "off", "digest email": cfg.get("digest_mail") == "off"}
    info["off"] = off
    for name in ("health", "regression", "digest email"):
        entry = next((i for i in items if isinstance(i, dict) and i.get("name") == name), None)
        if off[name]:
            continue
        if entry is None:
            g("MIG_AUTOMATION", name, "is not declared in automation, so it shows off while its setting is not off", tool("workflow-setup", "settings.py", "fill-repo") + ", or set its setting to off")
        elif entry.get("runs") != "mac:" + label:
            g("MIG_AUTOMATION", name, "does not run on the Mac task %s" % label, "set its runs to mac:" + label + " in automation")
        elif entry.get("enabled") is False or str(entry.get("cadence")) == "off":
            g("MIG_AUTOMATION", name, "is declared off without an explicit off setting", "set its setting to off, or turn the entry on")
    for key in ("health_cron", "regression_cron"):
        if not off[key.split("_")[0]] and not wf.slots(cfg.get(key)):
            g("MIG_AUTOMATION", key, "is not an every-N-hours or fixed-hours cron", "set %s to a shape like 47 */4 * * *" % key)
    if off["health"] and not off["regression"]:
        g("MIG_AUTOMATION", "health_cron", "is off while regression_cron is on, and the one task runs both", "turn health_cron on (47 */4 * * *), or turn regression_cron off")
    if not off["regression"] and cfg.get("regression_runs") != "mac":
        g("MIG_AUTOMATION", "regression_runs", "is not mac while regression_cron is on, public or private", "set regression_runs to mac in .loop/config.json")


def scheduled_task(label):
    """True when the Mac has a scheduled task folder named label (Claude's scheduled tasks, each at ~/.claude/scheduled-tasks/<id>/SKILL.md); LOOP_SCHEDULED_TASKS_DIR overrides the places."""
    dirs = [os.environ["LOOP_SCHEDULED_TASKS_DIR"]] if os.environ.get("LOOP_SCHEDULED_TASKS_DIR") else [os.path.expanduser("~/.claude/scheduled-tasks")]
    return any(os.path.isdir(os.path.join(d, label)) for d in dirs)


def task_gaps(root, cfg, g, info):
    plat = (os.environ.get("LOOP_SCHEDULE_PLATFORM") if os.environ.get("LOOP_TEST") == "1" else "") or sys.platform
    info["platform"] = plat
    if info["off"]["health"] and info["off"]["regression"]:
        return
    if plat != "darwin":
        info["skipped"].append("SKIP MIG_TASK (not a Mac)")
        return
    wf = mod("workflow-health", "workflows")
    label, origin = wf.task_name(root), wf.origin_of(root)
    try:
        found = wf.load()["repos"].get(wf.key_of(origin)) if origin else None
    except SystemExit:
        return g("MIG_TASK", "registry", "the local registry can't be read", "fix or remove repos.json in the schedule home, then " + tool("workflow-health", "automation.py", "local install"))
    install = tool("workflow-health", "automation.py", "local install")
    if scheduled_task(label):
        return  # the Mac's own scheduled task <repo>-health-regression runs it; the launch agent's registry need not list the repo
    if not origin:
        g("MIG_TASK", label, "this repo has no origin remote, so no task can be registered", "git remote add origin <url>, then " + install)
    elif found is None:
        g("MIG_TASK", label, "no local task is registered for this repo", install)
    elif found.get("name") != label:
        g("MIG_TASK", label, "the registered task is named %s" % clean(found.get("name") or "nothing"), install + " (it renames it)")
    elif not wf.slots(found.get("cron")) or wf.slots(found.get("cron"))[1] > wf.MAX_HOURS:
        g("MIG_TASK", label, "its cron does not run every %d hours or sooner" % wf.MAX_HOURS, "set health_cron to 47 */4 * * *, then " + install)


def checks_gaps(root, cfg, g):
    yml = os.path.join(root, ".github", "workflows", "regression.yml")
    if cfg.get("regression_cron") == "off":
        return
    if os.path.exists(yml):
        if "pull_request" not in read(yml) and cfg.get("regression_runs") != "mac":  # a mac repo's pr lane posts the statuses itself (AUT-2)
            g("MIG_CHECKS", "regression.yml", "does not trigger on pull_request, so no regression check reports on a PR", "add pull_request: under on: in regression.yml")
    elif cfg.get("regression_runs") == "mac" and not any(r["level"] == "land" for r in table(root)):
        g("MIG_CHECKS", ".loop/regression.tsv", "has no land row, so a pull-request check has nothing to run", "regression.py add a row at level land")


def docs_gaps(root, g):
    """docs.py check lines: a Runbook line is MIG_RUNBOOK, any other line (the PRD format, a page stale against the code) MIG_FORMAT.
    The blocks and the entry point have their own codes; a review note or the requirement cap is not a migration gap."""
    done = subprocess.run([sys.executable, os.path.join(SKILLS, "workflow-docs", "scripts", "docs.py"), "check"],
                          cwd=root, capture_output=True, text=True)
    out = [x for x in done.stdout.splitlines() if x.strip()]
    if not out:
        return g("MIG_FORMAT", "docs.py check", "gave no output (exit %d): %s" % (done.returncode, clean((done.stderr.strip().splitlines() or [""])[-1])[:200]), tool("workflow-docs", "docs.py", "audit"))
    for line in out:
        kind, _, rest = line.partition(" ")
        page, _, detail = rest.partition(": ")
        if kind in ("LAG", "SKIPPED", "CHANGED", "CAP") or line.startswith(("DOCS OK", "NO PAGES")) or "ENTRY_" in detail or page in ("Settings", "Automation", "README line"):
            continue
        what, _, fix = detail.partition(". Fix: ")
        g("MIG_RUNBOOK" if "Runbook: DOC-16" in detail else "MIG_FORMAT", clean(page), clean(what), clean(fix) or tool("workflow-docs", "docs.py", "audit"))


def wiki_gaps(root, g, info):
    """The published wiki against docs/wiki: one shallow clone in a private temp dir (30 s, a short list of transports), removed after.
    A page there with no source page is an orphan; a source page whose published text differs is stale. Nothing is written or deleted."""
    origin = subprocess.run(["git", "remote", "get-url", "origin"], cwd=root, capture_output=True, text=True).stdout.strip()
    fix = "check the origin and sign-in, then rerun; with no network pass --offline"
    if not origin:
        return g("MIG_WIKI_UNREADABLE", "wiki", "the repo has no origin remote", "git remote add origin <url>, then rerun")
    url = (origin[:-4] if origin.endswith(".git") else origin.rstrip("/")) + ".wiki.git"
    temp, shown = tempfile.mkdtemp(prefix="migration-wiki-"), clean(url)
    try:
        print("cloning the wiki (up to 30 s)", file=sys.stderr)
        proc = subprocess.Popen(["git", "clone", "--quiet", "--depth", "1", "--", url, os.path.join(temp, "w")], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True, env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ALLOW_PROTOCOL=PROTOCOLS))
        try:
            err = proc.communicate(timeout=30)[1]
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL) if hasattr(os, "killpg") else proc.kill()  # posix-only branch
            proc.communicate()
            return g("MIG_WIKI_UNREADABLE", "wiki", "timed out after 30 s reading %s" % shown, fix)
        if proc.returncode:
            if re.search(r"not found|does not exist", err):
                return info["notes"].append("no published wiki yet")
            return g("MIG_WIKI_UNREADABLE", "wiki", "can't read %s: %s" % (shown, clean(err.strip().splitlines()[-1] if err.strip() else "git failed")[:120]), fix)
        wiki = os.path.join(temp, "w")
        held = sorted(n for n in os.listdir(wiki) if n.endswith(".md") and os.path.isfile(os.path.join(wiki, n)))
        if not held:
            return info["notes"].append("no published wiki yet")
        pages, counting, pf = mod("workflow-health", "defects").pages(root), mod("workflow-docs", "counting"), mod("workflow-docs", "pageformat")
        made = set(counting.read_map(root)) | set(pf.GENERATED)
        for name in held:
            if name[:-3] in pages or name.startswith("_"):
                continue
            text = open(os.path.join(wiki, name), errors="replace").read()
            safe = re.fullmatch(r"[A-Za-z0-9._ -]{1,80}", name) and not name.startswith(("-", ".")) and ".." not in name
            ours = text.startswith(pf.MARKER)
            how = "git clone %s && cd %s && git rm -- %s && git commit -m 'remove retired wiki page' && git push" % (shlex.quote(shown), "<repo>.wiki", shlex.quote(name))
            g("MIG_WIKI_ORPHAN", clean(name) if safe else "(a page whose name this check will not print)",
              "published with no source page in docs/wiki (retired, renamed, old format or hand-made); owner only, after the merge, irreversible without the wiki's history",
              (how if ours else "this tool did not write it: keep it, or git rm it if it is retired (%s)" % how) if safe else "remove it by hand (the name has characters this check will not print)")
        for page in sorted(n for n in pages if n in made):
            published = os.path.join(wiki, page + ".md")
            if not os.path.exists(published) or open(published, errors="replace").read() != pages[page]:
                g("MIG_WIKI_STALE", page, "the published text differs from docs/wiki/%s.md" % page, tool("workflow-docs", "docs.py", "publish") + " (owner, after the merge)")
    finally:
        shutil.rmtree(temp, ignore_errors=True)
