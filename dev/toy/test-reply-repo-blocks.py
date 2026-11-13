#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-monitoring/scripts/reply_hook.py
"""MON-14: the reply hook flags a Dependencies section with no `== repo ==` block."""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "..", "skills", "workflow-monitoring", "scripts"))
import reply_hook  # noqa: E402

failed = []


def check(ok, text):
    print(("PASS: " if ok else "FAIL: ") + text)
    if not ok:
        failed.append(text)


def reply(deps):
    return ("One goal moved.\n\n## All sessions\n| a | b |\n|---|---|\n| x | y |\n\n## Dependencies\n" + deps +
            "\n\n## Needs you\n1. Release? Options: cut, leave. Recommended: leave.\n\n## Coming up\n- soon\n")


good = reply("```\n== toy ==\n[>] alpha\n |\n[ ] beta\n```")
bare = reply("```\n[>] alpha\n |\n[ ] beta\n```")
two = reply("== one ==\n[>] a\n\n== two ==\n[ ] b\n\nBetween repos\n- one/a -> two/b")
check(reply_hook.problems(good) == [], "MON-14: a Dependencies section with a == repo == block passes")
check(reply_hook.problems(two) == [], "MON-14: several repo blocks and a Between repos list pass")
found = reply_hook.problems(bare)
check(any("== repo ==" in line for line in found), "MON-14: a Dependencies section with no == repo == block is flagged")
check(len(found) == 1, "MON-14: only the missing repo block is reported (%s)" % found)
sys.exit(1 if failed else 0)
