#!/usr/bin/env python3
"""The release pull request: how the automatic release lands on a protected base branch (DEL-5).

autorelease.py calls it when the base takes no direct push (a `pull_request` rule, or a push refused for protection).
It pushes the release commit to `release/vX-<slug>` (force-updating only that branch on a restart), opens
`Release vX (<slug>)` with the release notes as its body, all scanned for private names first, and merges it itself
with `gh pr merge --merge`, never `--admin`. The merge happens here, never through merge.py, so it can't start a
second release.

What `gh pr view --json state,mergeStateStatus,reviewDecision,mergeCommit` says decides the next move:
  MERGED   VERSION at the merge commit must be vX (else RELEASE_VERSION_MISMATCH); the release targets that commit
  OPEN     required checks pending: waiting (`release_pr_waiting`, no error); the next merge.py run retries.
           A review required, or blocked: `release_error` RELEASE_PR_BLOCKED with the owner's command.
           A conflict (another release moved VERSION): close it and start again with the next version.
  CLOSED   forget it and start again on the new base
"""
import json

import autorelease
import release

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
