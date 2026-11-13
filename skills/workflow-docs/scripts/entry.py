#!/usr/bin/env python3
"""The repo's entry point, .loop/START.md, and the marked block in each agent's entry file, built from the repo's data.

usage: entry.py render|write|check|block|lag [--repo DIR]

  render   print .loop/START.md as it would be written
  write    write .loop/START.md and refresh the marked block in each agent file that already holds one
  check    STALE or MISSING lines (exit 1), LAG lines (exit 0), or ENTRY OK
  block    print the agent block (workflow-setup's agents.py writes it into CLAUDE.md and AGENTS.md)
  lag      print one line when the repo is behind the installed template, nothing when current (exit 0); --new SLUG exits 3
           with REFUSED when the majors differ (a migrate- slug passes)

START.md opens with a first-five-minutes list, then one part each for the loop, release, operation and workers, docs,
regression, health and settings (filled from .loop/config.json through references/start.md), then a Features table
(every PRD page in the wiki folder: its name, milestone, first sentence of Problem and the asks in its skills' Command maps) and a Settings
table (each repo setting, its value and its _help line). Private settings are never read. It holds no count, date or
machine path, so it changes only when a page or a setting does.

When the installed skills are newer than the repo's template_version, a difference in the parts built from the skills
(the narrative and the block's skill list) is LAG, not STALE: ask for workflow-setup update. The Features and Settings
tables are always checked. It runs git and nothing else.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.dirname(os.path.dirname(HERE))  # the folder holding the workflow-* skills
TEMPLATES = os.path.join(os.path.dirname(HERE), "references", "start.md")
REFERENCE = os.path.join(SKILLS, "workflow-setup", "references", "settings.md")  # every repo setting, default and line
ENTRY = os.path.join(".loop", "START.md")
OPEN, CLOSE = "<!-- workflow-loop -->", "<!-- /workflow-loop -->"
AGENT_FILES = ["CLAUDE.md", "AGENTS.md"]
PARTS = ("Loop", "Release", "Operation and workers", "Docs", "Regression", "Health", "Settings")

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")


def version_key(text):
    """The first three integers of a version; empty or unreadable is older than any version."""
    return tuple(int(x) for x in re.findall(r"\d+", str(text or ""))[:3])


def read(path, default=""):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return default


def config(root):
    try:
        found = json.loads(read(os.path.join(root, ".loop", "config.json"), "{}"))
    except ValueError:
        found = {}
    return found if isinstance(found, dict) else {}


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ").strip()


def show(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value in (None, "", [], {}):
        return "none"
    return value if isinstance(value, (str, int, float)) else json.dumps(value)


def sentence(text):
    """The first sentence: up to the first '. ' outside backticks."""
    ticks = 0
    for n, char in enumerate(text):
        ticks += char == "`"
        if char == "." and ticks % 2 == 0 and text[n + 1:n + 2] in (" ", "\n", ""):
            return text[:n + 1]
    return text


def section(text, name):
    found = re.search(r"^## %s\s*\n(.*?)(?=^## |\Z)" % re.escape(name), text, re.M | re.S)
    return found.group(1).strip() if found else ""


def reference():
    """{setting: (default, explanation)} for every repo setting in workflow-setup's generated reference, if installed."""
    part = read(REFERENCE).split("## Repo settings", 1)[-1].split("\n## ", 1)[0] if os.path.exists(REFERENCE) else ""
    rows = re.findall(r"^\| `([a-z_]+)` \| `(.*?)` \| (.*?) \|$", part, re.M)
    out = {}
    for key, default, text in rows:
        try:
            out[key] = (json.loads(default), text)
        except ValueError:
            out[key] = (default, text)
    return out


def settings(cfg):
    """[(key, value, explanation)]: every repo setting, the config's value or else its default, plus any other key held."""
    known, helps = reference(), cfg.get("_help") if isinstance(cfg.get("_help"), dict) else {}
    keys = sorted(set(known) | {k for k in cfg if not k.startswith("_")})
    return [(k, cfg[k] if k in cfg else known[k][0], helps.get(k) or known.get(k, ("", ""))[1]) for k in keys]


def purpose(problem):
    """The first sentence of Problem that says what the feature is for (a leading 'Skill: ...' sentence is skipped)."""
    first = sentence(problem)
    rest = problem[len(first):].strip()
    return sentence(rest) if re.match(r"^Skills?:", first) and rest else first


def owned(root, page):
    """The skills a page describes, from its .loop/docs.tsv paths."""
    for line in read(os.path.join(root, ".loop", "docs.tsv")).splitlines():
        cells = line.split("	")
        if cells[0] == page and len(cells) > 1:
            return sorted(set(re.findall(r"(?:^|,)skills/(workflow-[\w-]+)", cells[1])))
    return []


def commands(skill):
    """'`/skill`: verb / verb' for the asks in the skill's SKILL.md Command map."""
    asks = re.findall(r"^\| `/%s ([\w-]+)" % re.escape(skill), section(read(os.path.join(SKILLS, skill, "SKILL.md")), "Command map"), re.M)
    return "`/%s`: %s" % (skill, " / ".join(dict.fromkeys(asks)) or "see its SKILL.md")


def features(root, cfg):
    folder = os.path.join(root, cfg.get("wiki_dir") or "docs/wiki")
    rows = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        text = read(os.path.join(folder, name)) if name.endswith(".md") else ""
        if not (section(text, "Problem") and re.search(r"^## Requirements", text, re.M)):
            continue
        mile = re.search(r"^Milestone:\s*(\S.*)$", text, re.M)
        first = section(text, "Problem").split("\n\n")[0]
        if first.startswith("- "):  # a Problem written as bullets: the first bullet says what the feature is for
            first = re.split(r"\n(?=- )", first)[0][2:]
        problem = " ".join(first.split())
        items = [commands(skill) for skill in owned(root, name[:-3])]
        rows.append("| %s | %s | %s | %s |" % (name[:-3], cell(mile.group(1) if mile else "none"), cell(purpose(problem)),
                                              cell(" / ".join(items) or "none")))
    return rows


def narrative(cfg):
    text, out = read(TEMPLATES), []
    cfg = dict({k: v for k, v, _ in settings(cfg)}, **cfg)
    for part in PARTS:
        body = " ".join(section(text, part).split())
        out += ["## " + part, "", re.sub(r"\{(\w+)\}", lambda m: str(show(cfg.get(m.group(1)))), body), ""]
    return out


def render(root):
    cfg = config(root)
    lines = ["# Start here", "", "Generated by `entry.py write` from this repo's PRD pages and `.loop/config.json`. Don't edit it by "
             "hand: change a page or a setting, then run `docs.py audit`.", "", "## First five minutes", "",
             "1. Read this page: how the parts fit together, every feature and how to use it, and every setting.",
             "2. Ask for `workflow-monitoring report` to see what is running and what waits on you.",
             "3. Start a goal by asking for `workflow-monitoring go \"goal\" --done \"line\"`.",
             "4. Each skill's Command map, in its SKILL.md, names the exact script behind every ask.",
             "5. Run `entry.py lag`; if it prints a line, this repo is behind the template: tell the owner.", ""]
    lines += narrative(cfg)
    lines += ["## Features", "", "| Feature | Milestone | What it is for | How to use it |", "|---|---|---|---|"]
    lines += features(root, cfg) or ["| none | | | |"]
    lines += ["", "## Settings table", "", "| Setting | Value | What it does |", "|---|---|---|"]
    lines += ["| `%s` | %s | %s |" % (key, cell(show(value)), cell(text)) for key, value, text in settings(cfg)]
    return "\n".join(lines) + "\n"


def skills():
    """(name, description) for each installed workflow-* skill beside this one, in name order."""
    out = []
    for name in sorted(os.listdir(SKILLS)):
        head = read(os.path.join(SKILLS, name, "SKILL.md")) if name.startswith("workflow-") else ""
        found = re.search(r"^description:\s*(.+)$", head.split("\n---", 1)[0], re.M)
        if found:
            out.append((name, sentence(found.group(1).strip())))
    return out


def block():
    lines = [OPEN, "## Workflow loop", "", "Generated by workflow-setup (`agents.py wire`); edit outside this block. Claude Code reads it in "
             "CLAUDE.md and Codex in AGENTS.md, so both run the same loop the same way.", "",
             "- Read `.loop/START.md` first: how the loop fits together, every feature and how to use it, every setting.",
             "- Run a command by asking for `<skill> <command>`. Each skill's Command map, in its SKILL.md, names the exact "
             "`python3 scripts/...` command, run from that skill's folder.",
             "- A merge conflict in this block or in `.loop/START.md`: take either side, run `entry.py write`, commit.",
             "- Run `entry.py lag` (workflow-docs) when a session starts; if it prints a line, tell the owner.", "", "Skills:", ""]
    lines += ["- `%s`: %s" % pair for pair in skills()]
    return "\n".join(lines + [CLOSE]) + "\n"


def held_block(text):
    """The marked block, LF endings and no final newline (a file may end at the close marker), or None."""
    found = re.search(r"%s.*?%s" % (re.escape(OPEN), re.escape(CLOSE)), text, re.S)
    return found.group(0).replace("\r\n", "\n") if found else None


def raw_text(path):
    """A file as written: line endings untouched (empty when missing or not UTF-8)."""
    try:
        with open(path, encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, ValueError):
        return ""


def agent_files(cfg):
    value = cfg.get("agent_files", AGENT_FILES)
    return [p for p in value if isinstance(p, str)] if isinstance(value, list) else AGENT_FILES


def installed():
    """The installed template version from workflow-package.json beside the skills; empty for a checkout (never LAG).
    A toy may set LOOP_INSTALLED_VERSION, honoured only with LOOP_TEST=1."""
    if os.environ.get("LOOP_TEST") == "1" and os.environ.get("LOOP_INSTALLED_VERSION"):
        return os.environ["LOOP_INSTALLED_VERSION"]
    try:
        return str(json.loads(read(os.path.join(SKILLS, "workflow-package.json"), "{}")).get("version") or "")
    except ValueError:
        return ""


def lagging(root, cfg):
    """True when the installed skills are newer than the repo's template_version (never for the template's own checkout)."""
    if os.path.realpath(SKILLS).startswith(os.path.realpath(root) + os.sep) or not installed():
        return False
    return version_key(installed()) > version_key(cfg.get("template_version"))


NOTE = "this repo is at v%s, the template is at v%s, run the migrate goal"


def lag(root, new=""):
    """(line, refusal): the version nag for a repo behind the installed template, '' when current. The refusal is set only for
    goal.py new (new = the slug) when both majors are known and differ; a migrate- slug is exempt."""
    want, held = installed(), config(root).get("template_version")
    if not want or os.path.realpath(SKILLS).startswith(os.path.realpath(root) + os.sep):
        return "", ""
    known = isinstance(held, str) and re.fullmatch(r"\d+\.\d+\.\d+", held)
    if known and version_key(held) >= version_key(want):
        return "", ""
    name = re.sub(r"[^a-z0-9]+", "-", os.path.basename(os.path.realpath(root)).lower()).strip("-")
    line = NOTE % (held if known else "0", want) + " (slug migrate-%s)" % name
    if known and new and not new.startswith("migrate-") and version_key(held)[0] != version_key(want)[0]:
        return line, "REFUSED: this repo is at v%s and the template at v%s (different major). Fix: start it as a migrate-%s goal; nothing was changed" % (held, want, name)
    return line, ""


def problems(root):
    """(kind, path, detail) for the entry point and the agent blocks; LAG never fails a check."""
    cfg, found = config(root), []
    want, have = render(root), read(os.path.join(root, ENTRY), None)
    lag = lagging(root, cfg)
    fix = "Fix: python3 <workflow-docs>/scripts/entry.py write (or docs.py audit)"
    note = NOTE % (cfg.get("template_version") or "0", installed())
    # MISSING applies once a repo was set up by a version that writes the entry point (it holds template_version), or
    # to the template's own checkout; a repo adopted before keeps passing until update writes it.
    owed = cfg.get("criteria") and (cfg.get("template_version") or os.path.realpath(SKILLS).startswith(os.path.realpath(root) + os.sep))
    if have is None:
        if owed:
            found.append(("MISSING", ENTRY, "no entry point (ENTRY_MISSING). " + fix))
    elif have != want:
        own = ["| `%s` |" % k for k in cfg if not k.startswith("_")]  # rows the repo's config holds, not new defaults
        rows = lambda text: sorted(r for r in section(text, "Settings table").splitlines() if r.startswith(tuple(own)))
        data_same = section(have, "Features") == section(want, "Features") and rows(have) == rows(want)
        found.append(("LAG", ENTRY, note + " (ENTRY_LAG)") if lag and data_same else ("STALE", ENTRY, "differs from its sources (ENTRY_STALE). " + fix))
    if not skills():
        found.append(("SKIPPED", "agent block", "no installed skills beside workflow-docs"))
        return found
    want_block = block().rstrip("\n")
    for name in agent_files(cfg):
        text = read(os.path.join(root, name))
        held = held_block(text)
        if (OPEN in text or CLOSE in text) and (text.count(OPEN) != 1 or text.count(CLOSE) != 1 or held is None):
            found.append(("STALE", name, "stray workflow-loop markers (ENTRY_MARKER). Fix: remove the stray marker, then ask "
                                         "for workflow-setup agents"))
        elif held is None and owed:
            found.append(("MISSING", name, "no workflow-loop block (ENTRY_MISSING). Fix: ask for workflow-setup agents"))
        elif held is not None and held != want_block:
            found.append(("LAG", name, note + " (ENTRY_LAG)") if lag else ("STALE", name, "its workflow-loop block differs (ENTRY_STALE). " + fix))
    return found


def write(root):
    path = os.path.join(root, ENTRY)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = render(root)
    changed = read(path, None) != text
    if changed:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
    names, want = [], block().rstrip("\n")
    for name in agent_files(config(root)) if skills() else []:
        full = os.path.join(root, name)
        raw = raw_text(full)
        span = re.search(r"%s.*?%s" % (re.escape(OPEN), re.escape(CLOSE)), raw, re.S)
        if not span or raw.count(OPEN) != 1 or raw.count(CLOSE) != 1:
            continue  # no block, or stray markers: agents.py wire refuses those with the fix (AGENTS_MARKER)
        if span.group(0).replace("\r\n", "\n") != want:
            with open(full, "w", encoding="utf-8", newline="") as handle:
                handle.write(raw[:span.start()] + want.replace("\n", "\r\n" if "\r\n" in raw else "\n") + raw[span.end():])
            names.append(name)
    return (["FIXED " + ENTRY] if changed else []) + ["FIXED " + n for n in names]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("render", "write", "check", "block", "lag"))
    parser.add_argument("--repo", default="")
    parser.add_argument("--new", default="")
    args = parser.parse_args()
    root = os.path.abspath(args.repo) if args.repo else subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or os.getcwd()
    if args.command == "render":
        sys.stdout.write(render(root))
    elif args.command == "block":
        sys.stdout.write(block())
    elif args.command == "lag":
        line, refusal = lag(root, args.new)
        if refusal or line:
            print(refusal or line, file=sys.stderr if refusal else sys.stdout)
        return 3 if refusal else 0
    elif args.command == "write":
        print("\n".join(write(root)) or "NO CHANGE " + ENTRY)
    else:
        found = problems(root)
        for kind, path, detail in found:
            print("%s %s: %s" % (kind, path, detail))
        if any(kind in ("STALE", "MISSING") for kind, _, _ in found):
            return 1
        print("ENTRY OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
