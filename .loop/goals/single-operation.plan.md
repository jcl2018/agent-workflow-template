# Plan: single-operation

Done lines (frozen) are in `.loop/goals/single-operation.md`; the design is `single-operation.design.md`. This plan is the
engineering review of that design against the real code, as an ordered build. I ran the review myself (autoplan was not
invoked; no outside voice ran). Where this plan and the design differ, the FINAL SPEC at the end wins.

## Review findings (what the code showed)

1. `operate.cmd_claim` writes only `<common>/loop/operation.id`; `govern_hook` and `reply_hook.claimed(common)` read that
   per repo. So a pod claim must also write `operation.id` into every followed repo, or the session governs only one repo
   by hook while MON-13 says it governs all. The design missed this.
2. `cmd_run` calls `cmd_claim(argparse.Namespace(id=""))`; the new `--replace` flag must be read with `getattr(args, "replace", False)`.
3. `graph.parse` splits `depends` on commas and whitespace, so a `repo/slug` token survives parsing. `graph.unmet` then reports
   it as `unknown goal`, so `watch.py` holds such a goal forever. That is safe (never starts early) and it is out of scope
   to change the start gate. The design's step "rewrite resolved cross-repo deps before graph.ready" is DROPPED: it would make
   the check-in say ready while watch holds. The check-in keeps calling `graph.ready` exactly as today.
4. `board_lines.render` filters `depends` to known slugs, so a cross-repo dep never draws today. Its output ends with
   `["", LEGEND]`; `grouped` strips those two lines per block and prints the legend once.
5. `board_lines.pack` lets a single long piece exceed the width, and `lb.fit(out, 100)` only wraps at 100. So `grouped`
   must wrap every line it emits at 60 itself (textwrap), or a long slug breaks the 60-column rule.
6. The reply hook finds sections by exact heading text (`heading()` strips `*#\`_`, a trailing colon and a count). A line
   `== alpha-app ==` or `Between repos` never equals Dependencies / Needs you / Coming up / All sessions /, so the hook's layout
   check still passes. The test must prove it (checkin-passes-hook already does; extend it to the three-repo output).
7. `criteria_max` is 15 in `.loop/config.json`; Monitoring has 12 requirements, so MON-13 and MON-14 make 14. Fine.
8. Other repos' state must come from that repo's own `.loop` (its config, its pool), via `lb.load(path)`, `lb.loop_dir(path)`.
   Needs you keeps the own repo's full detail; for other repos it adds only waiting questions (the owner would otherwise
   never see them, which defeats one operation session for the pod).
9. Existing toy tests may claim with different session ids in one repo or assert the old flat Dependencies. Before editing,
   run `grep -n "operate.py claim\|CLAUDE_SESSION_ID\|<- " dev/toy/*.sh` and fix each hit (see step 7).

## Ordered build

### 1. `skills/workflow-monitoring/scripts/operate.py` (8.5 KB, grows about 1.5 KB)

- Add `import board` is NOT used (board.py imports graph and is 17.7 KB; importing is fine, it adds no size). Use
  `board.followed()`; import lazily inside the new functions: `import board as bd`.
- `def pod_file()`: `os.path.join(os.path.expanduser("~"), ".workflow-loop", "operation.json")`.
- `def pod_record()`: read the JSON; return a dict with `session`, `repo`, `common` strings, else `{}` (missing, corrupt,
  not an object, or missing keys all mean no record; never raise).
- `def governed(common, record)`: True when `record.get("common")` equals `common`, or `common` is among the common dirs
  of `bd.followed()` AND the record's own common dir is among them too (the recorded repo and this repo are both in the
  pod). Compare git common dirs (realpath), never names or path strings.
- In `cmd_claim`, after the worker check and the no-session-id check:
  - `record = pod_record()`; `replace = getattr(args, "replace", False)`.
  - If `record.get("session") and record["session"] != sid and governed(common, record) and not replace`:
    `sys.exit("REFUSED: operation session %s already governs the pod (repo %s). Fix: work from that session, or claim with --replace to take over." % (record["session"], record["repo"]))`.
    It names the session and the repo by name, never a path.
  - Same session id: success, no refusal (idempotent).
  - Write the record `{"session": sid, "repo": basename(main), "common": common}` (create `~/.workflow-loop`, write to a temp
    file and `os.replace`). Then write `operation.id` into this repo and into every `bd.followed()` repo's `<common>/loop/`
    (makedirs; skip any that fail to write). A repo outside the pod claims normally and the record is rewritten to it.
  - Print `CLAIMED operation session <sid>` plus ` (replaced <old>)` when the old record's session differs.
- `claim` parser: add `--replace` (store_true). `cmd_run` is unchanged (it reaches the same refusal through `cmd_claim`; the
  `SystemExit` message ends the run).
- Update the module docstring's `claim` paragraph: one pod record, refusal, `--replace`.

### 2. `skills/workflow-monitoring/scripts/checkin.py` (8.6 KB, grows about 3 KB)

- `def gather(path, at)`: returns a dict for one repo: `name` (basename of main), `root`, `cfg`, `folder`, `runs`, `found`,
  `why`, `taken`, `states`, `live`, `queue`. This is the existing top of `render` moved without change of logic (so the own
  repo's output is identical). Wrap calls for OTHER repos in `try/except Exception` and record `(name, reason)`.
- `render(root=None, at=None, stamp=None)`: `pod = [(name, main, base) for ... in bs/board followed()]` (own repo first).
  Gather the own repo without a guard (as today); gather the rest guarded. The signature and the own-repo defaults stay,
  so `checkin.render()` callers and tests keep working.
- Headline counts: sum over every gathered repo (`counts` over all `live`); `len(queue)` summed; the pool line stays the
  own repo's.
- All sessions: one row per live run of every repo, own repo first, the repo column is that repo's name (it already
  uses `os.path.basename(root)`; make it `g["name"]`). Empty pod: the existing `nothing running` row with the own name.
- Dependencies: `out += ["", "Dependencies"] + grouped(blocks, edges)` where `blocks = [(name, items)]` per gathered repo
  (items built exactly as today per repo) .
- Needs you: unchanged for the own repo; for each other repo add `"<repo>/<slug> asks: ..."` for runs in state `waiting`,
  and `"<repo>: can't be read (<reason>); the other repos are shown"` for each guarded failure.
- New `def grouped(blocks)` (about 40 lines):
  1. For each `(name, items)`: header `"== %s ==" % shown`, where `shown = name if len(name) <= 54 else name[:51] + "..."`.
     Body: `lines = board_lines.render(local)` where `local` are the items with every `repo/slug` dependency removed from
     `depends`, then drop the trailing `["", LEGEND]` (`lines[:-2]` when `items` is non-empty; an empty repo body is
     `["- (none)"]`, which `board_lines.render` already returns without a legend).
  2. Edges: for each item and each dep containing `/`: `edge = (name, slug, repo, dep_slug)`. Target mark: look up
     `repo` among the gathered blocks, then `dep_slug` among its items; found gives the item's mark, otherwise `(unknown)`.
  3. After all blocks, if any edge: `"Between repos"`, then per edge `"%s/%s <- %s/%s [%s]"` using the target's
     `board_lines.MARKS` symbol, or `(unknown)` in place of `[x]` for an unknown repo or slug. Never dropped.
  4. Legend once, last: `"", board_lines.LEGEND`.
  5. Every emitted line passes through `textwrap.wrap(line, 60, subsequent_indent="    ", break_long_words=True)`
     (an empty line stays empty; a line at most 60 wide is untouched). The result is at most 60 columns throughout.
  6. A single-repo pod still prints its one `== name ==` block (consistent, simplest).
- `LEGEND` is the `board_lines.LEGEND` string, not a copy. Update the module docstring's Dependencies line.

No change to `board_lines.py` (16.8 KB), `board.py` (17.7 KB), `live_board.py` (18.6 KB, already over; do not touch),
`graph.py`, `board_status.py`.

### 3. Fixture and test: `dev/toy/test-single-operation.sh`

Header lines `# reads:` for operate.py, checkin.py, board.py, board_lines.py, graph.py, live_board.py, reply_hook.py
(the repo's toy tests all declare reads). Invented repo names only: `alpha-app`, `beta-svc`, `gamma-lib`. Cases, run as
`bash dev/toy/test-single-operation.sh [refuse|blocks|size|docs]` (default all), last line `ALL PASS` or `N FAILED`.
`SCRIPTS=${POD_SCRIPTS:-$here/skills/workflow-monitoring/scripts}` so the same test can run against the pre-change scripts.
Temp `HOME`; unset `CLAUDE_SESSION_ID LOOP_ROLE LOOP_OPERATION_SESSION LOOP_SESSION_TOOL`. Build repos with `git init -q`
plus an initial commit in `$T/alpha-app`, `$T/beta-svc`, `$T/gamma-lib`; `printf '%s\n' "$T/beta-svc" "$T/gamma-lib" > $HOME/.workflow-loop/repos`
(own repo is alpha-app).

Case `refuse` (done line 2):
- s1 claims in alpha-app: exit 0, prints `CLAIMED operation session s1`.
- s2 claims in beta-svc: exit non-zero; message contains `REFUSED`, `s1`, `alpha-app`, `--replace`; contains no `$T`.
- s1 claims again from beta-svc: exit 0 (no replaced note).
- s2 `--replace`: exit 0, message has `(replaced s1)`; `operation.json` shows `s2`; `operation.id` of alpha-app, beta-svc and gamma-lib all read `s2`.
- `LOOP_ROLE=worker` claim: refused with the old worker line (the worker check is first, before the pod check).
- A fourth repo `delta-tool` (not in the repos file, not recorded) with session s3: claims, record becomes s3.
- Corrupt `operation.json` (`printf 'not json'`): a claim from a new session succeeds.
- `CLAUDE_SESSION_ID=s9 operate.py run --once` in a repo governed by another session: exit non-zero, same REFUSED line.

Case `blocks` (done line 3, MON-14): give each repo `.loop/runs/*.json` run records and `.loop/queue.md` as in
`test-monitoring-prd.sh`'s `run()`/`fresh()` helpers (copy those helpers; this test needs them, do not source the other file).
- alpha-app: runs `core` (running) and queued `docs` depends on `core`. beta-svc: queued `api` depends-on `alpha-app/core`,
  and queued `edge` depends-on `omega-none/x` (a repo not in the pod). gamma-lib: nothing live or queued.
- Run `python3 $SCRIPTS/checkin.py` from alpha-app. Assertions on the `Dependencies` to `Needs you` slice:
  - `== alpha-app ==`, `== beta-svc ==`, `== gamma-lib ==` each appear exactly once, in that order.
  - `core` and `docs` lines sit after alpha-app's header and before beta-svc's; `api` and `edge` between beta-svc's and gamma-lib's.
  - gamma-lib's block is `- (none)`.
  - `Between repos` appears once, after the blocks, with `beta-svc/api <- alpha-app/core [>]` and `beta-svc/edge <- omega-none/x (unknown)`.
  - The legend line occurs exactly once in the whole output, last in the Dependencies slice.
  - `awk 'length > 60'` over the Dependencies slice prints nothing, including with a 70-character repo name (extra
    case: a repo directory `a-very-long-repository-name-that-keeps-going-past-sixty-chars-x`, header ends in `...`)
    and 50-character slugs.
  - All sessions table: row for `core` has `alpha-app` in the repo column; counts in the first line include beta-svc's queued goals (3 queued in total).
  - Single-repo pod (empty repos file): one `== alpha-app ==` block, no `Between repos`.
  - A followed repo whose `.loop/runs` holds a corrupt file: check-in still prints, with one Needs you line, no traceback.
  - `python3 $SCRIPTS/reply_hook.py check` (or the module's `problems()`; use whatever `checkin-passes-hook` in
    `test-reply-hook.sh` uses) accepts the three-repo output: no missing section.

Case `size` (done line 4): `for f in skills/*/scripts/*.py: wc -c < f` each under 18432 (18 KB). Note: `live_board.py` is
already 18,576 bytes; if the repo's own size rule treats it as pre-existing, the case must assert the same rule the repo uses
(read health's Size rule and `dev/toy/test-live-board.sh` size check, copy their threshold and exemption exactly) and
additionally assert `operate.py` and `checkin.py` each under 18000. File count: `git archive HEAD` of a clean checkout
(`git stash`-free: use a temp `git worktree`/`git archive HEAD | tar -t | grep -v '/$' | wc -l`) is at most 99 for the package
paths the repo counts as the package (`test-deployments.sh` line 19 lists them: skills docs .loop README.md CLAUDE.md AGENTS.md
VERSION listing.json CHANGELOG.md LICENSE); this change adds no skill file, one toy test under `dev/` (not in that list).

Case `docs` (done line 1): `grep -E '^- MON-13: \*\*Reviewed [0-9-]+\*\*' docs/wiki/Monitoring.md`, same for MON-14, each with
`<!-- reviewed [0-9a-f]{8} -->`; `python3 skills/workflow-docs/scripts/docs.py check` exits 0 (seals valid);
the owner's quote appears in the last line of `.git/loop/reviews.tsv` logged by criteria.py (skip that part when the
file is absent in CI; the check is the seal).

### 4. Wiki text (final before sealing)

In `docs/wiki/Monitoring.md`, after MON-12's sub-bullets and before `### Non-functional`, add exactly:

```
- MON-13: **Unreviewed** One operation session for the whole pod: it governs every registered repo directly and talks to each worker; there are only two layers, operation and workers; no repo gets its own operation session
  - Starting a second operation session for a repo the pod already governs is refused with a line naming the existing operation session and its repo; `operate.py claim --replace` takes over.
- MON-14: **Unreviewed** The check-in dependency map is grouped by repo first: one block per repo, headed by the repo's name, goals and their dependencies inside it, cross-repo dependencies drawn between blocks
  - The check-in prints each repo as `== name ==`, within 60 characters, the legend once, and a `Between repos` list of cross-repo dependencies; `repo/slug` in `depends-on` names a goal in another repo.
```

Also update MON-5's bullet "Dependencies" only if it names the flat graph (check with `grep -n "Dependencies" docs/wiki/Monitoring.md`;
MON-5 is Reviewed, so editing it needs `criteria.py unreview` with the owner's words and a re-review; do not edit it; MON-14
covers the grouping). Then seal:

```
LOOP_OWNER_WORDS="Add when the operation that I should only get one operation session for the entire pod. So it can manage. There's no operation plus operation session in the monitoring and the worker session. They're just two layers. And also for the printout, when operation session should print out all the should show the dependency map. It should show by groups first group by the reponents. Right now it's not showing the reponents very cleanly." \
  python3 skills/workflow-docs/scripts/criteria.py review MON-13 MON-14 --user
```

(The words are the owner's quote from the goal file, copied exactly, not paraphrased.) Wording is frozen once sealed; any
edit afterwards needs `unreview`.

### 5. Regression rows (after the tests pass and the wiki is sealed)

Add with `python3 skills/workflow-regression/scripts/regression.py add ID --level land --command C --goal G --describe D --category criterion`:

| ID | command | goal | describe |
|---|---|---|---|
| `single-operation-docs` | `bash dev/toy/test-single-operation.sh docs 2>&1 \| tail -1 \| grep -qx "ALL PASS"` | `single-operation:1` | Given the Monitoring PRD, when MON-13 and MON-14 are read, then both are Reviewed with a valid seal. |
| `single-operation-refuse` | same with `refuse` | `single-operation:2` | Given a pod whose operation session is s1, when a second session claims for a repo the pod governs, then it is refused with a line naming s1 and the repo, and `--replace` takes over. |
| `single-operation-blocks` | same with `blocks` | `single-operation:3` | Given three repos, when the check-in prints, then the dependency map is one `== name ==` block per repo, within 60 columns, cross-repo edges between blocks. |
| `single-operation-size` | same with `size` | `single-operation:4` | Given the package, when sizes are counted, then every script is under 18 KB and the package has 99 files or fewer. |
| `mon13-one-operation` | same with `refuse` | `MON-13` | Given one operation session in a pod, when another claims for a governed repo, then it is refused; the claim writes the govern record in every pod repo. |
| `mon14-repo-blocks` | same with `blocks` | `MON-14` | Given three repos with a cross-repo dependency, when the check-in prints, then each repo is a headed block and the edge is listed between blocks. |

Each row must be SEEN FAILING (`red`). Run after the change is committed by the pipeline (red copies HEAD); the break commands:

- refuse and mon13: `regression.py red single-operation-refuse --break "sed -i.bak 's/and governed(/and False and governed(/' skills/workflow-monitoring/scripts/operate.py"`
- blocks and mon14: `--break "sed -i.bak 's/\"== %s ==\"/\"%s\"/' skills/workflow-monitoring/scripts/checkin.py"`
- size: `--break "python3 -c \"open('skills/workflow-monitoring/scripts/operate.py','a').write('#'*19000+'\\n')\""`
- docs: `--break "sed -i.bak 's/^- MON-13: \\*\\*Reviewed/- MON-13: **Unreviewed/' docs/wiki/Monitoring.md"`

If the pipeline cannot run `red` before commit, also prove the failure before the fix now, without stash: extract the base
scripts and run the new test against them:

```
mkdir -p $TMP/base && git archive HEAD skills/workflow-monitoring | tar -x -C $TMP/base
POD_SCRIPTS=$TMP/base/skills/workflow-monitoring/scripts bash dev/toy/test-single-operation.sh refuse   # expect FAIL (2nd claim succeeds)
POD_SCRIPTS=$TMP/base/skills/workflow-monitoring/scripts bash dev/toy/test-single-operation.sh blocks   # expect FAIL (no headers)
```

(HEAD before the change is `da490a7`; do this before committing the code, so base is the unchanged tree.) Then the same
commands against the new scripts must print `ALL PASS`. Record both outputs in the goal notes.

Then `python3 skills/workflow-docs/scripts/criteria.py render` writes the Monitoring Tests table and `docs/wiki/Tests.md`
(never hand-edit those files); `criteria.py render --check` then reports nothing stale.

### 6. Update existing tests

Run each, fix only assertions the new layout changes, and keep intent:
`bash dev/toy/test-operate.sh`, `test-monitoring-prd.sh`, `test-reply-hook.sh`, `test-operate-fit.sh`, `test-operate-fit-3.sh`,
`test-live-board.sh`, `test-session-workers.sh`, `test-govern.sh`, `test-lanes.sh`. Expect: the check-in's Dependencies now has a
`== name ==` line first and no legend duplicate; any test claiming from a second session in the same repo gets
`--replace` or a fresh `HOME`. The board and live_board layouts are unchanged (only the check-in changed), so board tests
should not move.

### 7. Final checks

1. `for f in skills/*/scripts/*.py; do wc -c < $f; done` shows `operate.py` and `checkin.py` under 18 KB (expected about 10 KB and 11.5 KB).
2. Package file count with a clean `git archive HEAD | tar -t | grep -v '/$' | wc -l` stays at or under 99.
3. `python3 skills/workflow-docs/scripts/docs.py check`, `criteria.py render --check`, `regression.py check` (UNPROVEN none).
4. Full lane through the repo's normal command (`/CJ`-free: `bash dev/toy/make.sh` wrappers as CI uses; find with `cat .github/workflows/regression.yml`).
5. Print a real check-in with the repos file emptied (single block) as the by-hand step.

### Verify by hand (add to the goal file)

1. In two registered repos, claim from one session, then claim from a second. Expect: a REFUSED line naming the first session and the repo's name; `--replace` then takes over.
2. Run the check-in with two followed repos. Expect: one `== name ==` block per repo, no line over 60 characters, a cross-repo dependency listed under `Between repos`, the legend once.

## Risks and accepted limits

- A dead operation session leaves a stale record; the owner passes `--replace` (the message says so). No liveness check.
- `watch.py` still treats `repo/slug` as an unknown goal, so such a goal waits until the owner removes or changes the dependency; the
  check-in shows it as an edge with the target's real mark. Cross-repo gating in watch is a follow-up, not this goal.
- A followed repo that is slow is still read serially; the guarded gather prevents a crash, not latency.
- `live_board.py` (18,576 bytes) already exceeds 18 KB; done line 4 concerns scripts this change touches. If the repo's own size
  rule flags it independently, that is a pre-existing defect and is not made worse (this change does not edit it).
- Sealing: wording of MON-13/14 is final before `review`.

## FINAL SPEC (wins over earlier text, including the design)

- One pod record `~/.workflow-loop/operation.json` = `{"session","repo","common"}`; `operate.py claim` writes it and `operation.id` in every followed repo.
- Refusal text, exact: `REFUSED: operation session <id> already governs the pod (repo <name>). Fix: work from that session, or claim with --replace to take over.` A worker is refused first with the existing worker line. Same session re-claim succeeds. Corrupt record means no record. A repo outside the pod claims and replaces the record. `--replace` prints `(replaced <old>)`.
- Check-in Dependencies: per repo, in order (own repo first, then the repos file), `== <name> ==` (name cut to 51 chars plus `...` above 54), the board_lines graph without its legend, `- (none)` for an empty repo; then, only when edges exist, `Between repos` with lines `<repo>/<slug> <- <repo>/<slug> [<mark>]` (or `(unknown)`); then one blank line and the legend once. Every line at most 60 columns, wrapped by textwrap with a 4-space continuation.
- Cross-repo dependency syntax is `repo/slug` in `depends-on`; edges appear only in Between repos (no inline re-attach to the node). `graph.ready` is called as today, with no rewrite.
- All sessions lists every repo's live goals with the repo name; headline counts cover the pod; Needs you adds other repos' waiting questions prefixed `repo/slug` and one line per unreadable repo.
- No new skill files; code goes only in `operate.py` and `checkin.py`; each stays under 18 KB; package at most 99 files.
- Tests use only `alpha-app`, `beta-svc`, `gamma-lib`, `delta-tool`, `omega-none` as repo names.
- Six regression rows (docs, refuse, blocks, size, mon13, mon14), each keyed to a done line or MON id and recorded as seen failing before it counts.
- MON-13 and MON-14 are sealed Reviewed with the owner's quote through `LOOP_OWNER_WORDS`; no other Reviewed line is edited.
