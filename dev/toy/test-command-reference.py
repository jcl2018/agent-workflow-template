#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-docs/SKILL.md skills/workflow-docs/references/commands.md
"""DOC-6: each skill's SKILL.md Command map names its commands, and its references/commands.md carries them: every
`/skill verb` ask in the map appears in the skill's SKILL.md or references/commands.md as a verb with its syntax."""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bad = 0
for doc in sorted(glob.glob(os.path.join(ROOT, "skills", "workflow-*", "SKILL.md"))):
    skill = os.path.basename(os.path.dirname(doc))
    text = open(doc, encoding="utf-8").read()
    maps = text.partition("## Command map")[2].partition("\n## ")[0]
    verbs = sorted(set(re.findall(r"^\| `/%s ([\w-]+)" % re.escape(skill), maps, re.M)))
    ref = os.path.join(os.path.dirname(doc), "references", "commands.md")
    held = text + (open(ref, encoding="utf-8").read() if os.path.exists(ref) else "")
    missing = [v for v in verbs if not re.search(r"\b%s\b" % re.escape(v), held.replace(maps, ""))]
    print(("PASS: " if verbs and not missing else "FAIL: ") + "%s: every Command map verb has syntax in its reference%s" % (skill, " (missing: %s)" % ", ".join(missing) if missing else ""))
    bad += not verbs or bool(missing)
print("ALL PASS" if not bad else "%d FAILED" % bad)
sys.exit(1 if bad else 0)
