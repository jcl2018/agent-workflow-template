#!/usr/bin/env python3
"""The automatic release, called by merge.py: run the owner's routines, then after the merge bump the version once,
write the CHANGELOG entry, push that commit to the base branch and create a published GitHub release.

No draft, no question. Every failure is recorded on the goal as `release_error`, which shows under Needs you.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import release

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

PUSH_TRIES = 3


def sh(args, cwd=None):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    except OSError as error:
        return subprocess.CompletedProcess(args, 127, "", str(error))


def fail(state, text):
    """Record the failure on the goal and stop."""
    state["release_error"] = text[:400]
    report = state.setdefault("report", {})
    report["text"] = ("%s Release failed: %s" % (report.get("text", ""), text)).strip()[:600]
    release.save(state, "release failed: " + text[:200])
    sys.exit("REFUSED: " + text)


def base_config(top, cfg):
    """The routines come from the base branch, so a pull request cannot add a command the merge then runs."""
    base = cfg.get("base", "main")
    shown = sh(["git", "show", "origin/%s:.loop/config.json" % base], cwd=top)
    try:
        return json.loads(shown.stdout) if shown.returncode == 0 else cfg
    except ValueError:
        return cfg


def run_routines(top, cfg, state):
    for item in base_config(top, cfg).get("routines") or []:
        argv = ["sh", "-c", item] if isinstance(item, str) else list(item)
        done = sh(argv, cwd=top)
        if done.returncode:
            tail = (done.stderr or done.stdout).strip()[-200:]
            fail(state, "routine %s exited %d before the merge, so nothing was merged: %s" % (
                item if isinstance(item, str) else " ".join(item), done.returncode, tail))
        print("ROUTINE ok: %s" % (item if isinstance(item, str) else " ".join(item)))


def need_of(top, state):
    """patch for any change, minor for a new feature, a breaking change gets major (minor while the version is 0.x)."""
    part, reason = release.auto_need(top, state)
    if part == "leave":
        return "patch", "a docs or test change"
    if part == "ask":
        return "major", reason
    return part, reason


def stage_notes(top, state, cfg):
    if "release_bullets" not in state:
        state["release_bullets"] = release.subjects(release.base_of(top, cfg), top)
        state["release_steps"] = release.verify_steps(top, state["slug"]) or "No manual steps were recorded."
        release.save(state)


def stage_part(top, state):
    if not state.get("release_part"):
        state["release_part"], state["release_reason"] = need_of(top, state)
        release.save(state)


def next_version(old, part):
    if part == "major" and old.startswith("0."):
        part = "minor"
    return release.bump(old, part)


def push_release_commit(top, cfg, state, part):
    base = cfg.get("base", "main")
    slug = state["slug"]
    temp = tempfile.mkdtemp(prefix="release-")
    tree = os.path.join(temp, "tree")
    try:
        for _ in range(PUSH_TRIES):
            if sh(["git", "fetch", "-q", "origin", base], cwd=top).returncode:
                fail(state, "could not fetch origin/%s" % base)
            sh(["git", "worktree", "remove", "--force", tree], cwd=top)
            if sh(["git", "worktree", "add", "-q", "--detach", tree, "origin/" + base], cwd=top).returncode:
                fail(state, "could not check out origin/%s" % base)
            version_file = cfg.get("version_file") or "VERSION"
            if os.path.isabs(version_file) or ".." in version_file.split("/"):
                fail(state, "version_file must be a path inside the repo")
            vpath = os.path.join(tree, version_file)
            if os.path.exists(vpath):
                with open(vpath) as handle:
                    version = next_version(handle.read().strip(), part)
            else:
                version = "0.1.0"
            tag = "v" + version
            if sh(["git", "ls-remote", "--exit-code", "--tags", "origin", tag], cwd=top).returncode == 0:
                fail(state, "tag %s already exists" % tag)
            cpath = os.path.join(tree, "CHANGELOG.md")
            old = open(cpath).read() if os.path.exists(cpath) else ""
            day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
            with open(vpath, "w") as handle:
                handle.write(version + "\n")
            with open(cpath, "w") as handle:
                handle.write(release.changelog_text(old, version, day, state["release_bullets"], state["release_steps"]))
            files = [version_file, "CHANGELOG.md"]
            made = sh(["git", "add", "--"] + files, cwd=tree).returncode == 0 and sh(
                ["git", "commit", "-q", "-m", "Release %s (%s)" % (tag, slug), "--"] + files, cwd=tree).returncode == 0
            if not made:
                fail(state, "could not commit the release files")
            pushed = sh(["git", "push", "origin", "HEAD:" + base], cwd=tree)
            if pushed.returncode == 0:
                return version
            # Another goal moved the base first: read it again and redo the bump on top of it.
        fail(state, "push to %s was rejected %d times: %s" % (base, PUSH_TRIES, pushed.stderr.strip()[-200:]))
    finally:
        sh(["git", "worktree", "remove", "--force", tree], cwd=top)
        shutil.rmtree(temp, ignore_errors=True)


def create_release(top, cfg, state, version):
    base = cfg.get("base", "main")
    notes = tempfile.NamedTemporaryFile("w", suffix=".md", prefix="release-notes-", delete=False)
    with notes:
        notes.write("\n".join("- " + item for item in state["release_bullets"]) or "- No code changes")
        notes.write("\n\n## How to verify\n\n%s\n\nPull request: %s\n" % (state["release_steps"], state.get("pr", "")))
    try:
        made = sh(["gh", "release", "create", "v" + version, "--title", "v" + version, "--notes-file", notes.name,
                   "--target", base], cwd=top)
    finally:
        os.remove(notes.name)
    if made.returncode:
        fail(state, "gh release create v%s failed after the version was pushed; run merge.py again: %s" % (
            version, (made.stderr or made.stdout).strip()[-200:]))
    return (made.stdout.strip().splitlines() or [""])[-1]


def finish(top, cfg, state):
    """After the merge. Each step records itself, so a retry repeats only what did not finish."""
    if state.get("release") == "cut" and state.get("release_url"):
        print("ALREADY released %s as v%s" % (state["slug"], state.get("release_version")))
        return
    if not state.get("release_pushed"):
        stage_notes(top, state, cfg)
        stage_part(top, state)
        part, reason = state["release_part"], state["release_reason"]
        version = push_release_commit(top, cfg, state, part)
        state.update(release_pushed=version, release_part=part)
        release.save(state, "version pushed: v%s (%s)" % (version, reason))
    version = state["release_pushed"]
    url = create_release(top, cfg, state, version)
    state.update(release="cut", release_version=version, release_url=url, status="done", waiting=None)
    state.pop("release_error", None)
    release.save(state, "release v%s published %s" % (version, url))
    print("RELEASED v%s %s (%s bump)" % (version, url, state["release_part"]))
