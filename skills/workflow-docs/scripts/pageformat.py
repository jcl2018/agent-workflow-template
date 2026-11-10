#!/usr/bin/env python3
"""The page format (DOC-4..DOC-10): the checks docs.py check runs on Home, the README front door and each feature
page. Pure: text and data in, lines or findings out; it reads no file and runs nothing.

A finding is ("FORMAT", "<Page>:<line>", "<Section>: DOC-n <what> (got <value>). Fix: <how>"). Which checks run is the
`format` key of the template sheet's rules block (CHECKS, default all). The words of a line are its whitespace tokens
after `[text](url)` becomes text and backticks are stripped; one sentence means no `[.!?] ` followed by a capital.
"""
import re

GENERATED = {"Tests"}  # pages render writes; never mapped to paths, never a feature page
CHECKS = ("home", "frontdoor", "usage", "bullets", "problem", "tests")
BANNED = "script, function, regex, json, tsv, stdout"
MARKER = "<!-- workflow-docs -->"
HOME = ("Feature", "What it does", "How to use", "Milestone")
FRONT = ("You say", "What happens")
RULE = re.compile(r"^\|(\s*:?-+:?\s*\|)+$")
PATH = re.compile(r"(?<![\w/])/[\w.-]+/")
EXT = re.compile(r"\.(py|sh|json|tsv|md)\b")
ME = re.compile(r"\b(I|[Mm]y|[Mm]e)\b")
ENTRY = re.compile(r"^### `([^`]+)`$")
LABEL = re.compile(r"^- (Prints|Refuses|Does|Arguments): \S")


def bad(page, line, section, rule, what, got, fix):
    return ("FORMAT", "%s:%d" % (page, line), "%s: DOC-%d %s (got %s). Fix: %s" % (section, rule, what, got, fix))


def short(text):
    text = " ".join(str(text).split())
    return "'%s'" % (text if len(text) <= 60 else text[:57] + "...")


def words(text):
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).replace("`", "").split()


def sentences(text):
    return len(re.findall(r"[.!?] (?=[A-Z])", " ".join(words(text)))) + 1


def slug(text):
    """GitHub's heading anchor: lower case, punctuation dropped, spaces to dashes."""
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


def owner_repo(text):
    """OWNER/REPO from a GitHub remote or milestone URL, or ''."""
    found = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?(?:/milestone/\d+|/?$)", text.strip(), re.M)
    return found.group(1) if found else ""


def parts(text):
    """[(name, line number, [(number, line)])] for the head ('') and each level-2 section outside fences."""
    out, fenced = [("", 1, [])], False
    for number, line in enumerate(text.splitlines(), 1):
        fenced = fenced != line.startswith("```")
        if not fenced and line.startswith("## "):
            out.append((line[3:].strip(), number, []))
        else:
            out[-1][2].append((number, line))
    return out


def cells(line):
    return [item.strip() for item in re.split(r"(?<!\\)\|", line.strip()[1:-1])]


def table(header, rows):
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(x) + " |" for x in rows]


def tables(numbered):
    """[(line, header cells, [(line, cells)])] per run of '|' lines, and the other lines."""
    found, other, last = [], [], None
    for number, line in numbered:
        if line.startswith("|"):
            if last != number - 1:
                found.append((number, cells(line), []))
            elif not RULE.match(line.strip()) or found[-1][2]:
                found[-1][2].append((number, cells(line)))
            last = number
        elif line.strip():
            other.append((number, line))
    return found, other


def heading_of(page):
    return "How to use " + page.replace("-", " ")


def anchors(readme):
    return {slug(line[4:]) for name, _, lines in parts(readme) if name == "How to use"
            for _, line in lines if line.startswith("### How to use ")}


def home(text, features, existing, readme, repo):
    """DOC-4: the marker, '# title', '## Features' and one table HOME, one row per feature page, nothing else."""
    out, seen, keys = [], [], anchors(readme)
    lines = list(enumerate(text.splitlines(), 1))
    body = [(n, x) for n, x in lines if x.strip() and x.strip() != MARKER]
    found, other = tables([(n, x) for n, x in lines if not x.startswith(("# ", "## Features")) and x.strip() != MARKER])
    if not body or not body[0][1].startswith("# ") or "## Features" not in [x.strip() for _, x in body]:
        out.append(bad("Home", 1, "Features", 4, "Home is the marker, '# title' and '## Features'", short(body[0][1] if body else ""),
                       "write '# <repo>', then '## Features', then the features table"))
    for number, line in other:
        out.append(bad("Home", number, "Features", 4, "a line outside the features table", short(line), "move it to the README or a feature page"))
    if len(found) != 1 or tuple(found[0][1]) != HOME:
        return out + [bad("Home", found[0][0] if found else 1, "Features", 4, "one table with the header | %s |" % " | ".join(HOME),
                          "%d tables%s" % (len(found), ", header " + short(" | ".join(found[0][1])) if found else ""),
                          "use exactly that header, in one table")]
    for number, row in found[0][2]:
        page = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", row[0]) if len(row) == 4 else None
        if not page or page.group(1) != page.group(2) or page.group(1) not in existing:
            out.append(bad("Home", number, "Features", 4, "the Feature cell links an existing page as [X](X)", short(row[0]),
                           "name a page from .loop/docs.tsv"))
            continue
        name = page.group(1)
        seen.append(name)
        if name not in features:
            out.append(bad("Home", number, "Features", 4, "a row for a page that is not a feature page", name, "remove the row"))
        link = re.match(r"^\[[^\]]+\]\(https://github\.com/([\w.-]+/[\w.-]+)#([\w-]+)\)$", row[2])
        want = slug(heading_of(name))
        if not link or (repo and link.group(1).lower() != repo.lower()) or link.group(2) != want or want not in keys:
            out.append(bad("Home", number, "Features", 4, "How to use links the README's '### %s' section" % heading_of(name),
                           short(row[2]), "link [README](https://github.com/%s#%s) and add that README heading" % (repo or "OWNER/REPO", want)))
        if not re.search(r"/milestone/\d+", row[3]):
            out.append(bad("Home", number, "Features", 4, "Milestone links the feature's milestone", short(row[3]),
                           "link https://github.com/%s/milestone/N" % (repo or "OWNER/REPO")))
    for name in features:
        if seen.count(name) != 1:
            out.append(bad("Home", found[0][0], "Features", 4, "one row per feature page", "%d rows for %s" % (seen.count(name), name),
                           "give %s exactly one row" % name))
    return out


def frontdoor(readme, features):
    """DOC-5: '## How to use' holds one '### How to use <Feature>' per feature page, each an intro line and a FRONT
    table of quoted phrases."""
    held = [(n, lines) for name, n, lines in parts(readme) if name == "How to use"]
    if not held:
        return [bad("README", 1, "How to use", 5, "the README has a '## How to use' section", "none",
                    "add it, with one '### How to use <Feature>' per feature page")]
    start, lines = held[0]
    groups, out = [("", start, [])], []
    for number, line in lines:
        if line.startswith("### "):
            groups.append((line[4:].strip(), number, []))
        else:
            groups[-1][2].append((number, line))
    names = [name for name, _, _ in groups[1:]]
    for page in features:
        if names.count(heading_of(page)) != 1:
            out.append(bad("README", start, "How to use", 5, "one '### %s' section" % heading_of(page),
                           "%d" % names.count(heading_of(page)), "add it, with a | You say | What happens | table"))
    for name, number, body in groups:
        found, other = tables(body)
        if name and name not in [heading_of(p) for p in features]:
            out.append(bad("README", number, "How to use", 5, "a section named for a feature page", short(name),
                           "name it '### How to use <Feature>'"))
        for at, line in other[1:]:
            out.append(bad("README", at, "How to use", 5, "only one intro line per section", short(line), "move it out of How to use"))
        if not name:
            continue
        if len(found) != 1 or tuple(found[0][1]) != FRONT or not found[0][2]:
            out.append(bad("README", number, name, 5, "one table | You say | What happens | with at least one row",
                           "%d tables" % len(found), "say what the owner says and what happens next"))
            continue
        for at, row in found[0][2]:
            said = row[0]
            if "`" in said or not re.match(r'^"[^"]+"(\s*/\s*"[^"]+")*$', said) or re.match(r'^"?\s*(/|python|bash)', said):
                out.append(bad("README", at, name, 5, "You say is a quoted phrase, not a command", short(said),
                               "write what the owner says, in quotes, with no backticks"))
    return out


def known(syntax, maps, own):
    """Whether a Usage heading's command is in a Command map: a '/skill verb' in that skill's, else its first word
    (or the routine after python3/bash) in one of the page's skills' maps (either column)."""
    ask = re.match(r"/([\w-]+)\s+([\w-]+)", syntax)
    if ask:
        return bool(re.search(r"`/%s %s[ `]" % (re.escape(ask.group(1)), re.escape(ask.group(2))), maps.get(ask.group(1), "")))
    tokens = syntax.split()
    word = tokens[1] if tokens[0] in ("python3", "python", "bash", "sh") and len(tokens) > 1 else tokens[0]
    word = word.rsplit("/", 1)[-1]
    texts = [maps[k] for k in own if k in maps] or list(maps.values())
    return any(re.search(r"(?<![\w.-])%s(?![\w.-])" % re.escape(word), text) for text in texts)


def usage(page, name, lines, maps, own):
    """DOC-6: only '### `syntax`' entries, each with '- Prints:' and '- Refuses:' ('- Does:' and '- Arguments:'
    optional), nothing else but blank lines; each command is in its skill's Command map."""
    out, entry = [], None

    def close():
        if entry:
            for label in ("Prints", "Refuses"):
                if label not in entry[2]:
                    out.append(bad(page, entry[0], name, 6, "each entry has a '- %s:' bullet" % label, short(entry[1]),
                                   "add '- %s: ...' under it" % label))
    for number, line in lines:
        if not line.strip():
            continue
        head, label = ENTRY.match(line), LABEL.match(line)
        if head:
            close()
            entry = (number, head.group(1), set())
            if not known(head.group(1), maps, own):
                out.append(bad(page, number, name, 6, "the command is in its skill's Command map", short(head.group(1)),
                               "use a command from the skill's ## Command map"))
        elif label and entry:
            entry[2].add(label.group(1))
        else:
            out.append(bad(page, number, name, 6, "only ### `syntax` entries and Prints/Refuses/Does/Arguments bullets",
                           short(line), "write it as one of those, or remove it"))
    close()
    return out


GROUPS = ["Functional", "Non-functional"]


def bullets(page, name, lines, line_re, strict, groups_want=GROUPS):
    """DOC-7: Requirements is '### Functional' then '### Non-functional', each holding requirement lines with their
    '  - ' sub-bullets, or the single line 'None'. An orphan or deeper sub-bullet is always refused; with strict, the
    groups are checked, each requirement has a sub-bullet of one sentence of at most 30 words, and an Unreviewed line
    is at most 20 words (a Reviewed one is locked by DOC-2)."""
    out, held, groups = [], [], []
    say = lambda number, what, got, fix: out.append(bad(page, number, name, 7, what, short(got), fix))
    for number, line in lines:
        if not line.strip():
            continue
        if line.startswith("### "):
            groups.append([number, line[4:].strip(), 0, 0])
            held.append((number, None, []))  # a heading ends the requirement above
        elif line.startswith("  - ") and held and held[-1][1]:
            held[-1][2].append((number, line[4:]))
        elif line.startswith("  - ") or line[:1].isspace():
            say(number, "a sub-bullet is '  - ' (two spaces) right under a requirement line", line,
                "indent it by exactly two spaces under its requirement")
        elif strict and (not groups or (line.strip() != "None" and not line_re.match(line))):
            say(number, "only requirement lines, their sub-bullets or 'None' under ### Functional and ### Non-functional",
                line, "move it into a requirement, or remove it")
        else:
            held.append((number, line_re.match(line), []))
            if groups:
                groups[-1][3 if line.strip() == "None" else 2] += 1
    if strict and [g[1] for g in groups] != groups_want:
        say(groups[0][0] if groups else 1, "Requirements is '### Functional' then '### Non-functional'",
            ", ".join(g[1] for g in groups) or "none", "group the requirements under exactly those two headings, in order")
    for number, title, reqs, nones in groups if strict else []:
        if (reqs and nones) or nones > 1 or not (reqs or nones):
            say(number, "a group holds requirements or the single line 'None'", "%d requirements, %d None" % (reqs, nones),
                "write 'None' alone when %s has no requirement" % title)
    for number, match, subs in held if strict else []:
        if not match:
            continue
        if not subs:
            say(number, "%s has at least one sub-bullet" % match.group(1), "none", "split its wording into '  - ' bullets under it")
        if match.group(2) == "Unreviewed" and len(words(match.group(4))) > 20:
            say(number, "an Unreviewed requirement line is at most 20 words", "%d words" % len(words(match.group(4))),
                "make it a title and move the detail into sub-bullets")
        for at, text in subs:
            if len(words(text)) > 30 or sentences(text) > 1:
                say(at, "a sub-bullet is one sentence of at most 30 words", "%d words, %d sentences" % (len(words(text)), sentences(text)),
                    "split it into more bullets")
    return out


def problem(page, name, lines, most, banned):
    """DOC-8: 1 to `most` bullets, one in the first person, with no code: no backticks, paths, file extensions or
    banned words."""
    out, said = [], [(n, x) for n, x in lines if x.strip()]
    first = said[0][0] if said else 1
    for number, line in said:
        if not line.startswith("- "):
            out.append(bad(page, number, name, 8, "each line is a '- ' bullet", short(line), "write it as a bullet"))
        hit = ("`" in line and "`") or (PATH.search(line) or EXT.search(line) or [None])[0] or next(
            (w for w in banned if re.search(r"\b%s\b" % re.escape(w), line, re.I)), None)
        if hit:
            out.append(bad(page, number, name, 8, "the problem is said without code internals", short(hit),
                           "say what goes wrong for the person, not how the code works"))
    if not 1 <= len(said) <= most:
        out.append(bad(page, first, name, 8, "1 to %d bullets" % most, "%d lines" % len(said), "say the problem in 1 to %d bullets" % most))
    if said and not any(ME.search(line) for _, line in said):
        out.append(bad(page, first, name, 8, "at least one bullet in the first person (I, my, me)", "none",
                       "say it from the user's side: 'I can't ...'"))
    return out


def stale(page, name, start, lines, fresh):
    """DOC-9: the first line where the Tests section differs from a fresh render, as a TESTS finding, or None."""
    have = [(n, x) for n, x in lines if x.strip()] + [(start, "end")]
    want = [x for x in fresh if x.strip()]
    at = next((i for i, line in enumerate(want + [None]) if i >= len(have) - 1 or have[i][1] != line), None)
    if at is None or (at == len(want) and len(have) - 1 == len(want)):
        return None
    return ("TESTS", "%s:%d" % (page, have[at][0]), "%s: DOC-9 the table differs from a fresh render (got %s). "
            "Fix: /workflow-docs render" % (name, short(have[at][1])))
