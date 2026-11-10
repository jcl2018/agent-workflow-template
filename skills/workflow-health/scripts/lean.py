"""Hygiene rules that keep the repo lean: test time, stale loop worktrees, stale local branches. Used by health.py.

test-time reads the land lane record (regression.py's per-branch record under the git common folder's loop/tests/):
the current branch's, else the newest one with a readable `at`. It counts only rows that are land rows in the current
.loop/regression.tsv, and warns when their total is over test_budget_seconds (.loop/config.json, default 600),
naming the slowest rows and scripts.
worktrees lists loop worktrees (the git common folder's loop/worktrees/) that no live run names; local-branches lists
branches with no upstream (or a gone one), checked out nowhere, not merged into the base and older than
stale_branch_days (default 14). Each gets its removal command, shell-quoted; nothing is ever removed here. These rows
hold machine-local paths and names, so file.py never files them.
"""
import glob
import json
import os
import re
import shlex
import subprocess
import time

TEST_BUDGET = 600
STALE_DAYS = 14
SHOWN = 5
LIVE = ("running", "waiting", "failed", "stopped")
LANDED = ("merged", "cut", "leave")
REPORT_ONLY = ("test-time", "worktrees", "local-branches")


def row(state, subject, rule, detail, fix=""):
    return {"state": state, "family": "hygiene", "subject": subject, "rule": rule, "detail": detail, "fix": fix}


def git(root, *args):
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return done.returncode, done.stdout, done.stderr.strip()


def common(root):
    return os.path.realpath(os.path.join(root, git(root, "rev-parse", "--git-common-dir")[1].strip() or ".git"))


def setting(root, key, default):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            value = json.load(handle).get(key, default)
    except (OSError, ValueError):
        return default
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else default


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


def lane_record(root):
    """(record, path, why): the current branch's lane record, else the newest readable one."""
    folder = os.path.join(common(root), "loop", "tests")
    branch = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")[1].strip()
    found = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        try:
            with open(path) as handle:
                data = json.load(handle)
            rows = data["rows"]
            assert isinstance(rows, dict) and data.get("at")
        except (OSError, ValueError, KeyError, AssertionError, TypeError):
            continue
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", branch)
        found.append((branch and os.path.basename(path).startswith(safe + "-"), str(data["at"]), path, data))
    if not found:
        return None, "", "no lane record yet"
    found.sort(key=lambda item: (item[0], item[1]))
    return found[-1][3], found[-1][2], ""


def test_rows(root):
    record, path, why = lane_record(root)
    if record is None:
        return [row("INFO", "lane", "test-time", why, "run regression.py run land --reuse")]
    land = land_rows(root)
    seconds = {key: float(item.get("seconds") or 0) for key, item in record["rows"].items() if key in land}
    total = sum(seconds.values())
    budget = setting(root, "test_budget_seconds", TEST_BUDGET)
    if total <= budget:
        return [row("PASS", "lane", "test-time", "the land lane takes %d s, within test_budget_seconds=%d" % (total, budget))]
    slow = sorted(seconds.items(), key=lambda pair: (-pair[1], pair[0]))[:SHOWN]
    scripts = {}
    for key, value in seconds.items():
        scripts[land[key]] = scripts.get(land[key], 0) + value
    worst = sorted(scripts.items(), key=lambda pair: (-pair[1], pair[0]))[:3]
    return [row("WARN", "lane", "test-time", "the land lane takes %d s, over test_budget_seconds=%d in .loop/config.json; "
                "slowest rows: %s; slowest scripts: %s" % (
                    total, budget, ", ".join("%s %ds" % pair for pair in slow), ", ".join("%s %ds" % pair for pair in worst)),
                "move the slowest rows to nightly in .loop/regression.tsv, or raise test_budget_seconds")]


def runs_by_tree(root):
    out = {}
    for path in glob.glob(os.path.join(common(root), "loop", "runs", "*.json")):
        try:
            with open(path) as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(state, dict) and state.get("worktree"):
            out.setdefault(os.path.realpath(state["worktree"]), []).append(state)
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
        why = "no live goal"
        if "\nlocked" in "\n" + block:
            why = "locked; unlock it first"
        elif git(real, "status", "--porcelain")[1].strip():
            why = "uncommitted changes; the command refuses until they are committed or dropped"
        items.append((name, why, "git worktree remove " + shlex.quote(path)))
    return summary("worktrees", items, "loop worktrees")


def branch_rows(root):
    fields = "%(refname:short)\t%(upstream)\t%(upstream:track)\t%(committerdate:unix)\t%(worktreepath)\t%(HEAD)"
    code, out, err = git(root, "for-each-ref", "--format=" + fields, "refs/heads")
    if code:
        return [row("UNREAD", "local-branches", "local-branches", (err or "git for-each-ref failed")[:120])]
    base = "origin/main" if git(root, "rev-parse", "--verify", "--quiet", "origin/main")[0] == 0 else "main"
    days = setting(root, "stale_branch_days", STALE_DAYS)
    items = []
    for line in sorted(out.splitlines()):
        name, upstream, track, when, tree, head = (line.split("\t") + [""] * 6)[:6]
        if (upstream and track != "[gone]") or tree or head == "*" or name == base.split("/")[-1]:
            continue
        if not when.isdigit() or time.time() - int(when) < days * 86400:
            continue
        if git(root, "merge-base", "--is-ancestor", name, base)[0] == 0:
            continue  # merged: the branches rule names it
        only = git(root, "rev-list", "--count", name, "--not", "--remotes")[1].strip() or "0"
        why = "%s commits exist only on this machine; push it first to keep them" % only if only != "0" else "every commit is on a remote"
        items.append((name, why, "git branch -D " + shlex.quote(name)))
    return summary("local-branches", items, "local branches")


def rows(root):
    return test_rows(root) + worktree_rows(root) + branch_rows(root)


def facts(root):
    """Judge input lines: the land lane's total and its slowest rows."""
    record, _, why = lane_record(root)
    if record is None:
        return ["land lane: " + why]
    land = land_rows(root)
    seconds = {key: float(item.get("seconds") or 0) for key, item in record["rows"].items() if key in land}
    slow = sorted(seconds.items(), key=lambda pair: (-pair[1], pair[0]))[:10]
    return ["land lane: %d rows, %d s (budget %d s); slowest: %s" % (
        len(seconds), sum(seconds.values()), setting(root, "test_budget_seconds", TEST_BUDGET),
        ", ".join("%s %ds" % pair for pair in slow))]
