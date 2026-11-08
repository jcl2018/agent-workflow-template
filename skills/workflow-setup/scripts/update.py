#!/usr/bin/env python3
"""Show a newer version of the skills and what changed, then update the skills, and only the skills.

usage: update.py --from PACKAGE [--skills DIR] [--apply]

PACKAGE is a built ZIP or a folder with PACKAGE.json (a checkout of the repo works if it was built). --skills is the folder
that holds the workflow-* skill folders; it defaults to the folder holding this skill. Without --apply it only prints the
installed and new versions, the changelog entries between them and the files that would change. With --apply it copies the
changed skill files, deletes the ones the new package dropped, and writes workflow-package.json beside them.

It never reads or writes .loop/, docs, the wiki, a config or a private setting: every path it writes is checked to sit
inside the skills folder. It refuses a skills folder that is a link, since that is someone's checkout.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile

STAMP = "workflow-package.json"


def load(source):
    """(manifest, reader) from a ZIP or a folder. reader(rel) gives bytes for a manifest path."""
    if os.path.isdir(source):
        def read(rel):
            for base in ("skills/" + rel, "shared/" + rel, rel):
                if os.path.isfile(os.path.join(source, base)):
                    with open(os.path.join(source, base), "rb") as handle:
                        return handle.read()
            raise KeyError(rel)
        with open(os.path.join(source, "PACKAGE.json")) as handle:
            return json.load(handle), read
    bundle = zipfile.ZipFile(source)

    def read(rel):
        for base in ("skills/" + rel, "shared/" + rel, rel):
            if base in bundle.namelist():
                return bundle.read(base)
        raise KeyError(rel)
    return json.loads(bundle.read("PACKAGE.json")), read


def sha(data):
    return hashlib.sha256(data).hexdigest()


def newer(text, installed):
    """The changelog sections for versions above the installed one."""
    def key(v):
        return tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    out = []
    for part in re.split(r"(?m)^(?=## v)", text):
        head = re.match(r"## v([\d.]+)", part)
        if head and key(head.group(1)) > key(installed or "0"):
            out.append(part.strip())
    return "\n\n".join(out)


def inside(base, rel):
    full = os.path.realpath(os.path.join(base, rel))
    return full.startswith(os.path.realpath(base) + os.sep)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", dest="source", required=True)
    parser.add_argument("--skills", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    skills = os.path.abspath(args.skills)
    if os.path.islink(skills) or any(os.path.islink(os.path.join(skills, n)) for n in os.listdir(skills) if n.startswith("workflow-")):
        sys.exit("REFUSED: %s holds linked skills (a checkout). Fix: update the checkout with git instead." % skills)
    try:
        manifest, read = load(args.source)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        sys.exit("REFUSED: can't read a package at %s: %s" % (args.source, error))
    try:
        with open(os.path.join(skills, STAMP)) as handle:
            old = json.load(handle)
    except (OSError, ValueError):
        old = {"version": "", "files": {}}
    files = manifest["files"]
    changed = sorted(r for r, h in files.items() if old["files"].get(r) != h or not os.path.isfile(os.path.join(skills, r)))
    dropped = sorted(r for r in old["files"] if r not in files)
    print("INSTALLED: %s" % (old["version"] or "unknown (no %s)" % STAMP))
    print("AVAILABLE: %s" % manifest["version"])
    if not changed and not dropped:
        print("UP TO DATE: no skill file differs")
        return 0
    notes = newer(manifest.get("changelog", ""), old["version"])
    if notes:
        print("WHAT'S NEW:\n" + notes)
    for rel in changed:
        print("%s: %s" % ("update" if rel in old["files"] else "add", rel))
    for rel in dropped:
        print("remove: " + rel)
    if not args.apply:
        print("PREVIEW: nothing written. Run again with --apply to update the skills; your config, criteria, docs and settings are not touched")
        return 0
    for rel in changed + dropped:
        if not inside(skills, rel) or not (rel.startswith("workflow-") or "/" not in rel):
            sys.exit("REFUSED: %s is outside the skills folder or not a skill file; nothing written" % rel)
    for rel in changed:
        data = read(rel)
        if sha(data) != files[rel]:
            sys.exit("REFUSED: %s does not match its hash in the package; nothing written for it" % rel)
        os.makedirs(os.path.dirname(os.path.join(skills, rel)), exist_ok=True)
        with open(os.path.join(skills, rel), "wb") as handle:
            handle.write(data)
    for rel in dropped:
        if os.path.isfile(os.path.join(skills, rel)):
            os.remove(os.path.join(skills, rel))
    with open(os.path.join(skills, STAMP), "w") as handle:
        json.dump({"version": manifest["version"], "files": files}, handle, indent=1)
        handle.write("\n")
    print("UPDATED %d file(s) to %s in %s" % (len(changed) + len(dropped), manifest["version"], skills))
    return 0


if __name__ == "__main__":
    sys.exit(main())
