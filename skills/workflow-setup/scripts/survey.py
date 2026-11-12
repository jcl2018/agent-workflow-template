#!/usr/bin/env python3
"""Survey a git repo for setup: what it holds, and what adopting it would add or convert.

usage: survey.py [--repo DIR]

Prints the FOUND line and the add:/convert:/skip:/no fit: plan that setup.py would apply. Read-only.
"""
import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings  # noqa: E402

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
if not sys.stdin or not sys.stdin.isatty():
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)

CODE = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".c", ".cc", ".cpp", ".h", ".sh", ".swift", ".kt", ".php"}
NOT_AREAS = {"docs", "doc", "test", "tests", "dist", "build", "node_modules", "vendor", "scripts", "dev", "examples", "tools"}
MARKER = "<!-- workflow-docs -->"
CONTAINERS = {"packages", "apps", "services", "src", "lib", "modules", "cmd", "crates", "internal", "pkg"}
HEADING = re.compile(r"^#{1,4}\s*(?:Milestone|Track|Phase|Feature)s?\s*[\w.]*\s*[:\u2013\u2014-]\s*(.+?)\s*$", re.I | re.M)
RUN = re.compile(r"^\s*(?:-\s+)?run:\s*(\S.*?)\s*$")
TESTY = re.compile(r"^(\S+=\S+\s+)*(python3? -m )?(pytest|unittest|npm (run )?test|yarn test|pnpm test|make test|cargo test|go test|rspec|phpunit)\b|"
                   r"^(bash |sh |\./|python3? )\S*test\S*\.(sh|py)\b")


def git(repo, *args):
    done = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else ""


def page_name(folder):
    name = re.sub(r"[^A-Za-z0-9-]+", "-", folder).strip("-")
    return name[:1].upper() + name[1:]


def read(repo, rel):
    try:
        with open(os.path.join(repo, rel), errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def ci_commands(repo, files):
    """Single-line run: commands in the CI workflows that run tests. Matrix, working-directory and multiline blocks are skipped."""
    found = []
    for rel in files:
        if not re.match(r"\.github/workflows/[^/]+\.ya?ml$", rel):
            continue
        text = read(repo, rel) or ""
        if "working-directory" in text:
            continue
        for line in text.splitlines():
            match = RUN.match(line)
            if match and match.group(1) not in ("|", ">", "|-", ">-") and "${{" not in match.group(1):
                found += [c.strip() for c in match.group(1).split("&&") if TESTY.search(c)]
    return list(dict.fromkeys(found))


def py_tests(files, base, pats):
    """The .py files under base whose name matches one of the runner's patterns."""
    base = base.strip("./")
    return [f for f in files if f.endswith(".py") and (not base or f.startswith(base + "/"))
            and any(fnmatch.fnmatch(os.path.basename(f), p) for p in pats)]


def runs_tests(repo, files, cmd):
    """None when the command finds a test by its runner's real pattern, else why not (static; nothing runs)."""
    has = lambda name: os.path.exists(os.path.join(repo, name))
    for word in cmd.split():
        if word.endswith((".sh", ".py")) and "/" in word or word.startswith("./"):
            if not has(word):
                return "%s is not in the repo" % word
    if re.search(r"npm (run )?test|yarn test|pnpm test", cmd):
        try:
            if "no test specified" in (json.loads(read(repo, "package.json") or "{}").get("scripts", {}).get("test") or "no test specified"):
                return "package.json has no real test script"
        except ValueError:
            return "package.json does not parse"
    if "make test" in cmd and not any(l.startswith("test:") for l in (read(repo, "Makefile") or "").splitlines()):
        return "the Makefile has no test target"
    folder, pat = re.search(r"-s\s+(\S+)", cmd), re.search(r"-p\s+'?\"?([^'\"\s]+)", cmd)
    base = folder.group(1) if folder else ""
    if "unittest" in cmd and not py_tests(files, base, [pat.group(1) if pat else "test*.py"]):
        return "no test files match %s under %s" % (pat.group(1) if pat else "test*.py", base or "the repo")
    if "pytest" in cmd and not py_tests(files, base, ["test_*.py", "*_test.py"]):
        return "no test files under %s" % (base or "the repo")
    if "go test" in cmd and not any(f.endswith("_test.go") for f in files):
        return "no *_test.go files"
    if "cargo test" in cmd and not (any(f.startswith("tests/") and f.endswith(".rs") for f in files)
                                    or any(f.endswith(".rs") and "#[test]" in (read(repo, f) or "") for f in files)):
        return "no #[test] and no tests/ file"
    return None


def py_guess(repo, files):
    """The python test command for the repo's test files, by their content (unittest or pytest style)."""
    found = py_tests(files, "", ["test*.py", "*_test.py"])
    if not found:
        return []
    base = os.path.dirname(found[0])
    here = [f for f in found if os.path.dirname(f) == base]
    if any("unittest" in (read(repo, f) or "") for f in here):
        plain = any(fnmatch.fnmatch(os.path.basename(f), "test*.py") for f in here)
        return ["python3 -m unittest discover" + (" -s " + base if base else "") + ("" if plain else " -p '*_test.py'")]
    return ["python3 -m pytest -q"] if shutil.which("pytest") else []


def checks(repo, files):
    """(checks, notes): the repo's real test commands, CI first, and why each dropped candidate was dropped."""
    has = lambda name: os.path.exists(os.path.join(repo, name))
    guesses = []
    if has("package.json"):
        guesses.append("npm test")
    if has("Makefile"):
        guesses.append("make test")
    guesses += [c for c, ok in (("cargo test", has("Cargo.toml")), ("go test ./...", has("go.mod")),
                                ("python3 -m pytest -q", has("pytest.ini"))) if ok]
    guesses += py_guess(repo, files)
    guesses += ["bash " + n for n in ("scripts/validate.sh", "scripts/run-tests.sh", "scripts/test.sh", "tests/run.sh", "test.sh") if has(n)]
    keep, notes = [], []
    for cmd in ci_commands(repo, files):
        why = runs_tests(repo, files, cmd)
        notes.append("dropped CI command '%s': %s" % (cmd, why)) if why else keep.append(cmd)
    if keep:
        return keep, notes
    for cmd in dict.fromkeys(guesses):
        why = runs_tests(repo, files, cmd)
        if not why:
            return [cmd], notes + ["%s inferred from file names, not run" % cmd] * bool(re.search(r"unittest|pytest|go test", cmd))
        notes.append("dropped '%s': %s" % (cmd, why))
    return [], notes


def features(repo, files, wiki):
    """name -> path of the repo's own features: milestone or track headings, else folders with code in them."""
    for rel in ("ROADMAP.md", "docs/ROADMAP.md", "roadmap.md", "README.md"):
        names = [page_name(m) for m in HEADING.findall(read(repo, rel) or "")]
        names = [n for n in dict.fromkeys(names) if n]
        if names:
            return {n: rel for n in names}
    count = {}
    for f in files:
        parts = f.split("/")
        if len(parts) < 2 or parts[0].startswith(".") or parts[0] in NOT_AREAS or os.path.splitext(f)[1] not in CODE:
            continue
        key = "/".join(parts[:2]) if parts[0] in CONTAINERS and len(parts) > 2 else parts[0]
        count[key] = count.get(key, 0) + 1
    return {page_name(k): k for k, n in sorted(count.items()) if not k.startswith(wiki.split("/")[0] + "/")}


def version_habit(repo, files):
    """(version_file, notes): where the repo keeps its version, and how its changelog reads."""
    notes, where = [], None
    for rel in ("VERSION", "package.json", "pyproject.toml", "Cargo.toml"):
        if rel in files and (rel == "VERSION" or re.search(r'^\s*"?version"?\s*[:=]\s*"[\d.]+', read(repo, rel) or "", re.M)):
            where = rel
            break
    if where:
        notes.append("version lives in %s" % where)
    elif git(repo, "tag"):
        notes.append("version lives in git tags only (last %s); set \"version_file\" if a file holds it" % git(repo, "tag").splitlines()[-1])
    log = next((f for f in files if f.lower() in ("changelog.md", "changes.md", "history.md")), None)
    if log:
        head = re.search(r"^## .*$", read(repo, log) or "", re.M)
        notes.append("changelog %s, entries read like '%s'" % (log, head.group(0) if head else "none yet"))
    else:
        notes.append("no changelog; the release step will start CHANGELOG.md")
    return where, notes


def ignored(repo, paths):
    """(path, exception line) pairs, as an older setup.py reads them."""
    return [(p, line) for p, line, _ in blocked(repo, paths)]


def blocked(repo, paths):
    """(path, exception line, source ignore file) for each path an ignore rule keeps out of the setup commit."""
    found, tracked = [], set(git(repo, "ls-files").splitlines())
    for path in paths:
        if path in tracked:
            continue
        parts = path.split("/")
        for size in range(1, len(parts) + 1):
            part = "/".join(parts[:size])
            done = subprocess.run(["git", "-C", repo, "check-ignore", "-v", "--no-index", part], capture_output=True, text=True)
            rule = done.stdout.split("\t")[0].split(":", 2)  # source, line, pattern; a !pattern match is an exception, not a block
            if done.returncode == 0 and not rule[-1].startswith("!"):
                found.append((path, "!" + (rule[-1] if rule[-1].endswith("/") else part + ("/" if size < len(parts) else "")), rule[0]))
                break
    return found


def own_ignore(source):
    """True for a .gitignore of the repo, not .git/info/exclude or the owner's global excludes."""
    return bool(source) and not os.path.isabs(source) and not source.startswith(".git/") and os.path.basename(source) == ".gitignore"


def guards(repo, files):
    """The repo's hook and guard files that mention .tsv (one that refuses tracked data would refuse setup's commit)."""
    hooks = git(repo, "rev-parse", "--git-path", "hooks")
    cands = [f for f in files if re.match(r"\.(githooks|husky)/[^_]", f) or f == ".pre-commit-config.yaml"
             or re.search(r"(guard|hook)", os.path.basename(f), re.I) and f.endswith((".sh", ".py"))]
    if hooks and os.path.isdir(os.path.join(repo, hooks)):
        cands += [os.path.join(hooks, n) for n in sorted(os.listdir(os.path.join(repo, hooks))) if not n.endswith(".sample")]
    return [f for f in dict.fromkeys(cands) if ".tsv" in (read(repo, f) or "")]


PORTABLE = ("parallel", "max_tries", "cadence", "criteria", "criteria_max", "review_depth", "token_budget", "step_limit", "goal_levels",
            "ci_levels", "pool_size", "digest_mail", "regression_cron", "health_cron", "feature_labels", "stale_branch_days",
            "silent_minutes", "goal_lane_minutes", "test_budget_minutes", "prep_budget_minutes", "step_budget_minutes", "risky_paths")
HELD = ("auto_approve", "auto_merge", "full_auto", "mend", "resume_on_limit", "pr_bumps_version", "reply_hook", "govern_hook",
        "agent_files", "routines")
ENUMS = {"goal_levels": ("land", "nightly"), "ci_levels": ("nightly", "land"), "digest_mail": ("cloudflare", "smtp", "off"),
         "review_depth": ("full", "condensed")}


def fits(key, value, default):
    """Whether a borrowed value has the settings table's type and range."""
    if type(value) is not type(default) and not (key == "cadence" and isinstance(value, (int, str))):
        return False
    if key in ENUMS:
        return value in ENUMS[key]
    if key == "criteria_max":
        return 1 <= value <= 50
    if key.endswith("_budget_minutes"):
        return value >= 15
    if key == "risky_paths":
        try:
            return all(isinstance(r, str) and len(r) <= 200 and re.compile(r) for r in value)
        except re.error:
            return False
    return True


def borrow(model, defaults, private_value, allow=()):
    """(values, lines): an adopted repo's portable settings, read-only, as borrow:/held:/skip:/adapt: lines; a value holding a
    private value is never printed, and a held key is taken only when allow names it."""
    root = os.path.realpath(model)
    path = os.path.realpath(os.path.join(root, ".loop", "config.json"))
    try:
        if not path.startswith(root + os.sep):
            raise ValueError("its config.json leaves the repo")
        with open(path) as handle:
            theirs = json.load(handle)
        if not isinstance(theirs, dict):
            raise ValueError("config.json is not an object")
    except (OSError, ValueError) as error:
        return None, ["REFUSED: --from %s is not an adopted repo (%s)" % (model, error)]
    values, lines = {}, []
    for key in PORTABLE + HELD:
        if key not in theirs or theirs[key] == defaults.get(key):
            continue
        value, shown = theirs[key], json.dumps(theirs[key])
        take = key in PORTABLE or key in allow
        if private_value(shown):
            lines.append("skip: %s holds a private value" % key if key in PORTABLE else "held: %s (holds a private value; not shown)" % key)
        elif not fits(key, value, defaults.get(key)):
            lines.append("skip: %s = %s (not a valid value here)" % (key, shown))
        elif take:
            values[key] = value
            lines.append("borrow: %s = %s" % (key, shown))
        else:
            lines.append("held: %s = %s (unattended or runs code; add --allow %s to take it)" % (key, shown, key))
    lines += ["NOTE: %s is not held; nothing to allow" % k for k in allow if k not in HELD]
    for key in theirs.get("milestones") or []:
        lines.append("skip: milestone %s (free form, none made)" % (key.get("title") if isinstance(key, dict) else key))
    model_pages = [l.split("\t")[0] for l in (read(root, ".loop/docs.tsv") or "").splitlines() if l.strip() and not l.startswith("#")]
    lines.append("adapt: pages follow this repo's own areas; the model has " + (", ".join(p for p in model_pages if p != "Home") or "none"))
    lines.append("NOTE: your local layer already applies here (no private file was read)")
    return values, lines


def survey(repo, config):
    """What the repo holds. config is the merged .loop/config.json."""
    files = git(repo, "ls-files").splitlines()
    wiki = config.get("wiki_dir") or "docs/wiki"
    held = {}
    for line in (read(repo, ".loop/docs.tsv") or "").splitlines():
        if line.strip() and not line.startswith("#") and line.split("\t")[0] != "Home":
            held[line.split("\t")[0]] = line.partition("\t")[2].split(",")[0].strip() or "README.md"
    pages = {os.path.basename(f)[:-3]: f for f in files if f.startswith(wiki + "/") and f.endswith(".md") and f.count("/") == wiki.count("/") + 1}
    tests = [f for f in files if re.search(r"(^|/)(tests?|spec)(/|_)|(^|/)test_|_test\.|\.test\.", f)]
    return {"kind": "new" if len(files) < 3 else "existing", "files": len(files), "wiki": wiki, "pages": pages,
            "areas": held or features(repo, files, wiki), "tests": len(tests), "readme": read(repo, "README.md"),
            "tags": git(repo, "tag").splitlines(), "version": (read(repo, "VERSION") or "").strip(),
            "ci": [f for f in files if f.startswith(".github/workflows/")]}


def found_line(found, config):
    return "FOUND: %s repo, base %s, %d files, checks %s, areas %s, %d test files, tags %s, CI %s" % (
        found["kind"], config["base"], found["files"], config["checks"] or "none", ", ".join(found["areas"]) or "none",
        found["tests"], ", ".join(found["tags"][-3:]) or "none", len(found["ci"]) or "none")


CRITERION = re.compile(r"[A-Z]{2,5}(?=-\d+:)")
PLACEHOLDER = "Write this page from what is really in the repo."


def prefixes(repo, found):
    used = set()
    for rel in found["pages"].values():
        used |= set(CRITERION.findall(read(repo, rel) or ""))
    return used


def pick(name, used):
    letters = re.sub(r"[^A-Za-z]", "", name).upper() or "FT"
    for size in (3, 4, 5):
        if letters[:size] not in used and len(letters[:size]) >= 2:
            used.add(letters[:size])
            return letters[:size]
    used.add("FT")
    return "FT"


def summary_of(found, name):
    if name == "Home" and found["readme"]:
        for line in found["readme"].splitlines():
            if line.strip() and not line.startswith(("#", "!", "[", "<", "|", "```")):
                return line.strip()[:240]
    return PLACEHOLDER


def mapping(found):
    rows = {"Home": ["README.md"]}
    rows.update({name: [folder] for name, folder in found["areas"].items()})
    return rows


def precheck(repo, branch):
    """The refusal line when the repo's state makes an adoption unsafe, else None."""
    gd = git(repo, "rev-parse", "--absolute-git-dir")
    busy = [n for n in ("MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD", "REVERT_HEAD") if os.path.exists(os.path.join(gd, n))]
    other = [w for w in git(repo, "worktree", "list", "--porcelain").split("\n\n") if "branch refs/heads/%s" % branch in w.split("\n")
             and os.path.realpath(w.split("\n")[0][9:]) != os.path.realpath(repo)]
    if busy or other or not (git(repo, "symbolic-ref", "--quiet", "HEAD") and git(repo, "rev-parse", "--verify", "--quiet", "HEAD")):
        return ("REFUSED: a merge, rebase or cherry-pick is in progress, HEAD is detached or has no commit, or %s is checked out in another "
                "worktree (SETUP_REPO_STATE). Fix: finish or abort it, or switch away; nothing written." % branch)
    if git(repo, "rev-list", "--count", "HEAD..refs/heads/" + branch) not in ("", "0"):
        return "REFUSED: branch %s has commits HEAD lacks (SETUP_BRANCH_DIVERGED). Fix: git switch %s, or git branch -D %s; nothing written." % ((branch,) * 3)


def file_issues(repo, no_issues, count=0):
    """Open or link an issue per Adoption row (health.py file --open-only) when gh is signed in and origin is on GitHub."""
    found = re.search(r"github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?/?$", git(repo, "remote", "get-url", "origin"))
    py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "workflow-health", "scripts", "health.py")
    if no_issues or os.environ.get("LOOP_NO_ISSUES") == "1" or not (found and os.path.exists(py) and shutil.which("gh") and
                                                                          subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0):
        return print("NOTE: %d items left in .loop/findings.md; file them with workflow-health file --group adoption (SETUP_NOT_FILED)" % count) or 0
    print("FILING to %s: labels health, health:adoption" % found.group(1))
    done = subprocess.run([sys.executable, py, "file", "--group", "adoption", "--open-only"], cwd=repo, capture_output=True, text=True,
                          env=dict(os.environ, GH_REPO=found.group(1)))
    lines = ["[line withheld: holds a private value]" if settings.private_value(l) else l for l in done.stdout.splitlines()]
    print("\n".join(lines))
    ok = [l for l in lines if l.startswith("DONE") or l.startswith("SAME")]
    if done.returncode or any(l.startswith("FAILED") for l in lines):
        print("NOTE: filing failed after %d of %d issues; run workflow-health file --group adoption --open-only to finish, marks dedupe (SETUP_FILING)"
              % (len(ok), len([l for l in lines if l.split(" ")[0] in ("DONE", "SAME", "FAILED")])))
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = git(args.repo, "rev-parse", "--show-toplevel")
    if not repo:
        sys.exit("REFUSED: not inside a git repo.")
    config = json.loads(read(repo, ".loop/config.json") or "{}")
    config.setdefault("base", "main")
    config.setdefault("checks", [])
    print(found_line(survey(repo, config), config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
