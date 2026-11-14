#!/usr/bin/env python3
"""Check a repo's health with fixed rules. Same repo, same answer. check writes no file and calls no model.

usage: health.py check [--json] [--group NAME[,NAME]] [--skip NAME[,NAME]]
       health.py review [--feature NAME] [--json]          (judge.py; judge and suggest are aliases)
       health.py preview [--group NAME[,NAME]] [--feature NAME] [--review FILE]
       health.py file --group NAME[,NAME] [--feature NAME] [--review FILE]
       health.py triage [--feature NAME] [--close (--kind K | --issue N ...) --why WORDS [--older DAYS] [--yes] [--max N]]

check prints the formal report (report.py): the twelve groups of report.py, each under a heading with its angle, every
rule marked pass, warn, fail or unread with its fix, then one verdict, HEALTH: green or not green. Only FAIL and UNREAD
turn it red (exit 1). Every rule has a negative control (controls.py); a rule with none makes health.py refuse (exit 2).
preview lists what file would do and writes nothing; file writes GitHub issues tagged with each finding's group
(file.py, issues.py); triage lists and closes them in batches (issues.py). Rules live here and in defects.py
and rules.py; --json prints the rows.
"""
import argparse
import datetime
import glob
import importlib
import json
import os
import re
import subprocess
import sys
import time

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import report as G  # noqa: E402
except ImportError:  # a lone health.py: only the rules it holds itself, in four groups, no angles
    class G:
        RULES_OF = {"size": ("scripts",), "requirements": ("rows", "proof", "done"), "docs": ("docs-check",),
                    "hygiene": ("findings", "waiting", "branches"), "mine": (), "controls": ()}
        ORDER = tuple(RULES_OF)
        RULES = tuple(r for rules in RULES_OF.values() for r in rules)
        GROUP_OF = {r: g for g, rules in RULES_OF.items() for r in rules}
        ALIASES = {"criteria": "requirements", "cost": "performance"}

LIMIT = 20 * 1024
WARN_AT = LIMIT * 9 // 10
FINDINGS_WARN = 5
WAITING_HOURS = 24
RULES = G.RULES  # every rule of the twelve groups; each needs a negative control
FAMILY = {name: name for name in G.ORDER}
ORDER = G.ORDER
NAMES = list(G.ORDER) + sorted(G.ALIASES)
T0 = [float(os.environ.get("LOOP_HEALTH_T0") or 0) or None]  # check-time's start (set in cmd_check)


def run(args, cwd):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as error:
        return subprocess.CompletedProcess(args, 127, "", str(error))


def row(state, family, subject, rule, detail, fix=""):
    return {"state": state, "family": family, "subject": subject, "rule": rule, "detail": detail, "fix": fix}


def sibling(skill, script):
    path = os.path.join(HERE, "..", "..", skill, "scripts", script)
    return path if os.path.exists(path) else ""


def size_rows(root):
    rows, good = [], 0
    for path in sorted(glob.glob(os.path.join(root, "skills", "*", "scripts", "*.*"))):
        if not path.endswith((".py", ".sh")):
            continue
        with open(path, "rb") as handle:  # committed (LF) bytes: a Windows CRLF checkout reads the same
            size = len(handle.read().replace(b"\r\n", b"\n"))
        name = os.path.relpath(path, root)
        if size > LIMIT:
            rows.append(row("FAIL", "size", name, "scripts", "%d bytes, over %d" % (size, LIMIT), "split it into modules"))
        elif size >= WARN_AT:
            rows.append(row("WARN", "size", name, "scripts", "%d bytes, %d%% of %d" % (size, size * 100 // LIMIT, LIMIT),
                            "trim or split before it passes the limit"))
        else:
            good += 1
    if not rows:
        rows.append(row("PASS", "size", "scripts", "scripts", "%d scripts under %d bytes" % (good, WARN_AT)))
    return rows


def criteria_rows(root):
    script = sibling("workflow-regression", "regression.py")
    if not script:
        return [row("UNREAD", "requirements", "regression", "rows", "regression.py is not installed beside this skill")]
    done = run([sys.executable, script, "sync"], root)
    lines = done.stdout.splitlines()
    if not lines and done.returncode:
        return [row("UNREAD", "requirements", "regression", "rows", (done.stderr.strip() or "no output")[:120])]
    rows, loose = [], 0
    for line in lines:
        gap = re.match(r"^GAP (\S+) (.*)$", line)
        if gap and re.match(r"^[A-Za-z0-9-]+:\d+$", gap.group(1)):
            loose += 1
        elif gap and "criterion has no regression row" in gap.group(2):
            rows.append(sibling_module("enforce").row(root, gap.group(1), row))
        elif line.startswith("PENDING "):  # owed to another machine: a warning past a week, never a failure
            old = re.search(r"owed on (.+?) since (\d{4}-\d{2}-\d{2})", line)
            if old and (datetime.date.today() - datetime.date.fromisoformat(old.group(2))).days > 7:
                rows.append(row("WARN", "tests", line.split()[1].rstrip(":"), "owed-proof", "proof owed on %s since %s" % old.groups(),
                                "regression.py red ID --off-platform"))
        elif line.startswith(("DRAFT ", "UNPROVEN ")):
            word, key = line.split()[:2]
            rows.append(row("FAIL", "requirements", key.rstrip(":"), "proof", "a draft row: no command or level yet",
                            "give it a command and level") if word == "DRAFT" else
                        row("FAIL", "tests", key.rstrip(":"), "seen-red", "never seen failing", "run regression.py red"))
    if loose:
        rows.append(row("WARN", "requirements", "done-lines", "done", "%d done lines have no regression row" % loose,
                        "regression.py sync --write drafts rows"))
    if not rows and not any(line.startswith("SYNC OK") for line in lines):
        return [row("UNREAD", "requirements", "regression", "rows", (done.stderr.strip() or "no SYNC OK line")[:120])]
    return rows


def docs_rows(root):
    script = sibling("workflow-docs", "docs.py")
    if not script:
        return [row("UNREAD", "docs", "docs", "check", "docs.py is not installed beside this skill")]
    done = run([sys.executable, script, "check"], root)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    if lines and lines[0].startswith("NO PAGES"):
        return [row("UNREAD", "docs", "wiki", "check", "no pages mapped", "run docs.py add")]
    if lines and lines[0].startswith("DOCS OK"):
        return [row("PASS", "docs", "wiki", "check", lines[0].lower())]
    if not lines:
        return [row("UNREAD", "docs", "docs", "check", (done.stderr.strip() or "no output")[:120])]
    rows = []
    for line in lines:
        kind, _, rest = line.partition(" ")
        page, _, detail = rest.partition(": ")
        if kind == "CAP":  # the requirement limit belongs to Size requirements-per-page
            continue
        rows.append(row("WARN" if kind == "STALE" else "FAIL", "docs", page, kind.lower(), detail[:120],
                        "update the page with workflow-docs"))
    return rows


def defect_rows(root):
    defects = sibling_module("defects")
    if not defects:
        return [row("UNREAD", "traceability", "defects", "defect-tests", "defects.py is not installed beside health.py")]
    gone = exempt(root, [ref for ref, _ in defects.missing(root)])  # a health or backlog finding that went away isn't a fixed bug
    return [row("FAIL", "traceability", ref, "defect-tests", "closed by %s with no defect test" % source,
                "regression.py add --category defect --link ...") for ref, source in defects.missing(root) if ref not in gone]


def exempt(root, refs):
    """The #N refs among `refs` that are issues labelled health or backlog (none when the issues can't be read)."""
    tracker = sibling_module("issues") if any(r[0] == "#" for r in refs) else None
    found = tracker.fetch(root, "held")[0] if tracker else None
    return {"#%d" % i["number"] for i in found or [] if {"health", "backlog"} & set(i.get("labels") or [])} & set(refs)


def hours_old(stamp):
    try:
        when = datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return 0
    return (datetime.datetime.now(datetime.timezone.utc) - when).total_seconds() / 3600


def hygiene_rows(root):
    rows = []
    try:
        with open(os.path.join(root, ".loop", "findings.md")) as handle:
            open_findings = [line for line in handle if line.startswith("- ")]
    except OSError:
        open_findings = []
    if len(open_findings) > FINDINGS_WARN:
        rows.append(row("WARN", "hygiene", "findings", "open", "%d open findings, over %d" % (len(open_findings), FINDINGS_WARN),
                        "resolve or remove them in .loop/findings.md"))
    common = run(["git", "rev-parse", "--git-common-dir"], root).stdout.strip()
    common = os.path.abspath(os.path.join(root, common))
    for path in sorted(glob.glob(os.path.join(common, "loop", "runs", "*.json"))):
        try:
            with open(path) as handle:
                state = json.load(handle)
        except (OSError, ValueError):
            rows.append(row("UNREAD", "hygiene", os.path.basename(path)[:-5], "run", "run record cannot be read"))
            continue
        if isinstance(state, dict) and state.get("status") == "waiting" and hours_old(state.get("updated")) > WAITING_HOURS:
            rows.append(row("WARN", "hygiene", state.get("slug") or os.path.basename(path)[:-5], "waiting",
                            "waiting over %d hours" % WAITING_HOURS, "answer it or retire it on the board"))
    base = "origin/main" if run(["git", "rev-parse", "--verify", "--quiet", "origin/main"], root).returncode == 0 else "main"
    merged = run(["git", "branch", "--merged", base], root)
    if merged.returncode:
        rows.append(row("UNREAD", "hygiene", "branches", "merged", (merged.stderr.strip() or "git branch failed")[:120]))
    else:
        for line in sorted(merged.stdout.splitlines()):
            name = line[2:].strip()
            if line.startswith("  ") and name.startswith("loop/"):
                rows.append(row("WARN", "hygiene", name, "branch", "already merged into %s" % base,
                                "worker.py cleanup"))
    return rows  # lean.py's test-time, worktrees and local-branches are rules of their own (rule_functions)


def sibling_module(name):
    sys.path.insert(0, HERE)
    try:
        return importlib.import_module(name)
    except ImportError:
        return None
    finally:
        sys.path.pop(0)


def docs_check(root):
    """docs.py's check."""
    return docs_rows(root)


def hard_unread(item):
    """An UNREAD row that means its function didn't run."""
    return item["state"] == "UNREAD"


def rule_functions():
    """Each rule -> the function that checks it (and that its control calls)."""
    lean, extra = sibling_module("lean"), {}
    for name in ("defects", "rules", "report"):
        module = sibling_module(name)
        extra.update(module.FUNCTIONS if module else {})
    found = {"scripts": size_rows, "rows": criteria_rows, "proof": criteria_rows, "done": criteria_rows,
             "seen-red": criteria_rows, "defect-tests": defect_rows, "docs-check": docs_check, "findings": hygiene_rows,
             "waiting": hygiene_rows, "branches": hygiene_rows, "cost": cost_rows}
    if lean:
        found.update({"test-time": lean.test_rows, "worktrees": lean.worktree_rows, "local-branches": lean.branch_rows, "hooks": lean.hook_rows})
    found.update(extra)
    return {name: found[name] for name in RULES if name in found}


MOVED = {"criteria": "requirements", "cost": "performance"}  # older family names some modules still return


def placed(item):
    """A row with its family set to its rule's group (lean's test-time row reports in Performance)."""
    family = MOVED.get(item["family"], item["family"])
    if item["rule"] in G.GROUP_OF and family not in ("mine", "controls"):
        family = G.GROUP_OF[item["rule"]]
    return dict(item, family=family)


def controls_rows(root):
    controls = sibling_module("controls")
    if controls is None:
        return [row("UNREAD", "controls", "controls.py", "control", "controls.py is missing")]
    return controls.run({name: (lambda root, fn=fn: [placed(i) for i in fn(root)]) for name, fn in rule_functions().items()}, HERE)


def mine_rows(root):
    mine = sibling_module("enforce")
    return mine.mine_rows(root) if mine else [row("UNREAD", "mine", "enforce.py", "mine", "enforce.py is not installed beside health.py")]


def cost_rows(root):
    cost = sibling_module("milestone")
    return (cost.cost_rows(root, HERE) + cost.timing_rows(root)) if cost else \
        [row("UNREAD", "cost", "milestone.py", "cost", "milestone.py is missing")]  # timing_rows: REG-7


def gather(root, family, ran_rules=None):
    """The rows of the groups asked (all when None), each rule function run once. A function that raises gives UNREAD
    rows for its rules; ran_rules (a set) collects the rules whose function ran."""
    asked = family or ORDER
    T0[0] = T0[0] or time.time()  # check-time measures every command that gathers (check, judge, preview, file)
    funcs, done, rows = rule_functions(), {}, []
    for name in asked:
        if name == "mine":
            got = mine_rows(root)
            rows += got
            if ran_rules is not None and not any(i["state"] == "UNREAD" for i in got) and any(i["state"] != "INFO" for i in got):
                ran_rules.update("mine:" + i["subject"] for i in got)
            continue
        if name == "controls":
            rows += controls_rows(root)
            continue
        for rule in G.RULES_OF[name]:
            fn = funcs.get(rule)
            if fn is None:
                rows.append(row("UNREAD", name, rule, rule, "no function checks this rule", "install the whole skill"))
                continue
            if fn not in done:
                try:
                    done[fn] = [placed(item) for item in fn(root)]
                except Exception as error:  # a broken rule is unread, never a pass
                    done[fn] = [row("UNREAD", name, rule, rule, "%s: %s" % (type(error).__name__, str(error)[:100]))]
            if ran_rules is not None and not any(hard_unread(i) for i in done[fn]):  # a shared source unread: none ran
                ran_rules.add(rule)
    for got in done.values():
        rows += [item for item in got if item["family"] in asked]
    return rows


def groups_of(text):
    """Group names from a --group value (performance is cost), or None for all."""
    names = [G.ALIASES.get(n.strip(), n.strip()) for n in (text or "").split(",") if n.strip()]
    bad = [n for n in names if n not in FAMILY]
    if bad:
        print("REFUSED[group]: unknown group %s. Groups: %s." % (", ".join(bad), ", ".join(NAMES)))
        sys.exit(2)
    return list(dict.fromkeys(names)) or None  # a repeated name (cost,performance) runs once


def report(rows, asked=None, ran_rules=None):
    """The formal report from report.py; a lone health.py prints the bare rows and a verdict."""
    formal = sibling_module("report")
    if formal:
        built = formal.build(rows, asked, ran_rules)
        return built[:4] + (built[6],)  # the rows the report shows, so --json rows agree with its counts
    counts = {state: sum(1 for item in rows if item["state"] == state) for state in ("PASS", "WARN", "FAIL", "UNREAD")}
    green = not counts["FAIL"] and not counts["UNREAD"]
    verdict = "HEALTH: %s (%d pass, %d warn, %d fail, %d unread)" % ("green" if green else "not green", *counts.values())
    return (["HEALTH REPORT"] + ["%(state)s %(family)s %(subject)s %(rule)s: %(detail)s" % item for item in rows] + [verdict],
            counts, green, verdict, rows)


def repo_root():
    top = run(["git", "rev-parse", "--show-toplevel"], os.getcwd())
    if top.returncode:
        sys.exit("REFUSED: not inside a git repo.")
    return top.stdout.strip()


def cmd_check(args):
    root = repo_root()
    whole = asked = groups_of(args.group)
    skipped = groups_of(args.skip) or []
    asked = [name for name in (asked or ORDER) if name not in skipped] if skipped else asked
    if asked == []:
        print("REFUSED: --skip leaves no group to check")
        return 2
    T0[0] = T0[0] or time.time()
    ran = set()
    text, counts, green, verdict, rows = report(gather(root, asked, ran), asked, ran)
    if args.json:
        print(json.dumps({"green": green, "counts": counts, "rows": rows, "verdict": verdict}, indent=2))
    else:
        print("\n".join(with_tests(text, root) if whole is None else text))
    return 0 if green else 1


def with_tests(text, root):
    """The report with the test list just before its verdict, so the verdict stays the last line."""
    last = len(text) - 1 if text and text[-1].startswith("HEALTH:") else len(text)
    return text[:last] + tests_block(root) + text[last:]


def tests_block(root):
    """Every test in workflow-regression's one format, grouped by feature, before the verdict; read-only."""
    script = sibling("workflow-regression", "tests.py")
    done = run([sys.executable, script, "list", "--root", root], root) if script else None
    if not done or done.returncode:
        return ["", "TESTS", "NOTE: the test list is unavailable (%s)" % ("tests.py is not installed beside this skill" if not done
                                                                 else (done.stderr.strip() or "no output")[:120]), ""]
    return ["", "TESTS"] + done.stdout.rstrip("\n").splitlines() + [""]


def main():
    commands = sibling_module("report")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("check", help="run the fixed rules")
    item.add_argument("--json", action="store_true")
    item.add_argument("--group", "--family", dest="group", help="one of: " + ", ".join(NAMES))
    item.add_argument("--skip", default="", help="groups to leave out")
    item.set_defaults(func=cmd_check)
    if commands:  # a lone health.py has check only
        commands.add(sub, sys.modules[__name__])
    args = parser.parse_args()
    return args.func(args)

if __name__ == "__main__":
    _controls = sibling_module("controls")
    _controls and _controls.refuse(RULES)  # a new rule must come with its negative control (exit 2)
    sys.exit(main())
