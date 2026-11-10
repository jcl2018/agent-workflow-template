#!/usr/bin/env python3
"""The live board's template lag: each followed repo on an older template version than the operator's installed skills.

usage: board_lag.py   (prints the Issues lines; live_board.py calls template_lag)

The baseline is the installed workflow-package.json beside the skills, else a checkout's VERSION. Each repo's version is
template_version in its base branch's .loop/config.json; a repo with none reads "template version unknown". A repo that
holds the board's own skills checkout is the template itself and is skipped. It runs git and nothing else.

Also here (the package stays under its file cap), the per-goal budget and decided-depth lines and the private-name
Issues lines, imported by live_board.py (were board_budget.py):

"""
import importlib.util
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_status as bs  # noqa: E402

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def git(*args, cwd=None):
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def read_json(path):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


SKILLS = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))


def version_key(text):
    """The first three integers of a version; empty or unreadable is older than any version."""
    return tuple(int(x) for x in re.findall(r"\d+", str(text or ""))[:3])


def baseline():
    """The operator's installed template version: workflow-package.json beside the skills, else a checkout's VERSION."""
    held = read_json(os.path.join(SKILLS, "workflow-package.json"))
    if isinstance(held, dict) and held.get("version"):
        return str(held["version"]), False
    try:
        with open(os.path.join(SKILLS, os.pardir, "VERSION")) as handle:
            return handle.read().strip(), True
    except OSError:
        return "", True


def followed(root):
    try:
        with open(os.path.expanduser("~/.workflow-loop/repos")) as handle:
            extra = [line.strip() for line in handle if line.strip()]
    except OSError:
        extra = []
    return list(dict.fromkeys([root] + extra))


def template_lag(root):
    """Issues lines for each followed repo on an older template version than the operator's installed skills (the
    baseline); a repo holding the board's own skills checkout is the template itself and is skipped."""
    want, source = baseline()
    out = []
    for repo in followed(root):
        if source and SKILLS.startswith(os.path.realpath(repo) + os.sep) or not os.path.isdir(repo):
            continue
        cfg = read_json(os.path.join(repo, ".loop", "config.json"))
        if not isinstance(cfg, dict):
            continue
        base = git("show", "%s:.loop/config.json" % (cfg.get("base") or "main"), cwd=repo)
        try:
            held = str((json.loads(base) if base else cfg).get("template_version") or "")
        except ValueError:
            held = str(cfg.get("template_version") or "")
        name = os.path.basename(os.path.realpath(repo))
        if not held:
            out.append("- %s: template version unknown" % name)
        elif version_key(held) < version_key(want):
            out.append("- %s runs template v%s, older than v%s" % (name, held, want))
        else:
            continue
        out.append("    fix: ask for workflow-setup update in that repo")
    return out




# ---- budget, decided depth and private-name Issues lines (DEL-8, DEL-6, DEL-9)
FIT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-delivery", "scripts", "fit.py")
LIST = "~/.workflow-loop/private-names"
SHOWN = "$HOME/.workflow-loop/private-names"  # the board shows no ~/ path (test-live-board)


def load_fit():
    """workflow-delivery's fit module, or None when it is missing or broken."""
    if not os.path.exists(FIT):
        return None
    try:
        spec = importlib.util.spec_from_file_location("fit", FIT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception:  # a broken sibling leaves the board as it was
        return None


fit = load_fit()


def mega(n):
    return "%.1fM" % (n / 1e6)


def spent(run, at):
    """(whole minutes, tokens) a goal has spent so far."""
    return int(sum(bs.seconds_by_step(run, at).values()) // 60), fit.spent_tokens(run)


def line(run, cfg, at, runs=None):
    """The budget line for one goal, or '' without fit."""
    if fit is None:
        return ""
    held, _ = fit.budget(fit.view(run, runs), cfg)
    minutes, tokens = spent(run, at)
    seconds = sum(bs.seconds_by_step(run, at).values())
    halves, over = [], []
    if held["minutes"] > 0:
        halves.append("%dm of %dm" % (minutes, held["minutes"]))
        over += ["OVER time"] if seconds > held["minutes"] * 60 else []
    if held["tokens"] > 0:
        halves.append("%s of %s tokens" % (mega(tokens), mega(held["tokens"])))
        over += ["OVER tokens"] if tokens >= held["tokens"] else []
    return "budget: " + (", ".join(halves + over) if halves else "none set")


def depth(run, setting, runs=None):
    """The depth the goal is held to and why, or '' without fit."""
    if fit is None:
        return ""
    found, why = fit.depth_for(setting, fit.view(run, runs))
    return "%s (%s)" % (found, why) if why else found


def missing_list():
    """True when no private-name list exists where private.py looks (a comments-only file exists: off on purpose)."""
    given = os.environ.get("LOOP_PRIVATE_NAMES")
    return not os.path.exists(given if given else os.path.expanduser(LIST))


def issues(root, runs=()):
    """Issues lines: the missing list (when fit is installed beside this skill), then each finding kept local."""
    out = []
    if fit is not None and missing_list():
        out += ["- no private-name list: nothing is scanned (create %s; a file holding only comments says off on purpose)" % SHOWN,
                "    fix: write one pattern per line to %s (or point $LOOP_PRIVATE_NAMES at a file)" % SHOWN]
    for run in runs:
        wait = " ".join(str(run.get("release_pr_waiting") or "").split())
        if wait and not run.get("release_url"):  # nothing reruns merge.py by itself once the goal's PR merged
            out += ["- %s: the release pull request waits: %s" % (run["slug"], wait[:200]),
                    "    fix: run merge.py %s again once its checks pass; it merges the release PR and creates the release" % run["slug"]]
        text = " ".join(str(run.get("finding_error") or "").split())
        if text:
            said, _, fix = text.partition(". Fix: ")
            out += ["- %s: a finding stayed local: %s" % (run["slug"], said[:200]),
                    "    fix: %s" % (fix[:200] or "remove what the scan found, then push the finding commit")]
    return out


if __name__ == "__main__":
    root = git("rev-parse", "--show-toplevel") or os.getcwd()
    print("\n".join(template_lag(root)) or "- (none)")
    sys.exit(0)
