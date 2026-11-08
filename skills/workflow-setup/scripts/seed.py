#!/usr/bin/env python3
"""Plan and write the rest of an adoption: feature pages, criteria, regression rows and workflow, milestones.

usage: seed.py [--repo DIR]     (setup.py imports this; run alone it prints the plan)

Every decision is add (new file), convert (an existing page gets the marker and the missing sections, its words untouched),
skip (already done) or no fit (left alone, for a person). It calls the sibling docs and regression scripts, which own
those file formats, and runs git and nothing else.
"""
import argparse
import json
import os
import re
import subprocess
import sys

import survey

HERE = os.path.dirname(os.path.abspath(__file__))
PLACEHOLDER = "Write this page from what is really in the repo."
CRITERION = re.compile(r"[A-Z]{2,5}(?=-\d+:)")


def sibling(skill, script):
    path = os.path.join(HERE, "..", "..", skill, "scripts", script)
    return path if os.path.exists(path) else None


def prefixes(repo, found):
    used = set()
    for rel in found["pages"].values():
        used |= set(CRITERION.findall(survey.read(repo, rel) or ""))
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


def decide(repo, config, found):
    """The plan: a list of (verb, path, note, action) with action None for skip and no fit."""
    acts, wiki = [], found["wiki"]
    old = survey.read(repo, ".loop/config.json")
    if old is None or json.loads(old) != config:
        acts.append(("add" if old is None else "convert", ".loop/config.json", "keys added; yours kept", "config"))
    for name in ("queue.md", "findings.md"):
        if survey.read(repo, ".loop/" + name) is None:
            acts.append(("add", ".loop/" + name, "", "file"))
    have = {}
    for line in (survey.read(repo, ".loop/docs.tsv") or "").splitlines():
        if line.strip() and not line.startswith("#"):
            have[line.split("\t")[0]] = line
    new_rows = [n for n in mapping(found) if n not in have]
    if new_rows:
        acts.append(("add" if not have else "convert", ".loop/docs.tsv", "pages " + ", ".join(new_rows), "map"))
    for name in mapping(found):
        rel = "%s/%s.md" % (wiki, name)
        text = survey.read(repo, rel)
        if text is None:
            acts.append(("add", rel, "page with a criterion and a Tests table", ("page", name)))
        elif text.startswith(survey.MARKER):
            acts.append(("skip", rel, "already ours", None))
        elif "\n## " in text:
            acts.append(("no fit", rel, "has its own sections; add the marker and the contract sections by hand", None))
        else:
            acts.append(("convert", rel, "marker, Summary heading and the missing sections added; words kept", ("convert", name)))
    for name in sorted(set(found["pages"]) - set(mapping(found))):
        acts.append(("no fit", found["pages"][name], "not a feature of this repo's top-level folders; left alone", None))
    if config["checks"]:
        if not any("regression.tsv" in a[1] for a in acts) and survey.read(repo, ".loop/regression.tsv") is None:
            acts.append(("add", ".loop/regression.tsv", "one land row per page's first criterion", "rows"))
        if survey.read(repo, ".github/workflows/regression.yml") is None:
            acts.append(("add", ".github/workflows/regression.yml", "nightly run on " + config.get("regression_cron", ""), "workflow"))
    else:
        acts.append(("no fit", ".loop/regression.tsv", "no check command found, so no test row can be seeded", None))
    acts.append(("note", "milestones", "Backlog and one per page: python3 milestone.py new --all --live, when you are ready", None))
    acts.append(("note", "health", "workflow-health check works with these files; its rules are fixed", None))
    return acts


def tool(repo, skill, script, *argv):
    path = sibling(skill, script)
    if not path:
        print("SKIP: %s is not installed beside this skill" % skill)
        return
    done = subprocess.run([sys.executable, path] + list(argv), cwd=repo, capture_output=True, text=True)
    if done.returncode:
        print("NOTE: %s %s: %s" % (script, argv[0], (done.stdout + done.stderr).strip()[-200:]))


def apply(repo, config, found, acts):
    """Write what decide() planned. Returns the paths to commit."""
    touched, wiki = [], found["wiki"]
    used = prefixes(repo, found)
    rows = []
    for verb, path, _, action in acts:
        if action in ("file",):
            with open(os.path.join(repo, path), "w") as handle:
                handle.write("# Findings\n\nOpen findings, one line each.\n" if "findings" in path else "# Goal queue\n\nOne goal a line.\n")
        elif isinstance(action, tuple):
            name = action[1]
            full = os.path.join(repo, path)
            if (survey.read(repo, path) or "").startswith(survey.MARKER):
                continue  # already adopted on the setup branch
            os.makedirs(os.path.dirname(full), exist_ok=True)
            tag = pick(name, used)
            criterion = "- %s-1: **Unreviewed** The repo checks pass with the %s change in." % (tag, name)
            rows.append((tag, name))
            if action[0] == "page":
                body = "%s\n# %s\n\n## Summary\n\n%s\n\n## Criteria\n\n%s\n\n## Tests\n\n" % (survey.MARKER, name, summary_of(found, name), criterion)
            else:
                text = survey.read(repo, path).rstrip("\n")
                title, _, rest = text.partition("\n")
                if not title.startswith("# "):
                    title, rest = "# " + name, text
                body = "%s\n%s\n\n## Summary\n\n%s\n\n## Criteria\n\n%s\n\n## Tests\n\n" % (survey.MARKER, title, rest.strip(), criterion)
            with open(full, "w") as handle:
                handle.write(body)
        touched.append(path)
    if any(a[3] == "map" for a in acts):
        for name, paths in mapping(found).items():
            tool(repo, "workflow-docs", "docs.py", "add", name, "--paths", ",".join(paths))
        touched.append(".loop/docs.tsv")
    if config["checks"]:
        for tag, name in rows:
            tool(repo, "workflow-regression", "regression.py", "add", "%s-checks" % tag.lower(), "--level", "land", "--command",
                 config["checks"][0], "--goal", "%s-1" % tag, "--describe", "The repo's checks pass.")
        touched.append(".loop/regression.tsv")
        if any(a[3] == "workflow" for a in acts):
            tool(repo, "workflow-regression", "regression.py", "workflow")
    tool(repo, "workflow-docs", "criteria.py", "render")
    return touched


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = survey.git(args.repo, "rev-parse", "--show-toplevel")
    config = json.loads(survey.read(repo, ".loop/config.json") or "{}")
    config.setdefault("base", "main")
    config.setdefault("checks", [])
    found = survey.survey(repo, config)
    for verb, path, note, _ in decide(repo, config, found):
        print("%s: %s %s" % (verb, path, ("(" + note + ")") if note else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
