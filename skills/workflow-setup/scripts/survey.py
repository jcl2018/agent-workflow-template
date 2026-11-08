#!/usr/bin/env python3
"""Survey a git repo for setup: what it holds, and what adopting it would add or convert.

usage: survey.py [--repo DIR]

Prints the FOUND line and the add:/convert:/skip:/no fit: plan that setup.py would apply. Read-only.
"""
import argparse
import json
import os
import re
import subprocess
import sys

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


def runs_tests(repo, files, cmd):
    """None when the command can run tests, else why it cannot (a static check: nothing is executed)."""
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
    if re.search(r"unittest|pytest", cmd):
        folder = re.search(r"-s\s+(\S+)", cmd)
        base = (folder.group(1) if folder else "").strip("./")
        if not any(os.path.basename(f).startswith("test") or f.endswith("_test.py") for f in files if f.endswith(".py") and f.startswith(base)):
            return "no test files under %s" % (base or "the repo")
    return None


def checks(repo, files):
    """(checks, notes): the repo's real test commands, CI first, and why each dropped candidate was dropped."""
    has = lambda name: os.path.exists(os.path.join(repo, name))
    pyfiles = [f for f in files if os.path.basename(f).startswith("test_") and f.endswith(".py")]
    guesses = []
    if has("package.json"):
        guesses.append("npm test")
    if has("Makefile"):
        guesses.append("make test")
    guesses += [c for c, ok in (("cargo test", has("Cargo.toml")), ("go test ./...", has("go.mod")),
                                ("python3 -m pytest -q", has("pytest.ini"))) if ok]
    guesses += ["python3 -m unittest discover -s " + f for f in ("tests", "test") if has(f)]
    if pyfiles:
        guesses.append("python3 -m unittest discover" + (" -s " + os.path.dirname(pyfiles[0]) if os.path.dirname(pyfiles[0]) else ""))
    elif has("pyproject.toml"):
        guesses.append("python3 -m unittest discover")
    guesses += ["bash " + n for n in ("scripts/validate.sh", "scripts/test.sh", "test.sh") if has(n)]
    keep, notes = [], []
    for cmd in ci_commands(repo, files):
        why = runs_tests(repo, files, cmd)
        notes.append("dropped CI command '%s': %s" % (cmd, why)) if why else keep.append(cmd)
    if keep:
        return keep, notes
    for cmd in guesses:
        why = runs_tests(repo, files, cmd)
        if not why:
            return [cmd], notes
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
    """(path, exception line) for each path .gitignore would keep out of the setup commit."""
    found = []
    for path in paths:
        parts = path.split("/")
        for size in range(1, len(parts) + 1):
            part = "/".join(parts[:size])
            if subprocess.run(["git", "-C", repo, "check-ignore", "-q", "--no-index", part]).returncode == 0:
                found.append((path, "!" + part + ("/" if size < len(parts) else "")))
                break
    return found


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
