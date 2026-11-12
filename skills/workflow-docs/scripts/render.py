#!/usr/bin/env python3
"""The Tests renderings (DOC-9 page tables, the DOC-10 full Tests page) from the regression rows, and the file reading
the page format checks (pageformat.py) need. The rendering functions are pure; render() writes.

criteria.py render calls render(); docs.py check calls generated() and front(). Each written file goes to a temp file
renamed into place, printed as WROTE <file>. It runs git and nothing else.
"""
import glob
import json
import os
import re
import subprocess
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
    """{row: (status, date, " FLAKY" when its 5th cell names the commit a result flipped on, REG-9)}."""
    return {row[0]: (row[1], row[2], " FLAKY" if (row + [""] * 5)[4] else "") for row in criteria.tsv(root, "regression-runs.tsv")}


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
    for where, name in refresh(root, args.check):
        stale.append("%s (%s block)" % (where, name))
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
    status, day = ran.get(row[0], ("not run", ""))[:2]
    guard = row[7] if row[6] == "defect" else row[3]
    return [row[0], row[6] if row[6] in ("defect", "workflow") else "requirement", guard or "-", row[5] or "-", row[1], (status + " " + day).strip(),
            row[4] if re.match(r"^\d{4}-\d\d-\d\d$", row[4]) else "no"]


def tests_table(ids, linked, defects, rows, fields, ran):
    """A feature page's Tests: one TESTS table in three parts: each requirement's rows (a 'not enforced' row when none
    passes), then the workflow tests (category workflow, REG-1), then the defect tests, each part in requirement order.
    `fields(row)` is tests.py's one format for a row."""
    out, flows = [], []
    for key, _ in ids:
        names = linked.get(key, [])
        for name in names:
            (flows if rows[name][6] == "workflow" else out).append(fields(rows[name]))
        if not any(ran.get(name, ("",))[0] == "PASS" for name in names):
            out.append(["-", "requirement", key, "no passing test", "", "not enforced"])
    out += flows + [fields(rows[name]) for key, _ in ids for name in defects.get(key, [])]
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


# --- the Settings and Automation blocks on Home, and the README's template line (generated, marked, kept fresh)
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATE_REPO = "jcl2018/agent-workflow-template"  # last resort when the install's origin names no GitHub repo
MARKS = ("settings", "automation", "template")


def block_re(name):
    return re.compile(r"<!-- %s:begin -->\n.*?<!-- %s:end -->\n" % (name, name), re.S)


def config_of(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            held = json.load(handle)
        return held if isinstance(held, dict) else {}
    except (OSError, ValueError):
        return {}


def reference():
    """[(name, default, meaning)] from `settings.py reference`, the repo settings table; [] when it can't be read."""
    path = os.path.join(SKILLS, "workflow-setup", "scripts", "settings.py")
    done = subprocess.run([sys.executable, path, "reference"], capture_output=True, text=True) if os.path.exists(path) else None
    rows, on = [], False
    for line in (done.stdout.splitlines() if done and done.returncode == 0 else []):
        if line.startswith("## "):
            on = line.strip() == "## Repo settings"
        found = re.match(r"^\| `(\w+)` \| (.+?) \| (.+) \|$", line) if on else None
        if found:
            rows.append((found.group(1), found.group(2).strip("`"), found.group(3)))
    return rows


def parsed(text):
    if text == "(empty)":
        return ""
    try:
        return json.loads(text)
    except ValueError:
        return text


def shown(value):
    return "(empty)" if value == "" else (value if isinstance(value, str) else json.dumps(value))


def settings_block(root):
    cfg, rows = config_of(root), []
    for name, default, meaning in reference():
        over = name in cfg and cfg[name] != parsed(default)
        rows.append(["`%s`" % name, meaning, 'set "%s" in .loop/config.json' % name, "`%s`" % default,
                     "**overridden:** `%s`" % shown(cfg[name]) if over else "default"])
    head = ["Name", "What it means", "How to set it", "Default", "This repo"]
    body = pageformat.table(head, rows) if rows else ["The settings reference is not installed here."]
    return "\n".join(["<!-- settings:begin -->", "## Settings", "",
                       "Every repo setting, from the template's settings reference and this repo's `.loop/config.json`.", ""]
                      + body + ["<!-- settings:end -->", ""])


def cadence(cron):
    if cron == "off":
        return "off"
    f = cron.split()
    if len(f) == 5 and f[2:] == ["*", "*", "*"]:
        if f[1].startswith("*/") and f[1][2:].isdigit():
            return "every %s hours" % f[1][2:]
        if f[0].isdigit() and f[1].isdigit():
            return "daily at %02d:%02d" % (int(f[1]), int(f[0]))
        if f[1] == "*" and f[0].startswith("*/") and f[0][2:].isdigit():
            return "every %s minutes" % f[0][2:]
    return "cron `%s`" % cron


def last_run(root):
    days = sorted(row[2] for row in criteria.tsv(root, "regression-runs.tsv") if len(row) > 2)
    return days[-1] if days else "unknown"


def automation_block(root):
    cfg, rows = config_of(root), []
    flows = os.path.join(root, ".github", "workflows")
    for name, key, default, flow, last in (("health", "health_cron", "47 */4 * * *", "health.yml", "unknown"),
                                         ("regression", "regression_cron", "17 */4 * * *", "regression.yml", last_run(root))):
        cron = str(cfg.get(key, default))
        there = os.path.exists(os.path.join(flows, flow))
        owed = "" if cron == "off" or there else "run workflow-setup to write .github/workflows/" + flow
        rows.append([name, "off" if cron == "off" else "on", cadence(cron), "GitHub Actions" if there else "not deployed", last, owed or "none"])
    mail = str(cfg.get("digest_mail", "cloudflare"))
    there = os.path.exists(os.path.join(flows, "health.yml"))
    rows.append(["digest email", "off" if mail == "off" else "on (%s)" % mail,
                 "with each health round" if mail != "off" else "off", "GitHub Actions" if there else "not deployed", "unknown",
                 "set the digest address and keys as Actions secrets (yours, outside git)" if mail != "off" else "none"])
    for command in cfg.get("routines") or []:
        rows.append(["`%s`" % command, "on", "before each release merge", "this Mac (the release step)", "unknown", "none"])
    head = ["Routine", "State", "Cadence", "Runs on", "Last run", "Owed by you"]
    return "\n".join(["<!-- automation:begin -->", "## Automation", "",
                       "Each routine, from `.loop/config.json`, the workflow files and the regression runs file.", ""]
                      + pageformat.table(head, rows) + ["<!-- automation:end -->", ""])


def template_line(root):
    repo = config_of(root).get("template_repo")
    if not repo:
        done = subprocess.run(["git", "-C", SKILLS, "remote", "get-url", "origin"], capture_output=True, text=True)
        repo = pageformat.owner_repo(done.stdout) if done.returncode == 0 else ""
    repo = repo if repo and re.match(r"^[\w.-]+/[\w.-]+$", str(repo)) else TEMPLATE_REPO
    return "<!-- template:begin -->\nBuilt with the [%s](https://github.com/%s) workflow loop.\n<!-- template:end -->\n" % (repo, repo)


def with_blocks(text, blocks):
    """text with each (name, block) put in place: replaced where its markers are, else appended (the template line
    goes after the first paragraph)."""
    for name, block in blocks:
        pattern = block_re(name)
        if pattern.search(text):
            text = pattern.sub(lambda _: block, text, 1)
        elif name == "template":
            head, sep, rest = text.partition("\n\n")
            text = head + "\n\n" + block + ("\n" + rest if sep else "")
        else:
            text = text.rstrip("\n") + "\n\n" + block
    return text


def front_files(root):
    """[(rel, blocks)] for Home and the README, when they exist."""
    out = []
    home = os.path.join(criteria.folder_of(root), "Home.md")
    if os.path.exists(os.path.join(root, home)):
        out.append((home, [("settings", settings_block(root)), ("automation", automation_block(root))]))
    if os.path.exists(os.path.join(root, "README.md")):
        out.append(("README.md", [("template", template_line(root)), ("settings", settings_block(root)),
                                  ("automation", automation_block(root))]))
    return out


def refresh(root, check=False):
    """Write the blocks (or with check, only list what differs): [(rel, name)] of the blocks that were stale."""
    stale = []
    for rel, blocks in front_files(root):
        held = read(os.path.join(root, rel)) or ""
        for name, block in blocks:
            found = block_re(name).search(held)
            if not found or found.group(0) != block:
                stale.append((rel, name))
        fresh = with_blocks(held, blocks)
        if fresh != held and not check:
            put(os.path.join(root, rel), fresh)
    return stale


def stale_blocks(root):
    """(STALE, Settings|Automation|README line, where and how to fix) for each block that differs from a fresh render."""
    names = {"settings": "Settings", "automation": "Automation", "template": "README line"}
    return [("STALE", names[name], "%s is missing or differs from a fresh render. Fix: /workflow-docs render" % where)
            for where, name in refresh(root, True)]
