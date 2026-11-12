"""Hygiene rules that keep the repo lean: test time, stale loop worktrees, stale local branches, git hooks. Used by health.py.

test-time reads the land lane record (regression.py's per-branch record under the git common folder's loop/tests/):
the current branch's, else the newest one with a readable `at`. It counts only rows that are land rows in the current
.loop/regression.tsv, and warns when their total is over test_budget_minutes (.loop/config.json, default 15, floor 15),
naming the slowest rows and scripts. It also warns when the newest full (non --reuse) run took over 30 minutes, and lists
each step or test run of a goal that hit its time budget with what it left (budget_hits in the run records).
worktrees lists loop worktrees (the git common folder's loop/worktrees/) that no live run names; local-branches lists
branches with no upstream (or a gone one), checked out nowhere, not merged into the base and older than
stale_branch_days (default 14). Each gets its removal command, shell-quoted; nothing is ever removed here. These rows
hold machine-local paths and names, so file.py never files them.
hooks (DEL-9, SET-8) runs `setup.py --git-hooks --check --json` and WARNs when a private-name hook is missing, foreign
(no call to private.py) or calls a script that is gone, or when the list is broken; no list is not a finding (the board
lists it). Skipped on GitHub Actions unless LOOP_HEALTH_HOOKS=1. Any other answer is one WARN to update the skills.
"""
import glob
import hashlib
import json
import math
import os
import re
import shlex
import subprocess
import sys
import time

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

TEST_BUDGET = 15  # minutes: the loop's test budget (default and floor)
SUITE_LIMIT = 30  # minutes: the scheduled full suite
STALE_DAYS = 14
SHOWN = 5
LIVE = ("queued", "running", "waiting", "failed", "stopped")
LANDED = ("merged", "cut", "leave")


def row(state, subject, rule, detail, fix=""):
    return {"state": state, "family": "hygiene", "subject": subject, "rule": rule, "detail": detail, "fix": fix}


def git(root, *args):
    done = subprocess.run(["git", "--no-optional-locks", *args], cwd=root, capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr.strip()


def common(root):
    return os.path.realpath(os.path.join(root, git(root, "rev-parse", "--git-common-dir")[1].strip() or ".git"))


def config(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def setting(root, key, default):
    value = config(root).get(key, default)
    return value if number(value) and value > 0 else default


def land_rows(root):
    """{row id: the toy script it runs} for the land rows of the current regression.tsv."""
    out = {}
    try:
        with open(os.path.join(root, ".loop", "regression.tsv")) as handle:
            for line in handle:
                cells = line.rstrip("\n").split("\t")
                if len(cells) > 2 and not line.startswith("#") and cells[1] == "land":
                    script = re.search(r"[\w./-]+\.(?:sh|py)\b", cells[2])
                    out[cells[0]] = script.group(0) if script else cells[2][:40]
    except OSError:
        pass
    return out


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def readable(data):
    rows = data.get("rows") if isinstance(data, dict) else None
    return isinstance(rows, dict) and data.get("at") and all(
        isinstance(r, dict) and number(r.get("seconds", 0))
        for r in rows.values())


def lane_record(root):
    """(record, mine, why): the current branch's lane record (named as regression.py names it), else the newest
    readable one (mine False). A damaged record of this branch is why, never read."""
    folder = os.path.join(common(root), "loop", "tests")
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")[1].strip()
    own = "%s-%s.json" % (re.sub(r"[^A-Za-z0-9._-]", "_", branch), hashlib.sha1(branch.encode()).hexdigest()[:8]) if branch else ""
    found = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        try:
            with open(path) as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            data = None
        if not readable(data):
            if os.path.basename(path) == own:
                return None, True, "this branch's lane record cannot be read: %s" % os.path.basename(path)
            continue
        found.append((os.path.basename(path) == own, str(data["at"]), path, data))
    if not found:
        return None, False, "no lane record yet"
    found.sort(key=lambda item: (item[0], item[1]))
    return found[-1][3], found[-1][0], "" if found[-1][0] else os.path.basename(found[-1][2])


def budget_minutes(root):
    value = config(root).get("test_budget_minutes", TEST_BUDGET)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= TEST_BUDGET else None


def suite_rows(root):
    """A WARN when the newest recorded full run (a record whose command has no --reuse) took over 30 minutes."""
    full = []
    for path in glob.glob(os.path.join(common(root), "loop", "tests", "*.json")):
        try:
            with open(path) as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            continue
        if readable(data) and "--reuse" not in str(data.get("command")) and number(data.get("total_seconds")):
            full.append((str(data["at"]), data["total_seconds"]))
    if not full or max(full)[1] <= SUITE_LIMIT * 60:
        return []
    return [row("WARN", "lane", "test-time", "the full suite took %d s, over %d minutes" % (max(full)[1], SUITE_LIMIT),
                "move the slowest rows to nightly in .loop/regression.tsv, or split them")]


def hit_rows(root):
    """One INFO row per step or test run that hit its budget, with what it left."""
    found = []
    for state in runs(root):
        if state.get("status") == "merged" or state.get("release") in LANDED:
            continue
        for hit in state.get("budget_hits") or []:
            if isinstance(hit, dict):
                found.append(row("INFO", "budget", "test-time", "%s: %s %s hit its %s-minute budget; left: %s" % (
                    state["slug"], hit.get("step"), {"step": "step", "prep": "preparation"}.get(hit.get("kind"), "tests"),
                    hit.get("minutes"), hit.get("left")), "run what it left with regression.py run land, or raise the budget"))
    return found


def test_rows(root):
    return lane_rows(root) + suite_rows(root) + hit_rows(root)


def lane_rows(root):
    record, mine, why = lane_record(root)
    if record is None:
        return [row("UNREAD" if mine else "INFO", "lane", "test-time", why, "run regression.py run land --reuse")]
    whose = "" if mine else " (from another branch's record, %s)" % why
    land = land_rows(root)
    seconds = {key: float(item.get("seconds") or 0) for key, item in record["rows"].items() if key in land}
    total = sum(seconds.values())
    minutes = budget_minutes(root)
    if minutes is None:
        return [row("WARN" if mine else "INFO", "lane", "test-time", "test_budget_minutes in .loop/config.json is under the "
                    "15-minute floor", "set test_budget_minutes to 15 or more")]
    if total <= minutes * 60:
        return [row("PASS" if mine else "INFO", "lane", "test-time",
                    "the land lane takes %d s, within test_budget_minutes=%d%s" % (total, minutes, whose))]
    slow = sorted(seconds.items(), key=lambda pair: (-pair[1], pair[0]))[:SHOWN]
    scripts = {}
    for key, value in seconds.items():
        scripts[land[key]] = scripts.get(land[key], 0) + value
    worst = sorted(scripts.items(), key=lambda pair: (-pair[1], pair[0]))[:3]
    return [row("WARN" if mine else "INFO", "lane", "test-time", "the land lane takes %d s, over test_budget_minutes=%d in .loop/config.json; "
                "slowest rows: %s; slowest scripts: %s%s" % (
                    total, minutes, ", ".join("%s %ds" % pair for pair in slow), ", ".join("%s %ds" % pair for pair in worst), whose),
                "move the slowest rows to nightly in .loop/regression.tsv, or raise test_budget_minutes")]


def runs(root, bad=None):
    """Every run record as a dict; the names of unreadable ones go in bad."""
    out = []
    for path in sorted(glob.glob(os.path.join(common(root), "loop", "runs", "*.json"))):
        try:
            with open(path) as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            state = None
        if isinstance(state, dict):
            out.append(dict(state, slug=state.get("slug") or os.path.basename(path)[:-5]))
        elif bad is not None:
            bad.append(os.path.basename(path))
    return out


def blind(rule, root):
    """An UNREAD row when a run record cannot be read: its goal's worktree or branch could look stale."""
    bad = []
    runs(root, bad)
    return [row("UNREAD", rule, rule, "run record %s cannot be read, so a live goal may look stale" % ", ".join(bad[:3]),
                "repair or remove it before removing anything")] if bad else []


def runs_by_tree(root):
    """realpath of a run's worktree (its own field, else loop/worktrees/<slug>) -> its runs."""
    out, folder = {}, os.path.join(common(root), "loop", "worktrees")
    for state in runs(root):
        tree = state.get("worktree") or os.path.join(folder, state["slug"])
        out.setdefault(os.path.realpath(os.path.join(root, tree)), []).append(state)
    return out


def live(runs):
    return any(r.get("status") in LIVE or (r.get("status") == "done" and r.get("release") not in LANDED) for r in runs)


def summary(rule, items, noun):
    """One WARN per kind: the count, the first SHOWN items with their commands, then how many more."""
    if not items:
        return [row("PASS", rule, rule, "no stale %s" % noun)]
    shown = "; ".join("%s (%s): %s" % (name, why, command) for name, why, command in items[:SHOWN])
    more = " and %d more (all in --json)" % (len(items) - SHOWN) if len(items) > SHOWN else ""
    found = row("WARN", rule, rule, "%d stale %s: %s%s" % (len(items), noun, shown, more),
                "run the commands shown; nothing is removed for you")
    found["items"] = [{"name": name, "why": why, "command": command} for name, why, command in items]
    return [found]


def worktree_rows(root):
    code, out, err = git(root, "worktree", "list", "--porcelain")
    if code:
        return [row("UNREAD", "worktrees", "worktrees", (err or "git worktree list failed")[:120])]
    if blind("worktrees", root):
        return blind("worktrees", root)
    folder, here, runs = os.path.join(common(root), "loop", "worktrees"), os.path.realpath(root), runs_by_tree(root)
    items = []
    for block in out.strip().split("\n\n"):
        path = next((line[9:] for line in block.splitlines() if line.startswith("worktree ")), "")
        real = os.path.realpath(path)
        if not real.startswith(folder + os.sep) or real == here or live(runs.get(real, [])):
            continue
        name = os.path.basename(real)
        if "\nprunable" in "\n" + block or not os.path.isdir(real):
            items.append((name, "its folder is gone", "git worktree prune"))
            continue
        why, (code, dirty, _) = "no live goal", git(real, "status", "--porcelain")
        if "\nlocked" in "\n" + block:
            why = "locked; unlock it first"
        elif code:
            why = "its status cannot be read; look before removing it"
        elif dirty.strip():
            why = "uncommitted changes; the command refuses until they are committed or dropped"
        items.append((name, why, "git worktree remove " + shlex.quote(path)))
    return summary("worktrees", items, "loop worktrees")


def branch_rows(root):
    fields = "%(refname:short)\t%(upstream)\t%(upstream:track)\t%(committerdate:unix)\t%(worktreepath)\t%(HEAD)"
    code, out, err = git(root, "for-each-ref", "--format=" + fields, "refs/heads")
    if code:
        return [row("UNREAD", "local-branches", "local-branches", (err or "git for-each-ref failed")[:120])]
    name_of_base = config(root).get("base")
    name_of_base = name_of_base if isinstance(name_of_base, str) and name_of_base else "main"
    base = next((ref for ref in ("origin/" + name_of_base, name_of_base) if git(root, "rev-parse", "--verify", "--quiet", ref)[0] == 0), "")
    if not base:
        return [row("UNREAD", "local-branches", "local-branches", "the base branch %s cannot be found" % name_of_base,
                    "set base in .loop/config.json")]
    if blind("local-branches", root):
        return blind("local-branches", root)
    days = setting(root, "stale_branch_days", STALE_DAYS)
    held = {r.get("branch") or "loop/" + r["slug"] for r in runs(root) if live([r])}
    items = []
    for line in sorted(out.splitlines()):
        name, upstream, track, when, tree, head = (line.split("\t") + [""] * 6)[:6]
        if (upstream and track != "[gone]") or tree or head == "*" or name == name_of_base or name in held:
            continue
        if not when.isdigit() or time.time() - int(when) < days * 86400:
            continue
        merged = git(root, "merge-base", "--is-ancestor", name, base)[0]
        if merged == 0:
            continue  # merged: the branches rule names it
        if merged != 1:
            return [row("UNREAD", "local-branches", "local-branches", "cannot tell whether %s is merged" % name, "")]
        only = git(root, "rev-list", "--count", name, "--not", "--remotes")[1].strip() or "0"
        why = "%s commits exist only on this machine; push it first to keep them" % only if only != "0" else "every commit is on a remote"
        items.append((name, why, "git branch -D " + shlex.quote(name)))
    return summary("local-branches", items, "local branches")


def srow(*args):
    return dict(row(*args), family="security")  # reported in Security and privacy


def hook_rows(root):
    if os.environ.get("GITHUB_ACTIONS") and os.environ.get("LOOP_HEALTH_HOOKS") != "1":
        return [srow("PASS", "hooks", "hooks", "skipped on GitHub Actions: hooks live on a machine")]
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-setup", "scripts", "setup.py")
    stale = [srow("WARN", "hooks", "hooks", "cannot read the hook state", "update the skills so setup.py has --git-hooks --check")]
    try:
        done = subprocess.run([sys.executable, script, "--repo", root, "--git-hooks", "--check", "--json"],
                              capture_output=True, text=True, timeout=60)
        data = json.loads(done.stdout)
        if done.returncode not in (0, 1) or data["version"] != 1:
            return stale
        found = ["%s: %s" % pair for pair in sorted(data["hooks"].items()) if pair[1] != "installed"]
        found += ["the private-name list is broken (python3 private.py check names the line)"] * (data["list"] == "broken")
        found += ["core.hooksPath is set: add the call lines to the hooks you use"] * (bool(found) and bool(data["hooks_path"]))
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
        return stale
    return [srow("WARN", "hooks", "hooks", "; ".join(found), "run python3 workflow-setup/scripts/setup.py --git-hooks from the "
                "installed skills")] if found else [srow("PASS", "hooks", "hooks", "the private-name hooks are installed")]


def rows(root):
    return test_rows(root) + worktree_rows(root) + branch_rows(root)


def facts(root):
    """Judge input lines: the land lane's total and its slowest rows."""
    record, _, why = lane_record(root)
    why = why if record is None else ""
    if record is None:
        return ["land lane: " + why]
    land = land_rows(root)
    seconds = {key: float(item.get("seconds") or 0) for key, item in record["rows"].items() if key in land}
    slow = sorted(seconds.items(), key=lambda pair: (-pair[1], pair[0]))[:10]
    return ["land lane: %d rows, %d s (budget %d s); slowest: %s" % (
        len(seconds), sum(seconds.values()), (budget_minutes(root) or TEST_BUDGET) * 60,
        ", ".join("%s %ds" % pair for pair in slow))]
