#!/usr/bin/env python3
"""Adopt a new or existing git repo without blocking: survey it, print what it would add or convert, then write it on a branch.

usage: setup.py [--repo DIR] [--branch NAME] [--dry-run] [--bare] [--from REPO [--allow KEY[,KEY]]] [--no-health] [--no-issues] [--strict]
       setup.py [--repo DIR] --reply-hook | --govern-hook [--remove]
       setup.py [--repo DIR] --git-hooks [--remove | --check [--json]]
       setup.py migration-check [--repo DIR] [--pr] [--offline]   every gap to the current template, each with its fix; writes nothing

Prints the health check's start state, the plan (add, convert, skip, no fit, GAP, GUARD, borrow, held) and, after a real run,
ADOPTION VERDICT. Writes .loop/ (config with every repo setting and its default, queue, findings, docs map, rows), a page for
each top-level code folder and Home, the README How to use sections and the regression workflow, and commits them on a branch
(default workflow-setup). An existing file is adapted, never overwritten. A refusal rolls everything back; a second run changes
nothing. Exit 0 whenever the adoption is on its branch, 3 with --strict and gaps, 1 or 2 refused, 4 half undone, 130
interrupted. --bare writes only the config, queue and findings.

--reply-hook and --govern-hook install the operation session's hooks (workflow-monitoring) in the repo's machine-local
.claude/settings.local.json, keeping every other key; --remove takes them out. --git-hooks writes the private-name scan as git
hooks (pre-commit, commit-msg, pre-push), as a default run does after its commit unless --no-git-hooks or LOOP_NO_GIT_HOOKS=1;
a hook that is not ours is never touched; --check [--json] prints their state.
"""
import argparse
import errno
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402
import seed  # noqa: E402
import settings  # noqa: E402
import survey  # noqa: E402
import sync  # noqa: E402
import update  # noqa: E402

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

QUEUE = """# Goal queue

One goal a line. Other lines are ignored. Example:

    - slug: fix-title | level: 0 | touches: README.md | goal: Fix the title | done: The title reads right
"""
FINDINGS = "# Findings\n\nOpen findings, one line each.\n"


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip() if done.returncode == 0 else ""


def base_branch(repo):
    head = git(repo, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", check=False)
    if head:
        return head.rsplit("/", 1)[-1]
    for name in ("main", "master", "trunk"):
        if git(repo, "rev-parse", "--verify", "--quiet", name, check=False):
            return name
    return git(repo, "branch", "--show-current") or "main"


def survey_agent():
    """The agent commands this machine has. Permissions stay as the user set them."""
    if shutil.which("claude"):
        return ["claude", "-p"]
    if shutil.which("codex"):
        return ["codex", "exec"]
    return []


ALLOWS = {"claude": ("--allowedtools", "--allowed-tools", "--permission-mode"),
          "codex": ("-s", "--sandbox", "--full-auto")}
ADD = {"claude": ["--allowedTools", "Bash,Read,Write,Edit"], "codex": ["--full-auto"]}


def bare_agent(command):
    """The line to add when the agent command grants no tools, else None."""
    name = os.path.basename(command[0]) if command else ""
    if name in ALLOWS and not any(a.lower().split("=")[0] in ALLOWS[name] or a.lower().startswith("--dangerous") for a in command[1:]):
        return '"agent_command": %s' % json.dumps(command + ADD[name])
    return None


def merged(repo, old, borrowed=None):
    """The config: values already there win, then values borrowed with --from, the survey fills the rest."""
    agent = survey_agent()
    config = settings.repo_defaults()
    files = git(repo, "ls-files").splitlines()
    config.update(base=base_branch(repo), checks=survey.checks(repo, files)[0], agent_command=agent)
    version = survey.version_habit(repo, files)[0]
    if version and "version_file" not in old:
        config["version_file"] = version
    settings.check_depth(old, ".loop/config.json")
    config.update(borrowed or {})
    config.update(old)
    config["_help"] = settings.repo_help(old)
    return config


try:  # moved to agents.py; kept importable here (an older agents.py: adopt() refuses, SETUP_MIXED_VERSION)
    refuse, HOOKS, reply_hook = agents.refuse, agents.HOOKS, agents.reply_hook
except AttributeError:
    pass


def measure(repo):
    """(the check's lines, why not): workflow-health's check beside this skill, without the owner's private rules."""
    py = agents.sibling("workflow-health", "health.py")
    if os.environ.get("LOOP_NO_HEALTH") == "1" or not py:
        return None, "skipped by --no-health" if py else "workflow-health is not beside workflow-setup"
    try:
        done = subprocess.run([sys.executable, py, "check", "--skip", "mine"], cwd=repo, capture_output=True, text=True,
                              timeout=int(os.environ.get("LOOP_HEALTH_LIMIT") or 120))
    except subprocess.TimeoutExpired:
        return None, "the check ran past its time limit"
    lines = done.stdout.splitlines()
    return (lines, "") if any(l.startswith("HEALTH:") for l in lines) else (None, "the check did not finish (exit %d)" % done.returncode)


def verdict(lines, why, failed):
    """Print each FAIL, WARN and UNREAD line, then ADOPTION VERDICT last; True when it is not green."""
    if lines is None:
        print("ADOPTION VERDICT: not measured (%s)" % why)
        return True
    gaps = list(dict.fromkeys(l for l in lines if l.split(" ", 1)[0] in ("FAIL", "WARN", "UNREAD")))
    print("\n".join(update.mask(l) for l in gaps))
    head = next(l for l in lines if l.startswith("HEALTH:"))
    n = [int(x) for x in re.findall(r"(\d+) (?:warn|fail|unread)", head)]
    bad = not head.startswith("HEALTH: green") or bool(failed)
    print("ADOPTION VERDICT: " + ("GAPS (%d warn, %d fail, %d unread, %d steps failed)" % (*n, len(failed)) if bad else
                                  "GREEN" + (" (%d warn, listed above)" % n[0] if n and n[0] else "")))
    return bad


def undo(tx, why, code=1):
    """Roll the adoption back, then say why (or that it is half undone, exit 4). Nothing stays written."""
    bad = tx.rollback()
    print(tx.failed(bad) if bad else "NOTE: the adoption was already committed on the branch and is kept (SETUP_COMMITTED)" if bad is None else why)
    return 4 if bad else code


def adopt(args, repo):
    missing = [n for n, m in (("Txn", sync), ("precheck", survey), ("borrow", survey), ("guard_staged", update), ("private_value", settings),
                              ("docs_format", agents)) if not hasattr(m, n)]
    if missing:
        print("REFUSED: the setup scripts are mixed versions, %s is missing (SETUP_MIXED_VERSION). Fix: run update; nothing written." % missing[0])
        return 1
    note = None if args.dry_run else sync.Txn.recover(repo)
    if note:
        print(note)
    if note and "HALF_UNDONE" in note:
        return 4
    bad = survey.precheck(repo, args.branch)
    if bad:
        print(bad)
        return 1
    old = json.loads(survey.read(repo, ".loop/config.json") or "{}")
    values, lines = ({}, []) if not args.from_ else survey.borrow(args.from_, settings.repo_defaults(), settings.private_value, [k for a in args.allow for k in a.split(",")])
    if values is None:
        print(lines[0])
        return 1
    config = merged(repo, old, values)
    if not args.bare and not config.get("template_version") and agents.installed_version():
        config["template_version"] = agents.installed_version()  # set up with this version; update moves it
    if args.bare and "criteria" not in old:
        config["criteria"] = False
    found = survey.survey(repo, config)
    wiki = found["wiki"]
    if os.path.isabs(wiki) or ".." in wiki.split("/") or wiki.strip("./") == "" or wiki.split("/")[0] == ".git":
        print("REFUSED: wiki_dir %s is not a folder inside the repo (SETUP_WIKI_DIR). Fix: set wiki_dir in .loop/config.json to a relative folder such as docs/wiki; nothing written." % wiki)
        return 1
    print(survey.found_line(found, config))
    files = git(repo, "ls-files").splitlines()
    for note in survey.checks(repo, files)[1] + survey.version_habit(repo, files)[1]:
        print("NOTE: " + note)
    for cmd in old.get("checks", []):
        if survey.runs_tests(repo, files, cmd):
            print("NOTE: %s finds no test files" % cmd)
    start, why = (None, "skipped for --bare") if args.bare else measure(repo)
    start_line = "HEALTH START: " + (next(l for l in start if l.startswith("HEALTH:"))[8:] if start else "not measured (%s)" % why)
    print(start_line)
    acts = seed.decide(repo, config, found)
    if args.bare:
        acts = [a for a in acts if a[3] in ("config", "file")]
    else:
        acts += agents.plan(repo)  # START.md and the agent files' block
    for verb, path, note, _ in acts:
        print(("%s: %s" % (verb, note)) if verb in ("GAP", "GUARD") else "%s: %s%s" % (verb, path, " (%s)" % note if note else ""))
    print("\n".join(lines), end="\n" if lines else "")
    if not (args.bare or args.no_git_hooks or os.environ.get("LOOP_NO_GIT_HOOKS") == "1"):
        print("hooks: pre-commit, commit-msg and pre-push (the private-name scan, written to the git hooks folder after the commit)")
    bare = None if args.bare else bare_agent(config["agent_command"])
    if bare:
        print("GAP: agent_command %s grants no tools, so a background agent stops at its first permission prompt. Fix: add to .loop/config.json: %s"
              % (config["agent_command"], bare))
    kinds = agents.kinds_of(acts)
    held = settings.load(settings.private_path())
    if args.dry_run:
        print("would add to %s: %s" % (settings.private_path(), ", ".join(k for k in settings.FLOW_KEYS if k not in held) or "nothing"))
        to = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", survey.git(repo, "remote", "get-url", "origin"))
        for k, v in list(kinds.items()) + [("agent-tools", ["agent_command"])] * bool(bare):
            print("WOULD FILE: adoption %s: %s [health, health:adoption] on %s" % (k, ", ".join(v), to.group(1) if to else "(no GitHub remote: stays in .loop/findings.md)"))
        print("DRY RUN: nothing written\nADOPTION VERDICT: not run (dry run)")
        return 0
    planned = [a[1] for a in acts if a[3] and a[0] in ("add", "convert")]
    dirty = [l.split(None, 1)[-1] for l in git(repo, "status", "--porcelain", "--untracked-files=no").splitlines()]
    mine = [p for p in planned if p in dirty]
    if any(a[3] == "agents" for a in acts) and agents.dirty(repo):
        print("REFUSED: %s has uncommitted changes (SETUP_AGENT_FILE_DIRTY). Fix: commit or stash them, then run setup "
              "again; nothing written." % ", ".join(agents.dirty(repo)))
        return 2
    if mine:
        print("REFUSED: %s has uncommitted changes (SETUP_PLANNED_PATH_DIRTY). Fix: commit or stash them, then run setup again; nothing written." % ", ".join(mine))
        return 2
    failed = []
    if not [a for a in acts if a[3]]:
        print("NO CHANGE: nothing to add or convert")
        post = None
    else:
        if not config["checks"]:
            print("NOTE: no test command found, so no regression row is seeded")
        print("NOTE: no claude or codex on PATH; add \"agent_command\"" if not config["agent_command"] else
              "NOTE: a background agent stops at any permission prompt: add the tools you allow to \"agent_command\"")
        tx = sync.Txn(repo, args.branch, [found["wiki"]] + agents.targets(repo))
        tx.begin()
        signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        try:
            if git(repo, "branch", "--show-current") != args.branch:
                made = git(repo, "rev-parse", "--verify", "--quiet", args.branch, check=False)
                git(repo, "checkout", "-q", "-B" if made else "-b", args.branch, *["HEAD"] * bool(made))
            os.makedirs(os.path.dirname(os.path.join(repo, ".loop", "config.json")), exist_ok=True)
            with open(os.path.join(repo, ".loop", "config.json"), "w") as handle:
                handle.write(json.dumps(agents.stored(config, old), indent=2) + "\n")
            seed.apply(repo, config, found, [a for a in acts if a[3] != "agents"])
            if not args.bare:
                agents.apply(repo)
            changed = tx.changed()
            if [p for p in changed if p in dirty]:
                return undo(tx, "REFUSED: a file the adoption changes had uncommitted changes (SETUP_PLANNED_PATH_DIRTY). Fix: commit or stash them; nothing written.", 2)
            held_back = set(subprocess.run(["git", "-C", repo, "check-ignore", "--stdin"], input="\n".join(changed), capture_output=True, text=True).stdout.split("\n"))
            git(repo, "add", "-f", "--", *[p for p in changed if p in held_back and p in seed.FORCED] or ["--"]) if held_back & set(seed.FORCED) else None
            git(repo, "add", "-A", "--", *[p for p in changed if p not in held_back] or ["--"])
            changed = [p for p in changed if p not in held_back or p in seed.FORCED]
            scan = agents.sibling("workflow-delivery", "private.py")  # SET-8: no private name in setup's commit
            if scan and subprocess.run([sys.executable, scan, "hook", "staged"], cwd=repo).returncode:
                return undo(tx, "REFUSED: a staged adoption file holds a private name (places above). Fix: remove it from that file, then run "
                                "setup again; nothing written (SETUP_PRIVATE_NAME).")
            hits = update.guard_staged(repo, changed)
            if hits:
                return undo(tx, "REFUSED: the adoption would commit a local setting or private value at %s (SETUP_PRIVATE_VALUE). Fix: set it in the "
                                "private flow file or remove it; nothing written." % ", ".join(hits))
            code, out = update.commit(repo, "Adopt the workflow loop\n" + start_line, changed)
            if code:
                print("\n".join(update.mask(l) for l in out.strip().splitlines()[-20:]))
                return undo(tx, "REFUSED: the repo's own commit hook refused the adoption commit (SETUP_HOOK_REFUSED). Fix: if it refuses tracked "
                                "data files, exempt .loop/*.tsv (docs, regression rows and runs) there, then run setup again; nothing written.")
            shutil.rmtree(tx.dir, ignore_errors=True)  # committed: the journal ends with the commit
        except KeyboardInterrupt:
            undo(tx, "REFUSED: interrupted; rolled back, nothing written (SETUP_INTERRUPTED)")
            return 130
        except SystemExit as error:  # a failed git call exits: also a refusal, rolled back
            return undo(tx, "%s; rolled back, nothing written" % (error.code if isinstance(error.code, str) else "REFUSED: a step stopped (exit %s)" % error.code))
        except Exception as error:
            trace = os.path.join(tx.gd, "workflow-setup-trace.txt")
            open(trace, "w").write("\n".join(update.mask(l) for l in traceback.format_exc().splitlines()) + "\n")
            return undo(tx, "REFUSED: unexpected failure (%s); rolled back, nothing written. Trace: %s. Fix: rerun with --dry-run, then report it "
                            "(SETUP_UNEXPECTED)" % (type(error).__name__, os.path.relpath(trace, repo)))
        shutil.rmtree(tx.dir, ignore_errors=True)
        post = git(repo, "rev-parse", "--short", "HEAD")
    if not (args.bare or args.no_git_hooks or os.environ.get("LOOP_NO_GIT_HOOKS") == "1"):
        update.step("git hooks", "python3 setup.py --git-hooks", lambda: seed.git_hooks(repo, adopting=True), failed)
    update.step("private settings", "python3 settings.py fill-private", fill_private, failed)
    if post and (kinds or bare) and not args.bare:
        update.step("issue filing", "workflow-health file --group adoption --open-only", lambda: survey.file_issues(repo, args.no_issues, len(kinds) + bool(bare)), failed)
    if post:
        print("WROTE the adoption on branch %s at %s" % (args.branch, post))
        print("NEXT: review the branch, then merge it into %s" % config["base"])
    if args.bare:
        return 0
    end, why = measure(repo)
    return 3 if verdict(end, why, failed) and args.strict else 0


def fill_private():
    try:
        print("PRIVATE settings added to %s: %s" % (settings.private_path(), ", ".join(settings.fill_private()) or "none missing"))
    except OSError as error:  # a sandbox (Codex's workspace-write) can leave the home folder read-only
        if error.errno not in (errno.EACCES, errno.EPERM, errno.EROFS):
            raise  # a full disk or a bad path is a real failure, not a read-only home
        print("PRIVATE_NOT_WRITTEN: private settings not written (%s). The repo adoption goes on. Fix: allow writes to %s and run setup.py again; "
              "go is refused until they exist." % (error.strerror or type(error).__name__, os.path.dirname(settings.private_path())))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--branch", default="workflow-setup")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--bare", action="store_true", help="only the config, queue and findings")
    parser.add_argument("--from", dest="from_", default="", help="an adopted repo to borrow settings from (read-only)")
    parser.add_argument("--allow", action="append", default=[], help="with --from: KEY[,KEY] of a held setting to take")
    parser.add_argument("--no-health", action="store_true", help="skip the health check before and after")
    parser.add_argument("--no-issues", action="store_true", help="file no issues for what does not fit")
    parser.add_argument("--strict", action="store_true", help="exit 3 when the verdict has gaps")
    parser.add_argument("--reply-hook", action="store_true", help="install the operation session's reply-format hook")
    parser.add_argument("--govern-hook", action="store_true", help="install the operation session's govern-only hook (MON-7)")
    parser.add_argument("--git-hooks", action="store_true", help="install the private-name scan as git hooks")
    parser.add_argument("--no-git-hooks", action="store_true", help="a default run installs no git hooks")
    parser.add_argument("--check", action="store_true", help="with --git-hooks: print the state, write nothing")
    parser.add_argument("--json", action="store_true", help="with --check: schema-versioned JSON")
    parser.add_argument("--remove", action="store_true", help="with --reply-hook, --govern-hook or --git-hooks: take that hook out")
    args = parser.parse_args()
    repo = git(args.repo, "rev-parse", "--show-toplevel")
    if args.git_hooks:
        code = 0 if args.check else seed.git_hooks(repo, args.remove)
        return seed.show(repo, args.check and args.json) if args.check else (seed.show(repo, False), code)[1]
    if args.govern_hook:
        return reply_hook(repo, args.remove, "govern_hook.py")
    if args.reply_hook:  # with the govern hook beside it (MON-7); --remove: reply only
        return reply_hook(repo, args.remove) or (0 if args.remove else reply_hook(repo, False, "govern_hook.py"))
    if args.no_health:
        os.environ["LOOP_NO_HEALTH"] = "1"
    return adopt(args, repo)


if __name__ == "__main__":
    sys.exit(agents.migration_check(sys.argv[2:]) if sys.argv[1:2] == ["migration-check"] else main())
