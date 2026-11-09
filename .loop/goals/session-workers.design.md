# Design: session-workers

Status: shaped by the idea skill in an app worker session, with the recommended answer at every question. Nothing was
approved, merged or pushed. The goal's done lines are frozen, and this design meets them as written.

## Problem

Issue 98. Goals moved into app worker sessions (`worker · <goal>`) still show on the live board as failed background
workers carrying the old error. The board reads only background run records, and `refresh()` / `worker.py loop` mark a
goal `failed` when its pid ends. The loop also still starts a headless agent for every step by default (`flow.py`
calls `agent_command`). That route is blocked when the usage limit is hit. The owner's new MON-1 and MON-2 make app
sessions the default worker and session messages the channel.

## Premises (taken as agreed)

1. A script can't call the app's session tools; only a model in a session can. So the scripts use a **session tool**,
   a command named by `session_command` in `.loop/config.json` (the `LOOP_SESSION_TOOL` env var overrides it). It
   takes `start NAME`, `rename ID NAME` and `send ID TEXT`, and a non-zero exit means it can't start or reach a
   session. Tests swap in a stand-in. In the app, the operation session can do the same work with its own tools and
   record it with `sessions.py bind`.
2. A goal in a session has no pid, so nothing marks it `failed` because a process ended. The existing rule "never set
   failed for a goal with no pid" already holds; binding a session clears `pid` and the old background finding.
3. The run record in `<git common dir>/loop/runs/` stays the one source of truth: the board, live board and handoff
   already read it. A session's reports go there too (`reports`, `report`, `step`, `status`).
4. Scripts stay under 20 KB: `watch.py` is 17.4 KB and `goal.py` 17.8 KB, so the new logic goes in a new module,
   `skills/workflow-monitoring/scripts/sessions.py`, with small hooks in watch.py, goal.py and flow.py.

## Approaches considered

- **A: Session tool behind a small module (recommended, taken).** `sessions.py` keeps a pool in
  `<common>/loop/sessions.json`, assigns, renames, sends, records and falls back. The rest of the loop stays the same.
  Effort M, risk low. Tests use a stand-in tool.
- **B: The operation model does everything by hand.** `operate.py` prints ASSIGN lines and the model acts on them with
  app tools. Rejected: it isn't deterministic (MON-1: "the same way every time") and can't be tested without a model.
- **C: Workers poll an outbox file instead of session messages.** Rejected: MON-2 names session messages as the channel.

## Recommended approach

1. **MON-1, MON-2 (line 1).** `criteria.py unreview MON-1 MON-2 --user`, rewrite both lines in
   `docs/wiki/Monitoring.md` word for word, then `criteria.py review MON-1 MON-2 --user`. `--user` needs the owner's
   own words, so the worker asks the owner in its session before running it.
2. **Assignment (line 2).** `sessions.assign(state, prompt, cfg)` is called by `watch.start_round` in place of
   `launch`:
   - pick a `free` session from the pool, or `start` a new one;
   - `rename` it `worker · <slug>`;
   - `send` it the goal prompt, which carries the goal, worktree and report instructions;
   - record `session: {id, name, via: "session"}` and `worker: "session"` on the run, with status `running` and no pid.

   Any tool failure, or no tool set, falls back to `launch` (background) with `worker: "background"` and
   `worker_why`. `sessions.py bind SLUG ID [--name]` records a session the operation model started itself, which is
   the issue-98 recovery path: it clears the failed status and the old finding.
3. **Reports (line 3).** `sessions.py report SLUG [--step S] [--status S] [--pr URL] [--text T]`: operate runs it for
   each session message a worker sends. It appends to `reports`, updates `step` and `status`, and sets `report` on a
   final status (merged, failed or waiting). On a final status the session goes back to `free` in the pool. The worker
   prompt tells the worker to SendMessage the operation session on each step change and at the end. The live board
   shows `worker · <slug>` (or `background`) on each running goal's line.
4. **Steps in the session (line 4).** `flow.py`: when the run has `worker: "session"` (or `LOOP_SESSION` is set), it
   doesn't start a headless agent. It prints `IN SESSION`, the mapped skill, the unattended rules and the reply file
   path, and writes the `.ran` marker. The session invokes the skill itself and writes the reply ending in `STEP:`.
   `goal.py record` then accepts that file (copied into place) because the run is a session run. Headless only when
   there's no worker session.
5. **Toy test (line 5).** `dev/toy/test-session-workers.sh` with a stand-in session tool (a shell script logging calls
   and returning ids, or failing on demand). It proves assignment, renaming, the report path, reuse of a finished
   session for the next goal, and the background fallback.
6. **Defect test (line 6).** A regression row of category defect linked to issue 98. It's red on the old code (a
   session-bound goal shows as failed, or without its session name) and green now. The PR body says "fixes #98".

## Risks

- **Size cap:** keep watch.py and goal.py under 20 KB; trim them if needed.
- **Message delivery can't be verified from a script.** The board says `background` whenever the tool path wasn't used,
  so nothing is hidden.
- **`--user` on criteria** needs the owner's own words. That decision stays with the owner.

## Open questions

- None that block the build.
