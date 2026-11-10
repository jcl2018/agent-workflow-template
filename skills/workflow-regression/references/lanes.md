# Lanes: what runs when, and every message a lane prints

A lane is one background run of the regression rows for a goal's step (qa, ship or pr), started by
`role.py lane SLUG NAME` (flow.py and goal.py call it). This page is the reference for its messages, clocks and
settings. The Regression wiki page holds the requirements (REG-1..REG-9); this page is the tool's own manual.

## Which tests run when

| Where | Rows that run | Takes a lane slot |
|---|---|---|
| goal lane, qa and ship | rows whose closure reaches a file the goal changed since its merge-base, the goal's new or changed rows, rows that run tools on the repo root, and rows that failed last time | no |
| goal lane, pr | the same, plus the full suite once when the goal changed a path no row declares, or deleted one (`FULL (unmapped <path> at pr)`) | only when FULL |
| goal lane with no merge-base (shallow clone, missing base) | every row (`FULL (no merge-base with <base>)`) | yes |
| hand run `regression.py run land\|nightly\|ID [--kind K]` | what you name; a plain `run nightly` is the full suite and records its time | when it is a full run |
| GitHub Actions, on the `regression_cron` schedule (every 4 hours by default; `off` stops it) and every v* tag | `ci_levels` (default nightly: every row, the full suite; land: land rows only) | n/a (a runner) |
| GitHub Actions, run by hand | its `target` input: land, nightly or a row id (empty: `ci_levels`); the workflow's own runner checks it, so a repo without the skills folder works | n/a |

ship and release reuse the qa lane's results when no code changed since (`REUSED`). Before a pull request merges,
merge.py checks the base: a move in paths this goal's rows reach refuses (`BASE_MOVED`); `goal.py pr` then merges the
base and reruns the affected rows. Which levels run where is fixed by design (land: goal lanes, hand runs and CI;
nightly: CI and hand runs); `goal_levels` and `ci_levels` change it.

## Lane messages

Status lines go to stdout, refusals and errors to stderr. A `Fix:` part is something to do before going on; a `Note:`
part is advice and never blocks.

| Code | Printed by | Exit | Meaning | What to do |
|---|---|---|---|---|
| LANE | lane.py | 0 / 1 | the lane ended: `LANE <step> <AFFECTED\|REUSED\|FULL> ran/total in Ns; rows: S selected (A affected, N new, R root runners, F failure reruns), U reused, X unfinished; unmapped: K; log: <path>` | read the log for each row's reason |
| RUNNING / WAITING | lane.py | 0 | still planning or running / waiting for a lane slot or a sibling lane of the goal | run the same command again, or `role.py lane-wait SLUG NAME` |
| LANE_WAIT | slots.py | — | all lane slots are busy; names the holders | none: it starts when one frees (`LOOP_LANE_LIMIT=0` skips the pool for one run) |
| LANE_WAIT_TIMEOUT | slots.py / lane.py | 4 / 2 | a hand run off a terminal waited 4x its time limit (4); `lane-wait --timeout` ran out while the lane keeps running (2) | run again later |
| LANE_SLOTS_UNAVAILABLE | slots.py | — | the lanes folder can't be used; the lane runs without a slot | `chmod 700` it, or set `LOOP_LANES_DIR` |
| LANE_STALE | slots.py | 5 | HEAD or the worktree changed while the lane waited; no rows ran | run the same command again |
| LANE_TIMEOUT | lane.py | 124 | past its time limit (flow file `limit`, else `step_limit`); killed, rows partly ran, nothing committed or pushed | run again, or raise the setting |
| LANE_TIMEOUT (FULL_TIMEOUT) | lane.py | 124 | a FULL goal lane passed `full_suite_minutes`; not retryable by the worker | the owner raises `full_suite_minutes` or narrows rows |
| LANE_DIRTY | lane.py / tables.py | 1 | uncommitted changes at start, a hand edit above a page's Tests section, or a row left files behind | commit or revert them; make the row clean up |
| LANE_PREP | tables.py | — | the lane first committed the re-rendered Tests tables and run dates | none |
| LANE_PREP_FAILED | tables.py | 1 | that commit or the render failed or hung (60 s); nothing committed | make the commit pass, then run again |
| LANE_RECORDER | lane.py | 1 | the flow file's `test_record` command isn't on this machine | install it or remove it |
| LANE_DIED | lane.py | 1 | the lane ended with no exit status | the next call starts a new lane |
| LANE_MISSING / HEAD_MOVED (record) | lane.py via goal.py | 2 | `goal.py record qa\|ship` with no passing lane on this HEAD; no try is used | run `role.py lane SLUG NAME` |
| NO LANE | lane.py | 3 | `lane-wait` found no lane for this HEAD | start one with `role.py lane SLUG NAME` |
| UNMAPPED | tiers.py | — | a changed or deleted path no row declares (Note) | declare it in the `# reads:` header of the row that tests it, or let pr run the full suite once |
| KILLED | regression.py | — | a signal stopped a row: `KILLED <row>: signal <name> (pid <n>)` (Note) | see the lane log |
| FLAKY | regression.py | per result | a row gave different results on the same clean commit, runner and python (Note): the raw result counts, the flag stays on that commit (regression-runs.tsv's flaky column, tests.py list, health's TESTS block) and the row is never reused | find the nondeterminism in the row's command; FLAKY clears when a later commit's clean run passes |
| SUITE_TIME | regression.py / CI run step | — | a plain full run's time (`regression.py run nightly`, or a CI run whose target is nightly), appended to `<git common dir>/loop/suite-times.tsv` for health's REG-7 check; CI keeps its line as artifact `suite-time`, which the scheduled health job downloads with a `ci` column | none |
| REFUSED (BAD_TARGET) | CI run step | 1 | the run-by-hand `target` input is not land, nightly or a row id: `REFUSED (BAD_TARGET): bad target "<value>": use land, nightly or a row id from regression.py list. Fix: rerun the workflow with one of those`; no row ran | rerun the workflow with one of those |
| REFUSED (BASE_MOVED) | merge.py | 2 | the base moved in paths this goal's rows reach since the pr lane | `goal.py pr SLUG`, then `merge.py SLUG` |
| REFUSED (BASE_FETCH) | merge.py | 3 | origin can't be fetched to check the base; nothing merged | run `merge.py SLUG` again when the remote answers |
| REFUSED (HEAD_MOVED) | merge.py | 4 | the pull request head moved since the pr lane | `goal.py pr SLUG`, then `merge.py SLUG` |

Exit codes shared by every lane entry point: 0 pass (or still running for `role.py lane`), 1 fail, 2 lane-wait
timeout, 3 no lane, 4 a hand run's slot wait timed out, 5 stale, 124 time limit.

## Clocks

A lane's time limit counts from its started marker (when it took its slot and began rows), never from launch. While
it waits for a slot it has a queue span instead (4x the time limit, restarted whenever any slot changes), so a healthy
backlog never kills a waiting lane; while planning it has 4x the time limit. A FULL goal lane's limit is
`full_suite_minutes`. A hand run on a terminal holding a slot has no deadline; off a terminal its slot wait stops after
4x its time limit (flow file `limit`, else `step_limit`, else 2700 s). `lane-wait` with no `--timeout` waits until the
lane ends.

## Settings

- `lane_limit` (flow file, default 2): full lanes that may run at once on this machine; 0 is unlimited. Best effort:
  it limits concurrent full lanes, not the machine's load; AFFECTED, by-id and red runs take no slot.
- `goal_lane_minutes` (10) and `full_suite_minutes` (30): health warns above them (REG-7); the second is also a FULL
  goal lane's time limit.
- `goal_levels` (land) and `ci_levels` (nightly): the levels a goal lane plans from and the CI target.
- Each lane child gets its own `TMPDIR` and `LOOP_LANE_PORT_BASE` (a leased range of 100 ports from 20000); a row that
  binds ports uses that range or picks a free port itself.
- Internal handoff variables (`_LOOP_LANE_HELD`, `_LOOP_LANE_LABEL`, `_LOOP_LANE_QUEUED`, `_LOOP_LANE_STARTED`,
  `_LOOP_LANE_NOTE`) are set by the lane; a `test_record` wrapper must keep the environment.

## Upgrading

Updating the skills while lanes run is safe: a lane job written by the old code keeps the old rules until it ends.
New: goal lanes no longer run the full suite at qa for an unmapped path (pr does, once); the lane commits re-rendered
Tests tables before it starts; regression-issues.tsv gains a reopened_at column and old files still read; the
regression workflow's run-by-hand gains a `target` input.

## Alternatives considered

GitHub's merge queue and "require branches to be up to date" make merges atomic on the platform; the loop keeps its
own base check for repos without them, and the window between its check and the merge is closed only by those
settings. Actions concurrency groups already keep one regression run at a time in CI. Running AFFECTED lanes in CI
was left out: CI runs the full suite only (REG-4).
