# Plan: session-workers

Status: The plan skill ran in the worker session, unattended, as a condensed review. The CEO scope pass and the eng
architecture and test pass were done by hand. No outside voice, snapshot driver or phase subagents ran. Every question
took the recommended answer, and nothing is approved. Source: `session-workers.design.md`.

## Scope (CEO pass)

- **In scope:** the six done lines, the docs that describe workers (monitoring SKILL.md, operation.md,
  docs/wiki/Monitoring.md, the delivery SKILL.md step-run text), and regression rows for the new behavior.
- **Not in scope:**
  - a real app session-tool binary, since the app gives none to scripts and the operation model binds sessions with
    `sessions.py bind`;
  - mend.py support for sessions (a session goal has no pid, so mend never touches it);
  - a session pool shared across repos.
- **Already exists and is reused:**
  - run records and the `report` / `reports` shape (worker.py `message`);
  - inbox follow-ups (`worker.py send`, `role.inbox`);
  - `refresh()` never failing a goal with no pid;
  - `flow.py` `.ran` / reply / `goal.py record` validation;
  - the live board's running-goal block.
- **Premise check:** "steps run in the session" needs no change to `goal.py record`. When flow.py writes the `.ran`
  marker after the session leaves its reply at the step's reply path, `record` accepts it unchanged. That is a smaller
  diff than the design's copy-into-place idea, so it's taken (decision 3).

## Architecture (eng pass)

```text
operate.py run ─▶ watch.py start_round ─▶ sessions.assign(state, prompt, cfg)
                                             │ tool ok: start/rename/send ─▶ run.worker=session, run.session={id,name}
                                             └ tool missing/fails ─▶ watch.launch() (background) ─▶ run.worker=background, worker_why
worker session ─ SendMessage ─▶ operation model ─▶ sessions.py report SLUG --step/--status/--pr ─▶ run.reports[], run.report
                                                                                         final status ─▶ pool[id].state=free (reused next assign)
worker session ─▶ flow.py SLUG STEP (run.worker=session) ─▶ prints IN SESSION + skill + rules + reply path (no headless agent)
               ─▶ invokes the skill itself, writes reply ─▶ flow.py again: .ran marker, NEXT ─▶ goal.py record
live_board.render ─▶ "- slug [bar] ... · worker · slug" or "· background"
```

## Steps

1. `skills/workflow-monitoring/scripts/sessions.py` (new, under 8 KB):
   - `tool()` reads `LOOP_SESSION_TOOL` or `session_command`;
   - `assign()`, `pool()` and `save_pool()`;
   - commands `assign SLUG`, `bind SLUG ID [--name]`, `report SLUG ...`, `list`.

   Proves done lines 2 and 3.
2. `watch.py` `start_round` calls `sessions.assign` when importable, and otherwise `launch`. GO_PROMPT gains the
   report rule ("send the operation session a message on each step change and at the end"). Done line 2.
3. `flow.py`: session mode prints IN SESSION and never starts the command, and a later call with a reply present
   writes `.ran` and NEXT. Done line 4.
4. `live_board.py` shows the worker kind and session name on running goals. Done lines 3 and 6.
5. The docs (monitoring SKILL.md, operation.md, Monitoring.md, delivery SKILL.md step text) and MON-1 / MON-2 through
   criteria.py with `--user`, asked of the owner first. Done line 1.
6. `dev/toy/test-session-workers.sh` with a stand-in tool covering assignment, rename, reports, reuse and fallback,
   plus the flow.py session mode. Done lines 4 and 5.
7. A defect regression row linked to issue 98 (`regression.py add --category defect --link ...`, `red` against the old
   code), and "fixes #98" in the goal. Done line 6.
8. Keep scripts under 20 KB, then run the repo checks.

## Test plan

| Codepath | Test |
|---|---|
| assign: new session, rename, send, record | toy: tool log has `start`, `rename ID worker · a`, `send ID ...`; run.worker=session |
| assign: reuse free session | toy: after `report a --status merged`, goal b gets the same ID with `rename ID worker · b` |
| fallback | toy: LOOP_SESSION_TOOL=failing stand-in → run.worker=background, launch pid set; board says background |
| report path | toy: `report a --step build` appends to reports, sets step; board shows step and session name |
| flow.py session mode | toy: run.worker=session → IN SESSION, no agent started; reply then flow.py → NEXT; record → RECORDED |
| issue 98 | defect row: a bound goal that had failed shows running with `worker · <slug>` and its step, not failed |

## Failure modes

- The tool hangs: there's a timeout (30 s), and a hang falls back to background.
- The pool file is corrupt: it reads as empty, and a new session is started.
- A report names an unknown slug: one REFUSED line.
- `bind` on a running background goal: it refuses, so a live pid is never hidden.

## Decision audit trail

| # | Phase | Decision | Class | Principle | Rejected |
|---|---|---|---|---|---|
| 1 | CEO | Keep scope to the six done lines plus the docs that describe workers | mechanical | P2 | adding mend support |
| 2 | CEO | No real app session binary; `bind` covers the app | taste | P5 | a fake CLI wrapper |
| 3 | Eng | Reuse flow.py `.ran` + reply path so `goal.py record` is unchanged | mechanical | P4 | copy-into-place in record |
| 4 | Eng | Tool timeout 30 s, then background fallback | mechanical | P1 | blocking |
| 5 | Eng | New module rather than growing watch.py (17.4 KB) | mechanical | P5 | inline |

Result: stopped at the final gate, pending (auto-approved by the repo's auto_approve).
