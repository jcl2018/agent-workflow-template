#!/usr/bin/env python3
"""The numbers the docs state that the repo can check: skills, feature pages, and a feature page's criteria and tests.

docs.py check, audit and publish call counts() through docs.counts(root). prose() is the text a reader sees: no fenced
or indented code, comments or code spans. The page map of docs.py (map_path, read_map, write_map)
and real(), which drops block-only commits from its staleness, sit at the end.
"""
import glob
import os
import re
import subprocess

import criteria
import pageformat

WORDS = "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
NOUNS = {"skill": "skill", "skills": "skill", "feature page": "page", "feature pages": "page", "criterion": "criteria",
         "criteria": "criteria", "test": "test", "tests": "test"}
# One word may sit between the number and the noun, but only a word meaning "all of them" ("eight workflow-ready
# skills"); any other word ("two delivery skills", "3 regression tests") is a part or a label, so nothing is read.
# "defect" is the one part read: "2 defect tests" is checked against the page's defect tests.
ALL = r"workflow(?:-ready)?|installed|available|bundled|shipped|listed|defect"
CLAIM = re.compile(r"(?<![-\w.,/#])(\d+|%s)[ \t]+(?:(%s)[ \t]+)?(skills?|feature pages?|criteri(?:on|a)|tests?)\b"
                   % ("|".join(WORDS), ALL), re.I | re.ASCII)
FENCE = re.compile(r"^ {0,3}(`{3,}(?=[^`]*$)|~{3,})(.*)$")
QUOTE = re.compile(r"^(?: {0,3}> ?)+")
BREAK = re.compile(r"^ {0,3}([-*_])(?: *\1){2,} *$")  # a thematic break, not a list item
ITEM = re.compile(r"^( *)([-*+]|\d{1,9}[.)])( +(?=\S)|\s*$)")
NOT_A_COUNT = "<!-- not-a-count -->"
BOUND = re.compile(r"\b(up to|at most|at least|no more than|more than|fewer than|over|under)\s*$", re.I)
ID = re.compile(r"\b[A-Z]{2,5}-\d+\b")


def prose(text):
    """The lines a reader sees as prose: no fenced or indented code, comments or code spans; None if a fence never
    closes. Indented code is CommonMark's: four columns past the list item's text (or the margin), after a blank line;
    a code line stays as an empty line so the paragraphs around it stay apart."""
    lines, fence, comment, blank, code, column = [], None, False, True, False, None
    for raw in text.splitlines():
        line = QUOTE.sub("", raw)
        was_blank, blank = blank, not line.strip()
        opener = FENCE.match(line)
        if fence is not None:
            if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence) and not opener.group(2).strip():
                fence, blank = None, True  # indented code may follow a closing fence
            continue
        flat = line.expandtabs(4)
        indent = len(flat) - len(flat.lstrip(" "))
        if not blank and not comment:
            code = indent >= (column or 0) + 4 and (was_blank or code)
            if code:
                lines.append("")
                continue
            item = None if BREAK.match(flat) else ITEM.match(flat)
            if BREAK.match(flat) and indent < 4:
                column = None
            elif item and indent < (column or 0) + 4:
                gap = len(item.group(3)) if flat[item.end():].strip() else 0  # marker, then 1-4 spaces to the text
                column = len(item.group(1) + item.group(2)) + (gap if 0 < gap <= 4 else 1)
            elif indent == 0 and (was_blank or opener or re.match(r"[#|]", flat)):
                column = None  # a paragraph, heading, fence or table at the margin ends the list
        if opener and not comment:
            fence, code = opener.group(1), False
            continue
        line = re.sub(r"(`+)(?!`).*?(?<!`)\1(?!`)", "", line)  # code spans of any backtick length
        marked = NOT_A_COUNT in line
        if comment:
            end = line.find("-->")
            comment, line = (True, "") if end < 0 else (False, line[end + 3:])
        line = re.sub(r"<!--.*?-->", "", line)
        if "<!--" in line:
            comment, line = True, line[:line.index("<!--")]
        lines.append(line + (" " + NOT_A_COUNT if marked else ""))
        blank = blank or bool(re.match(r" {0,3}#{1,6}(\s|$)", flat))  # indented code may follow a heading
    return lines if fence is None else None


def text_of(path):
    with open(path, encoding="utf-8", errors="replace") as handle:
        return handle.read()


def counts(root, folder, rows, on):
    """Numbers the docs state that the repo can check, as (COUNT, file, detail) rows. `folder` is the wiki folder,
    `rows` the page map (.loop/docs.tsv) and `on` the criteria setting."""
    real_root = os.path.realpath(root)
    skills = len(glob.glob(os.path.join(root, "skills", "*", "SKILL.md")))
    pages = [p for p in rows if p != "Home" and p not in pageformat.GENERATED and os.path.exists(os.path.join(root, folder, p + ".md"))
             and not pageformat.is_guide(text_of(os.path.join(root, folder, p + ".md")))]
    linked = criteria.test_rows(root)[0] if on else {}
    defects = criteria.defect_rows(root) if on else {}
    names = ["README.md"]
    wiki = os.path.join(root, folder)
    if os.path.isdir(wiki):
        names += ["%s/%s" % (folder, n) for n in sorted(os.listdir(wiki)) if n.endswith(".md") and n[:-3] not in pageformat.GENERATED]
    names += sorted(os.path.relpath(n, root) for n in glob.glob(os.path.join(root, "skills", "*.md")))
    texts, ids = {}, {}
    for rel in names:
        full = os.path.realpath(os.path.join(root, rel))
        if full.startswith(real_root + os.sep) and os.path.isfile(full):  # only regular files inside the repo
            with open(full, encoding="utf-8", errors="replace") as handle:
                texts[rel] = handle.read()
            page = os.path.basename(rel)[:-3] if rel.startswith(folder + "/") else ""
            if on and page in pages:
                part, keep = [], False  # the Requirements section, read with prose()'s code rules
                for line in prose(texts[rel]) or []:
                    keep = bool(re.match(r"##\s+(Requirements|Criteria)\s*$", line)) or (keep and not line.startswith("## "))
                    part += [line] if keep else []
                ids[rel] = [m.group(1) for _, m in criteria.criteria_of(part) if m]
    known = set(i for found in ids.values() for i in found)
    found = []
    for rel, text in texts.items():
        lines = prose(text)
        if lines is None:
            found.append(("COUNT", rel, "a code fence never closes, so its counts can't be read"))
            continue
        mine = ids.get(rel)
        own = set(mine or [])
        real = {"skill": skills or None, "page": len(pages) if on else None,
                "criteria": len(mine) if mine is not None else None,
                "test": sum(len(linked.get(i, [])) + len(defects.get(i, [])) for i in mine) if mine is not None else None,
                "defect": sum(len(defects.get(i, [])) for i in mine) if mine is not None else None}
        # A line naming this file's own criterion is about that criterion: skipped whole. A line naming another page's
        # criterion still has its skills and pages counts read; its criteria and tests counts are about that one.
        alone = lambda s: NOT_A_COUNT in s or own.intersection(ID.findall(s))
        other = lambda s: known.intersection(ID.findall(s))
        paras = []
        for line in lines:  # soft-wrapped lines joined; a skipped line stays alone, so its skip covers only itself
            new = not paras or not line.strip() or re.match(r"\s*([|#]|$)", paras[-1]) or re.match(r"\s*([-*+|#>]|\d+\.)", line)
            new = new or alone(line) or alone(paras[-1]) or other(line) or other(paras[-1])
            paras.append(line) if new else paras.__setitem__(-1, paras[-1] + " " + line.strip())
        for line in paras:
            if alone(line):
                continue  # marked, or about one of this page's criteria
            for match in CLAIM.finditer(line):
                said, word, noun = match.group(1).lower(), (match.group(2) or "").lower(), match.group(3).lower()
                if BOUND.search(line[:match.start()]):  # "up to 6 criteria" is a limit, not a count
                    continue
                if said == "one":  # "one test" is nearly always "a single test", not a count
                    continue
                said = int(said) if said.isdigit() else WORDS.index(said) + 1
                if said != 1 and noun in ("skill", "feature page", "test", "criterion"):
                    continue  # a singular noun after a number above one is a compound, as in "two test doubles"
                kind = NOUNS[noun]
                if word == "defect":
                    if kind != "test":
                        continue
                    kind = "defect"
                if kind in ("criteria", "test", "defect") and other(line):
                    continue  # about another page's criterion
                want = real[kind]
                if want is not None and said != want:
                    found.append(("COUNT", rel, "says %s, the repo has %d" % (match.group(0), want)))
    return found


# The page map of docs.py, moved here unchanged (size); docs.py imports it back.
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


BLOCK = re.compile(r"<!-- (settings|automation|template):begin -->\n.*?<!-- \1:end -->\n", re.S)  # render.py's blocks


def real(root, changed, paths):
    """changed ('<sha> <subject>' lines) without the commits whose change to paths lies only inside the generated
    blocks of README.md or a Home.md: a block refresh (or setup's insert) says nothing about the pages mapped there."""
    if not changed:
        return changed
    git = lambda *a: subprocess.run(["git", "-C", root] + list(a), capture_output=True, text=True)  # noqa: E731
    names = {}  # one git call for every commit's files
    for chunk in git("log", "--no-walk=unsorted", "--no-renames", "--format=%x01%h", "--name-only",
                     *[c.split()[0] for c in changed], "--", *paths).stdout.split("\x01")[1:]:
        sha, *files = chunk.strip("\n").split("\n")
        names[sha] = [f for f in files if f]

    def blocks_only(sha, rel):
        old, new = git("show", "%s^:%s" % (sha, rel)), git("show", "%s:%s" % (sha, rel))
        bare = lambda t: re.sub(r"\n{3,}", "\n\n", BLOCK.sub("", t)).strip()  # noqa: E731 an insert leaves a blank line
        return not old.returncode and not new.returncode and bare(old.stdout) == bare(new.stdout)

    return [c for c in changed if not (names.get(c.split()[0]) and all(
        os.path.basename(rel) in ("README.md", "Home.md") and blocks_only(c.split()[0], rel) for rel in names[c.split()[0]]))]
