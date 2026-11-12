#!/usr/bin/env python3
"""The repo half of update.py: bring one repo's generated files and settings up to the installed template version.

usage: sync.py [--repo DIR] [--version X] [--wrote-skills]   (update.py --apply runs it; alone it syncs to the installed version)

It reads the base branch's .loop/config.json, never the person's checkout, and writes in a temporary worktree on
branch workflow-update-vX cut from the base branch:

    base ──(git worktree add -b workflow-update-vX)──> <git common dir>/loop/update-worktree
      fill missing repo settings (settings.fill_repo) · template_version = X · entry.py write · agents.py wire
      commit .loop/config.json .loop/START.md and the agent files ──> remove the worktree (always)
    branch states: none -> cut from base; unmerged -> reused (no new commit if nothing changed: PENDING);
                   merged but base's config still older -> refused (UPDATE_BRANCH_MERGED)

Hand-written data (config values already set, pages, rules, local settings) is only added to; the generated files
(START.md, the marked agent blocks, the stamp) are replaced. It never merges or pushes: NEXT says how to merge.
"""
import argparse
import difflib
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402
import settings  # noqa: E402

os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


class Txn:
    """setup's transaction: its folders are copied and a journal kept in the git dir before the first write, so a refusal, an
    exception, a signal or a hard kill (the next run recovers) leaves the tree, index and branches as they were."""

    def __init__(self, repo, branch, extra=(), journal=None):
        self.repo, self.branch, self.j = repo, branch, journal
        self.tops = (".loop", ".github/workflows", ".gitignore", "README.md") + tuple(extra)
        self.gd = git(repo, "rev-parse", "--absolute-git-dir")
        self.dir = os.path.join(self.gd, "workflow-setup-txn")

    def g(self, *args):
        return git(self.repo, *args, check=False)

    def files(self):
        for top in self.tops:
            full = os.path.join(self.repo, top)
            walked = os.walk(full) if os.path.isdir(full) and not os.path.islink(full) else [(os.path.dirname(full), [], [os.path.basename(full)])] if os.path.lexists(full) else []
            yield from (os.path.relpath(os.path.join(base, n), self.repo) for base, _, names in walked for n in names)

    def state(self, rel):
        full = os.path.join(self.repo, rel)
        return os.readlink(full) if os.path.islink(full) else hashlib.sha1(open(full, "rb").read()).hexdigest() if os.path.isfile(full) else None

    def begin(self):
        """Copy the folders, then journal HEAD, the branches, the index tree and each file's hash."""
        shutil.rmtree(self.dir, ignore_errors=True)
        for n, top in enumerate(self.tops):
            full = os.path.join(self.repo, top)
            if os.path.isdir(full) and not os.path.islink(full):
                shutil.copytree(full, os.path.join(self.dir, str(n)), symlinks=True)
            elif os.path.lexists(full):
                os.makedirs(self.dir, exist_ok=True)
                os.symlink(os.readlink(full), os.path.join(self.dir, str(n))) if os.path.islink(full) else shutil.copy2(full, os.path.join(self.dir, str(n)))
        os.makedirs(self.dir, exist_ok=True)
        self.j = {"branch": self.branch, "tops": self.tops, "orig": self.g("branch", "--show-current"), "head": self.g("rev-parse", "HEAD"),
                  "tip": self.g("rev-parse", "--verify", "--quiet", "refs/heads/" + self.branch), "tree": self.g("write-tree"),
                  "files": {r: self.state(r) for r in self.files()}}
        json.dump(self.j, open(os.path.join(self.dir, "journal.json"), "w"))

    def changed(self):
        """Files whose bytes or link differ from the copy."""
        have = self.j["files"]
        return sorted(r for r in set(have) | set(self.files()) if self.state(r) != have.get(r))

    def rollback(self):
        """Undo the adoption: the paths not restored, or None when the branch moved (it was committed; kept)."""
        j, bad = self.j, []
        try:  # a tool still writing would outlive the restore; no pkill (Windows) must not stop it
            subprocess.run(["pkill", "-KILL", "-P", str(os.getpid())], capture_output=True)
            while True:
                os.waitpid(-1, 0)
        except OSError:
            pass
        tip = self.g("rev-parse", "--verify", "--quiet", "refs/heads/" + j["branch"])
        if tip and tip not in (j["tip"], j["head"]):
            shutil.rmtree(self.dir, ignore_errors=True)
            return None
        bad += ["index"] * bool(subprocess.run(["git", "-C", self.repo, "read-tree", j["tree"]], capture_output=True).returncode)
        for n, top in enumerate(j["tops"]):
            full, kept = os.path.join(self.repo, top), os.path.join(self.dir, str(n))
            try:
                if os.path.islink(full) or os.path.isfile(full):
                    os.remove(full)
                elif os.path.isdir(full):
                    shutil.rmtree(full)
                if os.path.islink(kept):
                    os.symlink(os.readlink(kept), full)
                elif os.path.isdir(kept):
                    shutil.copytree(kept, full, symlinks=True)
                elif os.path.exists(kept):
                    shutil.copy2(kept, full)
            except OSError:
                bad.append(top)
        if j["orig"] and self.g("branch", "--show-current") != j["orig"] and subprocess.run(["git", "-C", self.repo, "checkout", "-q", j["orig"]], capture_output=True).returncode:
            bad.append("branch " + j["orig"])
        if j["branch"] != j["orig"]:
            bad += ["branch " + j["branch"]] * bool(subprocess.run(["git", "-C", self.repo, *(["branch", "-f", j["branch"], j["tip"]] if j["tip"] else ["branch", "-D", j["branch"]])], capture_output=True).returncode)
        if not bad:
            shutil.rmtree(self.dir, ignore_errors=True)
        return bad

    def failed(self, bad):
        return ("REFUSED: could not restore %s; the adoption is half undone. Fix: git status, then git checkout -- <paths>, git switch %s, git branch -D %s. "
                "Side effects: partial. Do not rerun setup until restored (SETUP_HALF_UNDONE)" % (", ".join(bad), self.j["orig"], self.branch))

    @classmethod
    def recover(cls, repo):
        """Roll back an interrupted run from its journal; the line to print, or None."""
        try:
            j = json.load(open(os.path.join(git(repo, "rev-parse", "--absolute-git-dir"), "workflow-setup-txn", "journal.json")))
        except (OSError, ValueError):
            return None
        txn = cls(repo, j["branch"], tuple(j["tops"][4:]), j)
        if git(repo, "rev-parse", "HEAD", check=False) != j["head"]:  # HEAD moved (committed, merged or switched): restoring would undo newer work
            shutil.rmtree(txn.dir, ignore_errors=True)
            bad = None
        else:
            bad = txn.rollback()
        return txn.failed(bad) if bad else "NOTE: an interrupted adoption had already committed; it is kept (SETUP_RECOVERED)" if bad is None else "NOTE: recovered an interrupted adoption (SETUP_RECOVERED); it was rolled back"


def version_key(text):
    return tuple(int(x) for x in re.findall(r"\d+", str(text or ""))[:3])


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and done.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), (done.stderr or done.stdout).strip()[-400:]))
    return done.stdout.strip() if done.returncode == 0 else ""


def base_of(repo):
    try:
        with open(os.path.join(repo, ".loop", "config.json")) as handle:
            return json.load(handle).get("base") or "main"
    except (OSError, ValueError, AttributeError):
        return git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False).split("/")[-1] or "main"


def base_config(repo):
    """The base branch's .loop/config.json ({} when the base has none)."""
    base = base_of(repo)
    text = git(repo, "show", "%s:.loop/config.json" % base, check=False)
    try:
        found = json.loads(text) if text else {}
    except ValueError:
        found = {}
    return dict(found, base=found.get("base") or base) if found else {}


def branch(version):
    return "workflow-update-v%s" % version


def state(repo, base, name):
    """none, unmerged or merged: the update branch against the base branch."""
    if not git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/" + name, check=False):
        return "none"
    return "merged" if subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", name, base]).returncode == 0 else "unmerged"


def report(repo, cfg, target):
    """Print the REPO line; True when the repo is behind or waits on a merge."""
    if not cfg:
        print("REPO: %s has no .loop/config.json on its base branch (merge the setup branch first)" % os.path.basename(repo))
        return False
    held = cfg.get("template_version") or ""
    if version_key(held) >= version_key(target) and held:
        print("REPO: template_version %s" % held)
        return False
    if state(repo, cfg["base"], branch(target)) == "unmerged":
        print("PENDING: %s is not merged into %s; merge it" % (branch(target), cfg["base"]))
        return True
    print("REPO: template_version %s, older than %s: run update --apply" % (held or "unknown", target))
    return True


def stamp_version(path, version):
    with open(path) as handle:
        held = json.load(handle)
    held["template_version"] = version
    with open(path, "w") as handle:
        json.dump(held, handle, indent=2)
        handle.write("\n")


def write_tree(tree, version):
    """Write the repo half inside the worktree; return the paths to commit."""
    config = os.path.join(tree, ".loop", "config.json")
    settings.fill_repo(config)
    stamp_version(config, version)
    paths = [".loop/config.json"] + agents.apply(tree)
    return paths


def apply_repo(repo, cfg, target, wrote_skills):
    """The repo half; returns the exit code."""
    if not cfg:
        print("SKIPPED repo: %s has no .loop/config.json on its base branch (merge the setup branch first) (UPDATE_SKIPPED_REPO)"
              % os.path.basename(repo))
        return 0
    base, name = cfg["base"], branch(target)
    held = cfg.get("template_version") or ""
    where = state(repo, base, name)
    if held and version_key(held) >= version_key(target):
        print("UP TO DATE: %s is at template %s" % (os.path.basename(repo), held))
        return 0
    if agents.entry(repo, "check")[0] is None:
        print("SKIPPED entry point: workflow-docs not installed beside workflow-setup (UPDATE_NO_ENTRY)")
        return 1
    if where == "merged":
        print("REFUSED: %s is already merged into %s but %s's config says template_version %s (UPDATE_BRANCH_MERGED). Fix: git "
              "branch -d %s, then run update --apply again" % (name, base, base, held or "unknown", name), file=sys.stderr)
        return 2
    common = os.path.join(repo, git(repo, "rev-parse", "--git-common-dir"))
    tree = os.path.join(os.path.abspath(common), "loop", "update-worktree")
    upstream = git(repo, "rev-list", "--count", "%s..%s@{upstream}" % (base, base), check=False)
    if upstream not in ("", "0"):
        print("WARN: local %s is %s commit(s) behind its upstream; git fetch origin %s first to cut from the latest" % (base, upstream, base))
    try:
        git(repo, "worktree", "remove", "--force", tree, check=False)
        git(repo, "worktree", "prune")
        if where == "none":
            git(repo, "worktree", "add", "-q", "-b", name, tree, base)
        else:
            git(repo, "worktree", "add", "-q", tree, name)
        paths = write_tree(tree, target)
        git(tree, "add", "-A", "--", *paths)
        if not git(tree, "diff", "--cached", "--name-only"):
            print("PENDING: %s is not merged into %s; merge it" % (name, base))
            return 1
        git(tree, "commit", "-q", "-m", "Update the workflow loop to v%s" % target)
        print("WROTE the repo half on branch %s at %s: %s" % (name, git(tree, "rev-parse", "--short", "HEAD"), ", ".join(paths)))
        print("NEXT: merge %s into %s (git switch %s && git merge %s, or open a pull request from it)" % (name, base, base, name))
        return 0
    except (RuntimeError, OSError, SystemExit) as error:
        why = str(error).strip().splitlines()[-20:]
        if where == "none":  # a branch cut this run with no commit would read as merged and refuse the rerun
            git(repo, "worktree", "remove", "--force", tree, check=False)
            if git(repo, "rev-list", "--count", "%s..%s" % (base, name), check=False) == "0":
                git(repo, "branch", "-D", name, check=False)
        if wrote_skills:
            print("PARTIAL: skills updated to v%s; repo half not written: %s (UPDATE_PARTIAL). Fix: fix the cause, then run "
                  "update --apply again (safe to rerun)" % (target, " ".join(why)), file=sys.stderr)
        else:
            print("REFUSED: repo half not written: %s (UPDATE_PARTIAL). Fix: fix the cause, then run update --apply again"
                  % " ".join(why), file=sys.stderr)
        return 2
    finally:
        git(repo, "worktree", "remove", "--force", tree, check=False)
        git(repo, "worktree", "prune", check=False)


# --- Propose: skill files edited in an adopted repo (LOCAL FIX lines) go back to the template as one GitHub issue.
# import difflib
# import getpass
# import hashlib
# import json
# import os
# import re
# import subprocess
# import sys
# 
# 
# # No terminal, no waiting: a prompt from git or gh must fail, not block.
# os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
# 
# def base_copy(skills, old, rel):

def base_copy(skills, old, rel):
    """The package copy a local fix was made on: the kept copy, else what the stamp's hash says was installed (unknown)."""
    kept = os.path.join(skills, ".workflow-kept", rel)
    if os.path.isfile(kept) and (old.get("kept") or {}).get(rel):
        return open(kept, encoding="utf-8", errors="replace").read(), (old["kept"][rel].get("base_version") or old.get("version"))
    return None, old.get("version") or "unknown"


def names(repo):
    """(kind, value) pairs the text must not carry."""
    out = [("repo folder name", os.path.basename(os.path.abspath(repo))), ("user name", getpass.getuser())]
    url = subprocess.run(["git", "-C", repo, "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    found = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?$", url)
    if found:
        out += [("origin owner", found.group(1)), ("origin name", found.group(2))]
    return out


def leak_patterns():
    try:
        with open(os.path.expanduser(os.environ.get("LOOP_FLOW") or "~/.workflow-loop/flow.json")) as handle:
            return [p for p in json.load(handle).get("leak_prefixes") or [] if isinstance(p, str)]
    except (OSError, ValueError, AttributeError):
        return []


def scrub(text, repo):
    """(kinds matched, skipped notes)."""
    hits, notes = [], []
    for kind, value in names(repo):
        if len(value) < 3:
            notes.append("SCRUB: skipped %s (shorter than 3 characters)" % kind)
        elif re.search(r"(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])" % re.escape(value), text, re.I):
            hits.append(kind)
    if os.path.expanduser("~") in text:
        hits.append("home folder path")
    for pattern in leak_patterns():
        try:
            if re.search(pattern, text, re.I):
                hits.append("a leak_prefixes pattern")
        except re.error:
            continue
    return sorted(set(hits)), notes


def draft(skills, old, fixes):
    parts = []
    for rel in fixes:
        mine = open(os.path.join(skills, rel), encoding="utf-8", errors="replace").read()
        base, version = base_copy(skills, old, rel)
        diff = "".join(difflib.unified_diff((base or "").splitlines(True), mine.splitlines(True), "a/" + rel, "b/" + rel))
        parts.append("### %s (made on v%s)\n\n```diff\n%s```\n" % (rel, version, diff if base is not None else
                                                                   "(no package copy kept: the whole file)\n" + mine))
    body = "A fix made in an adopted repo, proposed back to the template.\n\n" + "\n".join(parts)
    digest = hashlib.sha256(body.encode()).hexdigest()[:8]
    return "Fix from an adopted repo: %s (%s)" % (", ".join(fixes), digest), body


def save(repo, title, body):
    common = subprocess.run(["git", "-C", repo, "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
    path = os.path.join(repo, common, "loop", "propose-%s.md" % hashlib.sha256(title.encode()).hexdigest()[:8])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write("%s\n\n%s" % (title, body))
    return os.path.abspath(path)


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)


def run(skills, old, fixes, template, repo, file_issue):
    if not fixes:
        print("NOTHING TO PROPOSE: no skill file differs from the installed package (PROPOSE_NONE)")
        return 0
    title, body = draft(skills, old, fixes)
    hits, notes = scrub(title + "\n" + body, repo or ".")
    for note in notes:
        print(note)
    if hits:
        path = save(repo or ".", title, body)
        print("REFUSED: the proposal holds %s (PROPOSE_SCRUB). Fix: edit %s, then gh issue create --repo %s --title "
              "\"<title>\" --body-file <that file>" % (", ".join(hits), path, template or "OWNER/NAME"), file=sys.stderr)
        return 2
    print("TITLE: " + title)
    print(body)
    if not file_issue:
        print("PREVIEW: nothing filed. Run update --propose --file-issue to file it on %s" % (template or "the template"))
        return 0
    if not template:
        print("REFUSED: no template repo is known (UPDATE_NO_TEMPLATE). Fix: set template_repo, or pass --template", file=sys.stderr)
        return 2
    for _ in range(2):
        try:
            listed = gh("issue", "list", "--repo", template, "--state", "open", "--limit", "200", "--json", "title,url")
            same = [i for i in json.loads(listed.stdout or "[]") if i.get("title") == title] if listed.returncode == 0 else []
            if same:
                print("ALREADY FILED: %s" % same[0].get("url", ""))
                return 1
            path = save(repo or ".", title, body)
            done = gh("issue", "create", "--repo", template, "--title", title, "--body-file", path)
            if done.returncode == 0:
                print("FILED: " + done.stdout.strip())
                return 0
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue
    path = save(repo or ".", title, body)
    print("REFUSED: gh couldn't file the issue (PROPOSE_GH). Fix: edit %s, then gh issue create --repo %s --title \"%s\" "
          "--body-file %s" % (path, template, title, path), file=sys.stderr)
    return 2


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default="")
    parser.add_argument("--version", default="")
    parser.add_argument("--wrote-skills", action="store_true", help="update.py already wrote the skills (a failure is PARTIAL)")
    args = parser.parse_args()
    repo = args.repo or git(".", "rev-parse", "--show-toplevel", check=False)
    version = args.version or agents.installed_version()
    if not repo or not version:
        sys.exit("REFUSED: need a repo and an installed version (UPDATE_SKIPPED_REPO). Fix: pass --repo and --version")
    return apply_repo(repo, base_config(repo), version, args.wrote_skills)


if __name__ == "__main__":
    sys.exit(main())
