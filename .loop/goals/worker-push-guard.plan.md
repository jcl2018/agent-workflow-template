# Plan: worker-push-guard

Design: `.loop/goals/worker-push-guard.design.md` (idea step, spec review PASS at round 2, auto-approved).

## URGENT, outside this plan

None.

## Implementation plan

Done lines (frozen): (1) a pre-push hook that setup installs refuses, for a worker session, any push whose target is
main or a branch other than `loop/<its goal>`, naming the rule and the fix; (2) the operation session's merge and
release steps are unaffected; (3) regression rows for an allowed own-branch push and refused pushes to main and to
another goal branch, each seen failing then passing.

Gate (build start): main holds guard-enforce's `private.py hook push` (reads git's four-field ref lines on stdin) and a
pre-push stub that calls it. If it is not on main when the build starts, the build writes nothing and prints
`PENDING: guard-enforce's private.py hook push is not on main; merge it, then run this goal again`. Never a competing
`hook push`, stub or pre-push hook. Merge main first.

### 1. `skills/workflow-delivery/scripts/private.py` (no new file; about 50 lines)

- Constants `WORKER_PUSH = "WORKER_PUSH"` and `WORKER_PUSH_INTERNAL = "WORKER_PUSH_INTERNAL"`.
- `where()`: the git common dir (`git rev-parse --git-common-dir`, absolute) and the toplevel (`--show-toplevel`), both
  `realpath`ed; returns the slug when the toplevel is under `<common>/loop/worktrees/<slug>` (slug = the first folder
  below, the worktree folder name, not the branch suffix), else None. The temp release tree (system temp dir), the operation checkout and any other folder: None. It
  never reads `LOOP_ROLE` (worker.py sets it for the release step, so keying on it could refuse a legitimate release push).
- `worker_push(lines)` returns None (allow) or `(why, fix, code)` like `refusal()`: for each ref line
  `<local ref> <local sha> <remote ref> <remote sha>`, refuse unless the remote ref is `refs/heads/loop/<slug>` and it
  is not a delete (local sha all zeros); force pushes of the own branch pass; all lines are checked (a multi-ref push
  with one bad ref is refused whole). Fail closed: a `git rev-parse` that fails or prints an empty path, or a non-empty ref line that is not four
  fields, refuses with `WORKER_PUSH_INTERNAL`; empty stdin and a not-a-work-tree answer allow (obligations below).
- Refusal texts, private.py's style, exit 2: the literals are in the REFUSAL TEXTS obligation below, and they govern.
- `hook push` (guard-enforce's mode) runs `worker_push` first, with no private-name list needed, then the private-name
  scan; it prints both refusals when both apply, WORKER_PUSH first, and exits 2 either way. This is the only change to that mode.

### 2. Tests and rows

- `dev/toy/test-push-guard.sh` (new; sources reap.sh; `# reads:` header declares private.py and what it reaches):
  builds with `make.sh`, copies the skills folder to a temp dir and installs the hook from that copy (setup refuses a
  worktree path), adds a goal worktree at `<common>/loop/worktrees/<slug>` on `loop/<slug>` and a detached temp worktree
  for the release case. Cases: own branch allowed; `HEAD:main` refused; `HEAD:loop/other` refused; the operation
  checkout (no LOOP_ROLE) pushes main; the detached release tree with LOOP_ROLE=worker pushes main; a tag push and a
  delete of the own branch refused; a refused push still refused with no private-name list, an allowed one still
  passing; a multi-ref push refused whole; an internal error (broken GIT_DIR, malformed ref line) refused with
  `WORKER_PUSH_INTERNAL`; a worker env var in the main checkout passes (the known limit, asserted so changing it is a decision).
- `.loop/regression.tsv`: one `land` row per case, goal column the done line it proves (`worker-push-guard:1`, `:2`, `:3`), each seen failing first (committed first, then red by a break command; the old code has no guard)
  (`regression.py red`, refusal rows with `worker_push` stubbed to allow everything, allowed rows with it stubbed to
  refuse everything).
- The real flows run under the installed hook from a real goal worktree (the REAL PUSHERS obligation below); no existing
  toy installs the hook on main.

### 3. Docs

- `skills/workflow-delivery/references/commands.md`: the guard, who a worker is, what it may push, and the two codes in
  the refusal-codes table; the limits stated plainly (`--no-verify`, `core.hooksPath` and a push from the main
  checkout skip the hook; branch protection on main is the real backstop, an owner action).
- `docs/wiki/Delivery.md` is not edited (rows keyed by done line never render there); `docs/wiki/Tests.md` re-renders
  (the TOUCHES obligation below). No owner-reviewed page changes.


<!-- autoplan-accepted:ceo -->
- ROW KEYS: every new regression row names a done line (`worker-push-guard:1`, `:2`, `:3`) in its goal column, never DEL-9 (Delivery.md:52 is "Nothing private ships"). Each of the three done lines has at least one land row, and `regression.py sync` prints no GAP for the goal. Verify: `regression.py sync` clean; `regression.py red ID --break CMD` run for every row after the rows are committed.
- TOUCHES: docs/wiki/Delivery.md gets no edit. docs/wiki/Tests.md re-renders (`docs.py audit` render step) and is not in the goal's Touches, so the operation widens them (`goal.py touches worker-push-guard --add docs/wiki/Tests.md --why "rows render there"`) before `goal.py pr`; if it is not widened the build records that as a finding and does not edit Tests.md.
- GATE IS A PROBE: the build starts only when `printf '' | python3 skills/workflow-delivery/scripts/private.py hook push origin x` exits 0 AND the pre-push stub that calls it exists in setup's seed (grep it); otherwise it writes nothing and prints the PENDING line. Merge main first, then probe.
- EMPTY STDIN ALLOWS: a pre-push hook run with no ref lines (an up-to-date push) is allowed, never WORKER_PUSH_INTERNAL; only a non-empty line that is not four fields is internal.
- NOT A WORK TREE ALLOWS: `git rev-parse --is-inside-work-tree` printing false (a bare repo, the cwd inside .git) is not a worker; a rev-parse that exits non-zero is WORKER_PUSH_INTERNAL.
- COVERAGE LIMITS STATED: commands.md names that only goals in `<common>/loop/worktrees/<slug>` are guarded (a `--here` goal, a push from the main checkout and a push from any other worktree are not), alongside `--no-verify` and `core.hooksPath`.
- REAL PUSHERS UNDER THE HOOK: test-push-guard.sh installs the hook and runs the real `goal.py pr`, `guards.write_finding`, `wiki.py prepare --commit`, `release.py cut` and `merge.py`'s release push, each from a real `<common>/loop/worktrees/<slug>` with LOOP_ROLE=worker, and asserts each push lands; the plan's sentence that existing toys already run with the hook installed is false on main and is replaced by this.
- WHERE HELPER: `private.py where` prints `WORKER <slug>` or `NOT A WORKER (<why>)` and the INTERNAL refusal's Fix line names it.
- SLUG IS THE FOLDER: the slug is the worktree folder name below `<common>/loop/worktrees/`; the one allowed remote ref is exactly `refs/heads/loop/<folder>` (exact, case-sensitive string equality, never a prefix test, so `loop/<slug>-evil`, `loop/<slug>/x` and `loop/<Slug>` are refused). Every worktree the loop makes has folder == slug (watch.py:275-290, mend.py:173-211), so `release.py cut` (state branch or `loop/<slug>`) and the others land. A folder that differs from its branch is refused, and the refusal names the expected ref and says the folder must equal the goal slug. A detached HEAD in a worker worktree may push to `refs/heads/loop/<folder>` only.
- CONTEXT PATHS: `where()` joins a relative `--git-common-dir` answer to the toplevel before `realpath` (no use of `--path-format`, which needs git 2.31), and both paths come from git so a different-case cwd on a case-insensitive disk is already canonical (probe: a cwd typed in upper case printed the lower-case folder). The toy asserts a macOS `/var` temp release tree (a symlink to `/private/var`) is not a worker, and, when the disk is case-insensitive, that a cwd typed in another case is still a worker (refuses `HEAD:main`).
- RELEASE PR PUSH: the toy also pushes `HEAD:refs/heads/release/v<X>-<slug>` with `--force` from the detached temp tree (the `to_branch` path, autorelease.py:199) and it passes, next to the push to main.
- PER-REPO ONLY: the guard sees only pushes of this repo's hook; a push by a worker to another repo or to the wiki clone (docs.py:361) is outside it, stated in commands.md.
- BOTH REFUSALS: when the worker rule and the private-name scan both refuse, `hook push` prints WORKER_PUSH first and the private-name refusal second and exits 2; one refusal exits 2 as well.
- GATE GREP: the stub check is `grep -n "pre-push" skills/workflow-setup/scripts/seed.py`, together with the `hook push` probe above; both must hold.
- RED BY BREAK COMMAND: a refusal row's red break inserts an early `return None` as the first statement of `worker_push`; an allowed row's red break makes it return a refusal tuple first; each row is committed with its toy case before `regression.py red ID --break CMD` runs (red copies HEAD), and the seen_red dates are committed after.
- KNOWN LIMIT IS A TOY LINE: the worker-env-in-the-main-checkout case is a PASS line in the toy asserting the limit, not a regression row (a row would guard the limitation itself).
- FAKE GH: the merge.py release push in the toy uses the existing `dev/toy/fakegh` setup that test-autorelease.sh uses.
- REAL PUSHERS, SPLIT BY WHERE THE PUSH RUNS (replaces the merge.py clause of REAL PUSHERS UNDER THE HOOK above; that bullet's other pushers stand): from the worker worktree (LOOP_ROLE=worker) the toy runs `goal.py pr`, `guards.write_finding`, `wiki.py prepare --commit` and `release.py cut` (pushes `state.branch or loop/<slug>` with `-u origin <branch>`, release.py:366, from the goal tree) and each lands on `refs/heads/loop/<slug>`. `merge.py` is run with cwd the goal worktree and LOOP_ROLE=worker (exactly what `release_step` does, worker.py:78-90); its release push runs from the detached temp tree (autorelease.py:199), is not a worker location, and lands on main or `release/v<X>-<slug>`; that is done line 2 and asserts main moved. Nothing here expects a worker-location push to main to land.
- TOY CASE LIST (one list): own branch allowed; `HEAD:main`, `HEAD:loop/other`, `HEAD:loop/<slug>-evil`, `HEAD:loop/<slug>/x` refused; tag push, delete of the own branch, `--mirror` and `--all` refused; multi-ref push refused whole; no private list: refused still refused, allowed still allowed; empty stdin allowed; internal errors (broken GIT_DIR so rev-parse fails, a malformed non-empty ref line) refused with WORKER_PUSH_INTERNAL; operation checkout pushes main; detached temp tree with LOOP_ROLE=worker pushes main and `release/v<X>-<slug>` (forced); macOS `/var` temp tree not a worker; upper-case cwd still a worker where the disk is case-insensitive; worker env var in the main checkout passes (known limit, a PASS line); the four worker-location pushers and merge.py as in the split above; `private.py where` in a worker folder, the main checkout and the temp tree.
- REFUSAL TEXTS: WORKER_PUSH: `REFUSED: a worker session for goal <slug> may push only loop/<slug> (expected ref refs/heads/loop/<slug>; the worktree folder must equal the goal slug), not <ref>; nothing was pushed. Fix: push your own branch (goal.py pr <slug>); only the operation session publishes to main (merge.py), and another goal's branch is pushed from that goal's own worktree. (WORKER_PUSH)`. WORKER_PUSH_INTERNAL: `REFUSED: the worker-branch check could not read <what>; nothing was pushed. Fix: run private.py where in this folder to see why; push once with --no-verify only if the owner agrees. (WORKER_PUSH_INTERNAL)`. Both exit 2 and both codes go in commands.md's refusal-codes table.
- WHERE CLI: `private.py where` prints `WORKER <slug>` or `NOT A WORKER (<why>)` and exits 0; when git cannot answer it prints `UNKNOWN (<what>)` and exits 1 (the same fault the hook refuses on). The size estimate becomes about 50 lines; private.py stays under 18,000 bytes, measured after the merge of guard-enforce's `hook push`.
- WHO MERGES MAIN: the operation session or the owner merges guard-enforce first; the build step only probes and prints PENDING, it never merges or writes.
- TOUCHES CHECK: private.py, references/commands.md, dev/toy and .loop/regression.tsv are inside the goal's Touches; only docs/wiki/Tests.md is outside (above).
- MERGE.PY PATH IS ONE PATH: the toy runs merge.py against the unprotected bare origin (the default in test-autorelease.sh, FAKE_GH_ORIGIN, no pre-receive rule), so its release push goes to main and the toy asserts main moved; the `release/v<X>-<slug>` landing is asserted only by the separate forced-push case from the temp tree.
- COMMANDS.MD FRAMING: commands.md opens its guard section by saying the hook is a mistake guard, not enforcement; the rule is GitHub branch protection on main (Guardrails GRD-6, Setup, the owner enables required reviews) and, stronger, a worker credential limited to `loop/*` (an owner action, not built here). It never presents `--no-verify` as a fix.
- INTERNAL FIX WITHOUT --no-verify (replaces the Fix clause of the WORKER_PUSH_INTERNAL text above): `Fix: run private.py where in this folder to see why, then tell the owner; do not use --no-verify.` The hook never suggests the bypass.
- GATE VIA THE QUEUE: the recommended way to honor the gate is for the operation to hold this goal behind guard-enforce with the queue's depends-on (watch.py:285 stores it as waits_on, board.py:234 shows it), so no build starts and prints PENDING; the PENDING probe stays as the fallback for a goal started by hand.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:eng -->
- CWD-RELATIVE COMMON DIR (replaces the CEO CONTEXT PATHS clause that joins to the toplevel): `where()` resolves `git rev-parse --git-common-dir` against the process cwd (`os.path.realpath(os.path.join(os.getcwd(), out))`), because git prints it relative to the cwd (probe: `.git` at the top, `../../.git` two folders down, absolute in a linked worktree). The toy runs `private.py where` from a subdirectory of the main checkout (NOT A WORKER) and of the worker folder (WORKER <slug>).
- RETRY ONCE: `where()` retries a failed `git rev-parse` once before it reports WORKER_PUSH_INTERNAL. No owner off switch is built (deferred; see the gate brief).
- ZERO SHA: a push line is a delete when its local sha is non-empty and every character is `0` (40 or 64 long, SHA-1 and SHA-256 repos). Toy: a 64-zero line fed to `hook push` by hand is refused, and a delete of `loop/<other>` is refused.
- PUSH SHAPES: toy cases `git push -u origin HEAD` with push.default simple and with current (allowed), `git push --follow-tags origin HEAD` with no tag on the pushed commits (allowed) and with an annotated tag on them (refused, the tag ref is named), and `+HEAD:refs/heads/loop/<slug>` (allowed). The toy header lists the call-site grep result: no `--tags`, no `--follow-tags` and no non-`loop/` refspec in goal.py, guards.py, wiki.py or release.py, and autorelease.py pushes only from its temp tree; any other push shape is refused by design and the Fix names `goal.py pr`.
- STDIN ONCE: `hook push` reads stdin once into a list and gives that list to `worker_push` and then to the private-name scan, and `worker_push` runs before any early return for a missing list. Toy: with a list present, an own-branch push whose commit adds a planted name passes the worker rule and is refused by the scan with PRIVATE_NAME.
- WORKTREE THE LOOP'S WAY: the toy makes the worker worktree with the exact commands watch.py uses (`git worktree add -b loop/<slug> <common>/loop/worktrees/<slug> <base>`), runs `goal.py new --here` from it, and asserts the run's `state.branch` equals `loop/<slug>` before any pusher runs. A rule that allows the worktree's checked-out branch is rejected: a worker could `git switch -c` any name and push it.
- GROUPS AND TIME: the toy takes a group name (refuse, allow, internal, limits, pushers, where) so a row runs only its group; each row greps its own PASS line. The pushers group row is level `land` only when its measured time at build is under 60 seconds, else `nightly`; every group's `# reads:` header lists each skill file the toy executes and `bash dev/toy/check-reads.sh <row ids>` passes.
- CODES DOC: a toy line asserts WORKER_PUSH and WORKER_PUSH_INTERNAL both appear in commands.md's refusal-codes table.
- REMOTE-AGNOSTIC: the remote name and URL are ignored on purpose (a fork or second remote may receive the own branch only); stated in commands.md.
- FINAL SPEC (the single source for the build; it wins over every earlier bullet and over Sections 1-3 where they differ). (a) Files: private.py (constants WORKER_PUSH, WORKER_PUSH_INTERNAL; where(); worker_push(lines); the `where` CLI; one call at the top of guard-enforce's `hook push`), dev/toy/test-push-guard.sh, .loop/regression.tsv rows keyed `worker-push-guard:1`, `:2`, `:3`, skills/workflow-delivery/references/commands.md, docs/wiki/Tests.md re-rendered after the operation widens the touches; docs/wiki/Delivery.md is not edited. (b) where(): `git rev-parse --is-inside-work-tree` printing false returns None; the common dir (resolved against the cwd) and `--show-toplevel` are realpathed; the slug is the first folder below `<common>/loop/worktrees/`, else None; a failed rev-parse is retried once, then WORKER_PUSH_INTERNAL; `LOOP_ROLE` is never read. (c) worker_push(lines): empty input allows; where() None allows; every non-empty line must have four fields, else WORKER_PUSH_INTERNAL; the remote ref must equal `refs/heads/loop/<slug>` exactly and the local sha must not be all zeros; all lines are checked and the first bad ref is named. (d) WORKER_PUSH text: `REFUSED: a worker session for goal <slug> may push only loop/<slug> (expected ref refs/heads/loop/<slug>; the worktree folder must equal the goal slug), not <ref>; nothing was pushed. Fix: push your own branch (goal.py pr <slug>); only the operation session publishes to main (merge.py), and another goal's branch is pushed from that goal's own worktree. (WORKER_PUSH)`; WORKER_PUSH_INTERNAL text: `REFUSED: the worker-branch check could not read <what>; nothing was pushed. Fix: run private.py where in this folder to see why, then tell the owner; do not use --no-verify. (WORKER_PUSH_INTERNAL)`; both exit 2. (e) `hook push` prints WORKER_PUSH (or INTERNAL) first and the private-name refusal second, exit 2 on either. (f) `private.py where` prints `WORKER <slug>` or `NOT A WORKER (<why>)` and exits 0, or `UNKNOWN (<what>)` and exits 1. (g) Gate: the build starts only when `printf '' | python3 skills/workflow-delivery/scripts/private.py hook push origin x` exits 0 and `grep -n "pre-push" skills/workflow-setup/scripts/seed.py` finds the stub, else it writes nothing and prints the PENDING line; the recommended way is for the operation to hold the goal behind guard-enforce with depends-on. (h) Rows: one land row per case group line, each committed with its toy case first, then `regression.py red ID --break CMD` (a break that inserts an early `return None` as the first statement of worker_push for refusal rows, an early refusal tuple for allowed rows), then the seen_red dates committed; `regression.py sync` shows no GAP. (i) commands.md opens the guard section with "a mistake guard, not enforcement", names GitHub branch protection (GRD-6) and a `loop/*`-scoped credential as the owner's real backstop, lists the limits (`--no-verify`, `core.hooksPath`, a push from the main checkout or another worktree, a `--here` goal, another repo or the wiki clone), says the remote name is ignored, and adds both codes to the refusal-codes table.
<!-- /autoplan-accepted:eng -->
## Review record

<!-- autoplan:review-record -->

<!-- autoplan-baseline-edits:ceo {"sourceSha256":"8671ec90a5d2852d2598ec2235585b83dc6cb31037fcf6e9f79b5497489972db","replacements":[{"oldText":"goal DEL-9, each seen failing on the old code first","newText":"goal column the done line it proves (`worker-push-guard:1`, `:2`, `:3`), each seen failing first (committed first, then red by a break command; the old code has no guard)"},{"oldText":"- The existing flows (`goal.py pr`, `wiki.py prepare --commit`, `release.py cut`, autorelease's push) run in their\n  toy tests with the hook installed and still pass.","newText":"- The real flows run under the installed hook from a real goal worktree (the REAL PUSHERS obligation below); no existing\n  toy installs the hook on main."},{"oldText":"- `docs/wiki/Delivery.md`: only the Tests table is re-rendered (`criteria.py render`); Usage and Requirements are\n  owner-reviewed and stay untouched, so no page goes CHANGED.","newText":"- `docs/wiki/Delivery.md` is not edited (rows keyed by done line never render there); `docs/wiki/Tests.md` re-renders\n  (the TOUCHES obligation below). No owner-reviewed page changes."},{"oldText":"returns the slug when the toplevel is under `<common>/loop/worktrees/<slug>` (slug = the first folder\n  below), else None.","newText":"returns the slug when the toplevel is under `<common>/loop/worktrees/<slug>` (slug = the first folder\n  below, the worktree folder name, not the branch suffix), else None."},{"oldText":"it exits with the stronger refusal and prints both when both apply.","newText":"it prints both refusals when both apply, WORKER_PUSH first, and exits 2 either way."},{"oldText":"Fail closed: a failed or empty `git rev-parse` or a ref line that is not four\n  fields refuses with `WORKER_PUSH_INTERNAL`.","newText":"Fail closed: a `git rev-parse` that fails or prints an empty path, or a non-empty ref line that is not four\n  fields, refuses with `WORKER_PUSH_INTERNAL`; empty stdin and a not-a-work-tree answer allow (obligations below)."},{"oldText":"(no new file; about 40 lines)","newText":"(no new file; about 50 lines)"},{"oldText":"- Refusal text, private.py's style, exit 2: `REFUSED: a worker session for goal <slug> may push only loop/<slug>, not\n  <ref>; nothing was pushed. Fix: push your own branch (goal.py pr <slug>); only the operation session publishes to\n  main (merge.py), and another goal's branch is pushed from that goal's own worktree. (WORKER_PUSH)`.","newText":"- Refusal texts, private.py's style, exit 2: the literals are in the REFUSAL TEXTS obligation below, and they govern."}]} -->

### Phase 1 (CEO), Step 0 working record

**Premise table** (every claim carries a receipt; `unverified=0`)

| premise | claim | file:line receipt | verdict |
|---|---|---|---|
| P-a | private.py is 9.4 KB and has no `hook push` today | private.py (9459 bytes by `wc -c`), main() handles only check and scan, private.py:157-182 | confirmed |
| P-b | guard-enforce's `hook push` and pre-push stub are not on main | `git grep` of origin/main for pre-push, git-hooks, hook push, worker_push: no hit; guard-enforce worktree has a goal file and no plan or design | confirmed: the gate is live |
| P-c | workers run in `<common>/loop/worktrees/<slug>` | watch.py:275-290 (freeze makes the tree and branch), but goal.py:231 sets `"worktree": root()` for `goal.py new --here`, which runs in whatever checkout it was called in | partly wrong: only watch/mend goals are in loop/worktrees; `--here` goals are unguarded |
| P-d | `LOOP_ROLE=worker` leaks into the release process tree | watch.py:247 puts it in the launch env; worker.py:124 and :126 run the agent and then `release_step` (worker.py:78-90) in the same process, which inherits it; merge.py pushes nothing itself (autorelease.py:199 pushes from a temp tree) | confirmed (by inheritance; worker.py:124 itself sets it only on the agent command) |
| P-e | every worker push lands on `refs/heads/loop/<slug>` | goal.py:376, guards.py:214, wiki.py:83, release.py:366 and :382; autorelease.py:199 pushes from a tempfile.mkdtemp tree | confirmed |
| P-f | the git hook runs inside a linked worktree with GIT_DIR set | live probe (scratch repo, hook printing env): GIT_DIR=<common>/worktrees/x, cwd the worktree, `--git-common-dir` and `--show-toplevel` canonical, ref lines `<local ref> <local sha> <remote ref> <remote sha>`; a delete shows `(delete) 0000 <ref> <sha>`; an up-to-date push still runs the hook with EMPTY stdin | confirmed, and adds the empty-stdin case the plan omits |
| P-g | rows may be keyed `goal DEL-9` | Delivery.md:52 says DEL-9 is "Nothing private ships"; regression.py:149-160 and criteria.py:43 key a goal's done lines as `slug:N`; Tests.md already renders "done line lane-control:1" | WRONG as written: see REALITY surface-check and the Phase 1 obligation |
| P-h | existing toys run with the hook installed | `grep` of dev/toy for git-hooks and pre-push finds nothing on main; test-goal.sh:5 exports LOOP_ROLE=worker and :22 pushes main from the main checkout | WRONG: no existing toy installs it, so the plan's last test bullet proves nothing until a toy does |
| P-i | a refused push still stops with no private list | private.py patterns() returns none when no file (private.py:40-43) and scan passes | confirmed: worker_push must not sit behind that state |
| P-j | Delivery.md changes only in its Tests table | rows keyed to `slug:N` never render in Delivery.md (its Tests table lists the page's own requirement ids); they render in Tests.md, which is not in the goal's Touches | WRONG: Delivery.md has no change; Tests.md does |

REALITY: premise-table finding 3 premises wrong (P-c partly, P-g, P-h) and P-j; every claim above has a receipt, unverified=0 (private.py:157, watch.py:275, worker.py:124, Delivery.md:52)
REALITY: already-done pass `git log origin/main` since 2026-11-10 for private.py and skills/workflow-setup shows no worker_push, hook push or pre-push commit (git grep origin/main: no hit) (private.py:157)
REALITY: surface-check finding `setup.py --git-hooks`, `private.py hook push` and the pre-push stub do not exist on main (setup.py:5-6 lists only --reply-hook and --govern-hook); `criteria.py render` lives in workflow-docs (skills/workflow-docs/scripts/criteria.py:200), not workflow-regression; `regression.py red --break` exists and copies HEAD (regression.py:241-262) so a row must be committed before red (regression.py:241)
REALITY: binding-decisions pass the decision search for this branch returned no decision for this branch; the frozen done lines and the design's constraints are the binding set, and nothing here reintroduces an overruled default (.loop/goals/worker-push-guard.md:10)
REALITY: numbers pass private.py 9,459 bytes [measured: wc -c], the plan adds about 40 lines (about 2.4 KB) so about 12 KB of room to 18,000 [estimated]; guard-enforce's hook push is unmeasured [re-measure before gate]; criteria_max 15 with 9 Delivery requirements, no new requirement id (.loop/config.json:28)
REALITY: deferred-asks pass no linked issue; the owner's note ("Approve 1-9") names no request the plan drops (.loop/goals/worker-push-guard.md:1)
REALITY: pr-count pass one pull request for the goal, no ship-policy file (default one PR per wave) (.loop/goals/worker-push-guard.md:4)

**0A premise challenge.** The real problem is "a worker can publish to main or clobber a sibling goal's branch with one mistaken `git push`". Doing nothing costs one bad force-push or one unreviewed main commit per bad session; today nothing but the operation session's own discipline (govern_hook.py:127, which guards the operation session, not workers) prevents it. The plan solves the pain directly for the supported worker shape (a watch/mend goal in `<common>/loop/worktrees/<slug>`), and only a proxy for the rest: a hook is a mistake guard, GitHub branch protection (GRD-6, Setup, unbuilt) is the real backstop. The plan states that honestly.

**0B existing code leverage.** One engine (private.py) and one pre-push stub (guard-enforce) already exist as the shared hook; govern_hook.py:127-167 already decides worker by location; `refusal()` gives the `(why, fix, code)` shape; reap.sh and make.sh give the toy scaffold; regression.py `red --break` gives the seen-failing proof. Nothing is rebuilt. Rejected rebuild: a second hook or role.py check (design Approach B), because git's single stdin cannot be split between two programs.

**0C dream state.**

```
CURRENT                         THIS PLAN                          12-MONTH IDEAL
workers push anything   --->    hook refuses non-own refs   --->   base branch protected server-side (GRD-6),
(nothing but habit)             for loop/worktrees workers,         workers hold a token that cannot push
                                limits named in docs                main at all; the hook is the fast local
                                                                    message, the server is the rule
```

**0D alternatives.** A) the plan as written (worker_push in private.py behind guard-enforce's `hook push`); B) smaller: print a warning only; C) larger: server-side rule plus a per-worker push token. A is already the highest-completeness choice that fits the frozen done line 1 (a hook that refuses); B violates the done line; C is outside the touches and needs owner action on GitHub (named as the backstop). Auto-decision A, mechanical, not a close call.

**0E mode.** SELECTIVE EXPANSION (auto, by the autoplan override): an added capability to a repo that already has the engine.

**0F/0G proposals** (each auto-decided under P1/P2/P3/P4):

| # | proposal | effort | decision | reasoning |
|---|---|---|---|---|
| 1 | a second signal: `LOOP_ROLE=worker` in the main checkout also refuses non-own pushes | S | DEFERRED | dev/toy/test-goal.sh:5 and :22 export LOOP_ROLE=worker and push main from the main checkout, and `--here` goals do the same in real use; the signal leaks (P-d) and would refuse legitimate pushes; owner decision, not auto |
| 2 | `private.py where` prints `WORKER <slug>` or `NOT A WORKER (<why>)` | S | ACCEPTED | the fail-closed Fix line needs a command a person can run without crafting git's stdin; ~8 lines; in the blast radius |
| 3 | a health rule that the guard is installed | S | SKIPPED | duplicate: guard-enforce's pre-push state (installed, stale, foreign, missing) covers it (P4); the stub calls the shared engine so there is no second state |
| 4 | a line in the worker prompt (sessions.py:50) saying a worker pushes only its own branch | S | DEFERRED | outside the Touches (skills/workflow-monitoring); the refusal text already names the rule and fix at the moment it matters |
| 5 | `--here` goals: guard by branch name when the checkout is on `loop/<slug>` | M | DEFERRED | changes who counts as a worker for the operation checkout; needs the owner to decide whether `--here` is still a supported worker shape |
| 6 | a per-case row set (own branch, main, other goal, tag, delete, prefix tricks, multi-ref, internal) instead of 3 rows | S | ACCEPTED | done line 3 names only three rows; the others are the plan's own cases and the review's holes; blast radius is the new toy file |

**0I temporal interrogation.** HOUR 1: the implementer must know `hook push` is a dependency that is not on main (gate), where `where()` gets its answer, and that git canonicalises paths. HOUR 2-3: ambiguities: an empty-stdin hook run (an up-to-date push), `(delete)` as the local ref, `--is-inside-work-tree` false in a bare or .git cwd, case of the slug. HOUR 4-5: surprises: no existing toy installs the hook, the rows are keyed by done line not DEL-9, Tests.md re-renders and is outside Touches, the toy must run the real pushers from a real `loop/worktrees` folder. HOUR 6+: they will wish for `private.py where`, a case-insensitive-path row and the prefix-trick rows. Effort: human ~1 day / CC ~40 min.

### Phase 1 (CEO), voices, sections and outputs

**Voices.** Spec review loop: 3 launches (scores 6, 7, 8 of 10; 27 issues, all applied; round 3 fixes verified 2 of 2 against the amended text). Native CEO subagent: completed, 6 findings (3 high, 3 medium). Codex outside voice: unavailable (usage limit reached until Nov 12 07:55; no paid call ran; no further Codex calls this run). Tag: `[subagent-only]`.

| native finding | severity | disposition |
|---|---|---|
| 1 server-side control is a footnote, the hook cannot stop the named bypasses | high | accepted: COMMANDS.MD FRAMING obligation; GRD-6 (Guardrails.md) is the tracked owner requirement |
| 2 folder == slug is load-bearing, asserted only at hook time | high | deferred: a creation-time assertion belongs in watch.py `freeze` and mend.py (outside Touches); both build the path as `<worktrees>/<slug>` by construction (watch.py:275-277, mend.py:173) |
| 3 `--no-verify` as the documented escape erodes the guard | high | accepted: INTERNAL FIX WITHOUT --no-verify obligation; the log-line proposal is deferred (YAGNI until a refusal is seen) |
| 4 hard dependency on guard-enforce with no owner or expiry | medium | accepted: GATE VIA THE QUEUE obligation (depends-on, watch.py:285); no expiry is invented |
| 5 test sprawl against a 50-line function | medium | kept (taste): the owner named case, symlink, mirror/all and prefix holes for this review, each is one assertion in one toy; the case-insensitive row is conditional on the disk |
| 6 server-side and credential-scoping alternatives not weighed | medium | compared in 0D and the design (Approaches B, C); a single push wrapper is rejected because a worker agent runs free-form `git push` |

```
CEO DUAL VOICES - CONSENSUS TABLE:
  Dimension                             Claude  Codex  Consensus
  1. Premises valid?                    mostly  N/A    N/A (folder==slug load-bearing; --here goals unguarded)
  2. Right problem to solve?            yes     N/A    N/A (real fix is server-side; hook is the readable message)
  3. Scope calibration correct?         mostly  N/A    N/A (toy list long but cheap)
  4. Alternatives sufficiently explored? partly N/A    N/A (server-side named as backstop, now framed first)
  5. Competitive/market risks covered?  yes     N/A    N/A (platform rulesets may make it redundant: keep it small)
  6. 6-month trajectory sound?          mostly  N/A    N/A (INTERNAL refusals must not normalise --no-verify)
```

**Section 1 Architecture.** Current scope: SELECTIVE EXPANSION; accepted: where helper, full row set, framing; deferred: LOOP_ROLE signal, prompt line, --here guard; skipped: duplicate health rule. Findings: the guard is one function in an existing engine called by one existing stub, no new component. One real coupling: `worker_push` runs inside guard-enforce's `hook push`, which is not on main (gate). SPOF: private.py itself (a crash refuses every push; the stub fails closed by guard-enforce's design, matching this plan). Rollback: revert the call line in `hook push`; the stub keeps working; minutes.

```
git push (worker or not)
   |
.git/hooks/pre-push (guard-enforce's stub) --stdin: <lref> <lsha> <rref> <rsha> per ref
   |
private.py hook push  (guard-enforce)
   |-- worker_push(lines)  [this goal]
   |     |-- where(): git rev-parse --git-common-dir / --show-toplevel -> slug or None
   |     |-- None (not under <common>/loop/worktrees/<folder>) -> allow
   |     '-- slug: each line rref == refs/heads/loop/<slug> and lsha != 0 ? allow : WORKER_PUSH
   '-- private-name scan  [guard-enforce]  (no list -> passes with a note)
   exit 2 on either refusal, both printed; git aborts the push
```

**Section 2 Error and rescue.**

| capability | what can go wrong | class | rescued | user sees |
|---|---|---|---|---|
| where() | git rev-parse fails or prints nothing | CalledProcessError or empty | yes: refuse | WORKER_PUSH_INTERNAL with `private.py where` Fix |
| where() | cwd in .git or bare repo (`--is-inside-work-tree` false) | n/a | yes: allow (no worktree, cannot be a worker) | nothing |
| worker_push | non-empty line is not four fields | ValueError | yes: refuse | WORKER_PUSH_INTERNAL |
| worker_push | empty stdin (up-to-date push) | n/a | yes: allow | nothing |
| worker_push | remote ref not the own branch, tag, delete, mirror/all | n/a | refuse | WORKER_PUSH naming ref and Fix |
| hook push | private.py missing or crashes | stub, guard-enforce | yes: stub fails closed | guard-enforce's hook state `stale` |

No catch-all: the only caught failures are the named git failure and the named malformed line; GAPS 0.

**Section 3 Security.** The surface adds a read of git's own stdin and two git calls; no network, secret or file write. Threat: a worker leaves its worktree (high likelihood only by accident, low by intent) and pushes from the main checkout or another worktree, or uses `--no-verify` or `core.hooksPath`: the hook cannot see these; mitigation is the server rule (GRD-6) and the stated limits. Threat: prefix and case tricks: exact string equality. Threat: fork remote: remote-agnostic by design, only the ref counts. High severity: 0 new; one accepted residual (bypass) named.

**Section 4 Data flow and edge cases.**

```
INPUT (stdin lines) -> VALIDATE (4 fields) -> TRANSFORM (where() slug) -> DECIDE (equality, not delete) -> OUTPUT (exit 0 | REFUSED + code, exit 2)
 shadow: empty stdin -> allow | wrong field count -> INTERNAL | git error -> INTERNAL | not a work tree -> allow | symlink/case -> git canonicalises | timeout: none (two local git calls)
```

Interaction cases: `git push` up-to-date (empty stdin: allow), `--mirror` (refs/remotes lines: refuse), `--tags` (refuse), `+HEAD:refs/heads/loop/<slug>` (force: allow), `:ref` (delete: refuse), detached HEAD to the own ref (allow), a folder that differs from its slug (refuse, message names the expected ref). Unhandled: 0. No async ordering (one process, no shared mutable state).

**Section 5 Code quality.** Duplication: where() resembles govern_hook.py:127 and operate.py:133 (startswith checks); not extracted because those live in another skill and use `cwd.startswith` (case and symlink fragile, which this plan avoids); noted, no refactor. Cyclomatic: worker_push has a loop and four branches (under 5 per branch group); where() two. Naming fine. Over-engineering: none beyond `where` CLI (accepted, 8 lines).

**Section 6 Tests.** Diagram: where() (unit: toy row per location: worker folder, main checkout, temp tree, /var, upper-case), worker_push (per case list), hook push ordering (both refusals), real pushers (goal.py pr, write_finding, wiki.py prepare --commit, release.py cut, merge.py), docs (commands.md codes table). Pyramid: all toy-level (a hook needs a real git repo); one file. Flakiness: none timed; case row skipped on a case-sensitive disk. 2 a.m. test: the real pushers under the hook from a real loop/worktrees folder. Hostile QA test: prefix tricks, mirror, delete, malformed line. Chaos: broken GIT_DIR. Gaps: 0 after the obligations.

**Section 7 Performance.** Two `git rev-parse` calls per push (about 10 ms each) and a loop over a handful of ref lines; nothing scales. p99 under 100 ms.

**Section 8 Observability.** The refusal prints rule, ref, fix and a code on stderr; `private.py where` answers who the hook thinks you are. Deferred: a refusal log line (no evidence of need). Debug path after 3 weeks: the code in the message plus `where`. Runbook: commands.md's codes table.

**Section 9 Deployment.** No migration, no flag; the guard arrives with the stub guard-enforce installs, in each repo when its owner re-runs setup (a stale stub is guard-enforce's health state). Old and new private.py never coexist in one repo (single file). Rollback: revert the call line. Post-deploy check: `private.py where` in a goal folder says WORKER and `git push origin HEAD:main` from it is refused.

**Section 10 Trajectory.** Debt: one more function in a file near its cap (about 12 KB left of 18 KB; unmeasured after guard-enforce); path dependency: `loop/worktrees/<slug>` becomes a contract (a future worktree maker must keep folder == slug; creation-time assertion deferred). Reversibility 5/5. 1-year question: obvious, one function, one doc table. Next: GRD-6 server rule and a worker credential limited to `loop/*` make this hook redundant by design; keep it small. Retrospective on cherry-picks: the where helper and the row set were the right adds; the deferred LOOP_ROLE signal is not load-bearing for them.

**Section 11 Design.** SKIPPED (no UI scope).

**NOT in scope** (deferred items are in the gate brief; this repo's backlog is GitHub issues and FINDINGS.md, there is no TODOS.md): DEFERRED: a second signal for the main checkout (proposal 1), a worker-prompt line (4), guarding `--here` goals (5), a creation-time folder==slug assertion (native 2), a refusal log line (native 3). REJECTED: a second hook or role.py check (stdin cannot be split), a health rule (duplicate), a single push wrapper (free-form git push).

**What already exists:** private.py `refusal()` shape and CLI printing; guard-enforce's stub and `hook push` (not yet on main); govern_hook.py's location rule; reap.sh, make.sh, fakegh and test-autorelease.sh scaffolding; regression.py `red --break`; criteria.py render.

**Dream state delta:** after this goal a worker's honest mistakes are caught with a readable message in the supported shape; the 12-month ideal is server-side (GRD-6 plus a credential limited to `loop/*`), and the hook becomes the courtesy layer.

**Error and Rescue Registry:** the six rows in Section 2 (0 CRITICAL GAPS).

**Failure Modes Registry**

| codepath | failure mode | rescued | test | user sees | logged |
|---|---|---|---|---|---|
| where() | rev-parse fails | refuse | toy (broken GIT_DIR) | INTERNAL + Fix | stderr |
| worker_push | malformed ref line | refuse | toy | INTERNAL | stderr |
| worker_push | empty stdin | allow | toy | nothing | no |
| worker_push | other ref, tag, delete, mirror/all, prefix tricks | refuse | toy | WORKER_PUSH + Fix | stderr |
| hook push | both refusals | both printed, exit 2 | toy | two REFUSED lines | stderr |
| real pushers | a legit push refused by mistake | n/a | toy runs all five under the hook | would fail the toy | n/a |
| bypass (`--no-verify`, hooksPath, main checkout, --here goal) | hook not run | not rescued by design | known-limit PASS line | nothing | no |

0 CRITICAL GAPS: the last row is an accepted, named limit (RESCUED=N, TEST=limit line, USER SEES=silent is the nature of a bypassed hook; the server rule is the rescue).

**Dream-state and Completion Summary**

```
  +====================================================================+
  |            MEGA PLAN REVIEW - COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | guard-enforce not on main; DEL-9 mislabel;  |
  |                      | no toy installs the hook; --here unguarded  |
  | Step 0               | 6 proposals: 2 accepted, 3 deferred, 1 skipped |
  | Section 1  (Arch)    | 1 issue found (dependency gate)             |
  | Section 2  (Errors)  | 6 error paths mapped, 0 GAPS                |
  | Section 3  (Security)| 3 issues found, 0 High severity             |
  | Section 4  (Data/UX) | 7 edge cases mapped, 0 unhandled            |
  | Section 5  (Quality) | 1 issue found (duplicated location rule)    |
  | Section 6  (Tests)   | Diagram produced, 0 gaps after obligations  |
  | Section 7  (Perf)    | 0 issues found                              |
  | Section 8  (Observ)  | 1 gap found (refusal log, deferred)         |
  | Section 9  (Deploy)  | 1 risk flagged (stale stub per repo)        |
  | Section 10 (Future)  | Reversibility: 5/5, debt items: 2           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (8 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 6 rows, 0 CRITICAL GAPS                     |
  | Failure modes        | 7 total, 0 CRITICAL GAPS                    |
  | TODOS.md updates     | 0 (no TODOS.md; deferrals in the brief)     |
  | Scope proposals      | 6 proposed, 2 accepted (EXP + SEL)          |
  | CEO plan             | written (ceo-plans/2026-11-11-worker-push-guard.md) |
  | Outside voice        | codex unavailable (usage limit); native completed |
  | Lake Score           | N/A (no coverage-scored question asked)     |
  | Diagrams produced    | 3 (architecture, data flow, hook ordering)  |
  | Stale diagrams found | 0 (no ASCII diagram in a touched file)      |
  | Unresolved decisions | 0                                           |
  | Reality rows         | 7/7 rows (PLAN_REALITY), 0 unverified       |
  +====================================================================+
```

Stale diagram audit: private.py and commands.md hold no ASCII diagram; none to correct.

**Implementation tasks (CEO).**
- [ ] T1 (P1, human ~1h / CC ~10m) private.py: fold in the CEO obligations (slug folder rule, empty stdin, not-a-work-tree, `where` CLI, literal refusal texts). Verify: toy case list passes.
- [ ] T2 (P1, human ~2h / CC ~20m) dev/toy/test-push-guard.sh and rows keyed `worker-push-guard:N`. Verify: `regression.py sync` shows no GAP; `regression.py red` per row.
- [ ] T3 (P2, human ~30m / CC ~5m) commands.md guard section with the framing, limits and both codes. Verify: grep of the two codes and the limits.
- [ ] T4 (P2, human ~10m / CC ~2m) operation: widen touches for docs/wiki/Tests.md and hold the goal behind guard-enforce. Verify: `goal.py touches` output.


### Phase 3 (Eng), Step 0 scope challenge

Scope Challenge result: scope accepted as-is (never reduced, P2). Complexity check: changed files 5 (private.py, commands.md, the new test-push-guard.sh, .loop/regression.tsv, docs/wiki/Tests.md), new classes or services 0, so the 8-file selector does not trip; no cut or structure question is asked. Search check: the only pattern is git's own pre-push stdin contract, probed live (below); no framework or concurrency approach is new. Distribution check: no new artifact, no new skill file (package cap), no CI change.

**What already solves each sub-problem** (read, not assumed):

| sub-problem | existing code | verdict |
|---|---|---|
| refusal shape and CLI printing | private.py:140-154 `refusal()` and :176-179 | reuse |
| who is a worker | govern_hook.py:127, operate.py:133, reply_hook.py:369 (cwd startswith, symlink and case fragile), board_status.py:157, pool.py:148 | not reusable (other skills, cwd-string compare); the plan's git-canonical where() is the sturdier shape; cross-skill extraction is blocked by the skill boundary (no shared code reaches a skill outside its folder) |
| pushers to keep working | goal.py:376, guards.py:214, wiki.py:83, release.py:366/382, autorelease.py:199 | all read, all land on `refs/heads/loop/<slug>` from a worker folder, or run from a temp tree |
| toy scaffolding | make.sh, reap.sh, fakegh, test-autorelease.sh (merge() with FAKE_GH_*; `goal.py new --here` from a worktree on `loop/<slug>` is accepted, goal.py cmd_new) | reuse |
| seen-failing proof | regression.py `red --break` (copies HEAD, runs a break command) | reuse |

**Live probes (bounded, read-only, scratch repo):** (1) in a linked worktree the hook gets GIT_DIR=<common>/worktrees/<name>, cwd = the worktree top, ref lines `<lref> <lsha> <rref> <rsha>`, `(delete)` as the local ref with a zero sha; an up-to-date push still runs the hook with EMPTY stdin; `--mirror` lines include `refs/remotes/...`; (2) `git rev-parse --git-common-dir` is cwd-relative: `.git` at the top of the main checkout, `../../.git` two folders down, absolute in a linked worktree; `--show-toplevel` is always absolute and canonical (a cwd typed in upper case printed the lower-case folder; a symlink cwd printed the real path); (3) the detached temp release tree's toplevel is `/private/var/...` while `pwd` says `/var/...`.

REALITY: premise-table finding 5 claims corrected since the plan was written (DEL-9 key, existing-toys sentence, Delivery.md table, `--here` goals, relative common dir); every claim has a receipt, unverified=0 (private.py:157, goal.py:231, Delivery.md:52)
REALITY: already-done pass `git log origin/main` shows no worker_push, hook push or pre-push commit, and `git grep origin/main` finds none (private.py:157)
REALITY: surface-check finding `private.py hook push`, `setup.py --git-hooks` and the pre-push stub do not exist on main (setup.py:5-6); `criteria.py render` is in workflow-docs (skills/workflow-docs/scripts/criteria.py:200); `regression.py red --break CMD` verified in --help text of regression.py:14 (regression.py:241)
REALITY: binding-decisions pass no decision logged for this branch; the frozen done lines bind (.loop/goals/worker-push-guard.md:10)
REALITY: numbers pass private.py 9,459 bytes [measured: wc -c], plan adds about 50 lines about 3 KB [estimated], guard-enforce's part [re-measure before gate]; commands.md 22,985 bytes [measured: wc -c], Tests.md 113,126 bytes [measured: wc -c] (private.py:1)
REALITY: deferred-asks pass no linked issue, no ask left out (.loop/goals/worker-push-guard.md:1)
REALITY: pr-count pass one pull request, default policy (.loop/goals/worker-push-guard.md:4)

### Phase 3 (Eng), voices, sections and outputs

**Voices.** Native Eng subagent: completed, 10 findings (3 medium, 3 low-medium, 4 low). Codex outside voice: unavailable (the same usage limit, reset Nov 12 07:55; no further Codex call this run). Tag `[subagent-only]`.

| # | native finding | sev | disposition |
|---|---|---|---|
| 1 | the plan is a stack of overrides; a reader of Sections 1-2 could build the superseded text | medium | accepted: FINAL SPEC obligation, one text that wins on conflict, final refusal literals inline |
| 2 | fail-closed INTERNAL stalls unattended workers; no owner switch | medium | accepted in part: one retry of `git rev-parse` first; the owner off switch is deferred (taste: it needs a setting, settings.py and its reference, 3-5 files, and a worker can edit a repo-config switch in its own tree) |
| 3 | `release.py cut` pushes `state.branch or loop/<slug>`; folder == branch assumed | medium | accepted as a test, rejected as a rule: the toy builds the worktree with watch.py's own commands and asserts `state.branch == loop/<slug>`; a "checked-out branch" allowance is refused because a worker could `git switch -c` any name and push it |
| 4 | case-insensitivity rests on one probe | low-medium | evidence kept: git prints the canonical case (probe), the cwd string is never used; the planned conditional toy row stands |
| 5 | `--git-common-dir` is cwd-relative, the plan joins it to the toplevel | low-medium | accepted and confirmed by probe (`../../.git` two folders down): join to the cwd; toy runs `where` from subdirectories |
| 6 | every tag and `--follow-tags` push is refused; the user's own ship skill is untested | low-medium | accepted: push-shape cases and a call-site grep list; a push of any other shape is refused by design and the Fix names `goal.py pr` |
| 7 | `hook push` may return early without a list; stdin read once | low | accepted: STDIN ONCE case (worker passes, the scan still refuses a planted name) |
| 8 | zero sha may be 64 long | low | accepted: all-zero test, a 64-zero toy line |
| 9 | bypassable by design; remote name ignored | low | kept: remote-agnostic on purpose; limits already stated; the remote-name check is rejected (it would refuse a fork flow for no gain) |
| 10 | size and toy runtime | low | accepted: group the toy, measure the pushers group, level `land` only under 60 s |

```
ENG DUAL VOICES - CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?              yes     N/A    N/A
  2. Test coverage sufficient?        gaps    N/A    N/A (5 cases added)
  3. Perf risks + budget/bench named? ok      N/A    N/A (two git calls per push; toy time measured)
  4. Security threats covered?        limits  N/A    N/A (bypassable by design, stated)
  5. Error paths handled?             mostly  N/A    N/A (retry once added)
  6. Deployment risk manageable?      yes     N/A    N/A
```

**Section 1 Architecture.** Two shapes (the design-twice rule applies to a new module or boundary; this adds a function in an existing engine and no boundary, so one line: shape A, the function in `private.py`, is the pick; shape B, a check in `role.py` behind a second stub line, was rejected because git's single stdin cannot be split between two programs). Red flags screened: information leakage (the worker-location rule already lives in five other files as a cwd-string compare, govern_hook.py:127, operate.py:133, reply_hook.py:369, board_status.py:157, pool.py:148; not extracted, because skills cannot import each other and a shared file under the skill boundary is a larger change; noted as debt); hand-synced list (the code names in private.py and commands.md's table: a toy line asserts both); two ways to do one task (none); pass-through (none). Coupling: one new dependency, guard-enforce's `hook push` (gated). Security: no new surface; the stated bypasses stay. Production failure per path: rev-parse failure refuses every worker push (retry once, then INTERNAL with `where` as the diagnosis).

```
dependency graph (new = *)
 .git/hooks/pre-push stub (guard-enforce) --> private.py hook push (guard-enforce)
                                                 |-- worker_push*  --> where()* --> git rev-parse x3
                                                 |                  '--> WORKER_PUSH / WORKER_PUSH_INTERNAL codes*
                                                 '-- scan() / refusal() (existing, unchanged)
 private.py where* (CLI) --> where()*
 commands.md (codes table*, guard section*)   test-push-guard.sh* --> setup copy, make.sh, fakegh, real pushers
 .loop/regression.tsv rows*  --> regression.py red --break
```

**Section 2 Code quality.** DRY: the location rule duplicates five cwd-string checks (above); the new one differs on purpose (git-canonical paths, folder identity, no env); extraction is deferred with the skill-boundary reason, which is the shared-code rubric's "deployment boundary" exception; callers verified at the five locations above. Naming: `worker_push`, `where`, codes: fine. Complexity: worker_push has one loop and four exits; where() three git calls with one retry; under 5 branches each. Error handling: named git failure only, no catch-all. Over-engineering: none left (the off switch was declined). Stale diagrams: none in touched files. Findings: 1 (informational, confidence 8): the five-copy location rule.

**Section 3 Test review** (read: private.py in full, test-autorelease.sh:1-30, make.sh, regression.py:241-262, and the live probes above).

```
CODE PATHS                                                   USER FLOWS (worker / operator)
[+] private.py worker_push                                   [+] worker push, own branch
  |-- empty stdin ..................... [GAP->case] allow       |-- [GAP->case] git push -u origin loop/<slug>
  |-- where() None (not a worker) ..... [GAP->case] allow       |-- [GAP->case] git push -u origin HEAD (push.default)
  |-- 4-field line, own ref ........... [GAP->case] allow       |-- [GAP->case] --follow-tags, no tag
  |-- other ref / tag / mirror / all .. [GAP->case] refuse      '-- [GAP->case] +force of own branch
  |-- delete (zero sha 40 and 64) ..... [GAP->case] refuse    [+] worker push, wrong target
  |-- malformed non-empty line ........ [GAP->case] INTERNAL     |-- [GAP->case] HEAD:main, HEAD:loop/other
  |-- multi-ref one bad ............... [GAP->case] refuse      |-- [GAP->case] loop/<slug>-evil, loop/<slug>/x
  '-- prefix and case tricks ......... [GAP->case] refuse      '-- [GAP->case] tag, delete own, --mirror, --all
[+] private.py where                                          [+] operation / release (done line 2)
  |-- --is-inside-work-tree false ..... [GAP->case] allow        |-- [GAP->case] operation checkout pushes main
  |-- rev-parse fails (retry once) .... [GAP->case] INTERNAL     |-- [GAP->case] temp tree pushes main
  |-- cwd subdirectory ................ [GAP->case] correct       |-- [GAP->case] temp tree forced release/v<X>-<slug>
  |-- /var symlink temp tree .......... [GAP->case] not worker   '-- [GAP->case] merge.py from the goal folder lands
  '-- upper-case cwd (case-insens.) ... [GAP->case] worker      [+] real pushers from a worker folder
[+] hook push ordering                                           |-- [GAP->case] goal.py pr
  |-- no private list, refuse/allow ... [GAP->case]              |-- [GAP->case] write_finding (push -u origin HEAD)
  |-- both refusals, WORKER_PUSH first  [GAP->case]              |-- [GAP->case] wiki.py prepare --commit
  '-- worker passes, scan refuses ..... [GAP->case]              '-- [GAP->case] release.py cut
[+] commands.md codes table .......... [GAP->case] grep
COVERAGE: 0 of 30 paths tested today (no toy installs the hook); the plan's cases cover all 30 after the obligations. Existing-behavior regression risk: the five pushers, the temp-tree release push (done line 2) are the IRON RULE items: each has a case.
GAPS: 30 -> 0 after the case list; 0 E2E beyond the toy, 0 eval (no LLM or prompt change; CLAUDE.md has no prompt patterns).
```

Value cards, test plan artifact: written under the review state root (`<user>-<branch>-eng-review-test-plan-<datetime>.md`); tests to retire: none. The case-insensitive row is conditional, the known-limit line is a PASS line not a row. Regression rule: every pusher in the diagram is an existing flow at risk; each has a dedicated case (no skip).

**Section 4 Performance.** Per push: Python start plus two or three `git rev-parse` (about 10 ms each) and a loop over the ref lines (a handful; `--mirror` may bring dozens): under 100 ms, unknown scale marked as such; no per-request or looped path, no memory growth, no cache. Toy time: the pushers group runs real flows (goal.py pr runs a regression lane): measure at build; level `land` only under 60 s, else `nightly`.

**Outside voice section.** Codex unavailable (usage limit); autoplan runs its own dual voices instead of the loaded skill's separate outside-voice step, so no native fallback was dispatched.

**NOT in scope:** an owner-controlled off switch for the INTERNAL refusal (deferred, taste: setting + reference + toy, and a worker can edit a repo setting in its own tree); extraction of the five-copy worker-location rule (blocked by the skill boundary); guarding `--here` goals; the creation-time folder == slug assertion; a refusal log line; server-side protection and the `loop/*` credential (owner actions); a remote-name check (rejected).

**What already exists:** see Step 0 table; everything above is reused, nothing rebuilt.

**Failure modes registry (Eng)**

| codepath | failure | rescued | test | user sees | logged |
|---|---|---|---|---|---|
| where() | rev-parse fails | retry once, then refuse | toy (broken GIT_DIR) | INTERNAL + Fix | stderr |
| where() | cwd in .git | allow | toy | nothing | no |
| worker_push | zero sha 64 long read as a non-delete | prevented by the all-zero test | toy | would let a delete through | n/a |
| hook push | stdin consumed twice | prevented: read once | toy (STDIN ONCE) | would skip a scan | n/a |
| real pusher | a legitimate push refused by mistake | n/a | toy, five pushers | would fail the toy | n/a |
| merge.py temp tree | treated as a worker | prevented by the location rule | toy | would refuse a release | n/a |
| bypass | `--no-verify`, hooksPath, main checkout, --here | not rescued by design | known-limit line | silent | no |

Critical gaps: 0 (the last row is a named, accepted limit).

**Parallelization.** Sequential implementation, no parallelization opportunity: one module (private.py) and a toy that depends on it, plus docs.

**Implementation tasks (Eng).**
- [ ] T5 (P1, human ~30m / CC ~5m) private.py: cwd-relative common dir, one retry, all-zero sha test, STDIN ONCE order. Surfaced by: Eng findings 5, 2, 8, 7. Verify: where-from-subdirectory, broken GIT_DIR, 64-zero and multi-line cases.
- [ ] T6 (P1, human ~2h / CC ~20m) test-push-guard.sh groups and rows (refuse, allow, internal, limits, pushers, where) incl. watch-style worktree, push shapes, codes-table grep; `check-reads.sh` passes. Surfaced by: Eng findings 3, 6, 10. Verify: each row seen red by break command.
- [ ] T7 (P2, human ~20m / CC ~5m) FINAL SPEC text is the build's single source. Surfaced by: Eng finding 1. Verify: reading order.

**Completion summary (Eng)**
- Step 0: Scope Challenge: scope accepted as-is
- Reality rows: 7/7 applicable rows emitted (PLAN_REALITY), 0 unverified premises
- Architecture Review: 1 issue found
- Code Quality Review: 1 issue found
- Test Review: diagram produced, 30 gaps identified (all covered by the case list)
- Performance Review: 0 issues found
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 0 (no TODOS.md; deferrals listed in the gate brief)
- Failure modes: 0 critical gaps flagged
- Unresolved decisions: 0 in this review
- Outside voice: codex, unavailable (usage limit); native completed
- Parallelization: 1 lane, 0 parallel / 1 sequential
- Lake Score: N/A (no coverage-scored question asked)


### Accepted obligations ledger (CEO)

<!-- autoplan-accepted:ceo -->
- ROW KEYS: every new regression row names a done line (`worker-push-guard:1`, `:2`, `:3`) in its goal column, never DEL-9 (Delivery.md:52 is "Nothing private ships"). Each of the three done lines has at least one land row, and `regression.py sync` prints no GAP for the goal. Verify: `regression.py sync` clean; `regression.py red ID --break CMD` run for every row after the rows are committed.
- TOUCHES: docs/wiki/Delivery.md gets no edit. docs/wiki/Tests.md re-renders (`docs.py audit` render step) and is not in the goal's Touches, so the operation widens them (`goal.py touches worker-push-guard --add docs/wiki/Tests.md --why "rows render there"`) before `goal.py pr`; if it is not widened the build records that as a finding and does not edit Tests.md.
- GATE IS A PROBE: the build starts only when `printf '' | python3 skills/workflow-delivery/scripts/private.py hook push origin x` exits 0 AND the pre-push stub that calls it exists in setup's seed (grep it); otherwise it writes nothing and prints the PENDING line. Merge main first, then probe.
- EMPTY STDIN ALLOWS: a pre-push hook run with no ref lines (an up-to-date push) is allowed, never WORKER_PUSH_INTERNAL; only a non-empty line that is not four fields is internal.
- NOT A WORK TREE ALLOWS: `git rev-parse --is-inside-work-tree` printing false (a bare repo, the cwd inside .git) is not a worker; a rev-parse that exits non-zero is WORKER_PUSH_INTERNAL.
- COVERAGE LIMITS STATED: commands.md names that only goals in `<common>/loop/worktrees/<slug>` are guarded (a `--here` goal, a push from the main checkout and a push from any other worktree are not), alongside `--no-verify` and `core.hooksPath`.
- REAL PUSHERS UNDER THE HOOK: test-push-guard.sh installs the hook and runs the real `goal.py pr`, `guards.write_finding`, `wiki.py prepare --commit`, `release.py cut` and `merge.py`'s release push, each from a real `<common>/loop/worktrees/<slug>` with LOOP_ROLE=worker, and asserts each push lands; the plan's sentence that existing toys already run with the hook installed is false on main and is replaced by this.
- WHERE HELPER: `private.py where` prints `WORKER <slug>` or `NOT A WORKER (<why>)` and the INTERNAL refusal's Fix line names it.
- SLUG IS THE FOLDER: the slug is the worktree folder name below `<common>/loop/worktrees/`; the one allowed remote ref is exactly `refs/heads/loop/<folder>` (exact, case-sensitive string equality, never a prefix test, so `loop/<slug>-evil`, `loop/<slug>/x` and `loop/<Slug>` are refused). Every worktree the loop makes has folder == slug (watch.py:275-290, mend.py:173-211), so `release.py cut` (state branch or `loop/<slug>`) and the others land. A folder that differs from its branch is refused, and the refusal names the expected ref and says the folder must equal the goal slug. A detached HEAD in a worker worktree may push to `refs/heads/loop/<folder>` only.
- CONTEXT PATHS: `where()` joins a relative `--git-common-dir` answer to the toplevel before `realpath` (no use of `--path-format`, which needs git 2.31), and both paths come from git so a different-case cwd on a case-insensitive disk is already canonical (probe: a cwd typed in upper case printed the lower-case folder). The toy asserts a macOS `/var` temp release tree (a symlink to `/private/var`) is not a worker, and, when the disk is case-insensitive, that a cwd typed in another case is still a worker (refuses `HEAD:main`).
- RELEASE PR PUSH: the toy also pushes `HEAD:refs/heads/release/v<X>-<slug>` with `--force` from the detached temp tree (the `to_branch` path, autorelease.py:199) and it passes, next to the push to main.
- PER-REPO ONLY: the guard sees only pushes of this repo's hook; a push by a worker to another repo or to the wiki clone (docs.py:361) is outside it, stated in commands.md.
- BOTH REFUSALS: when the worker rule and the private-name scan both refuse, `hook push` prints WORKER_PUSH first and the private-name refusal second and exits 2; one refusal exits 2 as well.
- GATE GREP: the stub check is `grep -n "pre-push" skills/workflow-setup/scripts/seed.py`, together with the `hook push` probe above; both must hold.
- RED BY BREAK COMMAND: a refusal row's red break inserts an early `return None` as the first statement of `worker_push`; an allowed row's red break makes it return a refusal tuple first; each row is committed with its toy case before `regression.py red ID --break CMD` runs (red copies HEAD), and the seen_red dates are committed after.
- KNOWN LIMIT IS A TOY LINE: the worker-env-in-the-main-checkout case is a PASS line in the toy asserting the limit, not a regression row (a row would guard the limitation itself).
- FAKE GH: the merge.py release push in the toy uses the existing `dev/toy/fakegh` setup that test-autorelease.sh uses.
- REAL PUSHERS, SPLIT BY WHERE THE PUSH RUNS (replaces the merge.py clause of REAL PUSHERS UNDER THE HOOK above; that bullet's other pushers stand): from the worker worktree (LOOP_ROLE=worker) the toy runs `goal.py pr`, `guards.write_finding`, `wiki.py prepare --commit` and `release.py cut` (pushes `state.branch or loop/<slug>` with `-u origin <branch>`, release.py:366, from the goal tree) and each lands on `refs/heads/loop/<slug>`. `merge.py` is run with cwd the goal worktree and LOOP_ROLE=worker (exactly what `release_step` does, worker.py:78-90); its release push runs from the detached temp tree (autorelease.py:199), is not a worker location, and lands on main or `release/v<X>-<slug>`; that is done line 2 and asserts main moved. Nothing here expects a worker-location push to main to land.
- TOY CASE LIST (one list): own branch allowed; `HEAD:main`, `HEAD:loop/other`, `HEAD:loop/<slug>-evil`, `HEAD:loop/<slug>/x` refused; tag push, delete of the own branch, `--mirror` and `--all` refused; multi-ref push refused whole; no private list: refused still refused, allowed still allowed; empty stdin allowed; internal errors (broken GIT_DIR so rev-parse fails, a malformed non-empty ref line) refused with WORKER_PUSH_INTERNAL; operation checkout pushes main; detached temp tree with LOOP_ROLE=worker pushes main and `release/v<X>-<slug>` (forced); macOS `/var` temp tree not a worker; upper-case cwd still a worker where the disk is case-insensitive; worker env var in the main checkout passes (known limit, a PASS line); the four worker-location pushers and merge.py as in the split above; `private.py where` in a worker folder, the main checkout and the temp tree.
- REFUSAL TEXTS: WORKER_PUSH: `REFUSED: a worker session for goal <slug> may push only loop/<slug> (expected ref refs/heads/loop/<slug>; the worktree folder must equal the goal slug), not <ref>; nothing was pushed. Fix: push your own branch (goal.py pr <slug>); only the operation session publishes to main (merge.py), and another goal's branch is pushed from that goal's own worktree. (WORKER_PUSH)`. WORKER_PUSH_INTERNAL: `REFUSED: the worker-branch check could not read <what>; nothing was pushed. Fix: run private.py where in this folder to see why; push once with --no-verify only if the owner agrees. (WORKER_PUSH_INTERNAL)`. Both exit 2 and both codes go in commands.md's refusal-codes table.
- WHERE CLI: `private.py where` prints `WORKER <slug>` or `NOT A WORKER (<why>)` and exits 0; when git cannot answer it prints `UNKNOWN (<what>)` and exits 1 (the same fault the hook refuses on). The size estimate becomes about 50 lines; private.py stays under 18,000 bytes, measured after the merge of guard-enforce's `hook push`.
- WHO MERGES MAIN: the operation session or the owner merges guard-enforce first; the build step only probes and prints PENDING, it never merges or writes.
- TOUCHES CHECK: private.py, references/commands.md, dev/toy and .loop/regression.tsv are inside the goal's Touches; only docs/wiki/Tests.md is outside (above).
- MERGE.PY PATH IS ONE PATH: the toy runs merge.py against the unprotected bare origin (the default in test-autorelease.sh, FAKE_GH_ORIGIN, no pre-receive rule), so its release push goes to main and the toy asserts main moved; the `release/v<X>-<slug>` landing is asserted only by the separate forced-push case from the temp tree.
- COMMANDS.MD FRAMING: commands.md opens its guard section by saying the hook is a mistake guard, not enforcement; the rule is GitHub branch protection on main (Guardrails GRD-6, Setup, the owner enables required reviews) and, stronger, a worker credential limited to `loop/*` (an owner action, not built here). It never presents `--no-verify` as a fix.
- INTERNAL FIX WITHOUT --no-verify (replaces the Fix clause of the WORKER_PUSH_INTERNAL text above): `Fix: run private.py where in this folder to see why, then tell the owner; do not use --no-verify.` The hook never suggests the bypass.
- GATE VIA THE QUEUE: the recommended way to honor the gate is for the operation to hold this goal behind guard-enforce with the queue's depends-on (watch.py:285 stores it as waits_on, board.py:234 shows it), so no build starts and prints PENDING; the PENDING probe stays as the fallback for a goal started by hand.
<!-- /autoplan-accepted:ceo -->

### Accepted obligations ledger (Eng)

<!-- autoplan-accepted:eng -->
- CWD-RELATIVE COMMON DIR (replaces the CEO CONTEXT PATHS clause that joins to the toplevel): `where()` resolves `git rev-parse --git-common-dir` against the process cwd (`os.path.realpath(os.path.join(os.getcwd(), out))`), because git prints it relative to the cwd (probe: `.git` at the top, `../../.git` two folders down, absolute in a linked worktree). The toy runs `private.py where` from a subdirectory of the main checkout (NOT A WORKER) and of the worker folder (WORKER <slug>).
- RETRY ONCE: `where()` retries a failed `git rev-parse` once before it reports WORKER_PUSH_INTERNAL. No owner off switch is built (deferred; see the gate brief).
- ZERO SHA: a push line is a delete when its local sha is non-empty and every character is `0` (40 or 64 long, SHA-1 and SHA-256 repos). Toy: a 64-zero line fed to `hook push` by hand is refused, and a delete of `loop/<other>` is refused.
- PUSH SHAPES: toy cases `git push -u origin HEAD` with push.default simple and with current (allowed), `git push --follow-tags origin HEAD` with no tag on the pushed commits (allowed) and with an annotated tag on them (refused, the tag ref is named), and `+HEAD:refs/heads/loop/<slug>` (allowed). The toy header lists the call-site grep result: no `--tags`, no `--follow-tags` and no non-`loop/` refspec in goal.py, guards.py, wiki.py or release.py, and autorelease.py pushes only from its temp tree; any other push shape is refused by design and the Fix names `goal.py pr`.
- STDIN ONCE: `hook push` reads stdin once into a list and gives that list to `worker_push` and then to the private-name scan, and `worker_push` runs before any early return for a missing list. Toy: with a list present, an own-branch push whose commit adds a planted name passes the worker rule and is refused by the scan with PRIVATE_NAME.
- WORKTREE THE LOOP'S WAY: the toy makes the worker worktree with the exact commands watch.py uses (`git worktree add -b loop/<slug> <common>/loop/worktrees/<slug> <base>`), runs `goal.py new --here` from it, and asserts the run's `state.branch` equals `loop/<slug>` before any pusher runs. A rule that allows the worktree's checked-out branch is rejected: a worker could `git switch -c` any name and push it.
- GROUPS AND TIME: the toy takes a group name (refuse, allow, internal, limits, pushers, where) so a row runs only its group; each row greps its own PASS line. The pushers group row is level `land` only when its measured time at build is under 60 seconds, else `nightly`; every group's `# reads:` header lists each skill file the toy executes and `bash dev/toy/check-reads.sh <row ids>` passes.
- CODES DOC: a toy line asserts WORKER_PUSH and WORKER_PUSH_INTERNAL both appear in commands.md's refusal-codes table.
- REMOTE-AGNOSTIC: the remote name and URL are ignored on purpose (a fork or second remote may receive the own branch only); stated in commands.md.
- FINAL SPEC (the single source for the build; it wins over every earlier bullet and over Sections 1-3 where they differ). (a) Files: private.py (constants WORKER_PUSH, WORKER_PUSH_INTERNAL; where(); worker_push(lines); the `where` CLI; one call at the top of guard-enforce's `hook push`), dev/toy/test-push-guard.sh, .loop/regression.tsv rows keyed `worker-push-guard:1`, `:2`, `:3`, skills/workflow-delivery/references/commands.md, docs/wiki/Tests.md re-rendered after the operation widens the touches; docs/wiki/Delivery.md is not edited. (b) where(): `git rev-parse --is-inside-work-tree` printing false returns None; the common dir (resolved against the cwd) and `--show-toplevel` are realpathed; the slug is the first folder below `<common>/loop/worktrees/`, else None; a failed rev-parse is retried once, then WORKER_PUSH_INTERNAL; `LOOP_ROLE` is never read. (c) worker_push(lines): empty input allows; where() None allows; every non-empty line must have four fields, else WORKER_PUSH_INTERNAL; the remote ref must equal `refs/heads/loop/<slug>` exactly and the local sha must not be all zeros; all lines are checked and the first bad ref is named. (d) WORKER_PUSH text: `REFUSED: a worker session for goal <slug> may push only loop/<slug> (expected ref refs/heads/loop/<slug>; the worktree folder must equal the goal slug), not <ref>; nothing was pushed. Fix: push your own branch (goal.py pr <slug>); only the operation session publishes to main (merge.py), and another goal's branch is pushed from that goal's own worktree. (WORKER_PUSH)`; WORKER_PUSH_INTERNAL text: `REFUSED: the worker-branch check could not read <what>; nothing was pushed. Fix: run private.py where in this folder to see why, then tell the owner; do not use --no-verify. (WORKER_PUSH_INTERNAL)`; both exit 2. (e) `hook push` prints WORKER_PUSH (or INTERNAL) first and the private-name refusal second, exit 2 on either. (f) `private.py where` prints `WORKER <slug>` or `NOT A WORKER (<why>)` and exits 0, or `UNKNOWN (<what>)` and exits 1. (g) Gate: the build starts only when `printf '' | python3 skills/workflow-delivery/scripts/private.py hook push origin x` exits 0 and `grep -n "pre-push" skills/workflow-setup/scripts/seed.py` finds the stub, else it writes nothing and prints the PENDING line; the recommended way is for the operation to hold the goal behind guard-enforce with depends-on. (h) Rows: one land row per case group line, each committed with its toy case first, then `regression.py red ID --break CMD` (a break that inserts an early `return None` as the first statement of worker_push for refusal rows, an early refusal tuple for allowed rows), then the seen_red dates committed; `regression.py sync` shows no GAP. (i) commands.md opens the guard section with "a mistake guard, not enforcement", names GitHub branch protection (GRD-6) and a `loop/*`-scoped credential as the owner's real backstop, lists the limits (`--no-verify`, `core.hooksPath`, a push from the main checkout or another worktree, a `--here` goal, another repo or the wiki clone), says the remote name is ignored, and adds both codes to the refusal-codes table.
<!-- /autoplan-accepted:eng -->

### Decision Audit Trail

<!-- AUTONOMOUS DECISION LOG -->

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | 0 | Skip the toolkit upgrade prompt (1.92 to 1.99 available); log only | mechanical | P6 | unattended rule from the parent | upgrade now |
| 2 | 0 | Design phase skipped: scope check `uiRequired` false | mechanical | P3 | no UI term next to a visual noun, no rendered file | run design review |
| 3 | 0 | DX phase skipped: scope check `dxRequired` false (1 term, threshold 2); `--agent-primary` not set | taste | P5 | the parent said to follow the scope check; the refusal text is still written for a worker reader | enable DX with --agent-primary |
| 4 | 1 | Mode: SELECTIVE EXPANSION | mechanical | P1 | autoplan override | HOLD, EXPANSION |
| 5 | 1 | Approach A (worker_push in private.py behind guard-enforce's hook push) | mechanical | P1, P5 | only option meeting done line 1 inside the touches | warning only; server-side only |
| 6 | 1 | Key rows by done line `worker-push-guard:N`, not DEL-9; Delivery.md untouched, Tests.md re-render | taste | P4, P5 | Delivery.md:52 defines DEL-9 as private names; regression.py:149-160 and criteria.py:43 key a goal's done lines as slug:N | rows under DEL-9; a new DEL-10 requirement (owner-reviewed page) |
| 7 | 1 | Accept `private.py where` | mechanical | P2 | the fail-closed Fix needs a by-hand command | none |
| 8 | 1 | Accept the full row set beyond three rows | mechanical | P1 | holes named by the owner and the review | three rows only |
| 9 | 1 | Defer the LOOP_ROLE second signal | taste | P3 | toys (test-goal.sh:5,22) and --here goals push main from the main checkout with the variable set | build it |
| 10 | 1 | Skip a health rule for the guard | mechanical | P4 | guard-enforce's pre-push state already covers it | build it |
| 11 | 1 | Defer the worker-prompt line and the --here guard | taste | P3 | outside Touches / owner decision | build now |
| 12 | 1 | Gate is an executable probe; recommend holding via depends-on | mechanical | P5 | `hook push` and the stub are not on main | prose gate only |
| 13 | 1 | Empty stdin and not-a-work-tree allow; rev-parse failure refuses | mechanical | P1 | live probe: an up-to-date push runs the hook with empty stdin | refuse on empty stdin |
| 14 | 1 | Exact ref equality on the folder slug | mechanical | P5 | prefix and case tricks | startswith test |
| 15 | 1 | Split merge.py (temp tree, lands on main) from worker-location pushers | mechanical | P5 | spec review 2 | one worker-location assertion |
| 16 | 1 | Spec review: three launches, all fixes applied, round 3 fixes verified 2 of 2 | mechanical | P6 | cap reached | a fourth launch |
| 17 | 1 | Auto-approve the CEO documents (0H) | mechanical | P6 | unattended | pause |
| 18 | 1 | Codex outside voice unavailable (usage limit); continue with the native voice, tag subagent-only | mechanical | P6 | probe: usage limit, no paid call, no retry | wait for reset |
| 19 | 1 | Keep the long toy case list (native finding 5) | taste | P1 | the owner named case, symlink, mirror and prefix holes for this review; each is one assertion | trim to three done-line cases |
| 20 | 1 | Commands.md framing: mistake guard, GRD-6 and a loop/* credential as the real backstop | mechanical | P1 | native finding 1 | footnote only |
| 21 | 1 | INTERNAL Fix never suggests --no-verify | taste | P5 | native finding 3: unattended workers would make the bypass habitual | keep the design's "push once with --no-verify if the owner agrees" |
| 22 | 1 | Defer a creation-time folder == slug assertion and a refusal log line | taste | P3 | outside Touches (watch.py, mend.py) / YAGNI | build now |
| 23 | 3 | Scope accepted as-is; complexity 5 files, 0 new classes, no selector | mechanical | P2 | under the 8-file trigger | reduce |
| 24 | 3 | Join the common dir to the cwd, not the toplevel | mechanical | P5 | probe: `../../.git` two folders down | join to toplevel |
| 25 | 3 | Retry rev-parse once; no owner off switch | taste | P3 | a switch needs a setting, settings.py, its reference and a toy, and a worker can edit a repo switch in its own tree | build the switch |
| 26 | 3 | Reject "allow the worktree's checked-out branch" | mechanical | P5 | a worker could switch to any new name | accept it |
| 27 | 3 | Zero sha test is all-zero, any length | mechanical | P1 | SHA-256 repos | 40-char literal |
| 28 | 3 | Push-shape cases, stdin-once case, worktree made the loop's way | mechanical | P1 | native findings 6, 7, 3 | skip |
| 29 | 3 | Group the toy; pushers row `land` only under 60 s | mechanical | P3 | each row would otherwise rerun every flow | one row per case, all land |
| 30 | 3 | FINAL SPEC bullet is the build's single source | mechanical | P5 | native finding 1: stacked overrides | rewrite the immutable CEO block |
| 31 | 3 | Reject a remote-name check | mechanical | P3 | would refuse a fork flow for no gain | check origin only |
| 32 | 3 | Defer extraction of the five-copy worker-location rule | taste | P3 | skills cannot import each other; shared-code rubric deployment-boundary exception | build a shared helper |
| 33 | 3 | Codex outside voice unavailable again (same usage limit) | mechanical | P6 | no further Codex call this run | retry |

(autoplan appends below)
