# Plan: reply-hook (autoplan, unattended)

Reviewed in three phases (CEO, DX, Eng; no UI scope), native voice only: the outside voice could not run here
(`execution_failed`), so each phase closed native-only. 34 findings: CEO 8, DX 13, Eng 13. The final gate holds 3 items: d1
and d2 (user challenges, recommended "keep your direction") and p1 (plan approval, recommended "approve as-is"). The run left
them pending. The repo has `auto_approve` on, so `goal.py record` approves them, as logged.

## Implementation plan

1. `skills/workflow-monitoring/scripts/reply_hook.py`, stdlib only, under 20 KB. Commands: none (the Stop hook: JSON on
   stdin), `check FILE|-`, `status`.
   - Hook: prints `{"decision": "block", "reason": ...}` to block, nothing to pass, always exits 0. Fail open: any
     exception prints nothing and appends `fail-open: <error class>: <message>` to the log when the loop folder is known.
   - Repo: `git -C cwd rev-parse --show-toplevel --path-format=absolute --git-common-dir` (absolute, Eng F2); no repo, no
     `.loop/config.json`, `reply_hook` false, or env `LOOP_REPLY_HOOK=0` -> pass.
   - `session_id` must match `^[A-Za-z0-9_-]{1,128}$`, else pass (Eng F11).
   - Kind cache `<common>/loop/reply-hook/<session_id>.kind` (`worker` or `operation`, sticky once decided; CEO F6, Eng F9).
   - Transcript: main-chain entries only (`isSidechain` true skipped, Eng F5); tool results paired to tool_use by
     `tool_use_id`; result text flattened from a string or text blocks (Eng F6). A refusal: `is_error`, or any line starting
     `REFUSED`, or the result begins `Exit code N` (Eng F4, F6). Commands are matched on the script's basename and
     subcommand after splitting the command (`shlex`), never as a substring (Eng F4).
   - Worker: realpath cwd inside `<common>/loop/worktrees/`, or a non-refused `flow.py ...` or `goal.py step|record|pr ...`.
   - Operation: a non-refused `operate.py run` or `board.py board` (a background-launch result counts). A confirmed
     operation signal in a session that later cds into a worktree stays operation (Eng F12); a worker signal wins over an
     operation signal only when it came after it.
   - Final reply: `last_assistant_message`, else walk back past non-message entries (attachment, custom-title, ...) and
     sidechain entries to the last main-chain `user`/`assistant` entry; it must be an assistant entry (else pass); join the
     text blocks of the assistant entries with its `message.id` (Eng F1).
   - `problems(text)`: header = last line that starts `LIVE BOARD ` after Markdown marks are stripped (Eng F7); the section
     names come from `live_board.SECTIONS` (new constant, imported with a fallback copy; Eng F3); in order below the header;
     exactly one non-empty line after `Finish`, then only blanks or a closing fence; the nearest non-empty line above the
     header (skipping a fence) starts `Decisions:`, and no other line above the header does (Eng F7). The six-report-line
     cap stays a written rule; the hook does not count report lines.
   - Block reason (DX F3): `REPLY FORMAT (MON-5): ` + one problem per line, then the template: report lines, then
     `Decisions: ... (or Decisions: none)`, then the board exactly as live_board.py prints it, in a code fence, last.
   - Guard: `stop_hook_active` false resets the count; the 3rd block in a row is let through and logged; count written by
     tmp + `os.replace`, log appended with `O_APPEND` and trimmed to its last 200 lines past 400 (Eng F13).
   - `check FILE|-`: exit 0 silent when clean, 1 with one problem a line, 2 with `REFUSED: cannot read FILE. Fix: ...` (DX F10).
   - `status`: installed or not (repo's `.claude/settings.local.json`), script path exists, setting on, let-throughs in the
     log (DX F2, part).
2. `skills/workflow-setup/scripts/setup.py --reply-hook [--remove]` (DX F13 names it after the setting): resolves
   `../../workflow-monitoring/scripts/reply_hook.py` from its own folder. Refuses (stderr `REFUSED: <what>. Fix: <how>`,
   exit 1; DX F4) when the script is missing, the path holds a single quote, the path is inside a loop worktree (it would
   vanish; DX F5), or `.claude/settings.local.json` is invalid JSON or not the `{hooks:{Stop:[{hooks:[{type,command}]}]}}`
   shape (Eng F8). Order (DX F12): first make git ignore the file (`git rev-parse --git-path info/exclude`, unless already
   ignored), then write the settings atomically. Adds one Stop group `{"hooks": [{"type": "command", "command": "if [ -f
   '<path>' ]; then python3 '<path>'; fi"}]}`, keeping every other key and hook; an entry naming `reply_hook.py` with the
   same path -> `HOOK: already installed`, with another path -> replaced, `HOOK: updated` (DX F5, Eng F8). `--remove`
   deletes only Stop commands naming `reply_hook.py` (`HOOK: removed|not installed`; DX F8). After add/update it prints
   `NOTE: start a new Claude Code session (or open /hooks) to load it` (DX F9). No branch, no commit.
3. `skills/workflow-setup/scripts/settings.py`: repo setting `reply_hook` (default true); regenerate `references/settings.md`.
4. Docs: `references/operation.md` steps 5-6 merged, with a copy-paste passing reply and the reason a bad one gets (DX F11);
   `workflow-monitoring/SKILL.md` one line and command map rows (`reply-hook check`, `reply-hook status`);
   `workflow-setup/SKILL.md` command map row for `--reply-hook`; `skills/loop-files.md` the `loop/reply-hook/` folder.
5. `docs/wiki/Monitoring.md`: MON-5 rewritten to the proposed wording, `**Unreviewed**`; Usage line for install and check.
6. `dev/toy/test-reply-hook.sh`: fixtures shaped like real transcripts (trailing non-message entries, split `message.id`,
   sidechain entries, `Exit code 1` + `REFUSED` results, list-shaped content, a grep that only mentions operate.py, a bolded
   header) and real `live_board.py` output (round trip, Eng F3). Cases as in the design plus: hook run from another cwd
   (Eng F2), stale-path update, remove, env override, kind cache, fail-open logged, check exit codes.
7. `.loop/regression.tsv`: MON-5 rows; each seen failing with its own check disabled (a stub `problems()` returning nothing
   or the classifier forced to "operation"), not only "the script did not exist" (CEO F7, Eng F10). `criteria.py render`.
8. Goal file `## Verify by hand`.

## Not in this goal (findings filed)
- CEO F1: a stale board with the right headings passes; a digest token in the header would prove freshness.
- CEO F3/F5, DX F2 (rest)/F6: the board or health could show "reply hook not installed" and recent let-throughs; that
  touches workflow-health and the live board, outside this goal's paths. `reply_hook.py status` covers it by hand.
- CEO F4 (rest): health flagging a hook that has stopped running.

## Gate items (pending in the run; auto-approved here by `auto_approve`)
- d1 (CEO F2, user challenge): require the board only on board turns. Recommended and taken: keep the direction; done
  line 1 says every reply, and it is frozen.
- d2 (CEO F8, user challenge): make the board artifact the board channel. Recommended and taken: keep the direction.
- p1: approve the plan with the accepted findings above.
