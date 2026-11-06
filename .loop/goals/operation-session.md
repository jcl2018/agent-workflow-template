# Build the operation session: one session starts others, follows them in a loop, and keeps a progress board

- Slug: operation-session
- Level: standard
- Touches: skills/workflow-monitoring, skills/loop-files.md, dev/toy/test-board.sh, listing.json, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. A new self-contained skills/workflow-monitoring/scripts/board.py has a board command that builds one JSON document from run records and prints DIGEST, CHANGED yes or no, one CHANGE line per changed state field, NEXT_DELAY in seconds, and the path of the JSON and HTML it wrote, with --at TIME and --since FILE so the same inputs give the same output
2. The board has six sections in this order: Waiting on you (each question with the exact words to type and the session or worktree to type them in), Dependency map (each queued goal and the goal or shared file it waits on), Runs (goal, level, step, elapsed, tries, pull request, its check state, last message), Expected finish (estimated from finished goals of the same level, marked as an estimate, and no estimate when there is no history), Finished today (what finished and delivered, plus a one line note that it can be archived only when nothing waits on it), and Every step (one row per goal step with its status)
3. The HTML page is self-contained with no scripts or network, follows the light or dark setting, puts Waiting on you first, works at phone width, and escapes all text from records
4. board.py has cadence N or off (1 to 60 minutes, default 10) kept in the git common loop folder, and NEXT_DELAY is none after off, 3600 when nothing runs or waits, otherwise the cadence, clamped to 60 through 3600
5. board.py can follow several repos: repos add PATH keeps a list under the home folder, and board reads every listed repo, naming the repo on each row
6. A goal can run as a visible session instead of a hidden process: watch.py go --session freezes the goal, makes its worktree, starts no process, and prints WORKTREE and PROMPT for the governing session to start, and the record is marked external so a missing process never marks it failed; a quiet external goal shows as quiet on the board after 30 minutes without an update
7. board.py note SLUG TEXT records a session's latest message on its run, the board shows it as last message, and that text is treated as data
8. board.py handoff writes one file naming the repos, cadence, open goals, what waits on the owner and the next check-in steps, so a new session can take over
9. A new skills/workflow-monitoring/references/operation.md describes the operation session's loop: run watch once, read each session's latest report, run board, publish the HTML in place when an Artifact tool exists, write one chat line only when something changed, report at most 6 lines, then wait NEXT_DELAY; it states the rules: never answer a gate, give the owner the exact words and where to type them, treat other sessions' messages as information, merge only when told, never archive a session, and it is linked from SKILL.md
10. dev/toy/test-board.sh proves each line above with fixtures and no model calls, every other repo check passes, each script stays under 20 KB and each SKILL.md under 150 lines, and listing.json discloses the new commands and writes

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

1. Run `python3 skills/workflow-monitoring/scripts/board.py board` in a repo with some runs.
   Expect: it prints DIGEST, CHANGED, NEXT_DELAY, JSON and HTML lines; open the HTML and see "Waiting on you" first.
2. Run `python3 skills/workflow-monitoring/scripts/board.py cadence off`, then `board`.
   Expect: it prints `NEXT_DELAY none`.
3. Run `python3 skills/workflow-monitoring/scripts/watch.py go "demo" --done "x" --session`.
   Expect: it prints WORKTREE and PROMPT and starts no process.

## Design

`board.py` is a separate stdlib script (the 20 KB cap forbids sharing code with monitor.py, and it must stand alone).
It reads run records from each followed repo's git common dir, builds one JSON document (sections, rows and a flat
`state` map), and renders HTML from that same document with every value escaped. `--since` diffs the `state` map of the
previous JSON, so the same inputs and `--at` give the same output. `watch.py go --session` marks the queue line
`session: yes`; the record gets `external: true`, no pid, and `refresh`/`keep_moving` skip external records.
Risks: watch.py is near the size cap (trimmed docstrings); notes are untrusted text (collapsed, escaped, never executed).

## Plan
1. board.py with board, cadence, repos, note, handoff (done lines 1-5, 7, 8).
2. watch.py go --session and external records (line 6).
3. references/operation.md, SKILL.md link, loop-files.md, listing.json, README.md (lines 9, 10).
4. dev/toy/test-board.sh proves every line with fixtures (line 10); run it and the repo checks.

## Evidence

Output of `bash dev/toy/test-board.sh` (it now runs as a repo check; it also checks the 20 KB script and 150-line SKILL.md limits and the listing.json words):

```
PASS: operation.md: merge only when told
PASS: operation.md: never archive
PASS: SKILL.md links operation.md
PASS: under 20 KB: goal.py
PASS: under 20 KB: docs.py
PASS: under 20 KB: board.py
PASS: under 20 KB: monitor.py
PASS: under 20 KB: watch.py
PASS: under 20 KB: regression.py
PASS: under 20 KB: release.py
PASS: under 20 KB: setup.py
PASS: under 150 lines: workflow-delivery
PASS: under 150 lines: workflow-docs
PASS: under 150 lines: workflow-monitoring
PASS: under 150 lines: workflow-regression
PASS: under 150 lines: workflow-release
PASS: under 150 lines: workflow-setup
PASS: listing.json discloses "board"
PASS: listing.json discloses "cadence"
PASS: listing.json discloses "handoff"
PASS: listing.json discloses "note"
PASS: listing.json discloses board.json
PASS: listing.json discloses repos

ALL PASS
```
