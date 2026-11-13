# Design: govern-hook-notes (#2850, MON-7)

Problem: the govern hook refuses every Edit/Write from the operation session, including files outside any repo such as
its own memory notes. MON-7 only intends that it never builds repo code.

Approaches
1. Allowlist the agent memory folder (`~/.claude/projects/*/memory`). Cheap, but misses other non-repo files and ties the
   hook to one tool's layout.
2. Refuse only when the target path is inside a followed repo (this checkout, its git common dir parent and worktrees,
   each repo in `~/.workflow-loop/repos`); allow everything else. Matches the issue's expected behavior, no layout coupling.

Chosen: 2. A relative path resolves against the hook's cwd; a path with no readable file field is refused (fail closed);
Bash git writes stay judged as before, so commits, pushes and merges remain blocked.

Done line: refuse inside a followed repo, allow outside -> `dev/toy/test-govern-notes.py` (Python, runs on Windows), rows
mon16-notes-pass and mon16-edit-inside-refused, both seen red; new requirement MON-16 (Unreviewed).

Open questions: none. Note for the owner: adding MON-16 changes the reviewed Requirements lock on Monitoring (LOCKED).
