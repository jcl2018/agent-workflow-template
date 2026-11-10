#!/usr/bin/env python3
"""What a goal's pull request says: the goal file, then `## Result` with each step's result, depth, tokens and the
verdicts its reply named (issue 38), the decided review depth, the budget, the private-name scan, GitHub surfaces the
goal touches and scripts that may write back what it deletes (issue 117). Pure: goal.py passes everything in."""
import os
import re
import subprocess

import fit

# No terminal, no waiting: a prompt from git must fail, not block.
os.environ.update(GIT_TERMINAL_PROMPT="0", GH_PROMPT_DISABLED="1", GIT_EDITOR="true", GIT_ASKPASS="true", SSH_ASKPASS="true")

VERDICT = re.compile(r"^\W*VERDICT:\s*(.+?)\s*$", re.M)


def verdicts(text):
    """The `VERDICT: <who>: <verdict>` lines of a step reply, at most 12, each cut to 200 characters."""
    return [" ".join(item.split())[:200] for item in VERDICT.findall(text or "")][:12]


def step_line(step, seen):
    flow = seen.get("flow") or {}
    tokens = (seen.get("tokens") or {}).get(step)
    line = "\n- %s: %s" % (step, flow.get(step, "not run"))
    if isinstance(tokens, int) and tokens:
        line += " (%s tokens)" % format(tokens, ",")
    for item in ((seen.get("verdicts") or {}).get(step) or []):
        line += "\n  - verdict: " + item
    return line


def regen_warnings(top, base):
    """For each file the branch deletes, tracked scripts and workflows that name its path."""
    def git(*args):
        done = subprocess.run(["git"] + list(args), cwd=top, capture_output=True, text=True)
        return done.stdout if done.returncode == 0 else ""
    gone = [line for line in git("diff", "--name-only", "--diff-filter=D", "--no-renames", base + "...HEAD").splitlines() if line]
    scripts = [p for p in git("ls-files").splitlines() if p.endswith((".py", ".sh")) or p.startswith(".github/workflows/")]
    found = []
    for path in gone:
        named = git("grep", "-l", "-F", path, "--", *scripts).split() if scripts else []
        for script in named:
            found.append("WARN: %s names %s, which this goal deletes; it may write it back. Fix: update or delete %s in "
                         "this goal, or ask the operation session to widen touches" % (script, path, script))
    return found


def pr_body(goal_text, seen, cfg, setting, scan_note, warnings, base_note=""):
    """The pull request body. Keeps `## Result` and the `Skill flow:` lines other tools read."""
    depth, why = fit.depth_for(setting, seen)
    held, source = fit.budget(seen, cfg)
    parts = ["%dm" % held["minutes"] if held["minutes"] else "", "%s tokens" % format(held["tokens"], ",") if held["tokens"] else ""]
    body = goal_text + "\n## Result\n\nSkill flow:" + "".join(step_line(step, seen) for step in fit.STEPS) + "\n"
    body += "\nReview depth: %s (%s).\n" % (depth, why)
    body += "Budget: %s (%s); spent %s tokens.\n" % (", ".join(p for p in parts if p) or "none set", source,
                                                     format(fit.spent_tokens(seen), ","))
    body += scan_note + "\n"
    surfaces = [t for t in (seen.get("touches") or []) if t.startswith("github:")]
    if surfaces:
        body += "GitHub surfaces this goal changes: %s.\n" % ", ".join(surfaces)
    if base_note:
        body += base_note + "\n"
    if warnings:
        body += "\n" + "\n".join("- " + w for w in warnings) + "\n"
    return body
