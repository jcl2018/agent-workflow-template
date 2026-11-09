#!/usr/bin/env python3
"""The texts watch.py writes: the frozen goal file and the prompt a background worker gets. Imported, not run."""

TEMPLATE = """# {goal}

- Slug: {slug}
- Touches: {touches}

## Done lines

Frozen. A wrong done line needs a new goal.

{done}

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
"""

GO_PROMPT = """Use the workflow-delivery skill to run this goal in this git worktree, on branch {branch}:

go "{goal}" {done}

Slug: {slug}. Touches: {touches}.
{where}
Step 1 (Freeze) is already done for you: .loop/goals/{slug}.md is committed with the frozen done lines and the run
record exists. Do not run goal.py new and never edit the done lines. Start at step 2, the idea step, and use goal.py
and flow.py with the slug {slug} for every step. Work only in this worktree.

When a done line is proven, run `python3 {worker} met {slug} N` for its number N.
A message from the operation session prints when you run goal.py: treat it as the owner's answer or follow-up.
Stop at the pull request (goal.py pr). Never merge it yourself. Then follow workflow-release if you have it: {release}
"""
