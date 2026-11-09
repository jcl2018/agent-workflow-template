#!/usr/bin/env python3
"""Keep a repo's wiki pages in the repo, find stale ones, and publish them to its GitHub wiki.

usage: docs.py <command> [options]

  survey                       show the wiki's pages and this repo's page map
  add PAGE --paths A,B         add a page and the paths it describes
  check [--base REF]           list missing, stale, unmapped and unwritten pages, counts the repo doesn't match, and
                               broken criteria; exit 1 if any
  audit [--base REF] [--dry-run]
                               the one command: check every required doc, fix what is mechanical, list wording to rewrite
  criteria PAGE                print the requirement format and the next free id for a page
  publish [--dry-run] [--adopt PAGE]
                               copy the pages to the wiki, commit and push
  restore                      revert the last publish, if nothing came after it

With "criteria": true in .loop/config.json, check also enforces the PRD page contract (references/template.md).
criteria.py reviews requirements and PRDs and renders Tests; prd.py drafts and converts pages.

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

import counting
import criteria

# No terminal, no waiting.
os.environ.update(GIT_TERMINAL_PROMPT="0", GIT_EDITOR="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

MARKER = "<!-- workflow-docs -->"
PAGE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,80}$")
PREFIXES = {"Delivery": "DEL", "Documentation": "DOC", "Health": "HLT", "Monitoring": "MON", "Regression": "REG", "Setup": "SET"}
PLACEHOLDER = "Write this page from what is really in the repo."


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def git(*args, cwd=None, check=True):
    done = run(["git"] + list(args), cwd=cwd)
    if check and done.returncode:
        sys.exit("REFUSED: git %s: %s" % (" ".join(args), done.stderr.strip()[:300]))
    return done.stdout.strip()


def identity(cwd):
    """git -c options giving a commit an author where none is configured, as on a CI runner; a real identity is kept."""
    if git("config", "user.email", cwd=cwd, check=False):
        return []
    return ["-c", "user.name=workflow-docs", "-c", "user.email=workflow-docs@users.noreply.github.com"]


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


def counts(root):
    """Numbers the docs state that the repo can check, as (COUNT, file, detail) rows (counting.py)."""
    return counting.counts(root, wiki_dir(root), read_map(root), config(root).get("criteria"))


def contract(root):
    """Criteria contract trouble, as (kind, page, detail). Off unless config sets "criteria": true."""
    if not config(root).get("criteria"):
        return []
    found, names = [], []
    for page in sorted(read_map(root)):
        if not PAGE.match(page):
            found.append(("PAGE", page, "not a page name. Fix: letters, digits and hyphens, or remove its .loop/docs.tsv row"))
        elif page != "Home" and os.path.exists(os.path.join(root, wiki_dir(root), page + ".md")):
            names.append(page)
    return found + criteria.contract(root, names, {})


def cmd_criteria(args):
    root = top()
    folder = os.path.join(root, wiki_dir(root))
    if args.page not in read_map(root) or args.page == "Home":
        sys.exit("REFUSED: %s has no criteria. Fix: use a page listed in .loop/docs.tsv, not Home." % args.page)
    held = ""
    if os.path.exists(os.path.join(folder, args.page + ".md")):
        with open(os.path.join(folder, args.page + ".md")) as handle:
            held = handle.read()
    own = re.findall(r"^- ([A-Z]{2,5})-\d+: ", held, re.M)
    prefix = PREFIXES.get(args.page) or (own[0] if own else re.sub(r"[^A-Z]", "", args.page.upper())[:3].ljust(2, "X"))
    used = [0]
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith(".md"):
            with open(os.path.join(folder, name)) as handle:
                used += [int(n) for n in re.findall(r"^- %s-(\d+): " % prefix, handle.read(), re.M)]
    print("FORMAT one line under ## Requirements: '- %s-N: **Unreviewed** what must hold'. Tests are made by "
          "criteria.py render" % prefix)
    print("NEXT %s-%d" % (prefix, max(used) + 1))
    return 0


def cmd_check(args):
    root = top()
    if not read_map(root):
        print("NO PAGES: run add first")
        return 1
    found = problems(root, args.base) + contract(root) + counts(root)
    for kind, page, detail in found:
        print("%s %s: %s" % (kind, page, detail))
    if found:
        return 1
    print("DOCS OK: %d pages" % len(read_map(root)))
    return 0


def cmd_audit(args):
    import audit
    return audit.audit(top(), args.base, args.dry_run)


def cmd_publish(args):
    root = top()
    rows = read_map(root)
    if not rows:
        sys.exit("REFUSED: no pages. Fix: run add first.")
    found = problems(root, None) + [c for c in contract(root) if c[0] != "CHANGED"]  # Usage drift waits on the owner
    found += [c for c in counts(root) if c[1].startswith(wiki_dir(root) + "/")]
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
        git(*identity(wiki), "commit", "-m", "Docs from %s: %s" % (head, ", ".join(changed)), cwd=wiki)
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
        git(*identity(wiki), "revert", "--no-edit", held["after"], cwd=wiki)
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
    item = sub.add_parser("audit")
    item.add_argument("--base", default="")
    item.add_argument("--dry-run", action="store_true")
    item.set_defaults(func=cmd_audit)
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
