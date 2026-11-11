#!/usr/bin/env python3
"""The Tests renderings (DOC-9 page tables, the DOC-10 full Tests page) from the regression rows, and the file reading
the page format checks (pageformat.py) need. The rendering functions are pure; render() writes.

criteria.py render calls render(); docs.py check calls generated() and front(). Each written file goes to a temp file
renamed into place, printed as WROTE <file>. It runs git and nothing else.
"""
import glob
import os
import re
import sys

import criteria
import pageformat

SCENARIO = re.compile(r"^Given .+, when .+, then .+", re.I)
TESTS = ("Test", "Kind", "Guards", "Checks", "Last result")
FULL = ("Test", "Kind", "Guards", "Result", "Date", "Run", "Seen failing")
FORMAT = os.path.join(os.path.dirname(criteria.SHEET), "..", "..", "workflow-regression", "scripts", "tests.py")  # the one test format


def tests_format(held={}):
    """tests.py, the test format, loaded once; None, with a NOTE, if missing or broken."""
    import importlib.util
    if "m" not in held:
        sys.dont_write_bytecode, held["m"] = True, None
        try:
            spec = importlib.util.spec_from_file_location("regression_tests", FORMAT)
            held["m"] = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(held["m"])
            held["m"].fields, held["m"].issues_of, held["m"].entries  # too old: fall back
        except Exception as err:  # noqa: BLE001
            held["m"] = sys.stderr.write("NOTE: %s not found or broken (%s); Tests use a plain shape\n"
                                         % (os.path.normpath(FORMAT), type(err).__name__)) and None
    return held["m"]


def ran_of(root):
    return {row[0]: (row[1], row[2]) for row in criteria.tsv(root, "regression-runs.tsv")}


def table(root, ids, linked):
    """The Tests section of a page holding the requirements `ids` ((id, text) pairs): pageformat's Tests table."""
    ran, rows, fmt = ran_of(root), {row[0]: row for row in criteria.tsv(root, "regression.tsv")}, tests_format()
    issues = fmt.issues_of(root) if fmt else {}
    fields = (lambda row: fmt.fields(row[:8], {}, ran, issues, True)) if fmt else (lambda row: plain(row, ran))
    return tests_table(ids, linked, criteria.defect_rows(root), rows, fields, ran)


def repo_of(root, text=""):
    """OWNER/REPO from the origin remote, else from a milestone URL in text; '' when neither says."""
    return pageformat.owner_repo(criteria.git("remote", "get-url", "origin", check=False)) or pageformat.owner_repo(text)


def tests_page(root):
    """The full Tests page (DOC-10), from tests.py's entries and the runs file's optional fourth column."""
    fmt = tests_format()
    groups = fmt.entries(root, markdown=True) if fmt else []
    return full_page(groups, {row[0]: row[3] for row in criteria.tsv(root, "regression-runs.tsv")}, repo_of(root))


def maps(root):
    """{skill: its ## Command map text} for each skill in the repo."""
    out = {}
    for path in sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md"))):
        with open(path) as handle:
            out[os.path.basename(os.path.dirname(path))] = handle.read().partition("## Command map")[2].split("\n## ")[0]
    return out


def put(path, text):
    """Write text to a temp file beside path, then rename it into place."""
    temp = "%s.%d.tmp" % (path, os.getpid())
    with open(temp, "w") as handle:
        handle.write(text)
    os.replace(temp, path)


def render(args):
    root = criteria.git("rev-parse", "--show-toplevel")
    linked, _ = criteria.test_rows(root)
    clash = clashes([row[0] for row in criteria.tsv(root, "regression.tsv") if row[1] != "draft"])
    if clash:
        sys.exit("REFUSED: two rows would share one Tests anchor: %s. Fix: rename one row id." % "; ".join(clash))
    stale, out = [], []
    for rel in criteria.pages(root):
        if os.path.basename(rel)[:-3] in pageformat.GENERATED:
            continue
        with open(os.path.join(root, rel)) as handle:
            text = handle.read()
        parts = criteria.sections(text)
        if [n for n, _ in parts if n not in (criteria.rules()["usage"], criteria.rules()["deploy"])] != criteria.rules()["sections"]:
            continue
        ids = [(m.group(1), m.group(4)) for _, m in criteria.criteria_of(dict(parts)[criteria.rules()["sections"][1]]) if m]
        head, _, _ = text.partition("\n## Tests")
        out.append((rel, text, head + "\n## Tests\n\n" + "\n".join(table(root, ids, linked)) + "\n"))
    if out:  # a repo with feature pages gets the full Tests page
        rel = os.path.join(criteria.folder_of(root), "Tests.md")
        try:
            with open(os.path.join(root, rel)) as handle:
                held = handle.read()
        except OSError:
            held = None
        out.append((rel, held, tests_page(root)))
    for rel, text, fresh in out:
        if fresh != text:
            stale.append(rel)
            if not args.check:
                put(os.path.join(root, rel), fresh)
    for rel in stale:
        print("%s %s" % ("STALE" if args.check else "WROTE", rel))
    if not stale:
        print("TABLES OK")
    return 1 if stale and args.check else 0


def read(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return None


def generated(root):
    """(STALE, Tests, first differing line) when the full Tests page differs from a fresh render (DOC-10)."""
    rel = os.path.join(criteria.folder_of(root), "Tests.md")
    held = read(os.path.join(root, rel))
    if held is None:
        return [("STALE", "Tests", "no %s. Fix: /workflow-docs render" % rel)]
    have, want = held.splitlines(), tests_page(root).splitlines()
    for number in range(max(len(have), len(want))):
        got, fresh = (have + [""] * len(want))[number], (want + [""] * len(have))[number]
        if got != fresh:
            return [("STALE", "Tests", "line %d is %s, a fresh render has %s. Fix: /workflow-docs render"
                     % (number + 1, pageformat.short(got), pageformat.short(fresh)))]
    return []


def front(root, names):
    """DOC-4 on Home and DOC-5 on the README front door, for these feature pages."""
    on, folder, out = criteria.rules()["format"], os.path.join(root, criteria.folder_of(root)), []
    readme, home = read(os.path.join(root, "README.md")) or "", read(os.path.join(folder, "Home.md"))
    if "home" in on and home is not None:
        existing = {name[:-3] for name in os.listdir(folder) if name.endswith(".md")}
        out += pageformat.home(home, names, existing, readme, repo_of(root, home))
    if "frontdoor" in on and names:
        out += pageformat.frontdoor(readme, names)
    return out


def test_slug(name):
    return re.sub(r"[^a-z0-9-]", "-", name.lower())


def checks_cell(text):
    return text if SCENARIO.match(text) else text + " (not yet Given/When/Then)"


def plain(row, ran):
    """The fields tests.py would give, for when it is missing: test, kind, guards, checks, runs, result, seen."""
    status, day = ran.get(row[0], ("not run", ""))
    guard = row[7] if row[6] == "defect" else row[3]
    return [row[0], "defect" if row[6] == "defect" else "requirement", guard or "-", row[5] or "-", row[1], (status + " " + day).strip(),
            row[4] if re.match(r"^\d{4}-\d\d-\d\d$", row[4]) else "no"]


def tests_table(ids, linked, defects, rows, fields, ran):
    """A feature page's Tests: one TESTS table, each requirement's rows (a 'not enforced' row when none passes), then
    its defect rows. `fields(row)` is tests.py's one format for a row."""
    out = []
    for key, _ in ids:
        names = linked.get(key, [])
        for name in names:
            out.append(fields(rows[name]))
        if not any(ran.get(name, ("",))[0] == "PASS" for name in names):
            out.append(["-", "requirement", key, "no passing test", "", "not enforced"])
    out += [fields(rows[name]) for key, _ in ids for name in defects.get(key, [])]
    shown = [[x[0] if x[0] == "-" else "[%s](Tests#t-%s)" % (x[0], test_slug(x[0])), x[1], x[2],
              x[3] if x[0] == "-" else checks_cell(x[3]), x[5]] for x in out]
    return pageformat.table(TESTS, shown) if shown else []


def run_cell(value, repo, day=""):
    """A URL is its Actions run; an empty cell links that day's CI runs of the regression workflow; an old sha cell
    links its commit; else local."""
    if re.match(r"^https?://\S+$", value):
        return "[run](%s)" % value
    if re.match(r"^[0-9a-f]{7,40}$", value):  # an old cell, from before empty run cells
        return "[%s](https://github.com/%s/commit/%s)" % (value[:7], repo, value) if repo else value[:7]
    if not value and repo and re.match(r"^\d{4}-\d\d-\d\d$", day):
        return "[CI %s](https://github.com/%s/actions/workflows/regression.yml?query=created%%3A%s)" % (day, repo, day)
    return "local"


def full_page(groups, runs, repo):
    """docs/wiki/Tests.md: the marker, '# Tests', then per feature '## <Feature>' and a FULL table whose first cell
    carries the anchor the feature pages link to. `groups` is tests.py's entries(); `runs` maps a row to its run."""
    out = [pageformat.MARKER, "# Tests", ""]
    for feature, lines in groups:
        rows = []
        for x in lines:
            result = re.match(r"^(\S+) (\d{4}-\d\d-\d\d)$", x[5])
            guard = x[2].split(": ", 1)[0] if x[1] == "requirement" else x[2]  # the ID; its words are on its page
            rows.append(['<a id="t-%s"></a>%s' % (test_slug(x[0]), x[0]), x[1], guard, result.group(1) if result else x[5],
                         result.group(2) if result else "-", run_cell(runs.get(x[0], ""), repo,
                         result.group(2) if result else ""), x[6]])
        out += ["## " + feature, ""] + pageformat.table(FULL, rows) + [""]
    return "\n".join(out if groups else out + ["No tests yet.", ""])


def clashes(names):
    """Row ids whose anchors collide, as 'a and b share t-x' strings."""
    seen, out = {}, []
    for name in names:
        key = test_slug(name)
        if key in seen and seen[key] != name:
            out.append("%s and %s share t-%s" % (seen[key], name, key))
        seen.setdefault(key, name)
    return out
