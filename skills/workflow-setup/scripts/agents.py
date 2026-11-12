#!/usr/bin/env python3
"""Wire the same workflow skills into each agent's entry file, so Claude Code and Codex run the same loop the same way.

usage: agents.py wire [--repo DIR] [--dry-run]

Writes one marked block (between <!-- workflow-loop --> and <!-- /workflow-loop -->) into each file the repo setting
agent_files names (default CLAUDE.md and AGENTS.md; [] turns wiring off): it creates a missing file, replaces only the
block in a file that holds one, and appends the block to a file that has none. Text outside the block is never touched;
line endings and a byte-order mark are kept as found; a file linked to another is wired once. The block itself comes
from the sibling workflow-docs skill (entry.py block): read .loop/START.md first, the installed skills and how to ask for
their commands. --dry-run prints what it would write and writes nothing. It never commits: setup and update stage it.
"""
import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENTRY = os.path.join(os.path.dirname(os.path.dirname(HERE)), "workflow-docs", "scripts", "entry.py")
OPEN, CLOSE = "<!-- workflow-loop -->", "<!-- /workflow-loop -->"
BOM = "\ufeff"

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def targets(repo):
    """The agent files to wire, from the repo's agent_files setting."""
    try:
        with open(os.path.join(repo, ".loop", "config.json")) as handle:
            value = json.load(handle).get("agent_files", ["CLAUDE.md", "AGENTS.md"])
    except (OSError, ValueError, AttributeError):
        value = ["CLAUDE.md", "AGENTS.md"]
    return [p for p in value if isinstance(p, str)] if isinstance(value, list) else ["CLAUDE.md", "AGENTS.md"]


def block():
    if not os.path.isfile(ENTRY):
        return None
    done = subprocess.run([sys.executable, ENTRY, "block"], capture_output=True, text=True)
    return done.stdout if done.returncode == 0 and done.stdout.startswith(OPEN) else None


def inside(root, full):
    """True for a file in the repo's tree, outside its .git folder."""
    return full.startswith(root + os.sep) and ".git" not in os.path.relpath(full, root).split(os.sep)


def wired(raw, text):
    """raw with its block replaced by text, or text appended; line endings and a BOM kept."""
    bom, body = (BOM, raw[1:]) if raw.startswith(BOM) else ("", raw)
    newline = "\r\n" if "\r\n" in body else "\n"
    new = text.rstrip("\n").replace("\n", newline)
    if OPEN in body:
        start, end = body.index(OPEN), body.index(CLOSE, body.index(OPEN)) + len(CLOSE)
        return bom + body[:start] + new + body[end:]
    if not body:
        return bom + new + newline
    gap = "" if body.endswith(newline * 2) else newline if body.endswith(newline) else newline * 2
    return bom + body + gap + new + newline


def wire(repo, dry=False):
    """Return (changed paths, refusals)."""
    text, changed, refused, seen = block(), [], [], set()
    if text is None:
        return [], ["SKIPPED agent files: workflow-docs not installed beside workflow-setup (UPDATE_NO_ENTRY)"]
    root = os.path.realpath(repo)
    for name in targets(repo):
        full = os.path.realpath(os.path.join(repo, name))
        if not inside(root, full):
            refused.append("REFUSED: %s resolves outside the repo or into .git (AGENTS_OUTSIDE). Fix: point agent_files at "
                           "files inside it" % name)
            continue
        if full in seen:
            continue
        seen.add(full)
        try:
            with open(full, encoding="utf-8", newline="") as handle:
                raw = handle.read()
        except OSError:
            raw = ""
        if (OPEN in raw or CLOSE in raw) and (raw.count(OPEN) != 1 or raw.count(CLOSE) != 1 or raw.index(CLOSE) < raw.index(OPEN)):
            refused.append("REFUSED: %s has a stray workflow-loop marker (AGENTS_MARKER). Fix: remove the "
                           "stray marker, then run agents.py wire again" % name)
            continue
        new = wired(raw, text)
        if new != raw:
            changed.append(name)
            if not dry:
                with open(full, "w", encoding="utf-8", newline="") as handle:
                    handle.write(new)
    return changed, refused


def entry(repo, *argv):
    """Run the sibling entry.py; (returncode, stdout). Missing workflow-docs is (None, "")."""
    if not os.path.isfile(ENTRY):
        return None, ""
    done = subprocess.run([sys.executable, ENTRY] + list(argv) + ["--repo", repo], capture_output=True, text=True)
    return done.returncode, done.stdout


def installed_version():
    """The installed package's version from workflow-package.json beside the skills; empty for a checkout."""
    try:
        with open(os.path.join(os.path.dirname(os.path.dirname(HERE)), "workflow-package.json")) as handle:
            return str(json.load(handle).get("version") or "")
    except (OSError, ValueError, AttributeError):
        return ""


def plan(repo):
    """Setup's acts for the entry point and the agent files: (verb, path, note, "agents") for each that would change."""
    code, out = entry(repo, "check")
    if code is None:
        print("SKIPPED entry point: workflow-docs not installed beside workflow-setup (UPDATE_NO_ENTRY)")
        return []
    acts = []
    if not os.path.exists(os.path.join(repo, ".loop", "START.md")):
        acts.append(("add", ".loop/START.md", "the entry point every new session reads first", "agents"))
    elif "STALE .loop/START.md" in out or "LAG .loop/START.md" in out:
        acts.append(("convert", ".loop/START.md", "regenerated", "agents"))
    for name in wire(repo, dry=True)[0]:
        acts.append(("add" if not os.path.exists(os.path.join(repo, name)) else "convert", name, "the workflow-loop block", "agents"))
    return acts


def dirty(repo):
    """The agent files with uncommitted changes: setup won't sweep a person's edits into its commit."""
    done = subprocess.run(["git", "-C", repo, "status", "--porcelain", "--"] + targets(repo), capture_output=True, text=True)
    return [line[3:] for line in done.stdout.splitlines() if line.strip()]


def apply(repo):
    """Write the entry point and wire the agent files; say each refusal; return the paths to stage (inside the repo)."""
    code = entry(repo, "write")[0]
    if code not in (0, None):
        print("WARN: entry.py write failed (exit %s); .loop/START.md may be stale. Fix: run docs.py audit" % code, file=sys.stderr)
    for line in wire(repo)[1]:
        print(line, file=sys.stderr if line.startswith("REFUSED") else sys.stdout)
    root = os.path.realpath(repo)
    return [p for p in [os.path.join(".loop", "START.md")] + targets(repo)
            if os.path.exists(os.path.join(repo, p)) and inside(root, os.path.realpath(os.path.join(repo, p)))]


def git(repo, *args, check=True):
    done = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip() if done.returncode == 0 else ""


def sibling(skill, script):
    path = os.path.join(HERE, "..", "..", skill, "scripts", script)
    return path if os.path.exists(path) else None


BUILT = (("health", "Checks the repo, files findings.", "health_cron"), ("regression", "Runs the regression rows.", "regression_cron"),
         ("digest email", "Mails the round's digest.", ""))


def fill_automation(held, repo):
    """held's automation list plus the three built-in routines on the repo's one Mac task; an entry already set stays."""
    out, path = held.get("automation"), sibling("workflow-health", "workflows.py")
    if not isinstance(out, list) or not path:
        return out
    sys.path.insert(0, os.path.dirname(path))
    try:
        import workflows
    finally:
        sys.path.pop(0)
    for name, does, key in BUILT:
        if not any(isinstance(e, dict) and e.get("name") == name for e in out):
            out = out + [dict(name=name, does=does, cadence=str(held[key]) if key else "with each health round",
                              runs="mac:" + workflows.task_name(repo), **({"enabled": False} if not key and held.get("digest_mail") == "off" else {}))]
    return out


def refuse(what, fix):
    sys.stderr.write("REFUSED: %s. Fix: %s\n" % (what, fix))
    return 1


HOOKS = {"reply_hook.py": ("Stop", None, "it checks only the operation session's reply layout"),
         "govern_hook.py": ("PreToolUse", "Edit|Write|MultiEdit|NotebookEdit|Bash",
                            'it blocks edits and git commit/push/merge in the operation session; off: "govern_hook": false')}


def reply_hook(repo, remove, name="reply_hook.py"):
    """Add (or with remove, take out) one operation-session hook (HOOKS) in the repo's machine-local Claude settings."""
    event, matcher, what = HOOKS[name]
    script = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-monitoring",
                                           "scripts", name))
    common = os.path.realpath(os.path.join(repo, git(repo, "rev-parse", "--git-common-dir")))
    path = os.path.join(repo, ".claude", "settings.local.json")
    if not remove:
        if not os.path.exists(script):
            return refuse("%s is missing" % script, "install the workflow-monitoring skill beside workflow-setup")
        if "'" in script:
            return refuse("the hook's path %s holds a single quote" % script, "move the skills to a folder without one")
        if (script + os.sep).startswith(os.path.join(common, "loop", "worktrees") + os.sep) or \
                os.path.realpath(repo).startswith(os.path.join(common, "loop", "worktrees") + os.sep):
            return refuse("the hook (%s) or the repo is inside a goal's worktree, which goes away when the goal ends" % script,
                          "run setup.py from the main checkout or an installed copy of the skills")
    if not remove and git(repo, "ls-files", ".claude/settings.local.json", check=False):
        return refuse(".claude/settings.local.json is committed, so the hook's local path would be committed too",
                      "git rm --cached .claude/settings.local.json, commit that, then run again")
    try:
        with open(path) as handle:
            data = json.load(handle)
    except FileNotFoundError:
        data = {}
    except (OSError, ValueError) as error:
        return refuse("%s is not valid JSON (%s); nothing was written" % (path, error), "correct or move the file, then run again")
    stops = data.get("hooks", {}).get(event, []) if isinstance(data, dict) and isinstance(data.get("hooks", {}), dict) else None
    if not isinstance(stops, list) or not all(isinstance(g, dict) and isinstance(g.get("hooks", []), list) for g in stops):
        return refuse("%s has hooks in a shape this can't edit safely; nothing was written" % path,
                      'make "hooks" an object whose "%s" is a list of {"hooks": [...]} groups' % event)
    command = "if [ -f '%s' ]; then python3 '%s'; fi" % (script, script)
    mine = lambda h: isinstance(h, dict) and "/%s'" % name in str(h.get("command", ""))
    had = [h for g in stops for h in g.get("hooks", []) if mine(h)]
    if remove and not had:
        print("HOOK: not installed%s" % ("" if name == "reply_hook.py" else " (%s)" % name))
        return 0
    if not remove and [h.get("command") for h in had] == [command]:
        print("HOOK: already installed%s" % ("" if name == "reply_hook.py" else " (%s)" % name))
        return 0
    kept = []  # every other group and hook as it was; a group left empty only by taking ours out goes
    for group in stops:
        rest = [h for h in group.get("hooks", []) if not mine(h)]
        if rest or not any(mine(h) for h in group.get("hooks", [])):
            kept.append(dict(group, hooks=rest) if "hooks" in group else group)
    if not remove:
        kept.append(dict({"matcher": matcher} if matcher else {}, hooks=[{"type": "command", "command": command}]))
    if not subprocess.run(["git", "-C", repo, "check-ignore", "-q", ".claude/settings.local.json"]).returncode == 0:
        exclude = os.path.join(repo, git(repo, "rev-parse", "--git-path", "info/exclude"))
        os.makedirs(os.path.dirname(exclude), exist_ok=True)
        held = open(exclude).read() if os.path.exists(exclude) else ""
        if "/.claude/settings.local.json" not in held.splitlines():
            with open(exclude, "a") as handle:
                handle.write(("" if not held or held.endswith("\n") else "\n") + "/.claude/settings.local.json\n")
    data = data if isinstance(data, dict) else {}
    data.setdefault("hooks", {})[event] = kept
    if not kept:
        del data["hooks"][event]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w") as handle:
        handle.write(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)
    print("HOOK: %s%s" % ("removed" if remove else "updated" if had else "added", "" if name == "reply_hook.py" else " (%s)" % name))
    if not remove:
        print("NOTE: start a new Claude Code session (or open /hooks) to load it; %s" % what)
    return 0


FINDINGS_HEAD = "# Findings\n\nOpen findings, one line each.\n"
PLACEHOLDER = "Write this page from what is really in the repo."
FIXES = {"own-sections": "add the marker and the contract sections by hand (docs.py audit lists them)",
         "no-check": 'set "checks": ["<test command>"] in .loop/config.json, then run setup again',
         "tsv-guard": "exempt .loop/*.tsv (docs, regression rows and runs) in that file if it refuses tracked data files",
         "ignored": "add the exception line to the ignore file that keeps it out"}


def stored(config, old):
    """The config as written: every key but checks, which stays only where the config already held it (PR 83)."""
    return {k: v for k, v in config.items() if k != "checks" or "checks" in (old or {})}


def kinds_of(acts):
    """{kind: subjects} of what did not fit: one findings line per kind, four kinds in all."""
    got = {}
    for verb, path, note, _ in acts:
        kind = {"GUARD": "tsv-guard", "GAP": "ignored"}.get(verb)
        if verb == "no fit":
            kind = "no-check" if path == ".loop/regression.tsv" else "own-sections" if note.startswith("has its own") else None
        if kind:
            got.setdefault(kind, []).append(path)
    return got


def update_findings(text, kinds):
    """The findings text with this tool's [adoption] lines set to kinds: a line is rewritten when its subjects change and dropped
    when none are left; any other line, or one the owner marked [closed], stays."""
    line = lambda k: "- [adoption] %s: %s. Fix: %s" % (k, ", ".join(sorted(set(kinds[k]))), FIXES[k])
    out, seen = [], set()
    for row in text.split("\n"):
        found = re.match(r"- \[adoption\] ([\w-]+):", row)
        if not found or row.rstrip().endswith("[closed]"):
            out.append(row)
            seen.add(found.group(1) if found else "")
        elif found.group(1) in kinds and found.group(1) not in seen:
            seen.add(found.group(1))
            out.append(line(found.group(1)))
    while out and not out[-1].strip():
        out.pop()
    return "\n".join(out + [line(k) for k in kinds if k not in seen]) + "\n"


def ignore_lines(blocked):
    """Exception lines for what the repo's own ignore file blocks: (path, line, source) from survey.ignored; one *.tsv line a folder."""
    own = [(p, l) for p, l, src in blocked if os.path.basename(src) == ".gitignore" and not os.path.isabs(src) and not src.startswith(".git/")]
    return list(dict.fromkeys("!%s/*.tsv" % os.path.dirname(p) if l.endswith(".tsv") and "/" in p else l for p, l in own))


def ignore_with(text, lines):
    """The ignore file's text with the missing exception lines appended under one comment (line endings kept)."""
    nl, have = "\r\n" if "\r\n" in text else "\n", text.splitlines()
    note = "# workflow-setup: keep the loop files tracked"
    add = [l for l in lines if l not in have]
    return text + ("" if not text or text.endswith("\n") else nl) + nl.join(([] if note in have else [note]) + add) + nl if add else text


def docs_format():
    """workflow-docs' pageformat module (Home's table header and the heading names come from it), or None."""
    path = sibling("workflow-docs", "pageformat.py")
    if not path:
        return None
    spec = importlib.util.spec_from_file_location("pageformat", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def home_page(repo, names, pf):
    """Home in the docs format (DOC-4): marker, title, Features and one table, a row for each feature page."""
    found = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", git(repo, "remote", "get-url", "origin", check=False))
    link = "[README](https://github.com/%s#%%s)" % (found.group(1) if found else "OWNER/REPO")
    rows = [["[%s](%s)" % (n, n), PLACEHOLDER, link % pf.slug(pf.heading_of(n)), "-"] for n in names]
    return "%s\n# %s\n\n## Features\n\n%s\n" % (pf.MARKER, os.path.basename(repo), "\n".join(pf.table(pf.HOME, rows)))


def readme_with(text, names, pf):
    """The README with a '### How to use <Feature>' section (DOC-5) added for each page that lacks one; its words kept."""
    block = "\n\n".join("### %s\n\nAsk for %s in plain words.\n\n%s" % (pf.heading_of(n), n, "\n".join(pf.table(pf.FRONT, [['"Show me %s"' % n.lower(), PLACEHOLDER]])))
                         for n in names if pf.heading_of(n) not in text)
    if not block:
        return text
    at = text.find("\n## How to use\n")
    if at < 0:
        return text.rstrip("\n") + ("\n\n" if text.strip() else "") + "## How to use\n\n" + block + "\n"
    end = text.find("\n## ", at + 5) + 1 or len(text)
    return text[:end].rstrip("\n") + "\n\n" + block + "\n" + ("\n" + text[end:] if end < len(text) else "")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("wire",))
    parser.add_argument("--repo", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repo = args.repo or subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    if not repo:
        sys.exit("REFUSED: not inside a git repo. Fix: run it from the repo, or pass --repo DIR")
    changed, refused = wire(repo, args.dry_run)
    for line in refused:
        print(line, file=sys.stderr if line.startswith("REFUSED") else sys.stdout)
    for name in changed:
        print("%s %s" % ("WOULD WIRE" if args.dry_run else "WIRED", name))
    if not changed and not refused:
        print("NO CHANGE: every agent file holds the current block")
    return 2 if any(line.startswith("REFUSED") for line in refused) else 0


if __name__ == "__main__":
    sys.exit(main())
