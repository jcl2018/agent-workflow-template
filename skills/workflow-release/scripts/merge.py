#!/usr/bin/env python3
"""Merge a finished goal's pull request into the base branch: the release step, for now.

usage: merge.py SLUG

It refuses unless `"auto_merge": true` is in .loop/config.json, the goal is done and its pull request is open. A repo
without that switch keeps the owner's merge: nothing here merges there. Then it runs the routines listed in .loop/config.json on the base branch and refuses if one fails, merges, and
releases: one version bump, a CHANGELOG entry and a published GitHub release (autorelease.py). Any failure is recorded
on the goal as `release_error`. Where .loop/docs.tsv maps pages, it first refuses while a page the goal's paths map to is stale,
and after the merge it publishes the wiki through wiki.py; a refused publish is recorded as `wiki_error`, not undone.
Before merging it scans the branch and the release notes for private names (refusing, nothing merged), and holds the
merge (REQUIREMENT_MISSING) while a criterion row the goal adds names a requirement ID no wiki page on the base names,
where the base's pages already use that ID's prefix; otherwise a missing ID is only a NOTE.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
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


def missing_ids(top, cfg, head="HEAD"):
    """(held, noted): requirement IDs of criterion rows this goal adds that no wiki page on origin/<base> names."""
    base = "origin/" + cfg.get("base", "main")
    folder = (cfg.get("wiki_dir") or "docs/wiki").strip("/")
    added = run(["git", "diff", "-U0", base + "..." + head, "--", ".loop/regression.tsv"], cwd=top).stdout
    ids = set()
    for line in added.splitlines():
        cells = line[1:].split("\t") if line.startswith("+") and not line.startswith("+++") else []
        if len(cells) > 3 and (cells[6:7] in ([], [""], ["criterion"])) and re.match(r"^[A-Z]{2,5}-\d+$", cells[3]):
            ids.add(cells[3])
    if not ids:
        return [], []
    names = run(["git", "ls-tree", "--name-only", base, folder + "/"], cwd=top).stdout.split()
    text = "\n".join(run(["git", "show", "%s:%s" % (base, name)], cwd=top).stdout for name in names if name.endswith(".md"))
    mine = run(["git", "ls-tree", "--name-only", head, folder + "/"], cwd=top).stdout.split()  # a page this goal adds or edits counts too
    own = "\n".join(run(["git", "show", head + ":" + name], cwd=top).stdout for name in mine if name.endswith(".md"))
    gone = sorted(i for i in ids if not re.search(r"\b%s\b" % re.escape(i), text + "\n" + own))
    held = [i for i in gone if names and re.search(r"\b%s\d+\b" % re.escape(i.split("-")[0] + "-"), text)]
    return held, [i for i in gone if i not in held]


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
    view = run(["gh", "pr", "view", state["pr"], "--json", "state"])
    known = json.loads(view.stdout).get("state") if view.returncode == 0 else ""
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
        autorelease.stage_notes(top, state, cfg)
        autorelease.stage_part(top, state)
        head = "origin/" + state.get("branch", "")  # the pull request's own tip, wherever merge.py runs
        if not state.get("branch") or run(["git", "fetch", "-q", "origin", state["branch"]], cwd=top).returncode:
            autorelease.fail(state, "could not fetch the goal branch %s to scan it; nothing was merged (PRIVATE_LIST)" % state.get("branch"))
        autorelease.check(state, top, "origin/" + cfg.get("base", "main"), {"release notes": autorelease.notes_text(state)}, True, head)
        held, noted = missing_ids(top, cfg, head)
        if held:
            autorelease.fail(state, "criterion rows name %s, which no wiki page on origin/%s names; nothing was merged. Fix: "
                             "merge the goal that adds their text, then merge.py %s (REQUIREMENT_MISSING)" % (
                                 ", ".join(held), cfg.get("base", "main"), args.slug))
        if noted:
            print("NOTE: no wiki page on the base names %s yet; merging anyway" % ", ".join(noted))
        autorelease.run_routines(top, cfg, state)
        done = run(["gh", "pr", "merge", state["pr"], "--merge"])
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
