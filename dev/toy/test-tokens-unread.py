#!/usr/bin/env python3
# windows: ok
# reads: skills/workflow-delivery/scripts/fit.py skills/workflow-monitoring/scripts/board_lines.py
"""A goal with no token count shows 'tokens unread' on the board line and in the PR body; one with a count shows the number."""
import os
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(root, "skills", "workflow-delivery", "scripts"))
sys.path.insert(0, os.path.join(root, "skills", "workflow-monitoring", "scripts"))
import board_lines  # noqa: E402
import fit  # noqa: E402

fails = 0


def check(name, ok):
    global fails
    print(("PASS: " if ok else "FAIL: ") + name)
    fails += 0 if ok else 1


import datetime  # noqa: E402

now = datetime.datetime.now(datetime.timezone.utc)
bare = {"slug": "a", "status": "running", "step": "build", "flow": {}}
counted = dict(bare, tokens={"build": 12345})
worker = dict(bare, tokens={"total": 900})
zero = dict(bare, tokens={"build": 0})
cfg = {"token_budget": 3000000}
check("no count: tokens_text says tokens unread", fit.tokens_text(bare) == "tokens unread")
check("a zero count is unread too, never 0", fit.tokens_text(zero) == "tokens unread")
check("a count shows the number", fit.tokens_text(counted) == "12,345 tokens")
check("the worker total shows the number", fit.tokens_text(worker) == "900 tokens")
line = board_lines.line(bare, cfg, now)
check("board line with a budget and no count says tokens unread, not 0", "tokens unread" in line and "0 of" not in line)
check("board line with a count shows it", "tokens unread" not in board_lines.line(counted, cfg, now))
body = fit.pr_body("# g\n", bare, cfg, {}, "", [])
check("PR body says tokens unread", "spent: tokens unread" in body and "spent 0 tokens" not in body)
check("PR body shows a count", "spent: 12,345 tokens" in fit.pr_body("# g\n", counted, cfg, {}, "", []))
sys.exit(1 if fails else 0)
