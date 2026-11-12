#!/usr/bin/env python3
"""Show what a newer template version brings, then update the skills and this repo's generated files.

usage: update.py [--check | --apply | --propose [--file-issue]] [--take FILE ...] [--from PACKAGE] [--tag vX]
                 [--template OWNER/NAME] [--skills DIR] [--repo DIR]

--check (or no flag) writes nothing: INSTALLED, AVAILABLE, REPO, what's new, each file to change and each LOCAL FIX
(a skill file edited here). Exit 0 up to date, 1 behind, 2 refused. --apply writes the skills folder (hashes checked
first, atomic writes, workflow-package.json last; a LOCAL FIX is kept unless --take names it), then the repo half
(sync.py) on branch workflow-update-vX. --propose sends each LOCAL FIX back as an issue (sync.py). The source is
--from (a package or a source tree) or the template's latest GitHub release archive; the template is the installed
stamp's repo, else template_repo (both set and different: refused unless --template). It never downgrades.
"""
import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")
STAMP, KEPT = "workflow-package.json", ".workflow-kept"
SHARED = ("loop-files.md", "design-guide.md")
CAP = 20 * 1024 * 1024


def version_key(text):
    """The first three integers of a version; empty or unreadable is older than any version."""
    return tuple(int(x) for x in re.findall(r"\d+", str(text or ""))[:3])


def strings(value, skip=()):
    if isinstance(value, str):
        yield value
    for item in (value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else ()):
        if item[0] not in skip:
            yield from strings(item[1])


def local_values():
    """The owner's local strings that look like a path or an address (/, ~ or @; 8+ characters) and are not a template default."""
    import settings
    found = set(strings([settings.load(settings.private_path()), settings.load(settings.health_path())], ("_help",)))
    try:
        found |= set(open(os.path.expanduser("~/.workflow-loop/repos")).read().split())
    except OSError:
        pass
    default = set(strings([row[2] for row in settings.TABLE]))
    return {v for v in found if len(v) >= 8 and any(c in v for c in "/~@") and v not in default}


def guard_staged(repo, paths):
    """SET-8: what the staged adoption adds that is a local setting or private value, as file:line or key (never the value)."""
    import settings
    private = {row[0] for row in settings.TABLE if row[1] == settings.PRIVATE}
    home, mail, local = os.path.expanduser("~"), subprocess.run(["git", "-C", repo, "config", "user.email"], capture_output=True, text=True).stdout.strip(), local_values()
    diff = subprocess.run(["git", "-C", repo, "diff", "--cached", "-U0", "--no-color", "--"] + list(paths), capture_output=True, text=True).stdout
    out, path, at = [], "", 0
    for line in diff.splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
        elif line.startswith("@@"):
            at = int(re.search(r"\+(\d+)", line).group(1)) - 1
        elif line.startswith("+"):
            at += 1
            key = re.match(r'  "(\w+)":', line[1:]) if path == ".loop/config.json" else None
            if key and key.group(1) in private:
                out.append("%s:%d holds the local setting %s" % (path, at, key.group(1)))
            elif (len(home) > 1 and home in line) or (mail and mail in line) or any(v in line for v in local):
                out.append("%s:%d holds a private value" % (path, at))
    return out


def commit(repo, message, files):
    """(exit code, output) of git commit for exactly these files, run in its own process group so a signal reaches git and its hooks."""
    proc = subprocess.Popen(["git", "-C", repo, "commit", "--allow-empty", "-m", message, "--"] + files, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out = proc.communicate()[0]
    except BaseException:
        os.killpg(proc.pid, 15)
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, 9)
            proc.wait()
        raise
    return proc.returncode, out


def mask(line):
    import settings
    return "[line withheld: holds a private value]" if settings.private_value(line) else line


def step(name, fix, run, failed):
    """A post-commit step: its output is read as well as its exit status; a failure is a NOTE and a gap, never a refusal."""
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = run()
    except Exception as error:
        out.write("FAILED %s\n" % type(error).__name__)
        code = 1
    sys.stdout.write(out.getvalue())
    if code or re.search(r"^(FAILED|REFUSED|NOTE: .*(refus|failed|writes no))", out.getvalue(), re.M):
        failed.append(name)
        print("NOTE: %s failed; the adoption is committed on the branch. Fix: %s (SETUP_STEP)" % (name, fix))


def refuse(why, code, fix):
    print("REFUSED: %s (%s). Fix: %s" % (why, code, fix), file=sys.stderr)
    sys.exit(2)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe(name):
    return not (name.startswith("/") or ".." in name.split("/") or name.split("/")[0].endswith(":"))


def from_tree(names, get):
    """A manifest built from a source tree (skills/, VERSION, CHANGELOG.md), keyed as dev/package.py keys a package."""
    firsts = {n.split("/")[0] for n in names}
    top = "" if "skills" in firsts or len(firsts) != 1 else firsts.pop() + "/"  # a GitHub archive nests one folder
    files, data = {}, {}
    for name in names:
        rel = name[len(top):]
        if rel.startswith("skills/") and not rel.endswith("/") and "__pycache__" not in rel and not rel.endswith(".pyc"):
            key = rel[len("skills/"):]
            if "/" in key or key in SHARED:
                data[key] = get(name)
                files[key] = sha(data[key])
    if not files or top + "VERSION" not in names:
        raise ValueError("no skills/ and VERSION in it")
    log = get(top + "CHANGELOG.md").decode() if top + "CHANGELOG.md" in names else ""
    return {"version": get(top + "VERSION").decode().strip(), "files": files,
            "changelog": "\n".join(p.rstrip() for p in re.split(r"(?m)^(?=## v)", log)[1:4])[:6000]}, data.__getitem__


def load(source):
    """(manifest, reader) from a built ZIP or folder (PACKAGE.json) or a source tree or archive (VERSION + skills/)."""
    if os.path.isdir(source):
        names = [os.path.relpath(os.path.join(d, f), source).replace(os.sep, "/") for d, _, fs in os.walk(source) for f in fs]
        get = lambda rel: open(os.path.join(source, rel), "rb").read()
    else:
        bundle = zipfile.ZipFile(source)
        total = 0
        for info in bundle.infolist():
            total += info.file_size
            if not safe(info.filename) or (info.external_attr >> 16) & 0o170000 == 0o120000 or total > CAP:
                raise ValueError("unsafe member %s (absolute, .., a link, or over 20 MB)" % info.filename)
        names, get = [i.filename for i in bundle.infolist() if not i.is_dir()], bundle.read
    if "PACKAGE.json" not in names:
        return from_tree(names, get)

    def read(rel):
        for base in ("skills/" + rel, "shared/" + rel, rel):
            if base in names:
                return get(base)
        raise KeyError(rel)
    return json.loads(get("PACKAGE.json")), read


def stamp(skills):
    try:
        with open(os.path.join(skills, STAMP)) as handle:
            held = json.load(handle)
        return held if isinstance(held, dict) else {}
    except (OSError, ValueError):
        return {}


def checkout(skills):
    """The checkout's VERSION when the skills folder is a source checkout (linked, or no stamp and a VERSION above it)."""
    linked = os.path.islink(skills) or any(os.path.islink(os.path.join(skills, n)) for n in os.listdir(skills) if n.startswith("workflow-"))
    above = os.path.join(os.path.realpath(skills), os.pardir, "VERSION")
    if linked or (not os.path.exists(os.path.join(skills, STAMP)) and os.path.exists(above)):
        target = os.path.realpath(os.path.join(skills, next((n for n in sorted(os.listdir(skills)) if n.startswith("workflow-")), "")))
        for path in (above, os.path.join(target, os.pardir, os.pardir, "VERSION")):
            if os.path.exists(path):
                return open(path).read().strip()
        return "unknown"
    return None


def template(skills, repo_cfg, chosen):
    held, own = stamp(skills).get("repo") or "", repo_cfg.get("template_repo") or ""
    if chosen:
        return chosen, "--template"
    if held and own and held != own:
        refuse("the installed package's template %s and the repo setting template_repo %s differ" % (held, own),
               "UPDATE_TEMPLATE_MISMATCH", "pass --template OWNER/NAME to choose one")
    return (held, "the installed package") if held else (own, "template_repo")


def fetch(name, where, tag, into):
    """Download the template release's source archive with gh; return its path."""
    if not name:
        refuse("no template repo is known", "UPDATE_NO_TEMPLATE", "set template_repo in .loop/config.json, or run update --from <ZIP|DIR>")
    gh = lambda *a: subprocess.run(["gh", *a], capture_output=True, text=True, timeout=60)
    try:
        tag = tag or gh("release", "view", "--repo", name, "--json", "tagName", "-q", ".tagName").stdout.strip()
        done = gh("release", "download", tag, "--repo", name, "--archive", "zip", "--dir", into) if tag else None
    except FileNotFoundError:
        refuse("gh not found on PATH", "UPDATE_NO_GH", "install gh, or run update --from <ZIP|DIR>")
    except subprocess.TimeoutExpired:
        done = None
    zips = [f for f in os.listdir(into) if f.endswith(".zip")]
    if not done or done.returncode or not zips:
        tail = ((done.stderr if done else "") or "no release or a timeout").strip().splitlines()[-1:]
        print("context: TEMPLATE %s from %s, tag %s" % (name, where, tag or "latest"), file=sys.stderr)
        refuse("gh can't read %s releases: %s" % (name, " ".join(tail)), "UPDATE_GH",
               "gh auth login (or set GH_TOKEN), check the tag, then run the same command; nothing was written")
    return os.path.join(into, zips[0])


def newer(text, installed):
    out = []
    for part in re.split(r"(?m)^(?=## v)", text or ""):
        head = re.match(r"## v([\d.]+)", part)
        if head and version_key(head.group(1)) > version_key(installed):
            out.append(part.strip())
    return "\n\n".join(out)


def local_fixes(skills, old):
    """Skill files whose bytes differ from what the stamp says was installed."""
    out = []
    for rel, digest in sorted((old.get("files") or {}).items()):
        path = os.path.join(skills, rel)
        if os.path.isfile(path) and sha(open(path, "rb").read()) != digest:
            out.append(rel)
    return out


def check(skills, manifest, old, fixes, ours):
    """Print the preview; return (changed, dropped)."""
    files = manifest["files"]
    changed = sorted(r for r, h in files.items() if (old.get("files") or {}).get(r) != h or not os.path.isfile(os.path.join(skills, r)))
    dropped = sorted(r for r in (old.get("files") or {}) if r not in files and r not in fixes)  # a dropped LOCAL FIX is kept
    notes = newer(manifest.get("changelog", ""), ours)
    if notes:
        print("WHAT'S NEW:\n" + notes)
    for rel in changed:
        print("%s: %s" % ("update" if rel in (old.get("files") or {}) else "add", rel))
    for rel in dropped:
        print("remove: " + rel)
    for rel in sorted(r for r in fixes if r not in files):
        print("remove: %s (a LOCAL FIX: kept)" % rel)
    for rel in fixes:
        print("LOCAL FIX: %s (kept on apply; --take %s takes the package copy, --propose sends it back)" % (rel, rel))
    if not old.get("files"):
        print("LOCAL FIX: cannot detect (no %s)" % STAMP)
    return changed, dropped


def apply_skills(skills, manifest, read, old, fixes, take, where):
    """Write the skills half: verify every hash, write each file atomically, save kept copies, write the stamp last."""
    files, kept = manifest["files"], dict(old.get("kept") or {})
    keep = [r for r in fixes if r not in take]
    blobs = {}
    for rel, digest in files.items():
        if (old.get("files") or {}).get(rel) == digest and os.path.isfile(os.path.join(skills, rel)) and rel not in take + keep:
            continue
        data = read(rel)
        if sha(data) != digest or not (rel.startswith("workflow-") or "/" not in rel) or not os.path.realpath(
                os.path.join(skills, rel)).startswith(os.path.realpath(skills) + os.sep):
            refuse("%s doesn't match its hash or isn't a skill file" % rel, "UPDATE_BAD_ARCHIVE", "use a package built by dev/package.py; nothing was written")
        blobs[rel] = data
    for rel, data in blobs.items():
        if rel in keep:
            if sha(data) == sha(open(os.path.join(skills, rel), "rb").read()):
                keep.remove(rel)  # the local file already matches the new version: not a fix any more, stamp it
                kept.pop(rel, None)
                continue
            upstream = (old.get("files") or {}).get(rel) != files[rel]
            kept[rel] = {"hash": files[rel], "base_version": old.get("version") or ""}
            target = os.path.join(skills, KEPT, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            open(target, "wb").write(data)
            print("KEPT%s: %s" % (" (CONFLICT: upstream changed too)" if upstream else "", rel))
            continue
        path = os.path.join(skills, rel)
        os.makedirs(os.path.dirname(path) or skills, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=os.path.dirname(path) or skills, delete=False) as handle:
            handle.write(data)
        os.replace(handle.name, path)
        kept.pop(rel, None)
    for rel in (old.get("files") or {}):
        if rel not in files and rel not in keep and os.path.isfile(os.path.join(skills, rel)):
            os.remove(os.path.join(skills, rel))
    stamped = dict(files, **{r: (old.get("files") or {}).get(r) for r in keep if r in (old.get("files") or {})})
    new = {"version": manifest["version"], "files": stamped, "repo": manifest.get("repo") or old.get("repo") or where}
    if kept:
        new["kept"] = kept
    with tempfile.NamedTemporaryFile("w", dir=skills, delete=False) as handle:
        json.dump(new, handle, indent=1)
        handle.write("\n")
    os.replace(handle.name, os.path.join(skills, STAMP))
    print("UPDATED skills to %s in %s" % (manifest["version"], skills))


def locked(skills):
    handle = open(os.path.join(skills, ".workflow-update.lock"), "w")
    stop = time.time() + 10
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except OSError:
            if time.time() > stop:
                refuse("another update holds %s" % handle.name, "UPDATE_LOCKED", "run update again when the other one ends")
            time.sleep(0.5)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", default="")
    parser.add_argument("--skills", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir))
    parser.add_argument("--repo", default="")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--take", action="append", default=[])
    parser.add_argument("--propose", action="store_true")
    parser.add_argument("--file-issue", action="store_true")
    parser.add_argument("--tag", default="")
    parser.add_argument("--template", default="")
    args = parser.parse_args()
    import sync
    skills = os.path.abspath(args.skills)
    repo = args.repo or subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    base_cfg = sync.base_config(repo) if repo else {}
    old, tree = stamp(skills), checkout(skills)
    fixes = [] if tree else local_fixes(skills, old)
    if args.propose:
        name = template(skills, base_cfg, args.template)[0]
        return sync.run(skills, old, fixes, name, repo, args.file_issue)
    if tree == "unknown":
        print("SKIPPED repo: the checkout's VERSION can't be found, so there is no version to stamp (UPDATE_CHECKOUT)")
        repo = ""
    if tree:
        print("SKILLS: %s is a checkout; update it with git pull (UPDATE_CHECKOUT)" % skills)
        manifest, read, where = {"version": tree, "files": {}}, None, ""
    else:
        name, where = template(skills, base_cfg, args.template)
        with tempfile.TemporaryDirectory() as into:
            try:
                manifest, read = load(args.source or fetch(name, where, args.tag, into))
                if args.apply and not args.source:
                    blobs = {r: read(r) for r in manifest["files"]}
                    read = blobs.__getitem__
            except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
                refuse("can't read a package at %s: %s" % (args.source or "the release archive", error), "UPDATE_BAD_ARCHIVE",
                       "check the ZIP or folder; nothing was written")
        where = name
    ours = tree or old.get("version") or ""
    print("INSTALLED: %s" % (ours or "unknown (no %s)" % STAMP))
    print("AVAILABLE: %s" % manifest["version"])
    if not tree and version_key(manifest["version"]) < version_key(ours):
        print("AVAILABLE v%s is older than INSTALLED v%s: nothing to do" % (manifest["version"], ours))
        return 0
    target = manifest["version"] if version_key(manifest["version"]) > version_key(ours) else ours
    behind = sync.report(repo, base_cfg, target) if repo else False
    changed, dropped = check(skills, manifest, old, fixes, ours) if not tree else ([], [])
    if not args.apply:
        up = not changed and not dropped and not behind and not args.take and (tree or manifest["version"] == ours)
        print("UP TO DATE" if up else "PREVIEW: nothing written. Ask for workflow-setup update to apply")
        return 0 if up else 1
    wrote = not tree and bool(changed or dropped or args.take or manifest["version"] != ours)  # a version bump moves the stamp
    if wrote:
        with locked(skills):
            apply_skills(skills, manifest, read, old, fixes, args.take, where)
        # The repo half runs the sync.py just written, so the new version's settings and rules apply, not this run's.
        new = os.path.join(skills, "workflow-setup", "scripts", "sync.py")
        if repo and os.path.isfile(new) and "workflow-setup/scripts/sync.py" not in set(fixes) - set(args.take):
            sys.stdout.flush()
            return subprocess.run([sys.executable, new, "--repo", repo, "--version", target, "--wrote-skills"]).returncode
    return sync.apply_repo(repo, base_cfg, target, wrote) if repo else 0


if __name__ == "__main__":
    sys.exit(main())
