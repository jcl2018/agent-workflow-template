#!/usr/bin/env python3
"""The one commit a lane may make before it starts: the re-rendered wiki Tests tables and the run dates they come from.
Imported by lane.py. A page counts only when its edits are all in its ## Tests section (what criteria.py renders),
or it is the full Tests page render writes whole;
any other change refuses with LANE_DIRTY and nothing is rendered or committed. The commit is `git commit --only` of
those paths with a 60 s timeout; a refused or hung commit unstages them and starts nothing (LANE_PREP_FAILED).
"""
import os
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

HERE = os.path.dirname(os.path.abspath(__file__))
NOTHING = "the lane committed and pushed nothing"
BOOKKEEPING = (".loop/regression-runs.tsv", ".loop/goals/", ".loop/queue.md", ".loop/findings.md")


def git(*args):
    return subprocess.run(["git"] + list(args), capture_output=True, text=True)


def dirty():
    out = git("status", "--porcelain", "--no-renames", "--untracked-files=all").stdout
    return [line[3:].strip('"') for line in out.splitlines() if not line[3:].strip('"').startswith(BOOKKEEPING)]


def generated(cfg):
    """The dirty paths a lane may leave or commit before it starts: rendered Tests sections and the full Tests page."""
    return [p for p in dirty() if is_page(p, cfg) and tests_only(p)]


def is_page(path, cfg):
    return path.startswith((cfg.get("wiki_dir") or "docs/wiki").rstrip("/") + "/") and path.endswith(".md")


def tests_only(path):
    """A page whose edits are all in its ## Tests section (what criteria.py renders) is a prep path; so is the full Tests
    page (Tests.md), which render writes whole (DOC-10)."""
    if os.path.basename(path) == "Tests.md":
        return True
    now = open(path).read().partition("\n## Tests")[0] if os.path.exists(path) else None
    shown = git("show", "HEAD:" + path)
    if now is None or shown.returncode:
        return False
    head = shown.stdout
    return now == head.partition("\n## Tests")[0] or ("\n## Tests" not in head and now == head)


def prep(top, cfg, log):
    """Re-render the Tests tables and commit them with the run dates (or nothing). Returns (line, refusal)."""
    criteria = os.path.normpath(os.path.join(HERE, "..", "..", "workflow-docs", "scripts", "criteria.py"))
    for path in dirty():
        if not (is_page(path, cfg) and tests_only(path)):
            if is_page(path, cfg):
                return None, "LANE_DIRTY: %s has edits above its ## Tests section; commit or revert them, then run the " \
                    "same command again; %s." % (path, NOTHING)
            return None, "LANE_DIRTY at start: %s. Fix: commit or remove them; %s." % (", ".join(dirty()[:10]), NOTHING)
    if not os.path.exists(os.path.join(top, ".loop", "docs.tsv")) or not os.path.exists(criteria):
        return "", None
    done = subprocess.run([sys.executable, criteria, "render"], cwd=top, capture_output=True, text=True, timeout=300)
    if done.returncode:
        first = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["exit %d" % done.returncode]
        return None, "LANE_PREP_FAILED: criteria.py render failed: %s. Fix: run it by hand; %s." % (first[0][:200], NOTHING)
    paths = [p for p in dirty() if is_page(p, cfg)]
    if git("status", "--porcelain", "--", ".loop/regression-runs.tsv").stdout.strip():
        paths.append(".loop/regression-runs.tsv")
    if not paths:
        return "", None
    proc = subprocess.Popen(["git", "commit", "--only", "-q", "-m", "Lane: re-render the Tests tables", "--"] + paths,
                            cwd=top, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, stdin=subprocess.DEVNULL,
                            start_new_session=True)  # its own group: a hung hook's children die with it
    try:
        out, err = proc.communicate(timeout=60)
        why = (err or out).strip().splitlines()[-1:] if proc.returncode else None
    except subprocess.TimeoutExpired:
        import signal
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except OSError:  # already gone
            pass
        out, err = proc.communicate()
        lock = os.path.join(top, git("rev-parse", "--git-path", "index.lock").stdout.strip())
        if os.path.exists(lock):  # the commit we killed held it; left behind it blocks every later commit
            os.remove(lock)
        why = ["timed out after 60s"]
    if why is not None:
        with open(log, "a") as handle:
            handle.write("prep commit: %s\n%s\n" % (" ".join(paths), err or out or ""))
        git("reset", "-q", "--", *paths)
        return None, ("LANE_PREP_FAILED: git commit failed: %s (full output: %s); the prep paths are unstaged and left "
                      "modified, nothing committed or pushed. Fix: make the commit pass (see the log), then run role.py lane "
                      "SLUG NAME again." % ((why or ["no message"])[0][:200], log))
    return "LANE_PREP: re-rendered the Tests tables (commit %s)" % git("rev-parse", "--short", "HEAD").stdout.strip(), None
