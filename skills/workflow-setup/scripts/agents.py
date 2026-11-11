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
import json
import os
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
