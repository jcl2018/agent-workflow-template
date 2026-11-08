# Design: health-green

Status: DRAFT for owner review. Meets the frozen done lines in .loop/goals/health-green.md; changes none of them.

## Problem (measured on this branch)
`health.py check` is not green: release.py is 19859 B (96% of 20 KB), 8 open findings, 11 merged `loop/*` branches, and the cost rule reads UNREAD ("no tokens recorded"). Only one run record has `tokens`, and it is a regex hit (`total: 3000000`).

Root cause of the token gap: `flow.py` runs `claude -p` with plain-text stdout into `<slug>.<step>.txt`, and `role.tokens()` greps that text for "N tokens". Plain `-p` output never says that, so nothing is recorded. The same regex is duplicated in `worker.py`.

## Approach (recommended): read usage from the agent's own JSON output
1. Done line 1. In `flow.py` `start()`, when the command's binary is `claude`, append `--output-format json`. On finish, parse the reply: take `usage` (input + output + cache-creation tokens, one documented formula, stated in SKILL.md) as the step's tokens, and rewrite the reply file to the `result` text so the STEP/PENDING lines and `goal.py record` work unchanged. Unparseable output falls back to the current regex, then to no record. Non-claude commands keep the regex path. Move the parse into `role.py` (one helper, `role.usage(text) -> (tokens, text)`), and make `worker.py` call it instead of its own copy of TOKENS. Tokens land in `state["tokens"][step]`, which `board_status.tokens_by_step` and `cost.py` already read, so the status block and Cost rule need no change. Add a toy test in `dev/toy` (fake agent printing JSON) asserting the per-step number and the status line.
2. Done line 2. Trim release.py to at most 18432 B (90%) with no behaviour change: remove duplicated helpers/comments and fold small functions (candidates: `restore`, `docs_lines`/`docs_trouble`, `loop_only`), or reuse `role.py`/`docs.py` helpers where they duplicate. Proof: `test-release.sh` passes unchanged, and `health.py` size row passes. No splitting into a new module (that would add a file to the install surface).
3. Done line 3. Triage the 8 findings in `.loop/findings.md`. All are "Failed 3 tries" for goals that have since landed or been superseded (project-wiki family, operation-session, auto-release, numbered-levels-2). For each, check the goal's run record and git log; retire it with a one-line reason if merged or superseded, keep it only if the failure is still reproducible. Target at most 5 open; none kept without a re-check.
4. Done line 4. Add `cleanup` (or `--clean`) to the monitoring/health tooling: delete only `loop/*` branches that `git branch --merged <base>` lists and that no worktree has checked out, using `git branch -d` (never `-D`), print each deletion, no remote deletes. Point the health fix line at it (`-> fix: <script> cleanup`) instead of per-branch `git branch -d`. Run it once here so the check shows no merged-branch warnings; branches checked out in other worktrees (e.g. `loop/no-gates`) are left and reported.

## Alternatives considered
- B, regex only: ask the agent to print "N tokens" in its reply. Rejected: depends on the model obeying, not "from the agent's own output".
- C, read `~/.claude` transcripts for usage. Rejected: couples to private file layout.

## Risks
- `--output-format json` changes the reply shape: guarded by the fallback and the rewrite-to-result step.
- Branch deletion is irreversible-ish: `-d` only, merged only, not checked out.
- Trimming release.py can regress cut/ask: existing release toy test is the gate.

## Distribution
No new artifact; ships in the existing skills.
