#!/usr/bin/env python3
"""Check the package against the Agensi rules and build the ZIP.

usage: package.py [--root DIR] [--out FILE]

Checks run in the order of the roadmap's rule table. Every failure is printed as
`FAIL <rule>: <what>`. One failure means no ZIP and exit 1.
"""
import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

SHIPPED = ["skills", "listing.json", "README.md"]
BAD_DIRS = {".git", "__pycache__", "node_modules", ".venv", ".pytest_cache", ".mypy_cache", "vendor"}
MAX_FILES, MAX_BYTES, MAX_SCRIPT = 99, 5 * 1024 * 1024, 20 * 1024
SECRETS = [r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9]{30,}", r"sk-[A-Za-z0-9]{20,}", r"xox[baprs]-[A-Za-z0-9-]{10,}",
           r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*['\"][^'\"\s]{8,}"]
OBFUSCATION = [r"base64\.b64decode", r"b64decode", r"\bexec\s*\(", r"\beval\s*\(", r"\bmarshal\b", r"\bpickle\b",
               r"codecs\.decode", r"\\x[0-9a-fA-F]{2}(\\x[0-9a-fA-F]{2}){5,}", r"[A-Za-z0-9+/]{100,}={0,2}", r"__import__"]
AGENT_AIMED = [r"(?i)ignore (all |any )?(previous|prior|above) instructions", r"(?i)do not (tell|inform|mention to) the user",
               r"(?i)without (telling|asking|informing) the user", r"(?i)dangerously-skip-permissions", r"bypassPermissions",
               r"(?i)disregard (your|the) (system|safety)", r"(?i)you must (secretly|silently) "]
LIMITS = {"tags": 10, "keywords": 10, "use_cases": 8}
failures = []


def fail(rule, text):
    failures.append((rule, text))
    print("FAIL %s: %s" % (rule, text))


def walk(root):
    out = []
    for base in SHIPPED:
        path = os.path.join(root, base)
        if os.path.isfile(path):
            out.append(base)
        for here, dirs, names in os.walk(path):
            for name in names:
                out.append(os.path.relpath(os.path.join(here, name), root))
            for name in dirs:
                if name in BAD_DIRS:
                    out.append(os.path.relpath(os.path.join(here, name), root) + "/")
    return sorted(out)


def read(root, rel):
    with open(os.path.join(root, rel), "rb") as handle:
        return handle.read()


def frontmatter(text):
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def check_frontmatter(root, files):
    skills = [f for f in files if re.fullmatch(r"skills/[^/]+/SKILL\.md", f)]
    if not skills:
        fail("Frontmatter", "no skills/<name>/SKILL.md found")
    for rel in skills:
        fields = frontmatter(read(root, rel).decode("utf-8", "replace"))
        folder = rel.split("/")[1]
        if not fields.get("name"):
            fail("Frontmatter", "%s has no name" % rel)
        elif fields["name"] != folder:
            fail("Frontmatter", "%s name %r does not match folder %r" % (rel, fields["name"], folder))
        if not fields.get("description"):
            fail("Frontmatter", "%s has no description" % rel)
    return skills


def load_listing(root):
    try:
        return json.loads(read(root, "listing.json"))
    except (OSError, ValueError) as error:
        fail("Listing fields", "listing.json unreadable: %s" % error)
        return {}


def check_listing(listing):
    summary = listing.get("summary", "")
    if not summary:
        fail("Listing fields", "no summary")
    if len(summary) > 300:
        fail("Listing fields", "summary is %d characters, 300 at most" % len(summary))
    for key, limit in LIMITS.items():
        if len(listing.get(key, [])) > limit:
            fail("Listing fields", "%s has %d entries, %d at most" % (key, len(listing[key]), limit))


def check_files(root, files):
    total = 0
    for rel in files:
        if rel.endswith("/"):
            fail("Files", "forbidden folder " + rel)
            continue
        path = os.path.join(root, rel)
        data = read(root, rel)
        total += len(data)
        if os.stat(path).st_mode & 0o111:
            fail("Files", "%s is executable" % rel)
        if rel.endswith((".pyc", ".pyo", ".so", ".dylib", ".exe", ".class", ".jar", ".whl")):
            fail("Files", "%s is a compiled or bundled file" % rel)
        try:
            text = data.decode("utf-8")
            if "\0" in text:
                raise ValueError
        except ValueError:
            fail("Files", "%s is not text" % rel)
    if len(files) > MAX_FILES:
        fail("Size", "%d files, under 100 allowed" % len(files))
    if total >= MAX_BYTES:
        fail("Size", "%d bytes, under 5 MB allowed" % total)


def check_scripts(root, files):
    for rel in [f for f in files if f.endswith(".py")]:
        data = read(root, rel)
        text = data.decode("utf-8", "replace")
        if len(data) >= MAX_SCRIPT:
            fail("Scripts", "%s is %d bytes, under 20 KB allowed" % (rel, len(data)))
        modules = set()
        try:
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.Import):
                    modules |= {item.name.split(".")[0] for item in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                    modules.add(node.module.split(".")[0])
        except SyntaxError as error:
            fail("Scripts", "%s does not parse: %s" % (rel, error))
        for name in sorted(modules - set(sys.stdlib_module_names)):
            fail("Scripts", "%s imports %s, which is not in the standard library" % (rel, name))
        if "__file__" in text:
            fail("Scripts", "%s reads its own location, so it can't run alone" % rel)
        if re.search(r"skills/|\.\./", text.replace("../loop-files.md", "")) and re.search(r"open\([^)]*(skills/|\.\./)", text):
            fail("Scripts", "%s opens another package file" % rel)
        with tempfile.TemporaryDirectory() as lone:
            copy = os.path.join(lone, "alone.py")
            with open(copy, "wb") as handle:
                handle.write(data)
            done = subprocess.run([sys.executable, "-I", copy, "--help"], capture_output=True, text=True, cwd=lone)
            if done.returncode:
                fail("Scripts", "%s does not run alone: %s" % (rel, done.stderr.strip()[-200:]))


def check_safety(root, files):
    for rel in files:
        if rel.endswith("/"):
            continue
        text = read(root, rel).decode("utf-8", "replace")
        for group, patterns in (("secret", SECRETS), ("obfuscation or encoded text", OBFUSCATION), ("instruction aimed at the agent", AGENT_AIMED)):
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    fail("Safety", "%s in %s: %r" % (group, rel, match.group(0)[:40]))


def check_disclosure(root, files, listing):
    said = " ".join(listing.get("commands", [])).split()
    wanted = set()
    for rel in files:
        if rel.endswith(".py"):
            wanted |= set(re.findall(r"add_parser\(\"([a-z-]+)\"", read(root, rel).decode("utf-8", "replace")))
        if re.fullmatch(r"skills/[^/]+/SKILL\.md", rel):
            wanted |= set(re.findall(r"^## `([a-z-]+)", read(root, rel).decode("utf-8", "replace"), re.M))
    for name in sorted(wanted):
        if name not in said:
            fail("Disclosure", "command %r is not in listing.commands" % name)
    hosts = set()
    for rel in files:
        if not rel.endswith("/") and rel != "listing.json":
            hosts |= set(re.findall(r"https?://([A-Za-z0-9.-]+)", read(root, rel).decode("utf-8", "replace")))
    hosts -= {"example.com", "example.test"}
    for host in sorted(hosts):
        if host not in " ".join(listing.get("network", [])):
            fail("Disclosure", "host %s is not in listing.network" % host)
    if not listing.get("writes"):
        fail("Disclosure", "listing.writes is empty")
    if not listing.get("network"):
        fail("Disclosure", "listing.network is empty (state \"none\" or each host)")


def build(root, files, out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as bundle:
        for rel in files:
            info = zipfile.ZipInfo(rel, (2026, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            bundle.writestr(info, read(root, rel))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    parser.add_argument("--out", default="dist/agent-workflow-template.zip")
    args = parser.parse_args()
    root = os.path.abspath(args.root)
    files = walk(root)
    check_frontmatter(root, files)
    listing = load_listing(root)
    check_listing(listing)
    check_files(root, files)
    check_scripts(root, files)
    check_safety(root, files)
    check_disclosure(root, files, listing)
    if failures:
        print("REFUSED: %d rule failure(s); no ZIP built" % len(failures))
        return 1
    build(root, files, args.out)
    print("PASS: %d files, ZIP at %s (%d bytes)" % (len(files), os.path.abspath(args.out), os.path.getsize(args.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
