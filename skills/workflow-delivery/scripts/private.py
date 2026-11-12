#!/usr/bin/env python3
"""The private-name scan: nothing private ships (DEL-9). Every push or GitHub write in delivery, release and monitoring
runs it first; setup's git hooks run it as `hook staged | message FILE | push`.

usage: private.py where                 say whether this is a goal worktree (a worker may push only loop/<slug>)
       private.py check                 say where the list is and how many patterns it holds
       private.py scan [--base REF]     scan this branch from REF (default origin/<base>) to HEAD

The list lives outside the repo: `$LOOP_PRIVATE_NAMES` (a file path) or `~/.workflow-loop/private-names`, one regular
expression per line, matched without case; `#` starts a comment. No file: the scan passes and says nothing was checked.
Only comments: off on purpose. A file that can't be read or holds a bad pattern: every scan refuses.

A scan reads the branch name, changed file names, the added lines and message of every commit from the base to HEAD
(a name added and removed later still counts), and named texts. A hit names its place and list line, never the text.
"""
import os
import re
import signal
import subprocess
import sys
import time

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

LOCAL_PATH = re.compile(r"(?<![\w/.:~])/(?:Users|home|private|var|tmp|mnt|opt|srv|root|etc|usr|Volumes)(?:/[\w.@+-]+)+")
HOME_DIR = re.compile(r"(?:file://)?/(?:Users|home)/[^/\s]+")


def plain(text):
    """Local absolute paths cut to their last part (a home folder alone to ~): findings go in a pull request."""
    text = HOME_DIR.sub("/mnt/u", text)  # the account name never survives, whatever follows it
    return LOCAL_PATH.sub(lambda m: m.group(0).split("/")[-1] if m.group(0).count("/") > 2 else "~", text)


def mend(git, files, base):
    """A merge that conflicts only in generated files is resolved here: the regression tsv files union (a row both sides
    changed, or one side deleted, stays a real conflict), Tests.md takes the base's page and is re-rendered from the rows.
    Else False, nothing kept (the caller aborts the merge)."""
    import tempfile  # lazily: only a conflict needs it
    top, tsv = git("rev-parse", "--show-toplevel").stdout.strip(), (".loop/regression.tsv", ".loop/regression-runs.tsv")
    page = lambda f: os.path.basename(f) == "Tests.md" and os.path.dirname(f).endswith("wiki")
    criteria = os.path.join(HERE, "..", "..", "workflow-docs", "scripts", "criteria.py")
    if not files or not all(f in tsv or page(f) for f in files):
        return False
    if any(page(f) for f in files) and not (os.path.exists(top + "/.loop/docs.tsv") and os.path.exists(criteria)):
        return False
    for f in files:
        s = [git("show", ":%d:%s" % (n, f)) for n in (1, 2, 3)]
        if s[1].returncode or s[2].returncode:
            return False
        if f not in tsv:
            git("checkout", "--theirs", "--", f)
            continue
        with tempfile.TemporaryDirectory() as tmp:
            for n, r in zip("abc", (s[1], s[0], s[2])):
                open(tmp + "/" + n, "w").write(r.stdout if not r.returncode else "")
            union = subprocess.run(["git", "merge-file", "-p", "--union"] + [tmp + "/" + n for n in "abc"],
                                   capture_output=True, text=True).stdout
        rows = lambda t: {l.split("\t")[0]: l for l in t.splitlines() if l and l[0] != "#"}
        b, o, t = rows(s[0].stdout if not s[0].returncode else ""), rows(s[1].stdout), rows(s[2].stdout)
        if any(k not in o or k not in t for k in b):
            return False
        out, at = [], {}
        for line in union.splitlines():
            k = line.split("\t")[0]
            if line[0:1] == "#" or not line or k not in at:
                at[k] = len(out)
                out.append(line)
            elif line != out[at[k]]:
                if f != tsv[1] or line.split("\t")[2:3] == out[at[k]].split("\t")[2:3]:
                    return False
                out[at[k]] = max(line, out[at[k]], key=lambda l: l.split("\t")[2:3])
        open(top + "/" + f, "w").write("\n".join(out) + "\n")
    if any(page(f) for f in files):
        if subprocess.run([sys.executable, criteria, "render"], cwd=top, capture_output=True).returncode:
            return False
        git("add", "-u")
    if git("add", "--", *files).returncode or git("commit", "--no-edit", "-q").returncode:
        return False
    print("MENDED %s: rows unioned, Tests.md taken from %s and re-rendered" % (", ".join(files), base))
    return True


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = "~/.workflow-loop/private-names"
LIMIT, WIDTH = 60, 4096  # seconds for a whole scan (git included), characters per matched piece of a line
PRIVATE_NAME, PRIVATE_LIST = "PRIVATE_NAME", "PRIVATE_LIST"
WORKER_PUSH, WORKER_PUSH_INTERNAL = "WORKER_PUSH", "WORKER_PUSH_INTERNAL"


def source():
    """(path to open, the name shown)."""
    given = os.environ.get("LOOP_PRIVATE_NAMES")
    return (given, "$LOOP_PRIVATE_NAMES") if given else (os.path.expanduser(DEFAULT), DEFAULT)


def patterns():
    """(state, [(list line, compiled)], error); state: none, off, on or broken."""
    path, shown = source()
    if not os.path.exists(path):
        if os.environ.get("LOOP_PRIVATE_NAMES"):  # a list named on purpose that isn't there is a typo, not "no list"
            return "broken", [], "%s names a file that doesn't exist" % shown
        return "none", [], ""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return "broken", [], "%s can't be read (%s)" % (shown, type(error).__name__)
    found = []
    for number, line in enumerate(lines, 1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        try:
            found.append((number, re.compile(text, re.I)))
        except re.error:
            return "broken", [], "%s line %d isn't a valid pattern" % (shown, number)
    return ("on" if found else "off"), found, ""


def git(top, *args, stop=None):
    try:
        done = subprocess.run(["git", "-c", "core.quotepath=off"] + list(args), cwd=top, capture_output=True, text=True, errors="replace",
                              timeout=max(1, (stop or time.time() + LIMIT) - time.time()))
    except subprocess.TimeoutExpired:
        raise RuntimeError("git %s passed the %d second limit" % (" ".join(args[:2]), LIMIT))
    if done.returncode:
        raise RuntimeError("git %s failed: %s" % (" ".join(args[:2]), done.stderr.strip()[:200]))
    return done.stdout


def added(rows, tag):
    """(place, text) for each added line of a -U0 diff."""
    path, line, header = "", 0, False
    for row in rows:
        if row.startswith("diff "):
            header = True
        elif header and row.startswith("+++ "):
            path = row[6:] if row.startswith("+++ b/") else row[4:]
        elif row.startswith("@@"):
            header, hunk = False, re.search(r"\+(\d+)", row)
            line = int(hunk.group(1)) if hunk else 0
        elif row.startswith("+") and path and not header:
            yield "%s:%d (%s)" % (path, line, tag), row[1:]
            line += 1


def commit_places(top, sha, stop=None):
    for line in git(top, "log", "-1", "--format=%B", sha, stop=stop).splitlines():
        yield "commit:%s message" % sha[:7], line
    yield from added(git(top, "show", "--format=", "--no-color", "--no-ext-diff", "-U0", sha, stop=stop).splitlines(),
                     "commit:" + sha[:7])


def places(top, base, stop=None, head="HEAD"):
    """(place, text) for everything a push from base to head would publish."""
    branch = git(top, "branch", "--show-current", stop=stop).strip() if head == "HEAD" else head.split("/", 1)[-1]
    if branch:
        yield "branch", branch
    for name in git(top, "diff", "--name-only", "--no-renames", base + "..." + head, stop=stop).splitlines():
        yield "file name " + name, name
    for sha in git(top, "rev-list", "--reverse", base + ".." + head, stop=stop).split():
        yield from commit_places(top, sha, stop)


def windows(text):
    """Overlapping WIDTH-character pieces."""
    return [text[at:at + WIDTH] for at in range(0, max(len(text), 1), WIDTH - 256)]


def shown_place(place, found):
    """The place as a hit names it, masked."""
    for _, pattern in found:
        place = pattern.sub("<private>", place)
    return place


def scan(top, base, texts=None, head="HEAD", items=None):
    """{"state": clean|hit|none|off|broken, "hits": [...], "note": str}. base None scans only the texts; head is the
    branch tip (merge.py passes the goal's pushed branch); items(stop) yields (place, text) in place of the branch."""
    state, found, error = patterns()
    shown = source()[1]
    if state != "on":
        return {"state": state, "hits": [], "note": error or "Private-name scan: %s." % (
            "no list at %s, nothing was checked" % shown if state == "none" else "off on purpose (%s holds only comments)" % shown)}
    hits, rows, stop = [], [], time.time() + LIMIT
    if base or items:
        try:
            rows = list(items(stop) if items else places(top, base, stop, head))
        except RuntimeError as failed:
            return {"state": "broken", "hits": [], "note": "the scan couldn't read the branch: %s" % failed}
    for name, text in (texts or {}).items():
        rows += [("%s:%d" % (name, number), line) for number, line in enumerate((text or "").splitlines() or [""], 1)]
    for place, text in rows:
        if time.time() > stop:
            return {"state": "broken", "hits": hits, "note": "the scan passed its %d second limit" % LIMIT}
        for number, pattern in found:
            if any(pattern.search(piece) for piece in windows(text)):
                hits.append("%s matches list line %d" % (shown_place(place, found), number))
                break
    note = "Private-name scan: %d pattern%s from %s, %s." % (
        len(found), "" if len(found) == 1 else "s", shown, "%d hit%s" % (len(hits), "" if len(hits) == 1 else "s") if hits else "clean")
    return {"state": "hit" if hits else "clean", "hits": hits, "note": note}


def refusal(result, base="the base branch", pushed=False):
    """(why, fix, code) when the result must stop a push."""
    if result["state"] == "broken":
        return ("the private-name list or scan is broken: %s; nothing was pushed" % result["note"],
                "repair the list (private.py check names the line), then run the command again", PRIVATE_LIST)
    if result["state"] != "hit":
        return None
    shown = "; ".join(result["hits"][:8]) + (" and %d more" % (len(result["hits"]) - 8) if len(result["hits"]) > 8 else "")
    if pushed:
        fix = ("the branch is already on origin: the owner decides how to rewrite it (the loop never force-pushes); for a "
               "false positive, edit that line of the list")
    else:
        fix = ("remove the text, then squash so no commit keeps it: git reset --soft $(git merge-base HEAD %s) && git "
               "commit -m \"<goal>\", and run the command again; for a false positive, edit that line of the list" % base)
    return "a private name would be pushed: %s; nothing was pushed" % shown, fix, PRIVATE_NAME


def where():
    """(slug, why): the goal a worktree under <common>/loop/worktrees/ belongs to, else (None, why); (None, None) if unsure.
    Location only: LOOP_ROLE is never read (the release step sets it too)."""
    for attempt in range(2):
        done = subprocess.run(["git", "rev-parse", "--is-inside-work-tree", "--git-common-dir", "--show-toplevel"],
                              capture_output=True, text=True)
        if done.returncode == 0 and len(done.stdout.split("\n")) >= 3:
            break
    else:
        return None, None
    inside, common, top = done.stdout.split("\n")[:3]
    if inside != "true":
        return None, "not inside a work tree"
    root = os.path.realpath(os.path.join(os.getcwd(), common)) + os.sep + "loop" + os.sep + "worktrees" + os.sep
    top = os.path.realpath(top) + os.sep
    return (top[len(root):].split(os.sep)[0], "") if top.startswith(root) else (None, "not a goal worktree")


def worker_push(lines):
    """(why, fix, code) when a goal worker's push must stop, else None. A worker may push only refs/heads/loop/<slug>."""
    slug, why = where()
    if slug is None and why is None:
        return ("the worker-branch check could not read where this push runs; nothing was pushed",
                "run private.py where in this folder to see why, then tell the owner; do not use --no-verify", WORKER_PUSH_INTERNAL)
    if slug is None or not any(row.strip() for row in lines):
        return None
    for row in lines:
        if not row.strip():
            continue
        parts = row.split()
        if len(parts) != 4:
            return ("the worker-branch check could not read git's ref line; nothing was pushed",
                    "run private.py where in this folder to see why, then tell the owner; do not use --no-verify",
                    WORKER_PUSH_INTERNAL)
        if parts[2] != "refs/heads/loop/" + slug or not parts[1].strip("0"):
            return ("a worker session for goal %s may push only loop/%s (expected ref refs/heads/loop/%s; the worktree folder "
                    "must equal the goal slug), not %s; nothing was pushed" % (slug, slug, slug, parts[2] if parts[1].strip("0") else "a deletion of " + parts[2]),
                    "push your own branch (goal.py pr %s); only the operation session publishes to main (merge.py), and another "
                    "goal's branch is pushed from that goal's own worktree" % slug, WORKER_PUSH)
    return None


def hook_items(mode, arg):
    def run(stop):
        if mode == "staged":
            for name in git(".", "diff", "--cached", "--name-only", "-z", "--no-renames", stop=stop).split("\0")[:-1]:
                yield "file name " + name, name
            yield from added(git(".", "diff", "--cached", "-U0", "--no-color", "--no-ext-diff", "--no-renames",
                                 stop=stop).splitlines(), "staged")
        elif mode == "message":
            char = git(".", "config", "--default", "#", "core.commentChar", stop=stop).strip()
            char = "#" if char == "auto" else char[:1]  # auto: its comment lines are scanned
            for row in open(arg, errors="replace").read().splitlines():
                if row.startswith(char + " ------------------------ >8"):
                    break
                if not row.startswith(char):
                    yield "commit message", row
        else:
            for row in arg.splitlines():
                _, local, ref, _ = (row.split() + [""] * 4)[:4]
                if local.strip("0"):  # not a deletion
                    yield "ref name " + ref, ref
                    shas = git(".", "rev-list", "--reverse", local, "--not", os.environ.get("LOOP_HOOK_RANGE") or "--remotes",
                               stop=stop).split()
                    if len(shas) > 500:
                        raise RuntimeError("%d commits is over the 500 limit; set LOOP_HOOK_RANGE=<rev>" % len(shas))
                    for sha in shas:
                        yield from commit_places(".", sha, stop)
    return run


def hook(mode="", arg=""):
    """Exit 1 a hit, 2 broken, 64 usage; a scan is killed past LOOP_HOOK_DEADLINE seconds (default 30)."""
    if mode not in ("staged", "push", "message") or (mode == "message" and not arg):
        print("usage: private.py hook staged | message FILE | push")
        return 64
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, signal.SIG_DFL), signal.alarm(int(os.environ.get("LOOP_HOOK_DEADLINE") or 30))
    code = 0
    if mode == "push":
        arg = sys.stdin.read()
        blocked = worker_push(arg.splitlines())
        if blocked:
            print("REFUSED: %s. Fix: %s (%s)" % blocked)
            code = 2
    state, found, error = patterns()
    for number, pattern in found:
        if any(pattern.search(text) for text in ("", "x", "a b", "def f():", "  ")):
            state, error = "broken", "%s line %d matches ordinary text" % (source()[1], number)
    got = {"state": "broken", "hits": [], "note": error} if state == "broken" else scan(".", None, items=hook_items(mode, arg))
    stop = refusal(got)
    if stop:
        fix = stop[1] if stop[2] == PRIVATE_LIST else "remove the text; for a false positive, edit that line of the list"
        print("REFUSED: %s. Fix: %s (%s)" % (stop[0].replace("pushed", "pushed" if mode == "push" else "committed"), fix, stop[2]))
    return max(code, {"broken": 2, "hit": 1}.get(got["state"], 0))


def main():
    args = sys.argv[1:]
    if args[:1] == ["hook"]:
        return hook(*args[1:3])
    if args[:1] == ["where"]:
        slug, why = where()
        print("UNKNOWN (git rev-parse failed)" if slug is None and why is None else
              "NOT A WORKER (%s)" % why if slug is None else "WORKER " + slug)
        return 1 if slug is None and why is None else 0
    if args[:1] == ["check"]:
        state, found, error = patterns()
        shown = source()[1]
        if state == "broken":
            print("PRIVATE LIST: broken: %s (%s)" % (error, PRIVATE_LIST))
            return 1
        print("PRIVATE LIST: none at %s" % shown if state == "none" else
              "PRIVATE LIST: off on purpose (%s holds only comments)" % shown if state == "off" else
              "PRIVATE LIST: %d pattern%s from %s" % (len(found), "" if len(found) == 1 else "s", shown))
        return 0
    if args[:1] == ["scan"]:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
        base = args[args.index("--base") + 1] if "--base" in args else "origin/main"
        result = scan(top, base)
        print(result["note"])
        for hit in result["hits"]:
            print("HIT " + hit)
        stop = refusal(result, base)
        if stop:
            print("REFUSED: %s. Fix: %s (%s)" % stop)
            return 2
        return 0
    print(__doc__.strip().splitlines()[2])
    return 0 if args in ([], ["-h"], ["--help"]) else 2


if __name__ == "__main__":
    sys.exit(main())
