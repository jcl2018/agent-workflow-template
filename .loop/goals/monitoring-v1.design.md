# monitoring-v1 design

Problem: three gaps the owner approved. (M4) the operation session runs its skills from the main checkout, which fell 204 and 18 commits behind origin/main. (M9) MON-14 says the check-in dependency map is grouped by repo under == name == lines but the reply hook never checks it. (M8) MON-8 says a worker silent for 30 minutes shows under Needs you; it is unproven by a test.

Approaches: M4: a new fresh.py that fast-forwards with git merge --ff-only at the start of each operate.py pass (chosen) vs a git hook or a cron (more moving parts). M9: one more check in reply_hook.problems for a repo block in the Dependencies body (chosen). M8: the logic already exists in graph.classify and checkin.py; prove it with a Python toy.

Done lines: a behind checkout fast-forwards with one line and no merge commit; a reply with no == repo == block is flagged; a worker silent 30 minutes shows under Needs you.

Open questions: none. Requirements are Reviewed and locked, so rows attach to MON-8, MON-13, MON-14.
