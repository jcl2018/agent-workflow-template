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
  automation                   each routine's live state here: a workflow's newest run, a launch agent loaded or not

With "criteria": true in .loop/config.json, check also enforces the PRD page contract (references/template.md).
It also enforces the page format (pageformat.py, FORMAT lines) and that the generated Tests page matches a fresh render.
criteria.py reviews requirements and PRDs and renders Tests; prd.py drafts and converts pages; counting.py reads counts.

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
import entry
import pageformat
from counting import map_path, read_map, write_map  # noqa: F401

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


def netless(root, judged, mine):
    """True when the paths read the same at HEAD as at the newest commit already judged (the page's, the base's or a merged
    one): commits that add and then revert a change leave nothing to describe, so they stale no page (issue 3771)."""
    tip = git("rev-list", "--no-walk=sorted", "-n1", *judged, cwd=root, check=False)
    return bool(tip) and not git("diff", "--name-only", tip, "HEAD", "--", *mine, cwd=root, check=False)


def problems(root, base):
    """Each page's trouble, as (kind, page, detail)."""
    found = []
    rows = read_map(root)
    folder = wiki_dir(root)
    merged = from_base(root, base)
    for page, paths in sorted(rows.items()):
        if page in pageformat.GENERATED:
            continue  # checked against a fresh render below
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
        skip = ["^" + sha for sha in seen + [base] + merged if sha]  # merges add nothing
        mine = paths + [":(exclude).loop/config.json"] * pageformat.is_guide(text)  # a guide isn't about settings values
        changed = counting.real(root, git("log", "--no-merges", "--full-history", "--format=%h %s", "HEAD", *skip, "--", *mine,
                                          cwd=root).splitlines(), mine)  # block-only commits say nothing
        if changed and not netless(root, [s for s in seen + [base] + merged if s], mine):
            found.append(("STALE", page, "%d commits since the page: %s" % (len(changed), changed[0][:70])))
    held = os.path.join(root, folder)
    if os.path.isdir(held):
        for name in sorted(os.listdir(held)):
            if name.endswith(".md") and name[:-3] not in rows and name[:-3] not in pageformat.GENERATED:
                found.append(("UNMAPPED", name[:-3], "not in .loop/docs.tsv"))
    if config(root).get("criteria"):
        import render
        found += render.stale_blocks(root) + (render.generated(root) if feature_pages(root) else [])
    return found


def from_base(root, base):
    """With a base, the base-branch commits merged into this branch since it, as parents to skip: they were judged in
    their own goal, so only what the branch itself changed can stale its pages."""
    if not base:
        return []
    name = config(root).get("base") or "main"
    tips = [t for t in ("origin/" + name,) if git("rev-parse", "--verify", "--quiet", t, cwd=root, check=False)
            and run(["git", "merge-base", "--is-ancestor", "HEAD", t], cwd=root).returncode]  # not on the base branch itself
    out = []
    for line in git("rev-list", "--merges", "--first-parent", "--parents", "HEAD", "^" + base, cwd=root, check=False).splitlines():
        for parent in line.split()[2:]:
            if any(not run(["git", "merge-base", "--is-ancestor", parent, t], cwd=root).returncode for t in tips):
                out.append(parent)
    return out


def guide(root, page):
    try:
        with open(os.path.join(root, wiki_dir(root), page + ".md")) as handle:
            return pageformat.is_guide(handle.read())
    except OSError:
        return False


def guarded(root, page):
    """The first requirement or Review line on a page, shortened; '' when it has none."""
    with open(os.path.join(root, wiki_dir(root), page + ".md")) as handle:
        hit = next((x for x in handle.read().splitlines() if criteria.LINE.match(x) or x.startswith("Review: ")), "")
    return pageformat.short(hit) if hit else ""


def feature_pages(root):
    """The mapped pages that exist, other than Home, guides and the generated ones."""
    return [page for page in sorted(read_map(root)) if PAGE.match(page) and page != "Home" and page not in pageformat.GENERATED
            and os.path.exists(os.path.join(root, wiki_dir(root), page + ".md")) and not guide(root, page)]


def counts(root):
    """Numbers the docs state that the repo can check, as (COUNT, file, detail) rows (counting.py)."""
    return counting.counts(root, wiki_dir(root), read_map(root), config(root).get("criteria"))


def contract(root):
    """Criteria contract trouble, as (kind, page, detail). Off unless config sets "criteria": true."""
    if not config(root).get("criteria"):
        return []
    import render
    found, names = [], feature_pages(root)
    for page in sorted(read_map(root)):
        if not PAGE.match(page):
            found.append(("PAGE", page, "not a page name. Fix: letters, digits and hyphens, or remove its .loop/docs.tsv row"))
        elif guide(root, page) and guarded(root, page):
            found.append(("FORMAT", page, "DOC-1 a guide page holds no requirement or Review line (got %s). Fix: remove "
                          "the line %s and use the feature page format, or move them to a feature page"
                          % (guarded(root, page), pageformat.GUIDE)))
    return found + criteria.contract(root, names, {}) + render.front(root, names)


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
    point = entry.problems(root)
    notes = [item for item in point if item[0] in ("LAG", "SKIPPED")]  # said, never a failure
    found = problems(root, args.base) + contract(root) + counts(root) + [i for i in point if i not in notes]
    for kind, page, detail in found + notes:
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
    if config(root).get("criteria"):
        import render
        render.refresh(root)  # the Settings and Automation blocks are written fresh, so the wiki gets them
    found = problems(root, None) + [c for c in contract(root) if c[0] != "CHANGED"]  # kept for older pages; Usage is gone
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
        made = [name for name in pageformat.GENERATED if os.path.exists(os.path.join(root, wiki_dir(root), name + ".md"))]
        for page in sorted(set(rows) | set(made)):
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


def cmd_automation(_args):
    return counting.live(top())


def cmd_prompts(_args):
    """One line per routine: the whole prompt its scheduler holds, a pointer to its Runbook on the repo's page."""
    import deployments
    root = top()
    parts = re.sub(r"(\.git)?/*$", "", git("remote", "get-url", "origin", cwd=root, check=False)).replace(":", "/").split("/")
    repo = "/".join(parts[-2:]) if len(parts) > 1 else os.path.basename(root)
    lines = deployments.prompts(root, repo, wiki_dir(root))
    for routine, text in lines:
        print("PROMPT %s: %s" % (routine, text))
    print("PROMPTS: %d routine(s)" % len(lines))
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
    sub.add_parser("automation").set_defaults(func=cmd_automation)
    sub.add_parser("prompts").set_defaults(func=cmd_prompts)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
