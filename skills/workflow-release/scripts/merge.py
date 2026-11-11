#!/usr/bin/env python3
"""Merge a finished goal's pull request into the base branch: the release step, for now.

usage: merge.py SLUG

It refuses unless `"auto_merge": true` is in .loop/config.json, the goal is done and its pull request is open. A repo
without that switch keeps the owner's merge: nothing here merges there. Then it runs the routines listed in .loop/config.json on the base branch and refuses if one fails, merges, and
releases: one version bump, a CHANGELOG entry and a published GitHub release (autorelease.py). Any failure is recorded
on the goal as `release_error`. Where .loop/docs.tsv maps pages, it first refuses while a page the goal's paths map to is stale,
and after the merge it publishes the wiki through wiki.py; a refused publish is recorded as `wiki_error`, not undone.
"""
import argparse
import datetime
import json
import os
import subprocess
import re
import sys

import autorelease
import release
import wiki

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


REACH = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-regression",
                                       "scripts", "lanes_cli.py"))


def reach(top, paths):
    """The row ids a change to PATHS can affect, or None when it means every row (unmapped, deleted, no planner)."""
    if not paths:
        return set()
    if not os.path.exists(REACH):
        return None
    done = run([sys.executable, "-B", REACH, "affected", "--root", top, "--"] + paths, cwd=top)
    found = re.search(r"^AFFECTED \d+ of \d+ rows \((.*)\)", done.stdout, re.M)
    if done.returncode or not found or re.search(r"^(UNMAPPED|DELETED) ", done.stdout, re.M):
        return None  # a planner that fails or can't map a path can't clear the merge
    return set(found.group(1).split(", ")) - {"none", ""}


def wiki_only(top, cfg, old, new):
    """True when NEW descends from OLD (the head the pr lane passed) and every commit between only adds or edits .md pages
    in the base branch's wiki folder (wiki_dir from origin/<base>'s config: the branch can't widen it), no SKILL.md."""
    if run(["git", "merge-base", "--is-ancestor", old, new], cwd=top).returncode:
        return False
    head = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=top).stdout.strip()  # not the branch's say
    shown = run(["git", "show", "%s:.loop/config.json" % (head or "origin/main")], cwd=top)
    try:
        folder = (json.loads(shown.stdout).get("wiki_dir") if shown.returncode == 0 else None) or "docs/wiki"
    except (ValueError, AttributeError):
        folder = "docs/wiki"
    done = run(["git", "diff", "--raw", "--no-renames", old, new], cwd=top)  # a move into the wiki shows its source
    rows = [(line.split("\t")[0].split(), line.split("\t")[1:]) for line in done.stdout.split("\n") if line]
    return not done.returncode and bool(rows) and all(
        len(m) == 5 and len(p) == 1 and m[4] in ("A", "M") and m[1] != "120000"  # a symlink is no page
        and p[0].startswith(str(folder).rstrip("/") + "/") and p[0].endswith(".md") and os.path.basename(p[0]) != "SKILL.md"
        for m, p in rows)


def base_moved(state, cfg, top):
    """None when the merge may go ahead, else (exit code, refusal): the base moved since the pr lane in paths this goal's
    rows reach (2), or origin can't be fetched to tell (3). A move elsewhere only notes it. workflow-regression/references/commands.md."""
    base, was = cfg.get("base", "main"), state.get("pr_base")
    if not was:  # a pull request opened before goal.py pr recorded its base
        return None
    try:
        done = subprocess.run(["git", "fetch", "-q", "origin", base], cwd=top, capture_output=True, text=True, timeout=60)
        why = (done.stderr.strip().splitlines() or ["exit %d" % done.returncode])[-1] if done.returncode else ""
    except subprocess.TimeoutExpired:
        why = "timed out after 60s"
    if why:
        return 3, "REFUSED (BASE_FETCH): cannot fetch origin/%s: %s. Fix: run merge.py %s again when the remote answers; " \
                  "nothing merged" % (base, why, state.get("slug", "SLUG"))
    now = run(["git", "rev-parse", "origin/" + base], cwd=top).stdout.strip()
    if now == was:
        return None
    def names(a, b):  # None when git can't diff (a commit missing here): unknown, so refused below
        done = run(["git", "diff", "--name-only", "--no-renames", a, b], cwd=top)
        return None if done.returncode else [p for p in done.stdout.split("\n") if p]
    theirs, ours = [None if x is None else reach(top, x) for x in (names(was, now), names(was, state.get("pr_head") or "HEAD"))]
    if theirs is None or ours is None or theirs & ours:
        return 2, "REFUSED (BASE_MOVED): %s moved in paths this goal's rows reach (lane on %s, base now %s). Fix: goal.py " \
                  "pr %s, then merge.py %s" % (base, was[:12], now[:12], state.get("slug", "SLUG"), state.get("slug", "SLUG"))
    print("NOTE: %s moved in paths this goal's rows don't reach; merging" % base)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug")
    args = parser.parse_args()
    top = run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    common = run(["git", "rev-parse", "--git-common-dir"]).stdout.strip()
    if not top or not common:
        sys.exit("REFUSED: not in a git repo.")
    try:
        with open(os.path.join(top, ".loop", "config.json")) as handle:
            cfg = json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")
    if cfg.get("auto_merge") is not True:
        sys.exit("REFUSED: auto_merge is off in this repo, so the owner merges. Nothing was merged.")
    path = os.path.join(os.path.abspath(common), "loop", "runs", args.slug + ".json")
    try:
        with open(path) as handle:
            state = json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no goal named %s." % args.slug)
    if state.get("status") != "done" or not state.get("pr"):
        sys.exit("REFUSED: %s has no finished pull request. Fix: run goal.py pr first." % args.slug)
    view = run(["gh", "pr", "view", state["pr"], "--json", "state,headRefOid"])
    info = json.loads(view.stdout or "{}") if view.returncode == 0 else {}
    known = info.get("state", "")
    if known != "MERGED":
        if wiki.top_of():
            stale = wiki.pending(top, cfg)
            if stale:
                autorelease.fail(state, "stale wiki pages: %s. Fix: update %s, then run wiki.py prepare %s --commit." % (
                    ", ".join(stale), ", ".join(sorted({l.split(":")[0].split()[1] for l in stale if l.startswith("REWRITE ")})) or "them", args.slug))
            if run(["git", "branch", "-r", "--contains", "HEAD", "--list", "origin/*"], cwd=top).stdout.strip() == "":
                sys.exit("REFUSED: this branch's latest commit is not on origin. Fix: run wiki.py prepare %s --commit." % args.slug)
        if known != "OPEN":
            sys.exit("REFUSED: the pull request %s is %s, not open." % (state["pr"], known or "unknown"))
        tested = state.get("pr_head")
        if tested and info.get("headRefOid") and info["headRefOid"] != tested and wiki_only(top, cfg, tested, info["headRefOid"]):
            print("NOTE: the pull request head moved only by wiki page commits (wiki.py prepare); merging %s" % info["headRefOid"][:12])
            tested = info["headRefOid"]  # only wiki pages changed since the lane: no row's code moved
        if tested and info.get("headRefOid") and info["headRefOid"] != tested:
            print("REFUSED (HEAD_MOVED): the pull request head moved since the pr lane passed (lane on %s, PR head %s). Fix: "
                  "goal.py pr %s, then merge.py %s" % (tested[:12], info["headRefOid"][:12], args.slug, args.slug), file=sys.stderr)
            return 4
        moved = base_moved(state, cfg, top)
        if moved:
            print(moved[1], file=sys.stderr)
            return moved[0]
        autorelease.run_routines(top, cfg, state)
        autorelease.stage_notes(top, state, cfg)
        autorelease.stage_part(top, state)
        done = run(["gh", "pr", "merge", state["pr"], "--merge"] + (["--match-head-commit", tested] if tested else []))
        if done.returncode:
            autorelease.fail(state, "gh could not merge %s: %s" % (state["pr"], done.stderr.strip()[-300:]))
    at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state["release"] = state["release"] if state.get("release") == "cut" else "merged"
    state["updated"] = at
    state.setdefault("log", []).append("%s merged %s (auto_merge)" % (at, state["pr"]))
    with open(path + ".tmp", "w") as handle:
        json.dump(state, handle, indent=2)
    os.replace(path + ".tmp", path)
    print("MERGED %s into %s" % (state["pr"], cfg.get("base", "main")))
    autorelease.finish(top, cfg, state)
    if wiki.top_of():
        wiki.cmd_publish(argparse.Namespace(slug=args.slug))
    return 0


if __name__ == "__main__":
    sys.exit(main())
