#!/usr/bin/env python3
"""The health rule for defect tests: every closed issue or finding needs a regression row of category defect.

A closed issue or finding is one a merged goal says it fixed ("fixes #35", "fixes finding:SLUG" in .loop/goals/*.md),
or a line of .loop/findings.md marked [closed]. A defect row links it: its link holds the issue's URL or finding:SLUG.
Reads files only: health check makes no gh call.
It also holds the Traceability and Consistency rules (report.py) and the page reader the other rule modules share (read-only):
  row-requirement  a regression row whose goal names no requirement on any page and is not a done line slug:N (FAIL)
  ids-unique       a requirement id defined on two pages (FAIL)
  refs             a page naming an id of a known prefix (HLT-12 when HLT ids exist) that no page defines (FAIL)
  usage-readme     a /workflow-<skill> <verb> in the README that no page's Usage names (WARN)
  migration        the migration-check engine (migration_gaps, below) as WARN rows: setup.py migration-check prints the same gaps
Each rule's negative control is in CONTROLS (controls.py runs it). Rows carry an evidence field of stable citations.
"""
import glob
import importlib
import json
import os
import re
import subprocess
import sys
import traceback


VERB = r"\b(?:fix(?:es|ed)?|close[sd]?|resolve[sd]?)\s+"
FIXES = re.compile(VERB + r"(?:issue\s+)?#(\d+)|" + VERB + r"finding:([a-z0-9][a-z0-9-]*)", re.I)


def read(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return ""


def closed(root):
    """Ref -> where it was closed: '#N' for an issue, 'finding:SLUG' for a finding."""
    found = {}
    for path in sorted(glob.glob(os.path.join(root, ".loop", "goals", "*.md"))):
        if path.endswith(".design.md"):
            continue
        for number, finding in FIXES.findall(read(path)):
            found.setdefault("#" + number if number else "finding:" + finding.lower(), os.path.basename(path)[:-3])
    for line in read(os.path.join(root, ".loop", "findings.md")).splitlines():
        named = re.match(r"^- ([a-z0-9][a-z0-9-]*):.*\[closed\]", line)
        if named:
            found.setdefault("finding:" + named.group(1), "findings.md")
    return found


def guarded(root):
    """The links of the defect rows, as one text."""
    cells = [line.rstrip("\n").split("\t") + [""] * 8 for line in read(os.path.join(root, ".loop", "regression.tsv")).splitlines()
             if line.strip() and line[0] != "#"]
    return " ".join(c[7] for c in cells if c[6] == "defect")


def missing(root):
    """(ref, source) for each closed issue or finding no defect row links."""
    links = guarded(root)
    out = []
    for ref, source in closed(root).items():
        pattern = r"(?:issues/|#)%s\b" % ref[1:] if ref[0] == "#" else re.escape(ref) + r"(?![\w-])"
        if not re.search(pattern, links):
            out.append((ref, source))
    return out


LINE = re.compile(r"^- ([A-Z]{2,5}-\d+[a-z]?): ", re.M)
SLUG_N = re.compile(r"^[a-z0-9][a-z0-9-]*:\d+$")
COMMAND = re.compile(r"/workflow-[a-z]+ [a-z][a-z-]*")


def setting(root, key, default):
    """A positive whole number set in .loop/config.json (a threshold a repo tunes), else the default."""
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            value = json.load(handle)[key]
    except (OSError, ValueError, KeyError, TypeError):
        return default
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else default


def row(state, family, subject, rule, detail, fix="", evidence=""):
    return {"state": state, "family": family, "subject": subject, "rule": rule, "detail": detail, "fix": fix,
            "evidence": evidence or subject}


def wiki(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            folder = json.load(handle).get("wiki_dir") or "docs/wiki"
    except (OSError, ValueError, AttributeError):
        folder = "docs/wiki"
    return os.path.join(root, folder)


def pages(root):
    """{page name: text} of the wiki pages."""
    out = {}
    for path in sorted(glob.glob(os.path.join(wiki(root), "*.md"))):
        with open(path, errors="replace") as handle:
            out[os.path.basename(path)[:-3]] = handle.read()
    return out


def defined(root):
    """{requirement id: [pages that define it]}."""
    out = {}
    for name, text in pages(root).items():
        for key in LINE.findall(text):
            out.setdefault(key, []).append(name)
    return out


def table(root):
    """Regression rows as dicts (id, level, command, goal, ...)."""
    names = ("id", "level", "command", "goal", "seen_red", "description", "category", "link")
    try:
        with open(os.path.join(root, ".loop", "regression.tsv")) as handle:
            lines = [line.rstrip("\n").split("\t") for line in handle if line.strip() and not line.startswith("#")]
    except (OSError, ValueError):
        return []
    return [dict(zip(names, cells + [""] * (8 - len(cells)))) for cells in lines]


def section(text, title):
    part = re.split(r"^## %s\s*$" % re.escape(title), text, maxsplit=1, flags=re.M)
    return part[1].split("\n## ", 1)[0] if len(part) > 1 else ""


def row_requirement(root):
    known = defined(root)
    out = []
    for item in table(root):
        goal = item["goal"].strip()
        if goal and goal != "-" and not SLUG_N.match(goal) and goal not in known:
            out.append(row("FAIL", "traceability", item["id"], "row-requirement", "row guards %s, which no page defines" % goal,
                           "fix the row's goal, or add the requirement", item["id"]))
    return out


def ids_unique(root):
    return [row("FAIL", "consistency", key, "ids-unique", "defined on %s" % ", ".join(names), "give each requirement one page", key)
            for key, names in sorted(defined(root).items()) if len(names) > 1]


def refs(root):
    known = defined(root)
    prefixes = {key.split("-")[0] for key in known}
    out, seen = [], set()
    for name, text in pages(root).items():
        for key in re.findall(r"\b([A-Z]{2,5}-\d+[a-z]?)\b", text):
            if key.split("-")[0] in prefixes and key not in known and (name, key) not in seen:
                seen.add((name, key))
                out.append(row("FAIL", "consistency", key, "refs", "page %s names %s, which no page defines" % (name, key),
                               "fix the reference or add the requirement", "%s:%s" % (name, key)))
    return out


def usage_readme(root):
    try:
        with open(os.path.join(root, "README.md"), errors="replace") as handle:
            readme = handle.read()
    except OSError:
        return []
    usage = "\n".join(section(text, "Usage") for text in pages(root).values())
    return [row("WARN", "consistency", command, "usage-readme", "the README names %s and no page's Usage does" % command,
                "add it to its page's Usage, or drop it from the README", command)
            for command in sorted(set(COMMAND.findall(readme))) if command not in usage]


# --- migration-check: one engine for `setup.py migration-check` (main) and health's migration rule. It writes nothing.
SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE = ("MIG_TASK", "MIG_WIKI_ORPHAN", "MIG_WIKI_STALE", "MIG_WIKI_UNREADABLE")  # close on the Mac or in the wiki, after the merge
CLASSES = ("MIG_VERSION", "MIG_FILES", "MIG_SETTINGS", "MIG_BLOCKS", "MIG_AUTOMATION", "MIG_RUNBOOK", "MIG_FORMAT", "MIG_CHECKS") + STATE
PROTOCOLS = "https:ssh:git:file"  # the only transports the wiki clone may use: an ext:: origin runs nothing
SEMVER = re.compile(r"\d+\.\d+\.\d+")


def mod(skill, name):
    """A module of a sibling skill, imported with its folder on the path for the import only."""
    where = os.path.join(SKILLS, skill, "scripts")
    sys.path.insert(0, where)
    try:
        return importlib.import_module(name)
    finally:
        sys.path.pop(0)


def clean(text):
    """One redaction for everything printed: no user:password@, no token or key value in a query, no control character."""
    text = re.sub(r"//[^/\s@]*@", "//", str(text))
    return re.sub(r"[\x00-\x1f\x7f]", " ", re.sub(r"(?i)\b((?:access_)?token|key)=[^&\s]+", r"\1=<x>", text))


def tool(skill, script, *args):
    return "python3 <%s>/scripts/%s %s" % (skill, script, " ".join(args)) if args else "python3 <%s>/scripts/%s" % (skill, script)


def config_of(root):
    try:
        with open(os.path.join(root, ".loop", "config.json")) as handle:
            found = json.load(handle)
        return found if isinstance(found, dict) else None
    except (OSError, ValueError):
        return None


def installed():
    try:
        return mod("workflow-docs", "entry").installed()
    except ImportError:
        return ""


def gaps_version(root, cfg, g, info):
    want, held = installed(), cfg.get("template_version")
    info["held"], info["want"] = held if isinstance(held, str) and SEMVER.fullmatch(held) else "none", "v" + want if want else "none (a checkout)"
    if not want or os.path.realpath(SKILLS).startswith(os.path.realpath(root) + os.sep):
        return  # a checkout that holds the skills has no installed version to be behind
    if "template_version" not in cfg:
        g("MIG_VERSION", "template_version", "none is set (read as 0.0.0), the template is at v%s" % want, "run the migrate goal (update.py --apply stamps it)")
    elif not (isinstance(held, str) and SEMVER.fullmatch(held)):
        g("MIG_VERSION", "template_version", "unparseable %s (read as 0.0.0), the template is at v%s" % (clean(repr(held))[:24], want), "run the migrate goal (update.py --apply stamps it)")
    elif mod("workflow-docs", "entry").version_key(held) < mod("workflow-docs", "entry").version_key(want):
        g("MIG_VERSION", "template_version", "v%s is behind the template at v%s" % (held, want), "run the migrate goal (update.py --apply)")


def behind(root):
    """MIG_VERSION as one WARN row for rules.template_version (the migration rule skips that code): none or older than the template."""
    found = []
    try:
        gaps_version(root, config_of(root) or {}, lambda *item: found.append(item), {})
    except Exception:
        return []
    return [row("WARN", "adoption", "template_version", "template-version", "MIG_VERSION: " + clean(what), "run the migrate goal", "template_version") for _, _, what, _ in found]


def gaps_files(root, cfg, g):
    for kind, path, detail in mod("workflow-docs", "entry").problems(root):
        if kind in ("STALE", "MISSING"):
            g("MIG_FILES", path, "%s: %s" % (kind.lower(), clean(detail.split(". Fix")[0])), tool("workflow-docs", "entry.py", "write"))
    flows = os.path.join(root, ".github", "workflows")
    for name, text in (("regression.yml", "left over: regression runs on the Mac"), ("health.yml", "left over: health runs on the Mac")):
        if os.path.exists(os.path.join(flows, name)) and (name == "health.yml" or cfg.get("regression_runs") == "mac"):
            g("MIG_FILES", ".github/workflows/" + name, text, "git rm .github/workflows/" + name)
    for name in ("queue.md", "findings.md", "regression.tsv"):
        if not os.path.exists(os.path.join(root, ".loop", name)):
            g("MIG_FILES", ".loop/" + name, "missing", "run workflow-setup (setup.py) again, which adds it")


def gaps_settings(root, cfg, g):
    st = mod("workflow-setup", "settings")
    known = {row[0] for row in st.keys(st.REPO)}
    extra = sorted(set(cfg) - known - {"_help", "template_version", "checks"})
    missing = sorted(known - set(cfg) - {"regression_runs"})
    if extra:
        g("MIG_SETTINGS", ", ".join(clean(k) for k in extra), "not in the settings table (unknown)", "remove the key from .loop/config.json")
    if missing:
        g("MIG_SETTINGS", ", ".join(missing), "missing from .loop/config.json", tool("workflow-setup", "settings.py", "fill-repo"))


def gaps_blocks(root, cfg, g):
    for rel, name in mod("workflow-docs", "render").refresh(root, True, True):
        g("MIG_BLOCKS", rel, "the %s block is missing or stale" % {"template": "README line"}.get(name, name.capitalize()), tool("workflow-docs", "render.py", "blocks"))


def migration_gaps(root, online=True, pr=False, info=None):
    """[(code, subject, what, fix)] for the repo at root. pr: only the gaps a pull request can close. online: also read the published
    wiki (one bounded clone). info is filled with what the run checked and what it could not."""
    info = {} if info is None else info
    info.update(skipped=[], notes=[], held="none", want="unknown", platform=sys.platform, off={"health": False, "regression": False})
    found, g = [], lambda *item: found.append(item)
    cfg = config_of(root)
    if cfg is None:
        g("MIG_SETTINGS", ".loop/config.json", "is missing or not valid JSON", "run workflow-setup (setup.py)")
    cfg = cfg or {}
    wiki_on = os.path.exists(os.path.join(root, ".loop", "docs.tsv"))
    gaps_version(root, cfg, g, info)
    gaps_files(root, cfg, g)
    gaps_settings(root, cfg, g) if cfg else None
    gate = mod("workflow-health", "enforce")
    gate.automation_gaps(root, cfg, g, info)
    gate.checks_gaps(root, cfg, g)
    if wiki_on:
        if cfg.get("criteria"):
            gaps_blocks(root, cfg, g)
        gate.docs_gaps(root, g)
    if not pr:
        gate.task_gaps(root, cfg, g, info)
        if wiki_on and online:
            gate.wiki_gaps(root, g, info)
        elif wiki_on:
            info["skipped"].append("the published wiki (offline)")
    else:
        info["skipped"].append("the state codes (--pr)")
    return found


def lines(root, gaps, info, pr, offline):
    """The output of `migration-check`, one string per line: GAP lines, NOT CHECKED, CHECKED, DOCS, then the verdict."""
    out = ["GAP %s %s: %s. Fix: %s" % (code, clean(subject), clean(what), clean(fix)) for code, subject, what, fix in gaps]
    skipped = ["branch protection (no gh read)"] + (["the pull-request check, none exists in mac mode"] if config_of(root) and (config_of(root) or {}).get("regression_runs") == "mac" else []) + info["skipped"] + info["notes"]
    out += [x for x in skipped if x.startswith("SKIP ")]
    out.append("NOT CHECKED: " + "; ".join(x for x in skipped if not x.startswith("SKIP ")))
    out.append("CHECKED: installed %s, repo template_version %s (working tree), platform %s, mode %s" % (info["want"], info["held"], info["platform"], "offline" if offline or pr else "online"))
    out.append("DOCS: each code's cause, class and fix are in the Setup page, Usage, migration-check")
    state = sum(1 for gap in gaps if gap[0] in STATE)
    cut = " (--pr: state codes not checked)" if pr else " (offline: wiki not checked)" if offline else ""
    out.append("MIGRATION: %d gap(s) (%d PR-closable, %d state)%s" % (len(gaps), len(gaps) - state, state, cut) if gaps else "MIGRATION OK" + cut)
    return out


def main(argv):
    """setup.py migration-check [--repo DIR] [--pr] [--offline]: exit 0 only with no gap, 1 for gaps, 2 usage, 4 could not run."""
    import argparse
    parser = argparse.ArgumentParser(prog="setup.py migration-check", description="List every gap between a repo and the current template, each with its fix; writes nothing.")
    parser.add_argument("--repo", default=".", help="the repo to check (default: the current directory)")
    parser.add_argument("--pr", action="store_true", help="only the gaps a pull request can close (skips the Mac task and the published wiki)")
    parser.add_argument("--offline", action="store_true", help="skip the published wiki (no network)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        stop.code and print("Fix: run setup.py migration-check --help", file=sys.stderr)
        raise
    top = subprocess.run(["git", "-C", args.repo, "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    if not top:
        print("migration-check: %s is not a git repo. Fix: run setup.py migration-check --help" % args.repo, file=sys.stderr)
        return 2
    info = {}
    try:
        gaps = migration_gaps(top, not (args.offline or args.pr), args.pr, info)
        text = lines(top, gaps, info, args.pr, args.offline)
    except Exception:
        import tempfile
        handle, path = tempfile.mkstemp(prefix="migration-check-", suffix=".trace")
        os.write(handle, traceback.format_exc().encode())
        os.close(handle)
        print("INTERNAL ERROR (MIG_INTERNAL): see %s; nothing was changed" % path, file=sys.stderr)
        return 4
    print("\n".join(text))
    return 1 if gaps else 0


def migration(root):
    """The health rule: each gap but MIG_VERSION (the template-version row says it once) is a WARN row; the wiki rows are grouped."""
    online, info = os.environ.get("LOOP_MIGRATION_ONLINE") == "1", {}
    mode = "online" if online else "offline"
    try:
        gaps = [x for x in migration_gaps(root, online, False, info) if x[0] != "MIG_VERSION"]
    except Exception as error:
        return [row("INFO", "adoption", "migration", "migration", "could not run (%s) [%s]" % (clean(type(error).__name__), mode))]
    out, wiki = [], {}
    for code, subject, what, fix in gaps:
        if code.startswith("MIG_WIKI") and code != "MIG_WIKI_UNREADABLE":
            wiki.setdefault(code, []).append(subject)
        else:
            out.append(row("INFO" if code == "MIG_WIKI_UNREADABLE" else "WARN", "adoption", "%s %s" % (code, clean(subject)), "migration", "%s: %s [%s]" % (clean(subject), clean(what), mode), clean(fix), "%s:%s" % (code, clean(subject))))
    for code, names in sorted(wiki.items()):
        shown = ", ".join(clean(n) for n in names[:20]) + (" and %d more" % (len(names) - 20) if len(names) > 20 else "")
        out.append(row("WARN", "adoption", code, "migration", "%s [%s]" % (shown, mode), "run the check for each page's fix (setup.py migration-check)", code))
    out += [row("INFO", "adoption", "migration", "migration", "not checked here: %s [%s]" % (clean(item), mode)) for item in info["skipped"] if "state codes" not in item and not item.startswith("SKIP ")]
    out += [row("INFO", "adoption", "migration", "migration", "%s [%s]" % (clean(item), mode)) for item in info["skipped"] if item.startswith("SKIP ")]
    return out


FUNCTIONS = {"row-requirement": row_requirement, "ids-unique": ids_unique,
             "refs": refs, "usage-readme": usage_readme, "migration": migration}


def _c():
    import controls
    return controls


def f_row_requirement(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/regression.tsv", "# id\tlevel\tcommand\tgoal\nr1\tland\ttrue\tZZZ-9\n")


def f_ids_unique(root):
    c = _c(); c.repo(root)
    for name in ("One", "Two"):
        c.write(root, "docs/wiki/%s.md" % name, "# %s\n\n## Requirements\n\n- AB-1: **Unreviewed** x.\n" % name)


def f_refs(root):
    c = _c(); c.repo(root)
    c.write(root, "docs/wiki/One.md", "# One\n\n## Requirements\n\n- AB-1: **Unreviewed** see AB-9.\n")


def f_usage_readme(root):
    c = _c(); c.repo(root)
    c.write(root, "README.md", "Run /workflow-toy frob to frob.\n")
    c.write(root, "docs/wiki/One.md", "# One\n\n## Usage\n\n- nothing here\n")


def f_migration(root):
    c = _c(); c.repo(root)
    c.write(root, ".loop/config.json", json.dumps({"base": "main", "wiki_dir": "docs/wiki", "legacy_toy_key": 1}))


CONTROLS = {"migration": ("adoption", "migration", f_migration), "row-requirement": ("traceability", "row-requirement", f_row_requirement),
            "ids-unique": ("consistency", "ids-unique", f_ids_unique), "refs": ("consistency", "refs", f_refs),
            "usage-readme": ("consistency", "usage-readme", f_usage_readme)}
