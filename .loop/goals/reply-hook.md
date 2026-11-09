# Enforce the operation session's reply format with a hook instead of a prompt rule

- Slug: reply-hook
- Touches: skills/workflow-monitoring, skills/workflow-setup, docs/wiki/Monitoring.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A Stop hook that setup can install checks the operation session's last reply ends with the full live board (and one decisions line above it); when it doesn't, the hook blocks the stop and says what is missing, so the session fixes the reply
2. The hook only acts in the operation session, never in worker sessions or other repos' sessions, and turning it off is one setting
3. MON-5 on the Monitoring PRD gains the rule as proposed wording marked Unreviewed, for the owner to review in their own words
4. A toy test proves a reply without the board is blocked, a reply with it passes, and a worker session is never checked
5. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

1. In the main checkout, run `python3 skills/workflow-monitoring/scripts/live_board.py > /tmp/board.txt`, then
   `{ echo "Decisions: none"; cat /tmp/board.txt; } | python3 skills/workflow-monitoring/scripts/reply_hook.py check -`.
   Expect: it prints nothing and exits 0.
2. Run `echo "all quiet" | python3 skills/workflow-monitoring/scripts/reply_hook.py check -`.
   Expect: `it does not end with the live board (no LIVE BOARD header)`, exit 1.
3. In a scratch clone that has `.loop/config.json`, run `python3 skills/workflow-setup/scripts/setup.py --reply-hook` twice.
   Expect: `HOOK: added` and a NOTE the first time, `HOOK: already installed` the second; `.claude/settings.local.json` holds
   one Stop hook naming reply_hook.py, and `git status` does not list it.
4. In that clone, run `python3 skills/workflow-monitoring/scripts/reply_hook.py status`, then
   `python3 skills/workflow-setup/scripts/setup.py --reply-hook --remove`.
   Expect: `REPLY HOOK: installed, setting on, script found, ...`, then `HOOK: removed`.
5. Open the Monitoring wiki page.
   Expect: MON-5 reads `**Unreviewed**` with the reply-format sentence, waiting for the owner's review.
