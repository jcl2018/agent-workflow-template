# Plan: pods

Done lines (frozen, six): `.loop/goals/pods.md`; design: `pods.design.md`. Autoplan ran inline, no outside voice. Where text differs, the FINAL SPEC wins. Read-only references (scratchpad `.../scratchpad/pl/`, call it PL):
`pod-layers.patch` (`git apply --check` passes here: operate.py, govern_hook.py, checkin.py, test-monitoring-prd.sh),
`pod-layers.plan.md`, `test-pod-layers.sh`. The `single-operation` refusal is dropped.

## What the code showed

1. Run record `<common>/loop/runs/<slug>.json`: `goal.save` rewrites the loaded dict, so a `pod` key survives a worker's saves; `fit.view` only merges
   the sidecar, and `pod` never changes, so it stays in the record. `sessions.held(slug)` is the load for `assign`, `send`, `report`; `session_bind.cmd_bind`
   loads via `g.load`; `goal.cmd_resume` wraps `guards.cmd_resume` (guards untouched); `mend.runs()` feeds `mend.one_pass`; `auto.decide_all` walks `runs/*.json`.
2. `merge.py` main: loads `state`, then calls `gh pr view`; the lock goes between. The release-PR path runs in the same process, so one lock covers it.
3. Sizes now: graph 14,022, goal 19,357, sessions 19,585, watch 19,578, merge 19,985, mend 13,171, auto 9,757, session_bind 9,041, operate 8,475
   (9,129 patched), checkin 8,647 (11,743 patched), board_lines 16,794. Prototype: graph 17,367, goal 19,692, merge 20,397 untrimmed (83 under: trim its docstring, step 3).
4. `docs/wiki/Release.md` does not exist; `.loop/docs.tsv` maps `skills/workflow-release` to **Delivery.md** (its line 18 describes
   `merge.py`). That page goes stale on the edit, so it is updated (a true line only). Touches names Release.md: after the
   build the operation runs `goal.py touches pods --add docs/wiki/Delivery.md` (operation only), no done line changes.
5. `criteria_max` is 15 and Monitoring has 12 requirements; adding MON-13/14/15 makes exactly 15.

## Ordered build

### 1. MON-13 and MON-14 (reuse)

`git apply PL/pod-layers.patch`. It makes `operate.claim` / `govern_hook.claim` add the id and keep the others, and rewrites `checkin.py` into per-repo `== name ==` blocks (`gather`, `grouped`, `Between repos`, the
legend once, every line <= 60, an unreadable followed repo is one Needs you line). Then in `operate.py` only:
- `cmd_claim` also prints `POD <sid>: set LOOP_POD_ID=<sid> to keep this pod if the session restarts` (no REFUSED/WARN/already/replaced text).
- `cmd_run`, before the loop: `pod = graph.pod_id() or os.environ.get("CLAUDE_SESSION_ID", ""); pod and os.environ.setdefault("LOOP_POD_ID", pod)`
  (watch, auto, merge, send inherit it; a Codex session sets `LOOP_POD_ID` itself).
- `cmd_send`, first line: `graph.refuse(graph.load_run(args.slug))` (helper below), so a foreign send writes no `answers.jsonl`.
- Docstring: `claim` paragraph per the patch plus one sentence: goals record their pod; only it acts on them.
Fix `test-monitoring-prd.sh` ~lines 121-124 per PL plan section 5.

### 2. `graph.py`: the one shared module (target <= 17,400 bytes, test cap 18,432)

Add `import atexit, sys, time` and append six functions (prototype tested at `.../scratchpad/pods/podcode.py`; graph.py 17,367):
`pod_id()` (the FINAL SPEC rule, id cleaned to `[A-Za-z0-9_.-]`, 64 chars), `stamp(state)` (set `pod` when absent and a pod id exists),
`foreign(state)` (owner when set, caller not a worker, owner != `pod_id()`, else ""), `refuse(state)` (the one stderr line below, `sys.exit(2)`),
`load_run(slug)` (the record from `git rev-parse --git-common-dir`, `{}` if missing or bad slug) and `merge_lock(common)`:

- loop: `os.open(<common>/loop/merge.lock, O_CREAT|O_EXCL|O_WRONLY)`, write the pid, `atexit.register(release)` (unlink only if the file still holds our pid);
- on `FileExistsError`: `age` from the file's mtime (init `age = 0`), pid from its text, `os.kill(pid, 0)`; `ProcessLookupError` means dead, `FileNotFoundError`
  means retry, any other error (a half-written file) leaves the age rule to decide;
- dead, or age > `int(LOOP_MERGE_LOCK_SECONDS or 1800)`: `os.rename(path, path + ".stale.<pid>")` then unlink it (one atomic rename, so of two waiters only one
  clears it), retry; otherwise print once `WAITING: another pod is merging into this repo (pid N); one merge at a time.` and sleep 0.2 s.

The prototype ran two concurrent holders without overlap and replaced a dead pid and an old file at once.

### 3. The enforcement edits (each a few lines; measured growth in brackets)

| File (bytes now) | Edit | Budget / cap |
|---|---|---|
| `workflow-monitoring/scripts/watch.py` (19,578) | `freeze`: after the `state = {...}` dict, `graph.stamp(state)`; `cmd_resume`: `graph.refuse(load(args.slug) or {})` first line | +90 -> <= 19,700 |
| `.../mend.py` (13,171) | `runs()` returns only `not graph.foreign(s)` records (mend never touches another pod's goal); `resume()`: `graph.refuse(state)` after the load; `import graph` via `sys.path` if mend lacks it | +150 |
| `.../auto.py` (9,757) | in `decide_all`, `continue` when `graph.foreign(run)` (a pod never auto-answers another pod's question) | +60 |
| `.../sessions.py` (19,585) | `held()`: `graph.refuse(state)` before `return state`; `assign()`: `graph.stamp(state)` before it saves | +110 -> <= 19,750 (graph already imported) |
| `.../session_bind.py` (9,041) | `cmd_bind`: after `tree = ...g.load(...)`, `g.graph.refuse(g.load(args.slug) or {})` (sessions exports graph) | +60 |
| `workflow-delivery/scripts/goal.py` (19,357) | the optional import block (`sys.path.append(<monitoring scripts>)`, `try: import graph as pods`, `except ImportError: pods = None`, 5 lines, after the `import role` line); `cmd_new`: `pods and pods.stamp(state)` after `guards.stamp(state, "idea")`; `cmd_resume`: `pods and pods.refuse(load(args.slug))` first line | measured 19,692; cap 19,800 |
| `workflow-release/scripts/merge.py` (19,985) | the same 5-line import after `import wiki`; after the `state` load and before `gh pr view`: `if pods:` / `pods.refuse(state)` / `pods.merge_lock(os.path.abspath(common))  # one merge per repo at a time, across pods` | measured 20,397 untrimmed; trim the module docstring by >= 500 bytes (drop the release-PR paragraph's repeated detail, keep every fact once, add one sentence: "Takes <common>/loop/merge.lock for the whole step"), final <= 19,985 |

The cross-skill import is safe: `sys.path.append` puts monitoring's folder last, so the script's own folder and the stdlib win every name; without workflow-monitoring `pods` is None and every call is guarded.

### 4. Marks (done line 2, "owned by <pod>")

- `board_lines.box`: `"[%s] %s%s%s" % (mark, slug, " owned by " + node["owner"] if node.get("owner") else "", cycle)` (+80 bytes; 16,794 -> <= 17,000).
- `board_status.board_items.item`: add `owner=graph.foreign(run)` for live runs (import graph if absent).
- `checkin.py` (patched version): items get `owner=graph.foreign(r)`; a foreign `waiting` goal is listed under Needs you as
  `- <slug> asks (owned by <pod>, read-only here)` and never as a numbered question; All sessions rows add nothing. Target <= 12,300.

### 5. Tests: `dev/toy/test-pods.sh` (copy PL/test-pod-layers.sh, rename, extend)

Header `# reads:` lists every script and wiki page it exercises. `SK=${POD_SKILLS:-$here/skills}` replaces `POD_SCRIPTS` so one variable points all three skills at another
copy (red proof). Usage `bash dev/toy/test-pods.sh [layers|blocks|owner|lock|twopods|size|docs]`, default all, last line
`ALL PASS` or `N FAILED`. Repo names only alpha-app, beta-svc, gamma-lib, delta-tool, omega-none; pod ids only pod-a, pod-b. Temp
HOME, `GIT_CONFIG_GLOBAL` empty, unset `LOOP_*` and `CLAUDE_SESSION_ID` first (as PL). Helper `own REPO SLUG POD STATUS` writes a
run record with `pod` (omit POD: none); `fp FILE` = md5 of a record.

- `layers` (MON-13, done line 4): PL's layers case verbatim (add, keep, followed repos, separate HOME pod, hook view, worker refused).
- `blocks` (MON-14, done line 5): PL's blocks case verbatim (three-repo fixture, headers once and in order, `Between repos`, legend
  once, `awk 'length > 60'` empty, 70-char dir, unreadable repo, reply_hook accepts), plus one extra: a `pod-a` goal seen from pod-b shows
  `core owned by pod-a` inside alpha-app's block and still within 60 columns.
- `owner` (done line 2, MON-15). alpha-app with `core` owned by pod-a (failed, with `session`/`worker` where a command needs them), `api` owned
  by pod-b, `plain` with no pod. As pod-b on `core`: `sessions.py send|assign|bind`, `goal.py resume`, `watch.py resume`, `operate.py send`, `merge.py`
  (auto_merge true, done, pr set). Each: exit 2, stderr exactly the one FINAL SPEC line naming pod-a, record md5 and `tries` unchanged, no
  `answers.jsonl`, no `merge.lock` left. As pod-a (`LOOP_POD_ID=pod-a`) no `owned by` text. `plain` is not refused for pod-b; a worker's `sessions.py
  report` never is. `auto.py pass --dry-run` (waiting `core`, full_auto on): pod-b prints no WOULD for it, pod-a does. Stamping: `watch.freeze` through
  python import records `pod-a` for pod-a, none for a pod-less caller; `graph.stamp` keeps an existing pod. Marks: `checkin.py` and `board.py board` as
  pod-b show `core owned by pod-a` (not `api`), none as pod-a; a foreign waiting question is not numbered under Needs you. Optional import: `goal.py`
  and `merge.py` copied beside no workflow-monitoring import cleanly with `pods is None`.
- `lock` (done line 3, MON-15): (a) two processes call `graph.merge_lock` around a 1.2 s sleep and log in/out times: windows do not overlap, the second
  prints one WAITING; (b) a live fresh lock blocks a third (`timeout 1.5` exits 124), which enters once the holder ends; (c) a dead-pid lock is replaced
  at once; (d) a live pid with a file older than `LOOP_MERGE_LOCK_SECONDS=1` is replaced; (e) the file is gone after normal exit, `sys.exit(1)` and an
  uncaught exception; (f) two concurrent `merge.py core` runs (auto_merge, done record with a pr) with a `gh` shim first on PATH that logs enter/leave
  around a 2 s sleep, then runs `dev/toy/fakegh/gh`: the two `gh pr view` windows do not overlap; (g) a foreign `merge.py` while a sleeper holds the
  lock returns under 1 s with the owner line and never waits.
- `twopods` (done line 4): shared alpha-app, `HOME_A` (repos file lists beta-svc) and `HOME_B` (none), pods pod-a and pod-b. Both `operate.py claim`: exit 0,
  no REFUSED/WARN/already/replaced, `operation.id` has both, the hook view treats both as operation sessions. pod-a freezes `api`, pod-b freezes
  `web` (python import, no process started); each check-in shows its own goal plain and the other's `owned by`; each `sessions.py send` works on its own
  goal and is refused on the other's; both pods then merge concurrently through the `lock` shim, neither refused, each record changed only by its owner,
  `merge.lock` gone at the end.
- `size` (done line 6): base = `git merge-base HEAD main`, else `origin/main`, else `HEAD`. For every `skills/*/scripts/*.py`: size
  < 20480 always; and < 18432 unless the base copy (`git show BASE:path`) was already >= 18432. Per-file caps: graph.py <= 18000,
  checkin.py <= 12500, operate.py <= 10500, goal.py <= 19800, sessions.py <= 19800, watch.py <= 19800, merge.py <= 19985, mend.py <= 14000,
  board_lines.py <= 17200. Package file count: exactly `dev/package.py`'s method (`MAX_FILES = 99`; run it in dry mode, or copy
  `test-deployments.sh`'s list) on `git ls-files --cached --others --exclude-standard`, at most 99, no new script file.
- `docs` (done line 1): `grep -E '^- MON-1[345]: \*\*Reviewed [0-9-]+\*\* .*<!-- reviewed [0-9a-f]{8} -->'` for all three in
  `docs/wiki/Monitoring.md`, each quoting the wording below byte for byte up to the first sub-bullet; `docs.py check` exits 0.

### 6. Wiki (wording from the goal file's first done line, byte for byte)

`docs/wiki/Monitoring.md`, after MON-12's sub-bullets and before `### Non-functional`:

```
- MON-13: **Unreviewed** Two layers per pod: one operation session governs every repo in its pod directly and talks to each worker, with no per-repo operation session; several pods may run concurrently and independently
  - A claim adds the session to every repo the pod follows and keeps the other sessions already claimed; nothing refuses or warns when a second operation session runs.
- MON-14: **Unreviewed** The check-in dependency map is grouped by repo first: one block per repo headed by the repo's name, cross-repo dependencies drawn between blocks
  - Each repo prints as `== name ==` within 60 characters, then a `Between repos` list for `repo/slug` dependencies, then the legend once.
- MON-15: **Unreviewed** Pods coordinate through shared state, not messages: every goal records its owning pod and only that pod starts, answers, merges or resumes it; other pods show it read-only as owned by that pod; merges into one repo's main are serialized across pods by a short lock
  - The pod id is `LOOP_POD_ID`, else the operation session's own id; a goal with no recorded pod belongs to no one. Another pod's attempt prints one `REFUSED: goal <slug> is owned by pod <id>. Fix: ...` line, exit 2, and changes nothing.
  - `merge.py` takes `<git common dir>/loop/merge.lock` for the whole merge step; a dead holder or one older than 30 minutes is replaced.
```

Also one Usage sentence naming `LOOP_POD_ID` and `owned by <pod>`; in `docs/wiki/Delivery.md` line 18 (`merge.py`) append
"Takes a per-repo merge lock so two pods never merge into one main at once, and refuses another pod's goal with one line naming the owner." and
the same owner clause on its `goal.py resume` line if that line exists (both statements are true after step 3). Touch no other line. Do not hand-edit
the Tests tables or `Tests.md`. Seal after the tests pass (`--user` needs the owner's own words; copied exactly from the goal file):

```
LOOP_OWNER_WORDS="Add when the operation that I should only get one operation session for the entire pod ... They're just two layers ... It should show by groups first group by the reponents." \
  python3 skills/workflow-docs/scripts/criteria.py review MON-13 MON-14 --user
LOOP_OWNER_WORDS="you should expect it that I have multiple monitoring sessions ... they don't need to know each other. yes add now" \
  python3 skills/workflow-docs/scripts/criteria.py review MON-15 --user
```
Never words of our own; wording is frozen once sealed, no other Reviewed line is edited.

### 7. Regression rows (after tests and seal pass); `T` = `bash dev/toy/test-pods.sh`, level `land`, category `criterion`

| ID | command | goal | describe |
|---|---|---|---|
| `pods-docs` | `T docs 2>&1 \| tail -1 \| grep -qx "ALL PASS"` | `pods:1` | Given the Monitoring PRD, when MON-13, MON-14 and MON-15 are read, then each is Reviewed with a valid seal. |
| `pods-owner` | `... owner ...` | `pods:2` | Given a goal owned by pod-a, when pod-b acts on it, then one REFUSED line names pod-a and the board marks it owned by pod-a. |
| `pods-lock` | `... lock ...` | `pods:3` | Given two concurrent merges into one repo, when both run, then they serialize and a dead or old lock is replaced. |
| `pods-independent` | `T layers twopods ...` | `pods:4` | Given two independent operation sessions, when both claim and work one repo, then neither is refused and neither collides. |
| `pods-blocks` | `... blocks ...` | `pods:5` | Given three repos, when the check-in prints, then each is a `== name ==` block within 60 columns. |
| `pods-size` | `... size ...` | `pods:6` | Given the package, when sizes are counted, then no script crosses 18 KB unless it already did, none passes 20 KB, and it has 99 files or fewer. |
| `mon13-two-layers` | `... layers ...` | `MON-13` | Given a second session's claim, when it claims, then the first stays an operation session. |
| `mon14-repo-blocks` | `... blocks ...` | `MON-14` | Given a cross-repo dependency, when the check-in prints, then it lists it between headed repo blocks. |
| `mon15-pod-owner` | `... owner ...` | `MON-15` | Given another pod's goal, when a pod acts on it, then it is refused naming the owner and shown owned by that pod. |
| `mon15-merge-lock` | `... lock ...` | `MON-15` | Given two pods merging into one main, when they run together, then the lock serializes them. |

Add with `regression.py add ID --level land --command C --goal G --describe D --category criterion`; each is SEEN FAILING via `regression.py red ID --break "..."` once committed:
- `pods-independent`, `mon13-two-layers`: break `sed -i.bak 's/open(path, "a")/open(path, "w")/' skills/workflow-monitoring/scripts/operate.py` (adapt to the exact write line).
- `pods-blocks`, `mon14-repo-blocks`: `sed -i.bak 's/"== %s =="/"%s"/' skills/workflow-monitoring/scripts/checkin.py`.
- `pods-owner`, `mon15-pod-owner`: `sed -i.bak 's/        sys.exit(2)/        return/' skills/workflow-monitoring/scripts/graph.py` (refuse stops refusing).
- `pods-lock`, `mon15-merge-lock`: `sed -i.bak 's/os.O_CREAT | os.O_EXCL | os.O_WRONLY/os.O_CREAT | os.O_WRONLY/' skills/workflow-monitoring/scripts/graph.py` (two holders at once).
- `pods-size`: `python3 -c "open('skills/workflow-monitoring/scripts/graph.py','a').write('#'*19000+'\n')"`.
- `pods-docs`: `sed -i.bak 's/^- MON-15: \*\*Reviewed/- MON-15: **Unreviewed/' docs/wiki/Monitoring.md`.
Before commit, prove red without a stash: `git archive $(git merge-base HEAD main) skills | tar -x -C $TMP/base`; `POD_SKILLS=$TMP/base/skills bash dev/toy/test-pods.sh`
`layers`, `blocks`, `owner`, `lock`, `twopods` must each FAIL and the new tree prints `ALL PASS` (record both). Then `criteria.py render`, and `render --check` reports nothing stale.

### 8. Final checks

`wc -c` against the caps in the `size` case; `dev/package.py` count <= 99; `docs.py check` and `audit`, `criteria.py render --check`, `regression.py check`
(no UNPROVEN); `grep -n "operation.id\|claim\|<- " dev/toy/*.sh` and fix each assumption of overwrite or the flat Dependencies layout; the toy tests the edits
touch (`test-monitoring-prd`, `-operate`, `-govern`, `-reply-hook`, `-session-workers`, `-board-held`, `-live-board`, `-goal`, `-guards`, `-release`,
`-autorelease`, `-merge-guard`, `-delivery-release`, `-scan-sites`, `-milestones`, `-lanes`); then the full lane as `.github/workflows/regression.yml` runs it.

## Verify by hand (copy into the goal file's section; done lines stay untouched)

1. In one repo run `CLAUDE_SESSION_ID=pod-a python3 skills/workflow-monitoring/scripts/operate.py claim`, then `CLAUDE_SESSION_ID=pod-b ... claim`. Expect: both print `CLAIMED operation session`, no REFUSED, WARN or `replaced`; `cat .git/loop/operation.id` lists pod-a and pod-b.
2. Queue a goal as pod-a (`LOOP_POD_ID=pod-a python3 skills/workflow-monitoring/scripts/watch.py watch --once`), then `cat .git/loop/runs/<slug>.json`. Expect: `"pod": "pod-a"`.
3. As pod-b run `LOOP_POD_ID=pod-b python3 skills/workflow-monitoring/scripts/operate.py send <slug> hi`. Expect: exactly one line `REFUSED: goal <slug> is owned by pod pod-a. Fix: ...`, exit status 2, the record unchanged.
4. Run `python3 skills/workflow-monitoring/scripts/checkin.py` as pod-b. Expect: the goal reads `owned by pod-a` and no question for it is numbered under Needs you; as pod-a it has no such words.
5. In two shells run `python3 skills/workflow-release/scripts/merge.py <slug>` for two goals of one auto_merge repo at once. Expect: the second prints `WAITING: another pod is merging into this repo` and starts only after the first ends; `.git/loop/merge.lock` is gone afterwards.
6. Write a dead pid into `.git/loop/merge.lock` (`echo 999999 > ...`) and run a merge. Expect: it takes the lock at once (no WAITING).
7. Run `python3 skills/workflow-monitoring/scripts/checkin.py` with two followed repos. Expect: one `== name ==` block per repo, no line over 60 characters, `Between repos` for a `repo/slug` dependency, the legend once.

## Risks and accepted limits

- A restarted session has a new id, so its goals look foreign until `LOOP_POD_ID=<old id>` is set (the refusal says so); PENDING below. A mistyped id refuses until corrected.
- A hung merge holds the lock up to 30 minutes, then is replaced. A pod-less caller is refused on an owned goal; unowned goals stay open.
- `watch.py` still holds `repo/slug` dependencies as unknown; The task text said seven done lines; the file has six, so no `pods:7`.

## FINAL SPEC (wins over earlier text, including the design)

- Pod id: `graph.pod_id()` = `$LOOP_POD_ID`, else `$CLAUDE_SESSION_ID`; empty in a worker. `operate.py claim` adds its id (never replaces, never refuses a second
  operation session) and prints the `POD` line; `operate.py run` exports `LOOP_POD_ID`.
- `pod` is in the run record, stamped once at `watch.freeze`, `goal.py new` (non-worker) and `sessions.assign`; no `pod` means no owner.
- `graph.refuse(state)`: exit 2, one stderr line `REFUSED: goal <slug> is owned by pod <id>. Fix: act from that pod (set LOOP_POD_ID=<id>), not from here.`, before any
  write, no try used, workers never checked; at watch resume, mend, `operate.py send`, auto, `sessions.held`, `session_bind.cmd_bind`, `goal.py resume`, `merge.py`.
- Board and check-in append ` owned by <pod>`; a foreign waiting question is read-only under Needs you.
- `merge.py`: `<git common dir>/loop/merge.lock` (O_EXCL, pid, `atexit` release, dead or older than `LOOP_MERGE_LOCK_SECONDS`/1800 s replaced by atomic rename), after the
  ownership check, before the first `gh` call.
- Shared code only in `graph.py` (<= 18,000); `goal.py`, `merge.py` import it by `sys.path.append` + `try/except ImportError`; caps in the `size` case; no script
  >= 20,480, none newly >= 18,432, package <= 99 files, no new script file.
- Tests `dev/toy/test-pods.sh` (layers, blocks, owner, lock, twopods, size, docs), invented names only. MON-13/14/15 wording exactly as the goal file, added Unreviewed,
  sealed with the owner's quotes; the ten rows, each seen failing first. `Delivery.md` (not the missing Release.md) gets the true sentences; Tests tables only from `criteria.py render`.
