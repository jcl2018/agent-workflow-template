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

Also here (the package stays under its file cap), the release pull request, which autorelease.py calls as
`merge.advance` when the base takes no direct push (a `pull_request` rule, or a push refused for protection): it pushes
the release commit to `release/vX-<slug>` (force-updating only that branch on a restart), opens `Release vX (<slug>)`
with the release notes as its body, all scanned for private names first, and merges it itself with `gh pr merge
--merge`, never `--admin`, never through main() here, so it can't start a second release. What `gh pr view` says decides
the next move: MERGED: VERSION at the merge commit must be vX (else RELEASE_VERSION_MISMATCH) and the release targets
that commit; OPEN: required checks pending wait (`release_pr_waiting`, no error; the next merge.py run retries), a
required review or a block records RELEASE_PR_BLOCKED with the owner's command, a conflict closes it and starts again
with the next version; CLOSED: forget it and start again on the new base.
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
    if not was and state.get("pr_head"):  # goal.py pr recorded a head but no base (origin/<base> unresolved): unknown, never clear
        return 2, "REFUSED (BASE_MOVED): the base the pr lane ran on was not recorded. Fix: goal.py pr %s, then merge.py %s" % (
            state.get("slug", "SLUG"), state.get("slug", "SLUG"))
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



# ---- the release pull request (DEL-5, issues 134 and 154)
FIELDS = "state,mergeStateStatus,reviewDecision,mergeCommit,statusCheckRollup,url,number"
REVIEW = ("REVIEW_REQUIRED", "CHANGES_REQUESTED")
PENDING = ("QUEUED", "IN_PROGRESS", "WAITING", "PENDING", "REQUESTED", "EXPECTED")
KEYS = ("release_pr", "release_pr_branch", "release_pr_version", "release_pushed", "release_pr_waiting")


def title_of(version, slug):
    return "Release v%s (%s)" % (version, slug)


def view(top, ref):
    got = autorelease.sh(["gh", "pr", "view", ref, "--json", FIELDS], cwd=top)
    try:
        seen = json.loads(got.stdout) if got.returncode == 0 else {}
    except ValueError:
        seen = {}
    return seen if isinstance(seen, dict) else {}


def forget(state, why):
    for key in KEYS:
        state.pop(key, None)
    release.save(state, "release PR forgotten: " + why)
    print("RESTART the release pull request: " + why)


def start(top, cfg, state):
    """Push release/vX-<slug> and open its pull request; records release_pr."""
    base, slug = cfg.get("base", "main"), state["slug"]
    version, _ = autorelease.push_release_commit(top, cfg, state, state["release_part"], to_branch=True)
    branch = "release/v%s-%s" % (version, slug)
    title, body = title_of(version, slug), autorelease.notes_text(state)
    autorelease.check(state, top, None, {"release PR title": title, "release notes": body})
    made = autorelease.sh(["gh", "pr", "create", "--base", base, "--head", branch, "--title", title, "--body", body],
                          cwd=top)
    url = (made.stdout.strip().splitlines() or [""])[-1] if made.returncode == 0 else ""
    if not url:  # a restart may find its pull request still open
        seen = view(top, branch)
        url = seen.get("url", "") if seen.get("state") == "OPEN" else ""
    if not url:
        autorelease.fail(state, "gh pr create for %s failed: %s. Side effects: branch %s pushed, no pull request "
                         "(partial). Fix: run merge.py %s again" % (branch, (made.stderr or "").strip()[-200:], branch, slug))
    state.update(release_pr=url, release_pr_branch=branch, release_pr_version=version)
    release.save(state, "release PR %s opened for v%s" % (url, version))
    print("RELEASE PR %s (%s)" % (url, title))


def pending(seen):
    return any(isinstance(item, dict) and (item.get("status") in PENDING or item.get("state") in PENDING)
               for item in seen.get("statusCheckRollup") or [])


def advance(top, cfg, state, again=False):
    """(version, merge commit) once the release PR is merged, None while it waits. Records any error and stops."""
    if not state.get("release_pr"):
        start(top, cfg, state)
    url, version, slug = state["release_pr"], state["release_pr_version"], state["slug"]
    seen, said = view(top, url), ""
    if seen.get("state") == "OPEN":
        autorelease.check(state, top, None, {"release PR title": title_of(version, slug),
                                             "release notes": autorelease.notes_text(state)})
        merged = autorelease.sh(["gh", "pr", "merge", url, "--merge"], cwd=top)
        said = (merged.stderr or merged.stdout).strip()[-200:]
        seen = view(top, url)
    status, number = seen.get("state"), seen.get("number") or url.rstrip("/").split("/")[-1]
    if status == "MERGED":
        oid = (seen.get("mergeCommit") or {}).get("oid") or ""
        autorelease.sh(["git", "fetch", "-q", "origin", cfg.get("base", "main")], cwd=top)
        found = autorelease.sh(["git", "show", "%s:%s" % (oid, cfg.get("version_file") or "VERSION")], cwd=top)
        if oid and found.stdout.strip() != version:  # the owner set VERSION on the base by hand: release at its tip
            tip = autorelease.sh(["git", "rev-parse", "origin/" + cfg.get("base", "main")], cwd=top).stdout.strip()
            fixed = autorelease.sh(["git", "show", "origin/%s:%s" % (cfg.get("base", "main"), cfg.get("version_file") or "VERSION")], cwd=top)
            oid, found = (tip, fixed) if tip and fixed.stdout.strip() == version else (oid, found)
        if not oid or found.stdout.strip() != version:
            autorelease.fail(state, "the release PR %s merged, but VERSION at its merge commit %s is %r, not %s; no "
                             "release was created. Fix: set VERSION on the base by hand, then run merge.py %s "
                             "(RELEASE_VERSION_MISMATCH)" % (url, oid[:12] or "(none)", found.stdout.strip(), version, slug))
        state.pop("release_pr_waiting", None)
        print("MERGED the release PR %s at %s" % (url, oid[:12]))
        return version, oid
    if not again and (status == "CLOSED" or (status == "OPEN" and seen.get("mergeStateStatus") in ("DIRTY", "BEHIND"))):
        if status == "OPEN":  # another release moved VERSION first: the next version, on the new base
            autorelease.sh(["gh", "pr", "close", url], cwd=top)
        forget(state, "%s was %s" % (url, "closed unmerged" if status == "CLOSED" else "behind the base"))
        return advance(top, cfg, state, again=True)
    if status == "OPEN" and seen.get("reviewDecision") not in REVIEW and (pending(seen) or seen.get("mergeStateStatus") == "UNKNOWN"):
        state["release_pr_waiting"] = "checks pending on %s (#%s)" % (url, number)
        state.pop("release_error", None)
        release.save(state, "waiting: " + state["release_pr_waiting"])
        print("WAITING %s: required checks are pending on the release PR %s; the next merge.py %s run merges it"
              % (slug, url, slug))
        return None
    state["release_tries"] = state.get("release_tries", 0) + 1
    why = "a review is required" if seen.get("reviewDecision") in REVIEW else "it is %s, %s" % (
        status or "unreadable", seen.get("mergeStateStatus") or said or "no reason given")
    autorelease.fail(state, "the release PR %s (#%s) can't merge: %s; it needs the owner to approve and merge it. Fix: "
                     "gh pr merge %s --merge, then merge.py %s. Side effects: branch %s pushed and the pull request open "
                     "(partial); try %d (RELEASE_PR_BLOCKED)" % (url, number, why, number, slug,
                                                                 state.get("release_pr_branch"), state["release_tries"]))


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
