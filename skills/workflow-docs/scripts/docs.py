#!/usr/bin/env python3
"""Keep a repo's wiki pages in the repo, find stale ones, and publish them to its GitHub wiki.

usage: docs.py <command> [options]

  survey                       show the wiki's pages and this repo's page map
  add PAGE --paths A,B         add a page and the paths it describes
  check [--base REF]           list missing, stale, unmapped and unwritten pages; exit 1 if any
  criteria PAGE                print the criterion format and the next free id for a page
  publish [--dry-run] [--adopt PAGE]
                               copy the pages to the wiki, commit and push
  restore                      revert the last publish, if nothing came after it

With "criteria": true in .loop/config.json, check also enforces the contract in SKILL.md: the page list and sections;
"- ID: **Stage** text" lines with unique ids; each regression row linked to one criterion; the Tests line and banner;
no script file names; a mermaid chart and Status line for every command under Commands.

Publish never deletes a page, and refuses to replace a page without this tool's marker unless you name it with --adopt.
It runs git and nothing else.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

MARKER = "<!-- workflow-docs -->"
PAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,80}$")
SECTIONS = ["Summary", "Commands", "Criteria", "Enforced by"]
PREFIXES = {"Delivery": "DEL", "Documentation": "DOC", "Health": "HLT", "Milestones": "MIL", "Monitoring": "MON", "Regression": "REG", "Release": "REL"}
CRITERION = re.compile(r"^- ([A-Z]{2,5}-\d+): (\S.*)$")
CRITERION_ID = re.compile(r"^[A-Z]{2,5}-\d+$")
STAGE = re.compile(r"^\*\*(Unreviewed|Reviewed|Enforced|Proven)\*\* \S")
MAX_CRITERIA = 6
BANNER = "> **Unreviewed:** %d of %d criteria on this page have not been reviewed by the owner."
PLACEHOLDER = "Write this page from what is really in the repo."
SCRIPT_FILE = re.compile(r"[\w./-]*\w\.(?:py|sh|bash|zsh|js|mjs|cjs|ts|rb|pl|php|ps1|bat)\b", re.I)
COMMAND = re.compile(r"^[a-z][a-z-]*$")
BULLET = re.compile(r"^- `([a-z][a-z-]*)\b")
CHART_HEADING = re.compile(r"^#{3,6} `([^`]+)`\s*$")
STATUSES = ("built and proven", "built only", "planned")


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def git(*args, cwd=None, check=True):
    done = run(["git"] + list(args), cwd=cwd)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()[:300]))
    return done.stdout.strip()


def top():
    return git("rev-parse", "--show-toplevel")


def config(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            return json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no readable .loop/config.json. Fix: run workflow-setup and merge its branch.")


def wiki_dir(root):
    name = config(root).get("wiki_dir") or "docs/wiki"
    if os.path.isabs(name) or ".." in name.split("/"):
        sys.exit("REFUSED: wiki_dir must be a path inside the repo.")
    return name


def map_path(root):
    return os.path.join(root, ".loop", "docs.tsv")


def read_map(root):
    rows = {}
    try:
        with open(map_path(root)) as handle:
            for line in handle:
                if line.strip() and not line.startswith("#"):
                    page, _, paths = line.rstrip("\n").partition("\t")
                    rows[page] = [item.strip() for item in paths.split(",") if item.strip()]
    except OSError:
        pass
    return rows


def write_map(root, rows):
    os.makedirs(os.path.dirname(map_path(root)), exist_ok=True)
    with open(map_path(root), "w") as handle:
        handle.write("# page<TAB>paths it describes, comma separated\n")
        for page in sorted(rows):
            handle.write("%s\t%s\n" % (page, ",".join(rows[page])))


def wiki_url(root):
    url = git("remote", "get-url", "origin", cwd=root)
    return (url[:-4] if url.endswith(".git") else url.rstrip("/")) + ".wiki.git"


def web_url(url):
    match = re.search(r"github\.com[:/](.+?)\.wiki\.git$", url)
    return "https://github.com/%s/wiki" % match.group(1) if match else url


def clone(url, into):
    done = run(["git", "clone", "--quiet", url, into])
    if done.returncode:
        sys.exit("REFUSED: can't read the wiki at %s. Fix: turn the wiki on and create its first page in the browser "
                 "(GitHub makes the wiki's repo only then), then run this again." % url)


def state_file():
    common = os.path.abspath(git("rev-parse", "--git-common-dir"))
    path = os.path.join(common, "loop")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "wiki.json")


def cmd_survey(_args):
    root = top()
    url = wiki_url(root)
    temp = tempfile.mkdtemp(prefix="wiki-")
    try:
        done = run(["git", "clone", "--quiet", "--depth", "1", url, temp + "/w"])
        if done.returncode:
            print("WIKI none yet. Create its first page in the browser before publishing.")
        else:
            for name in sorted(os.listdir(temp + "/w")):
                if name.endswith(".md"):
                    with open(os.path.join(temp, "w", name)) as handle:
                        ours = handle.read().startswith(MARKER)
                    print("WIKI %s %s" % ("ours" if ours else "other", name[:-3]))
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    for page, paths in sorted(read_map(root).items()):
        print("MAP %s: %s" % (page, ", ".join(paths)))
    print("DIR " + wiki_dir(root))
    return 0


def cmd_add(args):
    if not PAGE.match(args.page):
        sys.exit("REFUSED: bad page name. Fix: letters, digits and dashes, such as Using-the-workflow.")
    paths = [item.strip() for item in args.paths.split(",") if item.strip()]
    if not paths:
        sys.exit("REFUSED: no paths. Fix: name what the page describes with --paths.")
    root = top()
    rows = read_map(root)
    rows[args.page] = paths
    write_map(root, rows)
    folder = os.path.join(root, wiki_dir(root))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, args.page + ".md")
    if not os.path.exists(path):
        with open(path, "w") as handle:
            handle.write("%s\n# %s\n\n%s\n" % (MARKER, args.page.replace("-", " "), PLACEHOLDER))
    print("PAGE %s -> %s" % (path, ", ".join(paths)))
    return 0


def problems(root, base):
    """Each page's trouble, as (kind, page, detail)."""
    found = []
    rows = read_map(root)
    folder = wiki_dir(root)
    for page, paths in sorted(rows.items()):
        rel = "%s/%s.md" % (folder, page)
        full = os.path.join(root, rel)
        if not os.path.exists(full):
            found.append(("MISSING", page, rel))
            continue
        with open(full) as handle:
            text = handle.read()
        if PLACEHOLDER in text or len(text.replace(MARKER, "").split()) < 10:
            found.append(("UNWRITTEN", page, rel))
        seen = git("rev-list", "--no-merges", "HEAD", "--", rel, cwd=root, check=False).split()
        if not seen:
            continue
        skip = ["^" + sha for sha in seen + [base] if sha]  # merges add nothing
        changed = git("log", "--no-merges", "--full-history", "--format=%h %s", "HEAD", *skip, "--", *paths,
                      cwd=root).splitlines()
        if changed:
            found.append(("STALE", page, "%d commits since the page: %s" % (len(changed), changed[0][:70])))
    held = os.path.join(root, folder)
    if os.path.isdir(held):
        for name in sorted(os.listdir(held)):
            if name.endswith(".md") and name[:-3] not in rows:
                found.append(("UNMAPPED", name[:-3], "not in .loop/docs.tsv"))
    return found


def sections(text):
    """The page's level-2 sections, as (name, lines), outside code fences."""
    found, fenced = [], False
    for line in text.splitlines():
        if line.startswith("```"):
            fenced = not fenced
        if not fenced and line.startswith("## "):
            found.append((line[3:].strip(), []))
        elif found:
            found[-1][1].append(line)
    return found


def commands(lines):
    """Command names under Commands: the first word of a line in a text block, or of a bullet in backticks."""
    found, fence = [], None
    for line in lines:
        if line.startswith("```"):
            fence = None if fence is not None else line[3:].strip()
        elif fence == "text":
            word = line.split()[0] if line.strip() and not line[0].isspace() else ""
            if COMMAND.match(word) and word not in found:
                found.append(word)
        elif fence is None:
            match = BULLET.match(line)
            if match and match.group(1) not in found:
                found.append(match.group(1))
    return found


def charts(lines):
    """What each `command` heading holds, as {name: {"chart": bool, "status": bool}}."""
    found, name, fenced = {}, None, False
    for line in lines:
        if line.startswith("```"):
            if name and not fenced and line.strip() == "```mermaid":
                found[name]["chart"] = True
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            match = CHART_HEADING.match(line)
            name = match.group(1) if match else None
            if name:
                found[name] = {"chart": False, "status": False}
        elif not fenced and name and line.startswith("Status: "):
            found[name]["status"] = all(word in line.lower() for word in STATUSES)
    return found


def chart_trouble(page, lines):
    names = commands(lines)
    if not names:
        return [("CHART", page, "Commands lists no command")]
    held = charts(lines)
    found = []
    for name in names:
        item = held.get(name, {})
        if not item.get("chart"):
            found.append(("CHART", page, "%s has no chart. Fix: add a heading naming it in backticks, and a mermaid block" % name))
        elif not item.get("status"):
            found.append(("CHART", page, "%s has no status line with all three labels" % name))
    return found


def test_rows(root):
    """Real tests as {criterion: [(id, proved)]}, plus ids linked to none. None with no file."""
    try:
        with open(os.path.join(root, ".loop", "regression.tsv")) as handle:
            rows = [line.rstrip("\n").split("\t") + [""] * 5 for line in handle if line.strip() and line[0] != "#"]
    except OSError:
        return None, []
    linked, loose = {}, []
    for row in rows:
        key = next((item for item in (row[3], row[0]) if CRITERION_ID.match(item)), "")
        if row[1] == "draft":
            continue
        if key:
            linked.setdefault(key, []).append((row[0], bool(row[4]) or row[1] == "covered"))
        else:
            loose.append(row[0])
    return linked, loose


def stage_of(tests):
    """The stage a reviewed criterion's tests earn."""
    if not tests:
        return "Reviewed"
    return "Proven" if all(proved for _, proved in tests) else "Enforced"


def contract(root):
    """Criteria contract trouble, as (kind, page, detail). Off unless config sets "criteria": true."""
    if not config(root).get("criteria"):
        return []
    found, seen = [], {}
    linked, loose = test_rows(root)
    for page in sorted(read_map(root)):
        if page != "Home" and page not in PREFIXES:
            found.append(("PAGE", page, "not allowed. Fix: use %s or Home" % ", ".join(sorted(PREFIXES))))
            continue
        full = os.path.join(root, wiki_dir(root), page + ".md")
        if not os.path.exists(full):
            continue
        with open(full) as handle:
            text = handle.read()
        named = sorted(set(item.group(0) for item in SCRIPT_FILE.finditer(text)))
        if named:
            found.append(("SCRIPT", page, "names %s. Fix: describe the command and what it does" % ", ".join(named)))
        if page == "Home":
            continue
        parts = sections(text)
        names = [name for name, _ in parts]
        if names != SECTIONS:
            found.append(("SECTIONS", page, "have %s, want %s" % (", ".join(names) or "none", ", ".join(SECTIONS))))
            continue
        body = dict(parts)
        found += chart_trouble(page, body["Commands"])
        ids, stages = [], {}
        lines = [line for line in body["Criteria"] if line.strip()]
        heads = [line for line in lines if line.startswith(("> ", "Tests: "))]
        for line in lines:
            if line not in heads:
                match = CRITERION.match(line)
                if not match:
                    found.append(("CRITERION", page, "not one line '- ID: text': " + line.strip()[:60]))
                elif match.group(1) in seen:
                    found.append(("DUPLICATE", page, "%s is also in %s" % (match.group(1), seen[match.group(1)])))
                else:
                    seen[match.group(1)] = page
                    ids.append(match.group(1))
                    stage = STAGE.match(match.group(2))
                    stages[match.group(1)] = stage.group(1) if stage else ""
                    if not stage:
                        found.append(("STAGE", page, "%s has no stage after its id" % match.group(1)))
        if len(ids) > MAX_CRITERIA:
            found.append(("CAP", page, "has %d criteria, over the cap of %d" % (len(ids), MAX_CRITERIA)))
        rows = linked or {}
        waiting = sum(1 for stage in stages.values() if stage == "Unreviewed")
        want = ["Tests: %d." % sum(len(rows.get(key, [])) for key in ids)]
        want += [BANNER % (waiting, len(ids))] if waiting else []
        if heads != want[::-1] and heads != want:
            found.append(("TESTS", page, "want above the criteria: " + " | ".join(want)))
        enforced = {m.group(1): m.group(2) for m in map(CRITERION.match, body["Enforced by"]) if m}
        for key in ids:
            if key not in enforced:
                found.append(("UNENFORCED", page, "%s has no row in Enforced by" % key))
            elif linked is not None and set(enforced[key].split(", ")) != {name for name, _ in rows.get(key, [])}:
                found.append(("LINK", page, "%s lists %s, but its rows are %s" % (
                    key, enforced[key], ", ".join(name for name, _ in rows.get(key, [])) or "none")))
            earned = stage_of(rows.get(key, []))
            if stages[key] not in ("", "Unreviewed", earned):
                found.append(("STAGE", page, "%s says %s, and its tests make it %s" % (key, stages[key], earned)))
    for name in loose:
        found.append(("LINK", "regression", "row %s links to no criterion" % name))
    for key in sorted(set(linked or {}) - set(seen)):
        found.append(("LINK", "regression", "rows link to %s, which no page has" % key))
    return found


def cmd_criteria(args):
    root = top()
    prefix = PREFIXES.get(args.page)
    if not prefix:
        sys.exit("REFUSED: %s has no criteria. Fix: use %s." % (args.page, ", ".join(sorted(PREFIXES))))
    used = [0]
    folder = os.path.join(root, wiki_dir(root))
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith(".md"):
            with open(os.path.join(folder, name)) as handle:
                used += [int(n) for n in re.findall(r"^- %s-(\d+): " % prefix, handle.read(), re.M)]
    print("FORMAT one line under ## Criteria: '- %s-N: **Unreviewed** what must hold', and under ## Enforced by: "
          "'- %s-N: <regression row ids>'" % (prefix, prefix))
    print("NEXT %s-%d" % (prefix, max(used) + 1))
    return 0


def cmd_check(args):
    root = top()
    if not read_map(root):
        print("NO PAGES: run add first")
        return 1
    found = problems(root, args.base) + contract(root)
    for kind, page, detail in found:
        print("%s %s: %s" % (kind, page, detail))
    if found:
        return 1
    print("DOCS OK: %d pages" % len(read_map(root)))
    return 0


def cmd_publish(args):
    root = top()
    rows = read_map(root)
    if not rows:
        sys.exit("REFUSED: no pages. Fix: run add first.")
    found = problems(root, None) + contract(root)
    if found:
        for kind, page, detail in found:
            print("%s %s: %s" % (kind, page, detail))
        sys.exit("REFUSED: fix the pages above first.")
    url = wiki_url(root)
    temp = tempfile.mkdtemp(prefix="wiki-")
    try:
        wiki = os.path.join(temp, "wiki")
        clone(url, wiki)
        before = git("rev-parse", "HEAD", cwd=wiki)
        changed = []
        for page in sorted(rows):
            with open(os.path.join(root, wiki_dir(root), page + ".md")) as handle:
                text = handle.read()
            if not text.startswith(MARKER):
                sys.exit("REFUSED: %s lost its marker. Fix: restore the first line %s." % (page, MARKER))
            target = os.path.join(wiki, page + ".md")
            old = None
            if os.path.exists(target):
                with open(target) as handle:
                    old = handle.read()
                if not old.startswith(MARKER) and page not in args.adopt:
                    sys.exit("REFUSED: the wiki already has %s, and this tool didn't write it. Nothing was published. "
                             "Fix: rename your page, or pass --adopt %s to replace it." % (page, page))
            if old != text:
                changed.append(page)
                if not args.dry_run:
                    with open(target, "w") as handle:
                        handle.write(text)
        for page in changed:
            print("%s %s" % ("WOULD WRITE" if args.dry_run else "WROTE", page))
        if args.dry_run or not changed:
            print("NO CHANGE" if not changed else "DRY RUN: nothing pushed")
            return 0
        git("add", "--", *[page + ".md" for page in changed], cwd=wiki)
        head = git("rev-parse", "--short", "HEAD", cwd=root)
        git("commit", "-m", "Docs from %s: %s" % (head, ", ".join(changed)), cwd=wiki)
        pushed = run(["git", "push", "origin", "HEAD"], cwd=wiki)
        if pushed.returncode:
            sys.exit("REFUSED: wiki push failed, nothing changed: " + pushed.stderr.strip()[:300])
        after = git("rev-parse", "HEAD", cwd=wiki)
        with open(state_file(), "w") as handle:
            json.dump({"before": before, "after": after, "url": url, "pages": changed}, handle)
        print("PUBLISHED %s" % web_url(url))
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    return 0


def cmd_restore(_args):
    try:
        with open(state_file()) as handle:
            held = json.load(handle)
    except (OSError, ValueError):
        sys.exit("REFUSED: no publish on record.")
    temp = tempfile.mkdtemp(prefix="wiki-")
    try:
        wiki = os.path.join(temp, "wiki")
        clone(held["url"], wiki)
        if git("rev-parse", "HEAD", cwd=wiki) != held["after"]:
            sys.exit("REFUSED: the wiki changed after the last publish, so nothing was reverted.")
        git("revert", "--no-edit", held["after"], cwd=wiki)
        pushed = run(["git", "push", "origin", "HEAD"], cwd=wiki)
        if pushed.returncode:
            sys.exit("REFUSED: wiki push failed: " + pushed.stderr.strip()[:300])
    finally:
        shutil.rmtree(temp, ignore_errors=True)
    os.remove(state_file())
    print("RESTORED the wiki: reverted %s" % ", ".join(held["pages"]))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("survey").set_defaults(func=cmd_survey)
    item = sub.add_parser("add")
    item.add_argument("page")
    item.add_argument("--paths", required=True)
    item.set_defaults(func=cmd_add)
    item = sub.add_parser("check")
    item.add_argument("--base", default="")
    item.set_defaults(func=cmd_check)
    item = sub.add_parser("criteria")
    item.add_argument("page")
    item.set_defaults(func=cmd_criteria)
    item = sub.add_parser("publish")
    item.add_argument("--dry-run", action="store_true")
    item.add_argument("--adopt", action="append", default=[])
    item.set_defaults(func=cmd_publish)
    sub.add_parser("restore").set_defaults(func=cmd_restore)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
