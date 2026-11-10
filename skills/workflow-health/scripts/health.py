#!/usr/bin/env python3
"""Check a repo's health with fixed rules. Same repo, same answer. Read-only: it writes no file and calls no model.

usage: health.py check [--json] [--group NAME] [--skip NAME]
       health.py preview [--group NAME[,NAME]]
       health.py file --group NAME[,NAME]
       health.py judge

check prints the formal report (report.py): the groups run and skipped, every rule of each group, then one verdict
line, HEALTH: green or not green. Only FAIL and UNREAD (a rule that could not read its data) turn it red (exit 1).
judge (alias suggest) adds a section of suggestions (judge.py) and never changes the verdict. --json prints the rows.

Rules (at most MAX_RULES, asserted when the script loads; retire one before adding another):
  size      scripts under skills/*/scripts against 20 KB: WARN from 90%, FAIL over
  criteria  composes regression.py sync: a criterion with no row FAILs, a draft or never-failed row FAILs,
            done lines with no row WARN as one row; a closed issue or finding with no defect test FAILs (defects.py)
  docs      composes docs.py check: a stale page WARNs, any other gap FAILs
  hygiene   open findings over 5, runs waiting over 24 hours, merged loop branches; lean.py: the land lane over
            test_budget_seconds, stale loop worktrees and local branches (each with its removal command, never run)
  cost      a finished goal over time_budget_minutes or token_budget in .loop/config.json WARNs, naming its slowest or
            costliest steps (cost.py); no tokens recorded is UNREAD
  controls  each rule's negative control (controls.py) must fire, or it is FAIL "cannot fire"; a rule with no
            control makes health.py refuse to load (exit 2). Mine runs the owner's rules (mine.py).

preview lists what file would open, update, close or reopen, writing nothing; file --group NAME[,NAME] files only
those groups as issues on the Backlog milestone (file.py). run is an alias of preview. It runs git, gh and its siblings.
"""
import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

LIMIT = 20 * 1024
WARN_AT = LIMIT * 9 // 10
FINDINGS_WARN = 5
WAITING_HOURS = 24
RULES = ("size", "criteria-rows", "criteria-done", "defect-tests", "docs-check", "findings", "waiting", "branches", "cost",
         "test-time", "worktrees", "local-branches")
MAX_RULES = 12  # raised on purpose: 9 for cost, 12 for HLT-6's test time and stale worktrees and branches
assert len(RULES) <= MAX_RULES, "too many rules: retire one first"
FAMILY = {"size": "size", "criteria": "criteria", "docs": "docs", "hygiene": "hygiene", "cost": "cost", "mine": "mine",
          "controls": "controls"}
ORDER = ("size", "criteria", "docs", "hygiene", "cost", "mine", "controls")  # the fixed order of the groups in the report
NAMES = sorted(FAMILY) + ["performance"]  # performance is the Cost group's name in the report and its tag
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))


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
        size, name = os.path.getsize(path), os.path.relpath(path, root)
        if size > LIMIT:
            rows.append(row("FAIL", "size", name, "limit", "%d bytes, over %d" % (size, LIMIT), "split it into modules"))
        elif size >= WARN_AT:
            rows.append(row("WARN", "size", name, "limit", "%d bytes, %d%% of %d" % (size, size * 100 // LIMIT, LIMIT),
                            "trim or split before it passes the limit"))
        else:
            good += 1
    if not rows:
        rows.append(row("PASS", "size", "scripts", "limit", "%d scripts under %d bytes" % (good, WARN_AT)))
    return rows


def criteria_rows(root):
    script = sibling("workflow-regression", "regression.py")
    if not script:
        return [row("UNREAD", "criteria", "regression", "sync", "regression.py is not installed beside this skill")]
    done = run([sys.executable, script, "sync"], root)
    lines = done.stdout.splitlines()
    if not lines and done.returncode:
        return [row("UNREAD", "criteria", "regression", "sync", (done.stderr.strip() or "no output")[:120])]
    rows, loose = [], 0
    for line in lines:
        gap = re.match(r"^GAP (\S+) (.*)$", line)
        if gap and re.match(r"^[A-Za-z0-9-]+:\d+$", gap.group(1)):
            loose += 1
        elif gap and "criterion has no regression row" in gap.group(2):
            rows.append(row("FAIL", "criteria", gap.group(1), "rows", "criterion has no regression row",
                            "add a row with regression.py add"))
        elif line.startswith(("DRAFT ", "UNPROVEN ")):
            word, key = line.split()[:2]
            rows.append(row("FAIL", "criteria", key.rstrip(":"), "proof", "a draft row, or one never seen failing"
                            if word == "DRAFT" else "never seen failing", "run regression.py red"))
    if loose:
        rows.append(row("WARN", "criteria", "done-lines", "rows", "%d done lines have no regression row" % loose,
                        "regression.py sync --write drafts rows"))
    if not rows and not any(line.startswith("SYNC OK") for line in lines):
        return [row("UNREAD", "criteria", "regression", "sync", (done.stderr.strip() or "no SYNC OK line")[:120])]
    return rows or [row("PASS", "criteria", "rows", "sync", "every criterion and done line has a proven row")]


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
        rows.append(row("WARN" if kind == "STALE" else "FAIL", "docs", page, kind.lower(), detail[:120],
                        "update the page with workflow-docs"))
    return rows


def defect_rows(root):
    defects = sibling_module("defects")
    if not defects:
        return [row("UNREAD", "criteria", "defects", "defect-tests", "defects.py is not installed beside health.py")]
    return [row("FAIL", "criteria", ref, "defect-tests", "closed by %s with no defect test" % source,
                "regression.py add --category defect --link ...") for ref, source in defects.missing(root)]


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
    lean = sibling_module("lean")
    return rows + (lean.rows(root) if lean else [row("UNREAD", "hygiene", "lean.py", "test-time", "lean.py is not installed beside health.py")])


def sibling_module(name):
    sys.path.insert(0, HERE)
    try:
        return __import__(name)
    except ImportError:
        return None
    finally:
        sys.path.pop(0)


def rule_functions():
    """Each rule in RULES -> the function that gives its group's rows for a repo root (what its control calls)."""
    lean = sibling_module("lean")
    groups = {"size": size_rows, "criteria-rows": criteria_rows, "criteria-done": criteria_rows, "defect-tests": defect_rows,
              "docs-check": docs_rows, "findings": hygiene_rows, "waiting": hygiene_rows, "branches": hygiene_rows,
              "cost": cost_rows}
    if lean:
        groups.update({"test-time": lean.test_rows, "worktrees": lean.worktree_rows, "local-branches": lean.branch_rows})
    return {name: groups[name] for name in RULES if name in groups}


def controls_rows(root):
    controls = sibling_module("controls")
    if controls is None:
        return [row("UNREAD", "controls", "controls.py", "control", "controls.py is not installed beside health.py")]
    return controls.run(rule_functions(), HERE)


def mine_rows(root):
    mine = sibling_module("mine")
    return mine.mine_rows(root) if mine else [row("UNREAD", "mine", "mine.py", "mine", "mine.py is not installed beside health.py")]


def cost_rows(root):
    cost = sibling_module("cost")
    return cost.cost_rows(root, HERE) if cost else [row("UNREAD", "cost", "cost.py", "cost", "cost.py is not installed beside health.py")]


def gather(root, family):
    rules = {"size": size_rows, "criteria": lambda root: criteria_rows(root) + defect_rows(root), "docs": docs_rows, "hygiene": hygiene_rows,
             "cost": cost_rows, "mine": mine_rows, "controls": controls_rows}
    rows = []
    for name in (family or ORDER):
        rows += rules[name](root)
    return rows


def groups_of(text):
    """Group names from a --group value (performance is cost), or None for all."""
    names = [{"performance": "cost"}.get(n.strip(), n.strip()) for n in (text or "").split(",") if n.strip()]
    bad = [n for n in names if n not in FAMILY]
    if bad:
        sys.exit("REFUSED: unknown group %s. Groups: %s." % (", ".join(bad), ", ".join(NAMES)))
    return list(dict.fromkeys(names)) or None  # a repeated name (cost,performance) runs once


def report(rows, asked=None):
    """The formal report from report.py; a lone health.py prints the bare rows and a verdict."""
    formal = sibling_module("report")
    if formal:
        built = formal.build(rows, asked)
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
    asked = groups_of(args.group)
    skipped = groups_of(args.skip) or []
    asked = [name for name in (asked or ORDER) if name not in skipped] if skipped else asked
    text, counts, green, verdict, rows = report(gather(root, asked), asked)
    if args.json:
        print(json.dumps({"green": green, "counts": counts, "rows": rows, "verdict": verdict}, indent=2))
    else:
        print("\n".join(text))
    return 0 if green else 1


def cmd_judge(args):
    """The check report, then the judge section. The verdict and exit code are the check's, whatever the judge says."""
    root = repo_root()
    rows = gather(root, None)
    text, _, green, _, _ = report(rows)
    print("\n".join(text))
    print()
    judge = sibling_module("judge")
    if not judge:
        print("JUDGE UNAVAILABLE: judge.py is not installed beside health.py")
        return 0 if green else 1
    try:
        answer, why = judge.ask(judge.gather(root, HERE, rows), root)
        found = judge.parse(answer)
        if not why and not any(found.values()):
            why = "the answer had no tagged line"
        steps = judge.suggestions(root, rows)[1]
        print("\n".join(judge.render(found, steps)) if not why else "JUDGE UNAVAILABLE: " + why)
    except Exception as error:  # the judge is advice: nothing it does may change the verdict
        print("JUDGE UNAVAILABLE: %s" % str(error)[:120])
    return 0 if green else 1


def plan_for(root, asked, with_judge):
    """(file module, acts, groups) for the groups asked, or exit when file.py or gh cannot be used."""
    filing = sibling_module("file") or sys.exit("REFUSED: file.py is not installed beside health.py")
    groups = asked or list(filing.DEFAULT)
    rows = gather(root, None)
    judged, extra = False, []
    if with_judge and "cost" in groups:
        extra, judged = filing.saves(root, HERE, rows)
    issues, why = filing.held(root)
    if issues is None:
        sys.exit("REFUSED: could not read the health issues: %s" % why)
    return filing, filing.plan(rows, issues, groups, extra, judged), groups


def cmd_preview(args):
    """What file would do. Writes nothing; calls the judge only when performance is named."""
    root = repo_root()
    asked = groups_of(args.group)
    if args.live:
        print("NOTE: run and preview never write, even with --live. To write, run: health.py file --group NAME", file=sys.stderr)
    filing, acts, _ = plan_for(root, asked, bool(asked))
    count = filing.preview(acts)
    print("PREVIEW: %d to write, nothing written. To write, run: health.py file --group %s" % (count, args.group or "NAME"))
    return 0


def cmd_file(args):
    root = repo_root()
    asked = groups_of(args.group)
    if not asked:
        sys.exit("REFUSED: file needs --group NAME[,NAME], one of %s. Run preview first." % ", ".join(NAMES))
    filing, acts, groups = plan_for(root, asked, True)
    filing.apply(acts, root, groups)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    item = sub.add_parser("check", help="run the fixed rules")
    item.add_argument("--json", action="store_true")
    item.add_argument("--group", "--family", dest="group", help="one of: " + ", ".join(NAMES))
    item.add_argument("--skip", default="", help="NAME[,NAME]: groups to leave out, such as controls")
    item.set_defaults(func=cmd_check)
    for name in ("judge", "suggest"):
        item = sub.add_parser(name, help="the check report, then a judge section of suggestions")
        item.set_defaults(func=cmd_judge)
    for name, func in (("preview", cmd_preview), ("run", cmd_preview), ("file", cmd_file)):
        item = sub.add_parser(name, help="file findings as issues by group" if name == "file" else "list what file would do")
        item.add_argument("--group", "--family", dest="group", help="NAME[,NAME]: " + ", ".join(NAMES))
        item.add_argument("--live", action="store_true", help=argparse.SUPPRESS)
        item.set_defaults(func=func)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    _controls = sibling_module("controls")
    if _controls and _controls.missing(RULES):  # a new rule must come with its negative control
        print("REFUSED: rule %s has no negative control. Fix: add CONTROLS[\"%s\"] in controls.py" % (
            ", ".join(_controls.missing(RULES)), _controls.missing(RULES)[0]))
        sys.exit(2)
    sys.exit(main())
