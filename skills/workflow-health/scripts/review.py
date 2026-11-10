"""The repo review (HLT-5, HLT-9): per feature, conflicts, gaps, drift, weak tests and savings, each with its evidence.
Separate from the rules and never part of the verdict; writes nothing. Used by health.py review (judge is an alias).

Two layers, for each feature (each docs.tsv page but Home):
- deterministic, same answer twice: gap "no non-functional requirement" (a page with requirements and no Non-functional
  part); gap "an open issue naming no requirement" (on the feature's milestone); drift "a Usage command the skill doesn't
  name" (/workflow-<skill> <verb> missing from that skill's SKILL.md). Conditions a check rule owns are not repeated.
- the judge (judge_command in .loop/config.json), given every page, the README, the feature's issues, rows and code
  paths, answers FINDING|feature|kind|angle|evidence|fix lines (kind: conflict, gap, drift, weak-test, savings). Each
  citation is checked: a requirement id a page defines, a file (or file:line) in the repo, a regression row id, or an
  issue #N. A finding keeps only its verified citations; one with none is dropped and counted (HLT-9).
With no judge, or one that fails, it says JUDGE UNAVAILABLE with the reason and still prints the deterministic layer.
--json prints {"version": 1, "findings": [...]} for preview and file --review FILE.
"""
import json
import os
import re
import subprocess

# No terminal, no waiting: a prompt from git or gh must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

import feature
import ghcache
from rules_trace import LINE, defined, pages, section, table

KINDS = ("conflict", "drift", "gap", "weak-test", "savings")
COMMAND = re.compile(r"/(workflow-[a-z]+) ([a-z][a-z-]*)")
ASK = """You review one repo, feature by feature, against its own PRD pages. For each feature, report only real problems:
conflict (two requirements that contradict, or a page breaking a reviewed rule), gap (a missing requirement, an untested
promise, an open issue that fits no requirement), drift (code or Usage doing what its page doesn't say), weak-test (a test
that doesn't prove what it claims), savings (time or tokens to cut, ranked by size). Answer only lines of the form
FINDING|<feature>|<kind>|<angle>|<what is wrong>|<evidence>|<fix>
where evidence is comma-separated citations: a requirement id (HLT-2), a file or file:line, a regression row id, or #N.
A finding with no checkable evidence will be dropped.
"""


def finding(name, kind, angle, detail, evidence, fix, source):
    return {"feature": name, "kind": kind, "angle": angle, "detail": detail, "evidence": evidence, "fix": fix, "source": source}


def deterministic(root, name, text, paths):
    out = []
    if LINE.search(text) and not re.search(r"^#+\s*Non-functional", text, re.M | re.I):
        out.append(finding(name, "gap", "a reader's angle", "the page has no non-functional requirement (performance, safety, privacy)",
                           "docs/wiki/%s.md" % name, "add one under Non-functional, or say none applies", "rule"))
    found, _ = ghcache.issues(root)
    for issue in found or []:
        body = "%s %s" % (issue.get("title") or "", issue.get("body") or "")
        if issue.get("state") == "open" and issue.get("milestone") == name and not ghcache.is_health(issue) \
                and not re.search(r"\b[A-Z]{2,5}-\d+\b", body):
            out.append(finding(name, "gap", "an auditor's angle", "open issue #%d names no requirement" % issue["number"],
                               "#%d" % issue["number"], "tie it to a requirement, or add one", "rule"))
    skills = {p.split("/")[1] for p in paths if p.startswith("skills/workflow-")}
    for skill, verb in sorted(set(COMMAND.findall(section(text, "Usage")))):
        doc = os.path.join(root, "skills", skill, "SKILL.md")
        if skill in skills and os.path.exists(doc) and verb not in open(doc, errors="replace").read():
            out.append(finding(name, "drift", "a newcomer's angle", "Usage names /%s %s, which the skill doesn't name" % (skill, verb),
                               "docs/wiki/%s.md" % name, "fix the Usage line or the skill", "rule"))
    return out


def judge_answer(root, prompt):
    """(text, why)."""
    try:
        command = json.load(open(os.path.join(root, ".loop", "config.json"))).get("judge_command")
    except (OSError, ValueError, AttributeError):
        command = None
    if not isinstance(command, list) or not command:
        return "", "no judge_command in .loop/config.json"
    try:
        done = subprocess.run([str(p) for p in command], input=prompt, capture_output=True, text=True, timeout=300, cwd=root)
    except (OSError, subprocess.SubprocessError) as error:
        return "", "the judge did not run: %s" % str(error)[:100]
    if done.returncode:
        import judge
        return "", judge.cause(done)
    return done.stdout, ""


def verified(root, cite, known, rows, issues):
    cite = cite.strip()
    if cite in known or cite in rows:
        return True
    if re.match(r"^#\d+$", cite):
        return any(str(i["number"]) == cite[1:] for i in issues or [])
    path, _, line = cite.partition(":")
    full = os.path.realpath(os.path.join(root, path))
    if not full.startswith(os.path.realpath(root) + os.sep) or not os.path.isfile(full):
        return False
    return not line or (line.split("-")[0].isdigit() and int(line.split("-")[0]) <= sum(1 for _ in open(full, errors="replace")))


def judged(root, wanted, every):
    """(findings, dropped, why) from the judge, each citation verified."""
    data = ["## %s\n%s" % (name, text[:6000]) for name, text in every.items() if name in wanted]
    try:
        data.append("## README\n" + open(os.path.join(root, "README.md"), errors="replace").read()[:4000])
    except OSError:
        pass
    issues, _ = ghcache.issues(root)
    data.append("## open issues\n" + "\n".join("#%d [%s] %s" % (i["number"], i.get("milestone"), i.get("title"))
                                                for i in issues or [] if i.get("state") == "open"))
    data.append("## rows\n" + "\n".join("%s %s %s" % (r["id"], r["goal"], r["description"][:100]) for r in table(root)))
    text, why = judge_answer(root, ASK + "<<<DATA\n" + "\n".join(data) + "\nDATA>>>\n")
    if why:
        return [], 0, why
    known, rows = defined(root), {r["id"] for r in table(root)}
    out, dropped = [], 0
    for line in text.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) != 7 or parts[0] != "FINDING" or parts[2] not in KINDS or parts[1] not in wanted:
            continue
        cites = [c for c in parts[5].split(",") if c.strip() and verified(root, c, known, rows, issues)]
        if not cites:
            dropped += 1
            continue
        out.append(finding(parts[1], parts[2], parts[3], parts[4], ", ".join(c.strip() for c in cites), parts[6], "judge"))
    return out, dropped, ""


def review(root, only=None):
    """(findings, dropped, why)."""
    features, every = feature.features(root), pages(root)
    wanted = [name for name in features if name in every and (not only or name == only)]
    out = []
    for name in wanted:
        out += deterministic(root, name, every[name], features[name])
    model, dropped, why = judged(root, wanted, every)
    return out + model, dropped, why


def as_rows(findings):
    """The findings as health rows, for file.py: family review, the feature as subject, the kind as rule."""
    import hashlib  # one issue per finding: the feature and a hash of its normalized citations name it
    cite = lambda f: ",".join(sorted({re.sub(r":\d+(-\d+)?$", "", c.strip()) for c in f["evidence"].split(",") if c.strip()}))
    return [{"state": "WARN", "family": "review", "rule": f["kind"], "detail": f["detail"],
             "subject": "%s-%s" % (f["feature"], hashlib.sha1(cite(f).encode()).hexdigest()[:6]),
             "fix": f["fix"], "evidence": f["evidence"], "feature": f["feature"], "angle": f["angle"]} for f in findings]


def render(findings, dropped, why):
    out = ["REVIEW (per feature; never part of the verdict; writes nothing)"]
    if why:
        out.append("JUDGE UNAVAILABLE: " + why)
    for name in sorted({f["feature"] for f in findings}):
        mine = sorted([f for f in findings if f["feature"] == name], key=lambda f: KINDS.index(f["kind"]))
        out.append("== %s ==" % name)
        out += ["FINDING %s (%s): %s -- evidence: %s -> fix: %s" % (f["kind"], f["angle"], f["detail"], f["evidence"], f["fix"])
                for f in mine]
        steps = list(dict.fromkeys(f["fix"] for f in mine))[:3]  # one step per distinct fix, in rank order
        out.append("next steps: " + "; ".join("%d. %s" % (n, step) for n, step in enumerate(steps, 1)))
    out.append("REVIEW: %d findings, %d dropped for no evidence" % (len(findings), dropped))
    return out


def load(path):
    """The findings of a saved review --json, or None when it isn't one."""
    try:
        data = json.load(open(path))
    except (OSError, ValueError):
        return None
    return data["findings"] if isinstance(data, dict) and data.get("version") == 1 and isinstance(data.get("findings"), list) else None
