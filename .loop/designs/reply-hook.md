# Design: reply-hook (office-hours, unattended, recommended answers taken)

Status: APPROVED (unattended idea step; recommended answers taken). Spec review: 3 rounds, 20 of 23 findings confirmed resolved, R3-1 fixed and verified at the cap, R3-2 and R3-3 accepted as limits (premise 10).

Mode: builder (internal tooling). Done lines in `.loop/goals/reply-hook.md` are frozen; this design meets them and changes none.

## Problem
The operation session is told, by prose in `references/operation.md` and MON-5, to print the full live board every time. A
prompt rule drifts: a long session forgets it, and the owner gets a reply with no board, or a board with text after it. A
Stop hook is checked by the harness on every reply, so the rule holds without the model remembering it.

## Facts the design rests on
- A Claude Code Stop hook gets JSON on stdin: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `stop_hook_active`
  and, in recent versions, `last_assistant_message`. Printing `{"decision": "block", "reason": "..."}` (exit 0) keeps the
  session going and hands it the reason; printing nothing lets it stop.
- The transcript is JSONL; each assistant entry holds `message.content` blocks (`text`, `tool_use`).
- The live board (`live_board.py render`) always reads: `LIVE BOARD ...` header, then the lines `Issues`, `Running goals`,
  `Queued goals`, `Dependencies`, `Finish`, then one finish line, last.
- `LOOP_OPERATION_SESSION` is the app's session id, not the hook's `session_id`, so it can't name the operation session to a hook.
- Workers run in worktrees under `<git common dir>/loop/worktrees/`, but a worker session's own cwd may still be the main checkout.

## Premises (accepted)
1. The operation session is the session that ran `operate.py run`: a Bash `tool_use` whose command runs `operate.py` with
   `run` (or `board.py board`, which the loop also runs each pass), and whose matching `tool_result` is not a refusal. A result is a refusal when
   any of its lines starts `REFUSED` (role.py's refusal exits non-zero, and the Bash tool may put an `Exit code N` line or
   `is_error` first, so the first line alone is not trusted). `operate.py run` is a long loop, so the session may start it in the
   background; a background-launch result counts, it only must not be a refusal. Text that only mentions the command (a
   `cat` of the docs, a chat line) does not count: only Bash commands are read.
2. A worker is never checked. A session is a worker when its cwd is inside `<git common dir>/loop/worktrees/`, or when its
   transcript has a Bash command that runs a flow step only a worker runs (`flow.py`, or `goal.py step|record|pr`) and whose
   result is not a refusal. Commands the operation session may also run (`sessions.py bind`, `goal.py answer`, `merge.py`)
   are not markers, and a refused goal step in the operation session (role.py refuses it with one `REFUSED` line) leaves it
   checked. The worker test wins over premise 1.
3. "Other repos' sessions": the hook reads the repo from the hook's `cwd`; a session outside a repo, or in a repo with no
   `.loop/config.json`, is never checked. The hook is installed per repo, into that repo's own `.claude/settings.local.json`.
4. One setting turns it off: `"reply_hook": false` in `.loop/config.json` (default `true`), listed by `settings.py` like every other setting.
5. The reply shape, checked in this order:
   - the board's header is the last line starting `LIVE BOARD `;
   - below it, the lines (compared with surrounding whitespace and Markdown `*`, `#` and `` ` `` marks removed) `Issues`, `Running goals`, `Queued goals`, `Dependencies`, `Finish` appear, each exactly, in that order;
   - after `Finish` there is exactly one non-empty line (the finish time), then only blank lines or a closing code fence;
   - the nearest non-empty line above the header (a code fence line between them is skipped) starts with `Decisions:`, and it
     is the only line in the reply that does. With nothing to decide it reads `Decisions: none`.
   The reason it blocks with names every part that is wrong, for example "no `Decisions:` line right above the board;
   missing section Dependencies; text after the finish line", and ends "paste the board exactly as live_board.py prints it,
   inside a code fence, last".
6. The reply read is the final assistant message only, on both paths. `last_assistant_message` from the hook input when
   present. Otherwise the transcript: the final entry must be an assistant entry holding a text block (if it isn't, the
   transcript may lag behind the stop, so the hook passes); the reply is the text blocks of the entries that share that final
   entry's `message.id`, joined with newlines in order. No text at all passes.
7. Fail open: any error (bad stdin, unreadable transcript or config, an exception) exits 0 with no output, so a broken hook
   never blocks or clutters a session.
8. Install: the hook ships in the template (`skills/workflow-monitoring/scripts/reply_hook.py`) and only `setup.py --hook`
   installs it. setup resolves the script as the absolute path of `../../workflow-monitoring/scripts/reply_hook.py` beside its
   own folder (the copy of the skills setup itself runs from), refuses if that file is missing or its path holds a single quote, and adds to the repo's
   `.claude/settings.local.json` one Stop hook whose command is `if [ -f '<path>' ]; then python3 '<path>'; fi`, so a moved
   script fails open. It merges: loads the existing JSON, keeps every other key and hook, adds the entry only when no Stop
   command already names `reply_hook.py`, and refuses without writing when the file is not valid JSON. It makes git ignore the
   file through `git rev-parse --git-path info/exclude` when git doesn't already ignore it. A second run changes nothing.
   Nothing writes the user's own `~/.claude` settings or the machine's installed skills.
9. No loop forever: the count lives in `<git common dir>/loop/reply-hook/<session_id>.count`. A stop with
   `stop_hook_active` false is a new turn and starts the count at 0; each block adds one. The third block in a row is let
   through instead, with one line logged to `<git common dir>/loop/reply-hook/log` (time, session, what was missing; the log
   keeps its last 200 lines). A pass or
   a let-through deletes the count file.
10. Accepted limits: a background launch never shows its output, so a worker that launched `operate.py run` in the
    background before its first flow step is checked until that step (the three-block cap bounds it); a final message only
    partly flushed to the transcript is checked as written (the fallback is best-effort; `last_assistant_message` is preferred);
    an operation session that has not yet run `operate.py run` (a fresh handoff), or whose cwd moved into a
    worktree, goes unchecked until it does / moves back. MON-5's own wording and the operation docs carry the rule there.

## The reply order in the docs
`references/operation.md` steps 5 and 6 become one step: "Reply with at most 6 report lines (anything waiting on the owner
first), then one `Decisions:` line (what the owner must decide, or `Decisions: none`), then the full live board, last.
A hook installed by setup blocks a reply that doesn't end this way." The SKILL.md operation section says the same in one line.

## Proposed MON-5 wording (Unreviewed until the owner reviews it)
"Cadence and reply format. The operation session updates the board and prints the live board on a set cadence, 30 minutes by
default and changeable, and at once whenever a worker reports something new. It prints the full board every time. Every reply
it gives ends with one decisions line and then the full live board, and a hook that setup installs blocks a reply that
doesn't, saying what is missing; the hook never checks worker sessions or other repos, and one setting turns it off."

## Approaches
- A (recommended): a structural check in a stand-alone stdlib script. Reads the last reply (`last_assistant_message`, else
  the trailing assistant text in the transcript), checks premise 5's shape, blocks with a reason that names each missing
  part ("no Decisions: line above the board", "missing section: Dependencies", "text after the Finish line"). Cheap,
  offline, no gh calls on every reply.
- B (rejected): regenerate the board with `live_board.render()` inside the hook and compare text. Calls gh and health on every
  stop (seconds), and a board that moved between print and stop would block a correct reply.
- C (rejected): mark the operation session with a file `operate.py` writes. It can't know the hook's `session_id`, and a
  stale file would check the wrong session.

## Proof (done lines)
1. `reply_hook.py` blocks a reply with no board, a board missing a section, text after the finish line, or no/two decisions
   lines, and its reason names what is missing; it passes `Decisions: ...` + the full board; a third block in a row lets through and logs.
2. It passes, unchecked, a worker (worktree cwd or a goal-step command that ran), a session in another
   repo or in none, malformed input, and any session when `reply_hook` is `false`.
3. MON-5 gets the proposed wording as `**Unreviewed**` (owner reviews it in their own words with `criteria.py review MON-5 --user`).
4. `dev/toy/test-reply-hook.sh` proves blocked / passed / worker never checked (worktree, and main checkout after a goal step),
   operation session with a refused goal step still checked, background operate launch counts / transcript fallback / off switch / other repo / malformed input / setup install merges, keeps other content
   and is idempotent, with no model and no real session.
5. Regression rows (goal MON-5) for each, seen failing then passing, and `criteria.py render` lists them as Given/When/Then
   scenarios under MON-5 on the Monitoring page.

## Open questions
- None blocking. Whether this repo's own main checkout gets the hook installed is the owner's call (`setup.py --hook`); the goal ships the hook and the installer, it doesn't install it here.

## Next steps
1. `reply_hook.py` (check + decide), 2. `setup.py --hook` + `reply_hook` setting, 3. toy test + rows, 4. docs (MON-5,
   operation.md, SKILL.md files, settings reference), 5. render Tests.

## Reviewer concerns (independent spec review, 3 rounds)
- R3-1 (blocking at the cap, fixed): a refusal is any result line starting `REFUSED`, not only the first line (premise 1).
- R3-2 (minor, accepted): a background `operate.py run` launch never shows its output (premise 10).
- R3-3 (minor, accepted): a partly flushed final message is checked as written; the fallback is best-effort (premise 10).
