#!/usr/bin/env python3
"""The release step's wiki half: bring the goal's pages up to date before the merge, publish them after it.

usage: wiki.py <command> SLUG
       wiki.py batch plan|run [--size N] [--merge]   verify 3-4 ready pull requests with disjoint touches together (DEL-15)

  prepare SLUG [--commit]   list every wiki page docs.py check calls stale or missing, mapped to a touched path or not (exit 1);
                            with --commit, first commit edited pages in the wiki folder on the goal's branch, and when
                            nothing is stale push the branch. The agent rewrites the pages; this only checks.
  publish SLUG              after the merge: run docs.py publish from a clean checkout of origin/<base>; on a refusal
                            record `wiki_error` (page and reason) on the goal, which shows under Issues.

Both scan for private names first: prepare --commit scans the branch before its push; publish scans every page in the
wiki folder and publishes nothing on a hit (wiki_error names the page and line). A GitHub wiki with no first page can't
be cloned: the error says to create the first page in the repo's Wiki tab, then run merge.py SLUG again (issue 129).

A repo without .loop/docs.tsv has no wiki: both commands do nothing. It runs git and docs.py, and nothing else.

It also holds the release notes' proof lines (REG-6), fixes_lines: one "Fixes #N: test ROW, seen failing DATE, passing"
line per issue fixed since the previous v* tag, from workflow-regression's tests.py fixes. Called by release.py (cut) and
autorelease.py. A missing tests.py gives "Fixes: unknown (workflow-regression not installed)"; a failing one gives
"Fixes: not listed (<first line>). Note: ...": a report never fails a release. workflow-regression/references/commands.md.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

import autorelease
import release
from release import base_of, git, load, read_config, run, save

os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")  # release.py sets the rest on import
DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-docs", "scripts", "docs.py")
CRITERIA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-docs", "scripts",
                                         "criteria.py"))
TESTS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-regression",
                                      "scripts", "tests.py"))


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
        stop = autorelease.private_check(top, base_of(top, cfg), {}, True)
        if stop:
            sys.exit("REFUSED: %s. Fix: %s (%s)" % stop)
        pushed = run(["git", "push", "origin", "HEAD:" + branch], cwd=top)
        if pushed.returncode:
            sys.exit("REFUSED: push of the wiki update failed: " + pushed.stderr.strip()[:300])
    print("WIKI CURRENT: no stale page for %s" % args.slug)
    return 0


def rerender(tree, cfg):
    """Re-render the generated Tests tables in the publish tree and commit them there (DOC-11), so staleness that is only
    generated never blocks the publish. Returns the pages it changed. Hand-written pages are not touched, and a failed
    render is printed, not fatal: docs.py publish then names what is still stale."""
    done = run([sys.executable, CRITERIA, "render", "--tables"], cwd=tree)
    if done.returncode:
        print("RENDER FAILED: " + ((done.stderr or done.stdout).strip().splitlines() or ["exit %d" % done.returncode])[0][:200])
        return []
    folder = cfg.get("wiki_dir") or "docs/wiki"
    changed = [l[3:].strip().replace("\\", "/") for l in run(["git", "status", "--porcelain", "--", folder], cwd=tree).stdout.splitlines()]
    if not changed:
        return []
    git("add", "--", folder, cwd=tree)
    git("-c", "user.name=workflow-loop", "-c", "user.email=loop@localhost", "commit", "-m", "Wiki: re-render generated tables",
        "--", folder, cwd=tree)
    pages = [os.path.basename(path)[:-3] for path in changed if path.endswith(".md")]
    print("RERENDERED " + ", ".join(pages))
    return pages


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
        rerender(tree, cfg)
        folder = os.path.join(tree, cfg.get("wiki_dir") or "docs/wiki")
        texts = {}
        for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            if name.endswith(".md"):
                with open(os.path.join(folder, name), encoding="utf-8", errors="replace") as handle:
                    texts["wiki:" + name[:-3]] = handle.read()
        stop = autorelease.private_check(top, None, texts)
        if stop and stop[2] == "PRIVATE_NAME":
            return ("%s; nothing was published. Fix: remove the name from that page on %s (a goal that edits it), or edit "
                    "that line of the list for a false positive, then run merge.py %s again (PRIVATE_NAME)" % (stop[0], base, slug))
        if stop:
            return "%s; nothing was published. Fix: %s (%s)" % stop
        done = run([sys.executable, DOCS, "publish"], cwd=tree)
        lines = (done.stdout + done.stderr).strip().splitlines()
        if done.returncode and any("can't read the wiki" in line for line in lines):
            return ("the GitHub wiki has no first page, so it can't be cloned; nothing was published. Fix: create the "
                    "first page in the repo's Wiki tab, then run merge.py %s again" % slug)
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
        report, note = state.get("report"), ""
        if not isinstance(report, dict):  # a goal reset leaves report null; a hand edit can leave anything
            note = "" if report is None else "(the stored report was a %s and was reset) " % type(report).__name__
            report = state["report"] = {}
        report["text"] = ("%s %sWiki not published: %s" % (str(report.get("text") or ""), note, error)).strip()[:600]
        save(state, "wiki not published: " + error)
        print("WIKI REFUSED %s: %s" % (args.slug, error))
        return 1
    state.pop("wiki_error", None)
    save(state, "wiki published")
    return 0


def fixes_since(top):
    """The previous v* tag reachable from HEAD, else the first commit."""
    tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0", "--match", "v*"], cwd=top, capture_output=True, text=True)
    if tag.returncode == 0 and tag.stdout.strip():
        return tag.stdout.strip()
    roots = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=top, capture_output=True, text=True)
    return (roots.stdout.split() or ["HEAD"])[-1]


def fixes_lines(top, start=None):
    """The Fixes lines (or the one line saying why there are none listed) for the release notes and CHANGELOG."""
    if not os.path.exists(TESTS):
        return ["Fixes: unknown (workflow-regression not installed)"]
    start = start or fixes_since(top)
    done = subprocess.run([sys.executable, TESTS, "fixes", "--since", start, "--root", top], cwd=top, capture_output=True,
                          text=True)
    if done.returncode:
        first = ((done.stderr or done.stdout).strip().splitlines() or ["exit %d" % done.returncode])[0]
        return ["Fixes: not listed (%s). Note: issue states are unchanged; run tests.py fixes --since %s by hand"
                % (first[:200], start)]
    return [line for line in done.stdout.splitlines() if line.startswith("Fixes #")]


# Batch merge (DEL-15): ready goals with disjoint touches are verified together on one tree and merged in one go.
HERE = os.path.dirname(os.path.abspath(__file__))


def loop_dir():
    done = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True)
    return os.path.join(os.path.abspath(done.stdout.strip() or ".git"), "loop")


def ready(runs):
    """[(slug, touches)] of the goals ready to merge, oldest record first."""
    found = []
    for path in sorted(glob.glob(os.path.join(runs, "*.json"))):
        try:
            with open(path) as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            continue
        if isinstance(state, dict) and state.get("status") == "done" and state.get("pr") and not state.get("merged") \
                and not (state.get("hold_at") or state.get("held_at")) and state.get("release") != "ask":
            found.append((state.get("slug") or os.path.basename(path)[:-5], [str(t).strip("/") for t in state.get("touches") or []]))
    return found


def overlap(mine, theirs):
    """Same rule as the pr queue: any two paths equal or nested; no touches overlaps everything."""
    return not mine or not theirs or any(a == b or a.startswith(b + "/") or b.startswith(a + "/") for a in mine for b in theirs)


def group(goals, size=3):
    """Batches of at most `size` (at most 4) goals whose touches overlap none of their batch-mates', in order."""
    size, batches = max(1, min(int(size), 4)), []
    for slug, touches in goals:
        for batch in batches:
            if len(batch) < size and not any(overlap(touches, t) for _, t in batch):
                batch.append((slug, touches))
                break
        else:
            batches.append([(slug, touches)])
    return batches


def culprits(slugs, passes):
    """The goals that make `passes(list of slugs)` fail: [] when the batch passes; one slug when a single goal fails alone;
    a pair of halves that each pass but fail together is named as 'a+b'. Halves are checked alone, so a batch of n costs
    about 2*log2(n) more checks."""
    if passes(slugs):
        return []
    if len(slugs) == 1:
        return list(slugs)
    mid = len(slugs) // 2
    found = culprits(slugs[:mid], passes) + culprits(slugs[mid:], passes)
    return found or ["+".join(slugs)]  # each half passes alone: the failure is between them


def check_tree(base, slugs, command, states):
    """Merge the goals' branches into a temporary tree from origin/<base> and run the check there; True when it passes."""
    temp = tempfile.mkdtemp(prefix="batch-")
    tree = os.path.join(temp, "tree")
    try:
        if subprocess.run(["git", "worktree", "add", "-q", "--detach", tree, "origin/" + base], capture_output=True).returncode:
            return False
        for slug in slugs:
            branch = states[slug].get("branch") or "loop/" + slug
            merged = subprocess.run(["git", "-C", tree, "-c", "user.name=batch", "-c", "user.email=batch@localhost", "merge", "--no-edit",
                                     "origin/" + branch], capture_output=True)
            if merged.returncode:
                return False
        return subprocess.run(command, cwd=tree, shell=isinstance(command, str)).returncode == 0
    finally:
        subprocess.run(["git", "worktree", "remove", "--force", tree], capture_output=True)


def cmd_batch(args):
    runs = os.path.join(loop_dir(), "runs")
    goals = ready(runs)
    batches = group(goals, args.size)
    if not batches:
        print("NO BATCH: no goal is ready to merge")
        return 0
    for number, batch in enumerate(batches, 1):
        print("BATCH %d: %s" % (number, ", ".join(slug for slug, _ in batch)))
    if args.action == "plan":
        return 0
    states = {}
    for slug, _ in goals:
        with open(os.path.join(runs, slug + ".json")) as handle:
            states[slug] = json.load(handle)
    top = run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()
    cfg = read_config(top)
    base = cfg.get("base", "main")
    command = cfg.get("batch_check") or [sys.executable, os.path.join(HERE, "..", "..", "workflow-regression", "scripts", "regression.py"), "run"]
    code = 0
    for number, batch in enumerate(batches, 1):
        slugs = [slug for slug, _ in batch]
        bad = culprits(slugs, lambda part: check_tree(base, part, command, states))
        for name in bad:
            print("CULPRIT %s: batch %d fails with it" % (name, number))
            code = 1
        good = [slug for slug in slugs if slug not in "+".join(bad).split("+")]
        print("BATCH %d %s: %s" % (number, "PASSES" if not bad else "SPLIT", ", ".join(good) or "nothing passes"))
        for slug in good if args.merge else []:
            done = subprocess.run([sys.executable, os.path.join(HERE, "merge.py"), slug])
            code = code or done.returncode
    return code


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
    item = sub.add_parser("batch")
    item.add_argument("action", choices=["plan", "run"])
    item.add_argument("--size", type=int, default=3)
    item.add_argument("--merge", action="store_true")
    item.set_defaults(func=cmd_batch, slug="")
    args = parser.parse_args()
    args.slug and release.state_path(args.slug)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
