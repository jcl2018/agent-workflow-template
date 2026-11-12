# Plan: pod-layers

Done lines (frozen): `.loop/goals/pod-layers.md`; design: `pod-layers.design.md`. I ran the review myself against the
code (autoplan's phases were done inline; no outside voice ran). Where this plan and the design differ, the FINAL SPEC wins.
Reference only (read, never edit): `../worktrees/single-operation` has a working `checkin.py` (`gather`, `grouped`) and
`dev/toy/test-single-operation.sh` (its claim/refuse cases are dropped here).

## Review findings (what the code showed)

1. `operation.id` is read as a set by `govern_hook.operation_ids(common)` and `reply_hook.claimed(common)`; `is_operation`
   and the reply hook's `known = "operation"` both test `session in set`. Nothing to change on the read side.
2. The overwrite is in two places: `operate.py cmd_claim` (opens `operation.id` with `"w"`, prints
   `(replaced <old>)`; docstring line 19 says "the last claim wins and names the one it replaced") and
   `govern_hook.claim` (`open(..., "w")`, logs `(replaced ...)`; module docstring line 9 says the same). The hook's
   `claim` only writes when `session not in old`, so the append fix is the same one line.
3. `cmd_run` calls `cmd_claim(argparse.Namespace(id=""))`: it keeps working (no new flag).
4. `board.followed()` returns `(name, main, common)` for the own repo first, then each path in `~/.workflow-loop/repos`
   (deduped by git common dir). Reuse it to write the id into every followed repo (skip a repo whose write fails).
5. `graph.parse` keeps a `repo/slug` token; `graph.unmet` calls it `unknown goal`, so `watch.py` holds it. Out of scope
   (safe). The check-in keeps calling `graph.ready` as today, no rewrite.
6. `board_lines.render` ends with `["", LEGEND]` and filters `depends` to known slugs; `pack` can exceed the width on one
   long piece, so `grouped` must wrap every line itself with `textwrap` at `board_lines.WIDTH` (60).
7. The reply hook finds sections by exact heading; `== name ==` and `Between repos` never equal a required heading, so the
   layout check passes; the test proves it on the three-repo output.
8. The `single-operation` `grouped` reads marks as `board_lines.MARKS.get(mark)` with the item's mark string; an unknown
   repo or slug gives `(unknown)`. Verified as working by diff against HEAD's `checkin.py`.
9. Size at HEAD: `operate.py` 8.5 KB, `govern_hook.py` 11 KB, `checkin.py` 8.6 KB. Four other scripts are ALREADY over
   18,432 bytes (`reply_hook.py` 19.9, `sessions.py` 19.6, `watch.py` 19.6, `live_board.py` 18.6). Done line 4's "stays
   under" is read as: no script crosses 18,432 and none already over grows. This change touches only the first three.
10. `criteria.py review ... --user` with no terminal needs `LOOP_OWNER_WORDS` (`mark_all` reads it, spaces collapsed, and
    refuses empty words with no tty). `criteria_max` is 15 and Monitoring has 12 requirements, so 14 fits.
11. Existing test `dev/toy/test-monitoring-prd.sh` line ~122: `claim --id op2 | grep -q "replaced op1"` must change.

## Ordered build

### 1. `skills/workflow-monitoring/scripts/operate.py` (MON-13)

`cmd_claim`, after the worker and no-id checks, becomes:

```
ids = govern_ids(path)                    # existing file, one id per line, [] if absent
for target in [common] + followed commons: add sid to <target>/loop/operation.id when missing (append "a", makedirs)
print("CLAIMED operation session %s" % sid)
```

- Helper `def add_id(base, sid)`: reads the set, appends `sid + "\n"` only when absent, returns nothing, never raises (an
  `OSError` is skipped). `followed` commons come from `board.followed()`; import `board` lazily inside `cmd_claim`.
- No `replaced` text, no refusal, no `--replace`. The worker refusal line stays exactly as is.
- Docstrings: module docstring `claim` paragraph and `cmd_claim` become: "add this session to operation.id for this repo
  and every repo it follows; other sessions already there stay (several independent operation sessions may run at once);
  refused in a worker."

### 2. `skills/workflow-monitoring/scripts/govern_hook.py` (MON-13)

In `claim()`: replace `open(..., "w")` with `"a"`, keep the `session not in old` guard, and log
`"added %s to operation.id from its operate.py call"` (no `replaced`, no old list). Update the module docstring (line 9):
"...the claim adds its id and keeps the others". The `mkdir` of `<common>/loop` is as today.

### 3. `skills/workflow-monitoring/scripts/checkin.py` (MON-14)

Copy `gather()`, `grouped()` and the `render()` changes from the reference `single-operation/.../checkin.py` nearly
verbatim, then re-verify these against this repo's HEAD:
- `gather(root, at)` returns name, root, cfg, folder, runs, found, why, taken, states, live, queue; own repo unguarded,
  other followed repos in `try/except Exception` recording `(name, reason)`.
- Headline counts and the queued total sum over the pod; the pool line stays the own repo's. All sessions: one row per
  live run of every repo, repo column = that repo's name; empty pod keeps the `nothing running` row.
- `grouped(blocks)`: header `== name ==` (name over 54 chars cut to 51 plus `...`); body `board_lines.render` of the items
  with every `repo/slug` dependency removed, minus its last two lines (`["", LEGEND]`), or `- (none)` for an empty repo;
  then, only if edges exist, `Between repos` and per edge `a/x <- b/y [mark]` or `(unknown)`; then `""` and the legend
  once (the `board_lines.LEGEND` string, not a copy); every line through `textwrap.wrap(..., 60, subsequent_indent="    ")`
  (an empty line stays empty).
- Needs you: unchanged for the own repo; for each other repo `repo/slug asks: ...` for a `waiting` run, and
  `repo: can't be read (<reason>); the other repos are shown` for each unreadable repo.
- A single-repo pod prints one `== name ==` block (no `Between repos`). Update the module docstring's Dependencies line.

No change to `board_lines.py`, `board.py`, `live_board.py`, `graph.py`, `reply_hook.py`.

### 4. Test: `dev/toy/test-pod-layers.sh`

Start from the reference `test-single-operation.sh` (helpers `mk`, `queue`, `runrec`, `claim`, `check`, the temp HOME and
env unsets, the `reads:` header, `SCRIPTS=${POD_SCRIPTS:-$here/skills/workflow-monitoring/scripts}`). Usage
`bash dev/toy/test-pod-layers.sh [layers|blocks|size|docs]` (default all); last line `ALL PASS` or `N FAILED`. Repo names
only `alpha-app`, `beta-svc`, `gamma-lib`, `delta-tool`, `omega-none`. DELETE the reference's refuse/replace/record cases.

Case `layers` (done line 2, MON-13), each a `check` with exit 0 and no text matching `REFUSED|WARN|already|replaced`:
- Same repo: session s1 then s2 claim in alpha-app; both exit 0; `operation.id` of alpha-app holds s1 AND s2; s1 claiming
  again leaves exactly two lines.
- Followed repos: the claim in alpha-app also wrote s1 and s2 into beta-svc and gamma-lib (repos file lists them).
- Separate pods: a second `HOME` (`$T/home2`, own repos file listing only delta-tool) with s3 claiming from delta-tool:
  exit 0, no output text of the above words, `delta-tool` `operation.id` holds s3 only, and the first pod's repos are
  unchanged (still s1, s2). Then s4 claims from delta-tool in HOME 1 (outside its pod): exit 0.
- Hook view, via `python3 -c` importing `govern_hook` from `$SCRIPTS` (or `govern_hook.py check` if that is its CLI; read
  the module): for the common dir of alpha-app, `operation_ids` is `{s1,s2}`; `is_operation({"session_id": "s1", "cwd": alpha-app}, common)` and the same for
  s2 are True; for an unclaimed `s8` False; for s1 with `cwd` inside `<common>/loop/worktrees/x` False; with `LOOP_ROLE=worker`
  False. `reply_hook.claimed(common)` is `{s1,s2}`.
- Govern hook claim: feed the hook the JSON for a Bash call `python3 .../operate.py claim` from session `s5` (a valid id per
  `reply_hook.SESSION`) in gamma-lib: afterwards gamma-lib's `operation.id` has s5 plus the older ids; log has no `replaced`.
- A worker is still refused: `LOOP_ROLE=worker ... claim --id s6` exits non-zero with `a worker can't claim`.
- Check-in runs for both: `python3 $SCRIPTS/checkin.py` from alpha-app and from delta-tool (each HOME) exits 0, prints
  `Dependencies`, `Needs you`, no `Traceback`, and `reply_hook`'s layout check accepts it.
- `CLAUDE_SESSION_ID=s7 operate.py run --once` in a repo already governed by s1 exits 0 with no refusal text.

Case `blocks` (done line 3, MON-14), from the reference test: alpha-app runs `core` (running) + queued `docs` depends on
`core`; beta-svc queued `api` depends-on `alpha-app/core` and `edge` depends-on `omega-none/x`; gamma-lib empty. Assert on
the Dependencies-to-Needs-you slice: the three headers once and in order; `core`/`docs` inside alpha-app's block,
`api`/`edge` inside beta-svc's; gamma-lib's body `- (none)`; `Between repos` once after the blocks with
`beta-svc/api <- alpha-app/core [>]` and `beta-svc/edge <- omega-none/x (unknown)`; legend once, last; `awk 'length > 60'`
prints nothing, also with a 70-character repo directory (header ends in `...`) and 50-character slugs; the All sessions
row for `core` names `alpha-app` and the counts include beta-svc's 2 queued goals; an empty repos file gives one block and no
`Between repos`; a followed repo with a corrupt `.loop/runs` file still lets the check-in print, with one Needs you line and
no traceback; `reply_hook` accepts the three-repo output (use what `test-reply-hook.sh` uses for `checkin-passes-hook`).

Case `size` (done line 4): for every `skills/*/scripts/*.py` the size is under 18432 unless that file is also over it at
`git show HEAD:path` and not larger than at HEAD; `operate.py`, `govern_hook.py`, `checkin.py` each under 18000. Package
file count on a clean archive: `git archive HEAD | tar -t | grep -v '/$' | wc -l` restricted to the package paths that
`test-deployments.sh` counts (skills docs .loop README.md CLAUDE.md AGENTS.md VERSION listing.json CHANGELOG.md LICENSE) is
at most 99 (copy that test's exact list and command; run it on `git archive HEAD` plus the working tree's new files so a
new file is counted before commit: `git ls-files --cached --others --exclude-standard`).

Case `docs` (done line 1): `grep -E '^- MON-13: \*\*Reviewed [0-9-]+\*\* .*<!-- reviewed [0-9a-f]{8} -->'` and the same
for MON-14 in `docs/wiki/Monitoring.md`; `python3 skills/workflow-docs/scripts/docs.py check` exits 0.

### 5. Update the existing test

`dev/toy/test-monitoring-prd.sh` ~line 121-122: the claim check becomes
`python3 "$S/operate.py" claim --id op2 | grep -q "CLAIMED operation session op2"` and `! ... | grep -q replaced`,
and `grep -qx op1 "$L/operation.id" && grep -qx op2 "$L/operation.id"` (reset the file after as the test does), plus the
worker refusal unchanged. The preceding line `op3` check (`cat operation.id` equals op3 after the hook claim from a file
holding op1) now sees two lines: change it to `grep -qx op3 "$L/operation.id"` and `grep -qx op1`. Then run, fixing only
what the append changes and keeping intent: `test-monitoring-prd.sh`, `test-operate.sh`, `test-govern.sh`,
`test-reply-hook.sh`, `test-operate-fit.sh`, `test-operate-fit-3.sh`, `test-live-board.sh`, `test-session-workers.sh`,
`test-lanes.sh`. First `grep -n "operation.id\|operate.py claim\|<- " dev/toy/*.sh` and fix each hit that assumes overwrite
or the flat Dependencies layout (the check-in's Dependencies now starts with a `== name ==` line).

### 6. Wiki text (final before sealing)

In `docs/wiki/Monitoring.md`, after MON-12's sub-bullets and before `### Non-functional`, add exactly:

```
- MON-13: **Unreviewed** Two layers per pod: one operation session governs every repo in its pod directly and talks to each worker, with no per-repo operation session in between; several pods may run concurrently and independently, each with its own operation session, and none needs to know the others
  - A claim adds the session to every repo the pod follows and keeps the other sessions already claimed; nothing refuses or warns when a second operation session runs.
- MON-14: **Unreviewed** The check-in dependency map is grouped by repo first: one block per repo headed by the repo's name, goals and dependencies inside, cross-repo dependencies drawn between blocks
  - Each repo prints as `== name ==` within 60 characters, then a `Between repos` list for `repo/slug` dependencies, then the legend once.
```

Do not edit MON-5 or any Reviewed line. Seal (words copied exactly from the goal file, the two owner quotes joined):

```
LOOP_OWNER_WORDS="Add when the operation that I should only get one operation session for the entire pod. So it can manage. There's no operation plus operation session in the monitoring and the worker session. They're just two layers. And also for the printout ... It should show by groups first group by the reponents. you should expect it that I have multiple monitoring sessions ... they don't need to know each other. It's just like they can do their own stuff concurrently." \
  python3 skills/workflow-docs/scripts/criteria.py review MON-13 MON-14 --user
```

(The `...` marks the goal file's own elisions; no word is added. If `criteria.py` insists on one verbatim span, run `review`
twice: MON-13 with the first and last quote, MON-14 with "It should show by groups first group by the reponents.".)
Wording is frozen once sealed; a later edit needs `unreview`.

### 7. Regression rows (after the tests pass and the wiki is sealed)

`python3 skills/workflow-regression/scripts/regression.py add ID --level land --command C --goal G --describe D --category criterion`:

| ID | command (`T`=`bash dev/toy/test-pod-layers.sh`) | goal | describe |
|---|---|---|---|
| `pod-layers-docs` | `T docs 2>&1 \| tail -1 \| grep -qx "ALL PASS"` | `pod-layers:1` | Given the Monitoring PRD, when MON-13 and MON-14 are read, then both are Reviewed with a valid seal. |
| `pod-layers-independent` | same with `layers` | `pod-layers:2` | Given two independent operation sessions, when both claim, then neither is refused or warned and both stay governed. |
| `pod-layers-blocks` | same with `blocks` | `pod-layers:3` | Given three repos, when the check-in prints, then each repo is a `== name ==` block within 60 columns. |
| `pod-layers-size` | same with `size` | `pod-layers:4` | Given the package, when sizes are counted, then no script crosses 18 KB and the package has 99 files or fewer. |
| `mon13-two-layers` | same with `layers` | `MON-13` | Given a claim from a second session, when it claims, then the first session is still an operation session. |
| `mon14-repo-blocks` | same with `blocks` | `MON-14` | Given a cross-repo dependency, when the check-in prints, then it lists it between headed repo blocks. |

Each row must be SEEN FAILING. `regression.py red` copies HEAD, so run it only once the change is committed by the
pipeline. Break commands (each tested to fail the case, with the new test file present in HEAD):
- layers / mon13: `--break "sed -i.bak 's/open(path, \"a\")/open(path, \"w\")/' skills/workflow-monitoring/scripts/operate.py"` (adapt to the exact source line once written: the break reverts append to overwrite).
- blocks / mon14: `--break "sed -i.bak 's/\"== %s ==\"/\"%s\"/' skills/workflow-monitoring/scripts/checkin.py"`.
- size: `--break "python3 -c \"open('skills/workflow-monitoring/scripts/checkin.py','a').write('#'*19000+'\\n')\""`.
- docs: `--break "sed -i.bak 's/^- MON-13: \\*\\*Reviewed/- MON-13: **Unreviewed/' docs/wiki/Monitoring.md"`.

Before commit, also prove red now without stash: `mkdir -p $TMP/base && git archive HEAD skills | tar -x -C $TMP/base`, then
`POD_SCRIPTS=$TMP/base/skills/workflow-monitoring/scripts bash dev/toy/test-pod-layers.sh layers` must FAIL (second claim
overwrites the first) and `... blocks` must FAIL (no headers); the same on the new scripts prints `ALL PASS`. Record both in
the goal notes.

Then `python3 skills/workflow-docs/scripts/criteria.py render` (never hand-edit the Monitoring Tests table or
`docs/wiki/Tests.md`), then `criteria.py render --check` reports nothing stale.

### 8. Final checks

1. `wc -c` on the three scripts under 18 KB; no other script grew past it.
2. Package file count on a clean `git archive` at most 99 (this change adds only `dev/toy/test-pod-layers.sh`, outside the package list).
3. `docs.py check`, `criteria.py render --check`, `regression.py check` (no UNPROVEN).
4. The full lane exactly as CI runs it (`cat .github/workflows/regression.yml`).

## Verify by hand (add to the goal file's section)

1. In one repo, start two sessions and run `python3 skills/workflow-monitoring/scripts/operate.py claim --id one` then `... --id two`. Expect: both print `CLAIMED operation session` with no REFUSED, WARN or `replaced`; `cat .git/loop/operation.id` lists `one` and `two`.
2. Run `python3 skills/workflow-monitoring/scripts/checkin.py` with two followed repos in `~/.workflow-loop/repos`. Expect: one `== name ==` block per repo, no line over 60 characters, a `Between repos` list for a `repo/slug` dependency, the legend once.
3. Empty `~/.workflow-loop/repos` and run it again. Expect: one `== name ==` block, no `Between repos`.

## Risks and accepted limits

- `watch.py` holds `repo/slug` goals as unknown, so such a goal waits; the check-in shows the edge with the target's mark.
- Four scripts were over 18 KB before this goal (finding 9); the size case forbids growth, not their existence.
- `operation.id` is never pruned.

## FINAL SPEC (wins over earlier text, including the design)

- `operate.py claim` and `govern_hook.claim` ADD the id to `operation.id` and keep the others; no `replaced` text, no refusal, no warning, no pod record, no `--replace`. A worker is refused as before. `operate.py claim` also adds the id to every `board.followed()` repo.
- Check-in Dependencies: per repo, own repo first then the repos file order, `== <name> ==` (cut to 51 chars plus `...` above 54), the `board_lines` graph without legend, `- (none)` when empty; then, only when edges exist, `Between repos` lines `<repo>/<slug> <- <repo>/<slug> [<mark>]` or `(unknown)`; then a blank line and the legend once; every line at most 60 columns (textwrap, 4-space continuation); an unreadable followed repo never stops the check-in. `graph.ready` is called as today.
- Code only in `operate.py`, `govern_hook.py`, `checkin.py`; no new skill file; size rule per finding 9; package at most 99 files.
- Tests: `dev/toy/test-pod-layers.sh` with cases layers, blocks, size, docs; invented repo names only; `test-monitoring-prd.sh` updated.
- Six regression rows (`pod-layers-docs`, `pod-layers-independent`, `pod-layers-blocks`, `pod-layers-size`, `mon13-two-layers`, `mon14-repo-blocks`), each seen failing first.
- MON-13 and MON-14 use the goal file's first-done-line wording exactly, are added Unreviewed, then sealed with `criteria.py review MON-13 MON-14 --user` and `LOOP_OWNER_WORDS` set to the owner's quotes; no other Reviewed line is edited.
