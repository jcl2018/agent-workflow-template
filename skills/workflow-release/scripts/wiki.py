#!/usr/bin/env python3
"""The release step's wiki half: bring the goal's pages up to date before the merge, publish them after it.

usage: wiki.py <command> SLUG

  prepare SLUG [--commit]   list every wiki page docs.py check calls stale or missing, mapped to a touched path or not (exit 1);
                            with --commit, first commit edited pages in the wiki folder on the goal's branch, and when
                            nothing is stale push the branch. The agent rewrites the pages; this only checks.
  publish SLUG              after the merge: run docs.py publish from a clean checkout of origin/<base>; on a refusal
                            record `wiki_error` (page and reason) on the goal, which shows under Issues.

A repo without .loop/docs.tsv has no wiki: both commands do nothing. It runs git and docs.py, and nothing else.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import release
from release import base_of, git, load, read_config, run, save

os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")  # release.py sets the rest on import
DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-docs", "scripts", "docs.py")


def top_of():
    top = git("rev-parse", "--show-toplevel")
    return top if os.path.exists(os.path.join(top, ".loop", "docs.tsv")) else None


def pending(top, cfg, fix=False):
    """What the docs audit still finds for the goal, one line each. fix lets it mend the mechanical trouble first."""
    base = base_of(top, cfg)
    if fix:
        release.docs_trouble(top, base, True)  # mend the goal's own mechanical trouble, scoped to its commits
    return release.docs_trouble(top, base, whole=True)


def commit(top, cfg, slug):
    folder = cfg.get("wiki_dir") or "docs/wiki"
    if run(["git", "status", "--porcelain", "--", folder], cwd=top).stdout.strip():
        git("add", "--", folder, cwd=top)
        git("commit", "-m", "Wiki: update pages for %s" % slug, "--", folder, cwd=top)
        print("COMMITTED the wiki pages for %s" % slug)


def cmd_prepare(args):
    top = top_of()
    if not top:
        print("NO WIKI: .loop/docs.tsv is not set up.")
        return 0
    cfg = read_config(top)
    if args.commit:
        commit(top, cfg, args.slug)
    stale = pending(top, cfg, fix=args.commit)
    if args.commit:
        commit(top, cfg, args.slug)  # the audit's mechanical fixes
    for line in stale:
        print(line)
    if stale:
        names = sorted({l.split(":")[0].split()[1] for l in stale if l.startswith("REWRITE ")})
        print("NEXT: update %s, then wiki.py prepare %s --commit" % (", ".join(names) or "the pages above", args.slug))
        return 1
    if args.commit and load(args.slug).get("pr"):
        branch = git("branch", "--show-current", cwd=top)
        pushed = run(["git", "push", "origin", "HEAD:" + branch], cwd=top)
        if pushed.returncode:
            sys.exit("REFUSED: push of the wiki update failed: " + pushed.stderr.strip()[:300])
    print("WIKI CURRENT: no stale page for %s" % args.slug)
    return 0


def publish(top, cfg, slug):
    """Publish from origin/<base>. Returns the error text, or '' when the wiki is current or published."""
    base = cfg.get("base", "main")
    if run(["git", "fetch", "-q", "origin", base], cwd=top).returncode:
        return "could not fetch origin/%s" % base
    temp = tempfile.mkdtemp(prefix="wikipub-")
    tree = os.path.join(temp, "tree")
    try:
        if run(["git", "worktree", "add", "-q", "--detach", tree, "origin/" + base], cwd=top).returncode:
            return "could not check out origin/%s" % base
        done = run([sys.executable, DOCS, "publish"], cwd=tree)
        lines = (done.stdout + done.stderr).strip().splitlines()
        if done.returncode:
            reasons = [line for line in lines if not line.startswith("REFUSED")] or lines
            return " | ".join(line.strip() for line in (reasons[:3] + [line for line in lines if line.startswith("REFUSED")][:1]))[:400]
        print("\n".join(lines))
        return ""
    finally:
        run(["git", "worktree", "remove", "--force", tree], cwd=top)
        shutil.rmtree(temp, ignore_errors=True)


def cmd_publish(args):
    top = top_of()
    if not top:
        print("NO WIKI: .loop/docs.tsv is not set up.")
        return 0
    state = load(args.slug)
    error = publish(top, read_config(top), args.slug)
    if error:
        state["wiki_error"] = error
        report = state.setdefault("report", {})
        report["text"] = ("%s Wiki not published: %s" % (report.get("text", ""), error)).strip()
        save(state, "wiki not published: " + error)
        print("WIKI REFUSED %s: %s" % (args.slug, error))
        return 1
    state.pop("wiki_error", None)
    save(state, "wiki published")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("prepare")
    item.add_argument("slug")
    item.add_argument("--commit", action="store_true")
    item.set_defaults(func=cmd_prepare)
    item = sub.add_parser("publish")
    item.add_argument("slug")
    item.set_defaults(func=cmd_publish)
    args = parser.parse_args()
    release.state_path(args.slug)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
