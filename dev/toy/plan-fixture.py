#!/usr/bin/env python3
"""Deterministic fixture repos and a plan driver for test-plan-cache.sh (not shipped; stdlib only; no randomness).

  plan-fixture.py gen DEST [--rows N --skills S --modules M --docs D --app F]   one synthetic repo, branch feat/plan
  plan-fixture.py cases DEST [--scripts DIR]                                    the named case repos under DEST
  plan-fixture.py plan SCRIPTS REPO                                             tiers.plan of REPO's land rows, then a RETURN line
  plan-fixture.py golden SCRIPTS WORK                                           cases built in WORK, planned: the golden text
  plan-fixture.py walks SCRIPTS REPO                                            like plan, but os.walk calls go to stderr

A fixed author, committer and date per commit, so a commit id is the same on every machine. Every row is
`bash dev/toy/t<N>.sh`: 70% narrow (a `# reads:` header: a skill's module chain and a doc), 30% wide (no header: a
whole skill folder), and with --app every tenth row also lists the big app/ folder.
"""
import argparse
import os
import subprocess
import sys

CASES = ("narrow", "wide", "mixed", "root", "unmapped", "deleted", "merged", "record", "norecord", "nobase", "detached")
SMALL = dict(rows=12, skills=3, modules=3, docs=3, app=4)
STAMP = [1700000000]


def git(repo, *args, check=True):
    STAMP[0] += 60
    when = "%d +0000" % STAMP[0]
    env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.com", GIT_COMMITTER_NAME="Fixture",
               GIT_COMMITTER_EMAIL="fixture@example.com", GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when,
               GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null", LOOP_NO_GIT_HOOKS="1")
    done = subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"] + list(args), cwd=repo,
                          env=env, capture_output=True, text=True)
    if check and done.returncode:
        sys.exit("git %s failed: %s" % (" ".join(args), done.stderr.strip()))
    return done.stdout.strip()


def put(repo, rel, text):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(text)


def row_script(n, skills, docs, app):
    s, d = n % skills, n % docs
    if n % 10 < 7:
        return "#!/bin/bash\n# reads: skills/s%d/scripts/m0.py docs/d%d.md\npython3 skills/s%d/scripts/m0.py\n" % (s, d, s)
    more = "ls app/ > /dev/null\n" if app and n % 10 == 9 else ""
    return "#!/bin/bash\nls skills/s%d/ > /dev/null\n%s" % (s, more)


def gen(dest, rows, skills, modules, docs, app):
    os.makedirs(dest, exist_ok=True)
    git(dest, "init", "-q", "-b", "main")
    for s in range(skills):
        put(dest, "skills/s%d/SKILL.md" % s, "# s%d\n" % s)
        for m in range(modules):
            tail = "from m%d import value as nxt\n" % (m + 1) if m + 1 < modules else ""
            put(dest, "skills/s%d/scripts/m%d.py" % (s, m), '"""m%d of s%d"""\n%svalue = %d\n' % (m, s, tail, m))
    for d in range(docs):
        put(dest, "docs/d%d.md" % d, "doc %d\n" % d)
    put(dest, "app/a.txt", "a\n")
    put(dest, "app/b.txt", "b\n")
    for f in range(max(app - 2, 0)):
        put(dest, "app/f%d.txt" % f, "file %d\n" % f)
    lines = ["# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n"]
    for n in range(rows):
        put(dest, "dev/toy/t%d.sh" % n, row_script(n, skills, docs, app))
        lines.append("t%d\tland\tbash dev/toy/t%d.sh\tX-1\t2026-01-01\tRow %d works.\tcriterion\t\n" % (n, n, n))
    put(dest, ".loop/regression.tsv", "".join(lines))
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", "base")
    git(dest, "switch", "-q", "-c", "feat/plan")
    put(dest, "skills/s0/scripts/m1.py", '"""m1 of s0"""\nvalue = 99\n')
    put(dest, "docs/d0.md", "doc 0 changed\n")
    git(dest, "add", "-A")
    git(dest, "commit", "-q", "-m", "feature")


def edit(repo, rel, text, message):
    put(repo, rel, text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def save_record(repo, scripts, rows, ids, head):
    """The branch's lane record, written by the real lanes.save of the scripts under test, at a fixed time."""
    sys.path.insert(0, scripts)
    import lanes
    root = git(repo, "rev-parse", "--show-toplevel")
    base = git(repo, "merge-base", "HEAD", "main")
    results = [{"id": i, "state": ("FAIL" if i == "t2" else "PASS"), "seconds": 1.0, "clean": "yes", "host": "fixture",
                "python": "3"} for i in ids]
    lanes.save(lanes.record_path(root), root, "regression.py run land --reuse", results, head, "2024-01-01T00:00:00Z",
               fresh=True, base=base)


def case(dest, name, scripts):
    repo = os.path.join(dest, name)
    gen(repo, **SMALL)
    if name == "wide":
        edit(repo, "skills/s1/SKILL.md", "# s1 changed\n", "wide")
    elif name == "mixed":
        edit(repo, "app/f1.txt", "file 1 changed\n", "app")
    elif name == "root":
        put(repo, "dev/toy/root.sh", '#!/bin/bash\necho "$here" > /dev/null\n')
        with open(os.path.join(repo, ".loop/regression.tsv"), "a") as handle:
            handle.write('root\tland\techo "$here" > /dev/null\tX-1\t2026-01-01\tRoot runs.\tcriterion\t\n')
        edit(repo, "skills/s2/scripts/m0.py", '"""m0 of s2"""\nvalue = 7\n', "root runner")
    elif name == "unmapped":
        edit(repo, "notes/x.txt", "x\n", "unmapped")
    elif name == "deleted":
        git(repo, "rm", "-q", "docs/d1.md")
        git(repo, "commit", "-q", "-m", "delete")
    elif name == "narrow":
        pass
    elif name == "norecord":
        edit(repo, "docs/d2.md", "doc 2 changed\n", "docs")
    elif name == "record" or name == "merged":
        save_record(repo, scripts, None, ["t%d" % n for n in range(SMALL["rows"])], git(repo, "rev-parse", "HEAD"))
        if name == "record":
            edit(repo, "docs/d1.md", "doc 1 changed\n", "after record")
        else:
            git(repo, "switch", "-q", "main")
            edit(repo, "skills/s2/scripts/m0.py", '"""m0 of s2"""\nvalue = 8\n', "main moves")
            git(repo, "switch", "-q", "feat/plan")
            git(repo, "merge", "-q", "--no-edit", "main")
    elif name == "nobase":
        git(repo, "checkout", "-q", "--orphan", "lone")
        git(repo, "commit", "-q", "-m", "No shared history")
        git(repo, "branch", "-q", "-D", "main")
    elif name == "detached":
        git(repo, "switch", "-q", "--detach", "HEAD")
    return repo


def cases(dest, scripts):
    for name in CASES:
        case(dest, name, scripts)
    empty = os.path.join(dest, "empty")
    os.makedirs(empty, exist_ok=True)
    git(empty, "init", "-q", "-b", "main")
    put(empty, ".loop/regression.tsv", "# id\tlevel\tcommand\tgoal\tseen_red\tdescription\tcategory\tlink\n")


def plan(scripts, repo, count_walks=False):
    sys.path.insert(0, scripts)
    os.chdir(repo)
    walked = [0]
    if count_walks:
        real = os.walk

        def counting(*args, **kwargs):
            walked[0] += 1
            return real(*args, **kwargs)
        os.walk = counting
    import regression
    import tiers
    from runs import chosen
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    rows = chosen(regression.read_rows(root), "land")
    todo, reused, old, full = tiers.plan(root, rows, regression.lanes.record_path(root))
    print("RETURN todo=%s reused=%s old=%s full=%s" % (
        ",".join(todo), ",".join(reused), (old["commit"] + " " + old["at"]) if old else "none", full))
    if count_walks:
        print("WALKS %d" % walked[0], file=sys.stderr)


def golden(scripts, work):
    cases(work, scripts)
    here = os.path.abspath(__file__)
    for name in CASES:
        print("== " + name)
        sys.stdout.flush()
        done = subprocess.run([sys.executable, "-B", here, "plan", scripts, os.path.join(work, name)],
                              capture_output=True, text=True)
        sys.stdout.write(done.stdout)
        if done.returncode:
            sys.stdout.write("EXIT %d\n%s" % (done.returncode, done.stderr.splitlines()[-1:] and done.stderr.splitlines()[-1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=("gen", "cases", "plan", "golden", "walks"))
    ap.add_argument("a")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--scripts")
    for key, val in dict(rows=1500, skills=40, modules=30, docs=200, app=3000).items():
        ap.add_argument("--" + key, type=int, default=val)
    args = ap.parse_args()
    if args.mode == "gen":
        gen(args.a, args.rows, args.skills, args.modules, args.docs, args.app)
    elif args.mode == "cases":
        cases(args.a, os.path.abspath(args.scripts or args.b))
    elif args.mode in ("plan", "walks"):
        plan(os.path.abspath(args.a), os.path.abspath(args.b), args.mode == "walks")
    else:
        golden(os.path.abspath(args.a), os.path.abspath(args.b))


if __name__ == "__main__":
    main()
