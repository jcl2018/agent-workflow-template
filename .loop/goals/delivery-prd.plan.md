<!-- autoplan restore point: kept in the private review folder, outside the repo -->
# Plan: delivery-prd

Design: `.loop/goals/delivery-prd.design.md` (idea step, spec review converged, auto-approved).

## Implementation plan

Done lines (frozen): DEL-6 depth by size; DEL-5 patch default and protected-main release PR (issues 170, 154);
DEL-7 resume from the last recorded step; DEL-8 per-goal budget on the board; DEL-9 private-name scan before every
push; rows for DEL-5..9 and the Delivery Tests table; issues 38, 117, 129, 134 fixed with defect rows.

### 1. `skills/workflow-delivery/scripts/fit.py` (new, under 20 KB)

- `size_of(done_lines, touches) -> {"small": bool, "why": str}`: small = at most 3 done lines, no `github:` touch, at
  most one code area (first two path components; paths under `docs/`, `.loop/`, `dev/toy/`, `test/`, `tests/` are not
  areas; no touches = large).
- `depth_for(setting, state) -> (depth, why)`: `depth_override` wins; else `full` -> full; else `condensed` -> by size.
- `budget_of(cfg) -> {"minutes", "tokens"}` from `time_budget_minutes` / `token_budget` (0 = none).
- `cmd_set(g, args)`: `goal.py set SLUG [--depth full|condensed] [--bump minor|major] [--budget-minutes N]
  [--budget-tokens N] --why TEXT`, operation-only via `guards.operation_only` (refuses `LOOP_ROLE=worker`), logged.
- `resume_at(state)`: first of idea, plan, review, qa, ship whose record is not done/skipped; "build or review" when
  idea and plan are recorded and review is not; `pr` when all are.
- `again(state, step)`: clears the step's record and every later step's record, depth and verdicts; never touches
  `tries`; returns the cleared list.
- `verdicts(text)`: the `VERDICT: <who>: <verdict>` lines of a reply.
- `pr_body(goal_text, state, flow, scan_note, warnings)`: goal file + Result: each step with result, depth, tokens,
  verdicts; the decided review depth and why; the budget; the private-scan note; `github:` touches; regeneration warnings.
- `regen_warnings(top, base_ref)`: for each file the branch deletes, tracked `*.py`, `*.sh` and `.github/workflows/*`
  files naming its path -> `WARN: <script> names <path>, which this goal deletes; it may write it back`.

### 2. `skills/workflow-delivery/scripts/private.py` (new)

- `patterns()`: `LOOP_PRIVATE_NAMES` or `~/.workflow-loop/private-names`, one regex per line, `#` comments; returns
  `None` when no file.
- `scan(top, base_ref, texts={name: text}) -> (hits, note)`: branch name, changed file names, added diff lines
  (`path:line`), commit messages (`commit:<sha>`), each text (`<name>:<line>`). Hits never include the match. Note is
  "no list at ..., nothing was checked" when there is no list.

### 3. Hooks in existing delivery files (one call each; goal.py stays under 20 KB)

- `goal.py new`: store `size`, `budget` via `fit`. `goal.py set` subcommand added (one `add` line). `record`: store
  `verdicts`. `pr`: private scan of branch + title + body before push (refuse no-try `PRIVATE_NAME`, exit 2); body from
  `fit.pr_body`. `show`: adds `resume_at`.
- `role.depth_of(cfg, state=None)`: when a state is given, `fit.depth_for(base setting, state)`.
- `guards.check_record`: passes the state to `depth_of`. `guards.check_path`: accepts `github:<surface>`
  (wiki, milestones, projects, releases, labels, issues). `guards.cmd_resume`: message names `resume_at`.
- `flow.py`: depth prompt uses the goal's decided depth (small condensed goals are told to condense: one spec-review
  round, a lighter plan review, one review pass); token stop reads the goal budget first; refuses a recorded step with
  no try (`ALREADY_RECORDED`, exit 2, names `resume_at`) unless `--again`, which calls `fit.again`; the prompt asks
  for `VERDICT:` lines.

### 4. Release (`skills/workflow-release`)

- `release.auto_need`: `leave` for docs/tests/.loop only; else `(state bump or "patch", reason)`; never `ask`.
- `autorelease.need_of`: no `ask` branch. Release commit and notes scanned by `private.py` before push. A refused push
  whose message names protection goes to `release_pr.py`.
- `release_pr.py` (new): push `release/vX` (force-update on a restart), open the PR, `gh pr merge --merge`, record
  `release_pr`; after it lands, fetch origin/base, require VERSION == vX (else `release_error`), create the release with
  `--target <base sha>`. Reruns: MERGED -> release; OPEN -> retry the merge, else `release_error` "needs the owner to
  approve and merge"; CLOSED -> clear and restart.
- `merge.py`: private scan of the PR branch and release notes before merging (fail closed if `private.py` is missing).
- `wiki.py`: a publish failing because the GitHub wiki has no first page names the fix.
- Docs (#129): SKILL.md description and sections, `references/commands.md`: auto_merge publishes, no draft; without
  auto_merge, `cut` drafts.

### 5. Monitoring (`skills/workflow-monitoring`)

- `board_budget.py` (new): `line(run, cfg)` -> `budget: 35m of 120m, 0.4M of 3.0M tokens[, OVER time][, OVER tokens]`.
- `live_board.py`: the depth line shows the goal's decided depth; prints the budget line (two small edits).
- `mend.py`: resume prompt names `resume_at`.
- `session_bind.py`: `bind SLUG self` reads `CLAUDE_CODE_HOST_SESSION_ID`.

### 6. Tests, rows, docs

- `dev/toy/test-delivery-prd.sh`: one PASS line per behavior: small goal condensed, large goal full, non-skills repo
  sizing, override wins (operation-only, worker refused), condensed small goal still runs the full land lane; patch
  default, `ask` never major, `set --bump minor` honored, protected main release PR -> exactly one release, release PR
  needing review recorded; kill mid-step and resume (records kept, `ALREADY_RECORDED`, one try, rerun completes),
  `--again` clears later records and keeps tries; budget on the board with OVER flags; private hit refuses `pr` and
  `merge.py` with no push, missing list noted in the PR body; verdicts in the PR body (#38); `github:` touches, regen
  warning, `bind self` (#117); docs say published, wiki first-page fix (#129); protected release (#134).
- `.loop/regression.tsv`: rows DEL-5..9 (criterion) and defect rows linked #38, #117, #129, #134, #154, #170; each run
  red on the old code (`regression.py red`) before passing.
- `skills/workflow-delivery/SKILL.md`, `references/commands.md`: `set`, `--again`, size rule, private list, budget line.
- `docs/wiki/Delivery.md`: Tests table re-rendered only.


<!-- autoplan-accepted:ceo -->
- Dependency on docs-format: the DEL-6..DEL-9 requirement text reaches docs/wiki/Delivery.md only with goal docs-format (main's page holds DEL-1..DEL-5). This goal writes no requirement text. Before `pr` it merges origin/main; when docs-format is on the base, it re-renders the Delivery Tests table so the DEL-5..DEL-9 rows sit under their requirement headings; when it is not, the PR body says the DEL-6..DEL-9 rows show under Other until docs-format lands (the mechanism is the pr NOTE below). Verify: `tests.py list --markdown` groups every new row under DEL-5..DEL-9 once docs-format is on the base.
- Re-size on widened touches (E1): when `goal.py touches SLUG --add PATH` widens a goal's touches, `fit.size_of` is recomputed over the frozen done lines and all touches; a small goal can become large, never the reverse; the change is logged with its why. Toy check: a small goal widened to a second area reports large and its decided depth is full under `condensed`.
- Wiki publish scan (E2): `wiki.py` publish runs `private.scan` over the text of every page in the wiki folder (hits named `wiki:<page>:<line>`) before it clones or pushes; a hit records `wiki_error` naming the page and line and publishes nothing. Toy check: a planted name in an untouched wiki page stops the publish.
- Broken list fails closed (E3): a private-name list that exists but can't be read, or holds a line that is not a valid regex, makes every scan refuse (goal.py pr: no try used, exit 2; merge.py, autorelease and wiki publish: refuse or record the error, nothing pushed or merged), naming the file and line number, never the pattern. Toy check with an invalid regex line.
- One time rule (E4): `board_budget.line` measures time as the sum of `board_status.seconds_by_step(run, now)` and tokens as the sum of `board_status.tokens_by_step(run)`, the helpers health's cost rule uses; the budget is the goal's `state["budget"]`, else the repo settings. Toy check: the board line and health's cost rule agree on a finished goal's minutes and tokens.
- `private.py check` (E5): prints `PRIVATE LIST: N patterns from <source>` or `PRIVATE LIST: none at <source>` and exits 1 on a broken list; never prints a pattern. Toy check.
- Scan placement: `goal.py pr` runs the scan immediately before `git push`, after every commit `pr` itself makes (touches sync, version bump), over base..HEAD plus the PR title and body; autorelease scans the release commit and notes before any push to the base or to `release/vX`; `release_pr.py` scans the release PR title and body. Toy check: a private name in the body only (not the branch) refuses.
- Unexpanded path: every scan note and message names the list as `~/.workflow-loop/private-names` or `$LOOP_PRIVATE_NAMES`, never an expanded absolute home path. Toy check: the PR body with no list holds no `$HOME` path.
- Old run records: a goal frozen before this change (no `size`, no `budget` in its record) reads as large (full depth) and uses the repo budget; nothing crashes on the board, in `flow.py` or in `guards.check_record`. Toy check with a record lacking both keys.
- Monitoring page: if `wiki.py prepare` marks docs/wiki/Monitoring.md stale for this goal's monitoring edits, the worker asks the operation session to widen touches (`goal.py touches delivery-prd --add docs/wiki/Monitoring.md --why ...`) instead of editing outside its touches; Delivery.md changes stay outside its Requirements section.
- Release note for this goal states the rollout: releases default to patch; a repo on `review_depth: condensed` now holds large goals to full; DEL-6 condensing applies only where the repo setting is `condensed` (this repo stays `full`).
- Spec R1 fixes: E1 re-sizing lives in `guards.cmd_touches` only (goal.py's `touches` already delegates there) and updates `state["size"]` with a log line; a `depth_override` still wins over the new size.
- Budget always carried (spec R2): `goal.py new` always writes `state["budget"] = {"minutes", "tokens"}`, with 0 meaning none set; the board prints `budget: none set` when both are 0 (so the gap shows and `goal.py set --budget-*` fixes it) and only the set half when one is 0. The DEL-8 row counts an explicit none as a carried budget. Toy checks: a repo with no budget keys, and one with only a time budget.
- Protection match: a release push counts as refused for protection only when its stderr holds `GH006`, `GH013`, `protected branch`, `through a pull request` or `rule violations`; any other refusal keeps today's three tries and `release_error`. Toy check: a non-matching refusal opens no release PR.
- Release PR naming: branch `release/vX`, title `Release vX (<slug>)`, body the release notes; all three are scanned before the push and the PR create.
- Defect rows: #134's row proves that after a protected refusal the VERSION and CHANGELOG land through the release PR, exactly one GitHub release is created at the base commit, and the wiki publish still runs; #154's row proves the loop merges the release PR itself when it can and records "needs the owner to approve and merge it" when it can't; #170's row proves a removed file gives a patch bump. Each seen failing on the old code first.
- Killed step: the crashed step counts exactly one failed try (the dead pid gives no STEP line and `record` counts it); the toy test asserts `tries` went up by one.
- "The goal says minor or major" means the operation session runs `goal.py set SLUG --bump minor|major --why ...` right after freezing a goal whose text or queue line says so; delivery never parses the goal text for a bump.
- Rollout text goes in a commit subject (which the CHANGELOG copies) and in the PR body's Result section, not in CHANGELOG by hand.
- docs-format dependency is an operation action: the PR body states it, and the worker's pr step prints `NOTE: DEL-6..DEL-9 headings not on <base>; merge after docs-format` when they are missing, so the operation session holds the merge.
- Byte budget: all new logic lives in the new modules; each existing script gains at most one import and one call per hook. If goal.py still passes 20,480 bytes, `cmd_queue` moves to `fit.py` (goal.py keeps a one-line delegate). The toy test checks `wc -c` under 20,480 for every script the goal touches.
- Private module path: the release scripts load `private.py` from the sibling skill (`../../workflow-delivery/scripts/private.py`, the sibling-path pattern goal.py already uses for milestone.py) through one loader in `autorelease.py`; merge.py, autorelease, wiki publish and release_pr.py all fail closed when it is missing or broken. Toy check with the module moved away: nothing merged, pushed or published.
- `board_budget.py` imports only `board_status`, never `live_board`.
- DEL-6 reading (provisional taste T2, pending the gate): the DEL-6 regression row and the PR body state the reading "small goals run condensed where review_depth is condensed; review_depth full (this repo's owner setting) holds every goal to full; the per-goal override beats both". The row tests by-size under `condensed` and the override under `full`.
- Spec R2 fixes: (a) `goal.py new` prints `WARN: the goal text says minor/major; run goal.py set SLUG --bump ...` when the goal text names minor or major and no bump is set (no parsing into state); (b) one rule in the docs: no list means the scan passes with a note, a broken list or a missing module means refuse; (c) `resume_at` order: all five recorded -> `pr`; idea and plan recorded, review not -> `build or review`; else the first of idea, plan, review, qa, ship whose record is not done or skipped; (d) `again` clears the per-step recorded result, depth and verdicts of the step and every later step, never `depth_override`, `size`, `budget` or `tries`; (e) the killed step's try is counted by today's path: the next `flow.py SLUG STEP` sees the dead pid, removes the `.job`, writes `.ran`, and `goal.py record` finds no STEP line and calls `guards.failed_try` (tries +1); the toy test reads `tries` after that record and before any `resume` (which resets tries); (f) `private.scan(top, None, texts)` scans only the texts (wiki publish); (g) `cmd_set` lives in guards.py beside `cmd_touches` (goal.py delegates in one line) and fit.py keeps pure functions with no guards import, so role -> fit adds no cycle; (h) second byte fallback: the pr body, docs-format NOTE and re-render logic live in fit.py, goal.py keeps one call.
- Spec R3 fixes (at the cap, verified by text, not re-reviewed): (1) one budget rule everywhere (board_budget, the flow.py token stop, health-facing text): a `budget` key present in the run record wins, even at 0 (0 = none set for that half); a key absent (a record from before this change) means the repo settings; toy check: a stored 0 while the repo now sets a budget still shows none set; (2) `cmd_queue`'s fallback destination is guards.py beside `cmd_set` and `cmd_touches` (same one-line delegate), applied up front, so fit.py stays pure; (3) `cmd_set` is built once, in guards.py (the numbered section's fit placement is superseded); (4) `record` stores `fit.verdicts(text)` from the reply text it already reads, for done and skipped results only; (5) `goal.py set --depth` or `--bump` after the affected step is recorded (plan/review for depth, release for bump) refuses with no change and points to `flow.py SLUG STEP --again`; (6) an OPEN release PR is retried by the next `merge.py SLUG` run (by the watch or the operation); the first run that can't merge records `release_error` at once and every rerun retries; (7) the DEL-7 toy test pins a background worker (a session worker's reply with no STEP line is refused with no try, which the plan states as that mode's behavior); (8) the E4 agreement check passes one fixed `at` to both calls and compares whole minutes; (9) each defect row's description quotes its issue's title.
- D1 push-site inventory (both voices): every push or post in the three skills runs the private scan first: `goal.py pr` (push and PR create), `guards.write_finding` (pushes HEAD; on a hit or a broken list it keeps the finding commit local and prints `NOTE: finding stays local: private-name scan`), `wiki.py prepare --commit` (push), wiki publish (E2), autorelease (push and release create), `release_pr.py` (push and PR create), `release.py cut` (push and draft release notes) and `merge.py` (before merging). A scan whose git call fails refuses (fail closed). Negative control in the toy test: every file in the three skills holding `"push"`, `"pr", "create"` or `"release", "create"` must also call the scan, so a new unscanned site fails the test.
- D2 missing list visible: no list file means the scan passes with the note (PR body, run log) and the live board's Issues shows `no private-name list: nothing is scanned (create ~/.workflow-loop/private-names; a file holding only comments says off on purpose)`; a list holding only comments is off on purpose: the note says so and the board shows no issue. Toy checks for both.
- D3 release identity: the release branch is `release/vX-<slug>` (one per goal; force-update only that branch on a restart); before `gh release create`, `gh release view vX` adopts an existing release at the same target (a crash after create) and records `release_error` naming it when it belongs elsewhere; a release PR that can't merge because another release moved VERSION is closed and restarted with the next version. Toy checks: two goals releasing on one protected fake base get two versions and one release each; a crash after create is adopted on the rerun. The same reconcile applies to autorelease's direct path.
- D4 merge hold: `merge.py` refuses (records `release_error`, nothing merged) while a criterion row this goal adds names a requirement ID that no page in the wiki folder on origin/base names; this is the enforced form of the docs-format dependency (the pr NOTE stays as a hint). Toy check.
- D5 token accounting: `flow.py` adds each attempt's tokens to the step's total instead of replacing it, so failed tries and `--again` reruns count against the budget. Toy check: two attempts of one step sum.
- D6 budget semantics, stated in the delivery and monitoring docs: the token budget is a spending limit (no new step starts at or over it); the time budget is advisory (the board flags OVER time, nothing stops).
- D7 resume context: the resume message, mend's resume prompt and `goal.py show` give `resume_at` plus the worktree's uncommitted file count and HEAD short sha, so a resumed build reconciles partial edits. Toy check.
- D8 session-mode resume: a session worker killed mid-step keeps its records; `flow.py` on a recorded step refuses ALREADY_RECORDED; asking the unrecorded step again prints IN SESSION; a reply without a STEP line is refused with no try. Toy check beside the background-worker one.
- D9 protection detection: release asks `gh api repos/{owner}/{repo}/rules/branches/{base}` first and takes the release PR path up front on a `pull_request` rule; a 403/404 or no rule falls back to the stderr match. fakegh serves the endpoint. Toy check.
- D10 module split: `fit.py` holds decisions (size_of, depth_for, budget_of, resume_at, again); new `prbody.py` holds presentation (pr_body, verdicts, regen_warnings). Both pure, no guards import.
- D11 build-vs-adopt recorded in the design notes of the PR body: gitleaks/trufflehog not adopted (stdlib-only rule, no install on consumer repos, the list stays outside the repo); release-please/changesets not adopted (Node/Action dependency, conventional-commit contract, the loop already owns version, changelog and wiki).
- Supersession (later lines win): D3's `release/vX-<slug>` replaces the `release/vX` name in "Release PR naming" and section 4; D4's merge hold replaces the "operation action" NOTE as the enforced dependency; Spec R3 (2) and (3) place `cmd_queue` and `cmd_set` in guards.py, replacing the fit.py placements in section 1 and "Byte budget"; D10 moves `pr_body`, `verdicts` and `regen_warnings` from fit.py to prbody.py (section 1 and Spec R2 (h) read prbody.py); Spec R3 (1) is the budget rule that "One time rule (E4)" and "Old run records" follow.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:dx -->
- X1 (CAP4, write_finding channel): when the scan refuses a finding's push (hit, broken list, missing module), `guards.write_finding` keeps the commit local, exits non-zero from the calling command, records `finding_error` (place and list line, never text) on the run record, and the live board's Issues lists it with the fix. Toy check.
- X2 error contract: every new refusal ends with a stable code in the existing `(CODE)` style and puts the fix on its first or last line, states side effects (nothing pushed, or partial with what), and names caller-safe context (list source unexpanded, budget source, base ref). Codes: PRIVATE_NAME, PRIVATE_LIST, PRIVATE_MODULE, FINDING_LOCAL, ALREADY_RECORDED, SET_AFTER_RECORD, BUDGET_TOKENS, RELEASE_PR_BLOCKED, RELEASE_VERSION_MISMATCH, RELEASE_EXISTS, REQUIREMENT_MISSING, BIND_SELF_UNSET. delivery and release `references/commands.md` each carry a codes table with anchors. PRIVATE_MODULE names the sibling path it looked for and the fix (reinstall or put workflow-delivery beside workflow-release), with the import error text as context. Toy test greps each code in its refusal.
- X3 PRIVATE_NAME: the scan reads every commit's patch and message from base to HEAD (`git log -p`), not only the net diff, so a name added then removed in a later commit still refuses; each hit names its place and the list line number (never the text or pattern); the fix line gives the non-interactive squash (`git reset --soft $(git merge-base HEAD <base>) && git commit -m "<goal>"`, then `goal.py pr SLUG`) and the false-positive route (edit that line of the list). Toy check: a name added then removed in a later commit refuses.
- X4 release_error lines carry the release PR url and number, the owner's command (`gh pr merge <n> --merge`, then `merge.py SLUG`), side effects (branch pushed, PR open: partial) and a try count stored as `release_tries` and shown on the board.
- X5 the merge hold (D4) names the missing requirement IDs and the fix (merge the goal that adds their text, then `merge.py SLUG`), code REQUIREMENT_MISSING.
- X6 `sessions.py bind SLUG self` with `CLAUDE_CODE_HOST_SESSION_ID` unset is a usage error before any work: exit 2, BIND_SELF_UNSET, names the variable, fix `sessions.py bind SLUG <ID>`. Toy check.
- X7 the token stop names spent and limit, which budget applied (run record or repo settings), and the fix `goal.py set SLUG --budget-tokens N --why ...`, code BUDGET_TOKENS.
- X8 `resume_at` always returns a step name: with idea and plan recorded and review not, it returns `build` when no commit landed on the branch after the plan record, else `review`; every resume message prints the exact next command (`flow.py SLUG <step>`). Supersedes the "build or review" value in Spec R2 (c). Toy check for both cases.
- X9 delivery `references/commands.md` maps `--budget-minutes`/`--budget-tokens` to `time_budget_minutes`/`token_budget` in one table (flags not renamed).
- X10 the regen WARN ends with its action: `update or delete <script> in this goal, or ask the operation session to widen touches`.
- X11 delivery `references/commands.md` shows copy-paste examples: a private-names file and a comments-only "off" file, `private.py check` output, a `goal.py set` line, a `flow.py SLUG STEP --again` line, and the budget line in each state (none set, one half, OVER).
- X12 the docs say that `resume` resets the goal's tries (so try counts read before a resume).
- X13 the build follows the CEO Supersession line; sections 1 to 4 are read in their superseded form.
<!-- /autoplan-accepted:dx -->

<!-- autoplan-accepted:eng -->
- G1 (critical, lost update): `goal.py set` and the E1 re-size write `depth_override`, `bump`, `budget` and the widened `size` to the operation sidecar `<runs>/<slug>.extra.json` under its flock (extending the sidecar with a `set` map), never to the run record; every reader (depth_for, auto_need, board_budget, the flow.py token stop, set's own after-record check) merges sidecar over run record. Toy check: a `set` racing a worker `record` keeps both.
- G2: the scan reads only added lines (`+`, not `+++` headers, not removed or context lines) of each commit's patch plus every commit message, so a goal that removes a leaked name is not refused; when the branch is already on origin the PRIVATE_NAME fix says the owner must decide (the loop never force-pushes). Toy checks: removed-line-only passes; added-then-removed refuses; message-only hit refuses.
- G3: every write to GitHub in the three skills is a scan site: `git push`, and gh `create`, `edit`, `comment`, `merge`, and `api` with POST/PATCH; the toy control is an AST check per call site (the enclosing function must call the scan), so a second unscanned push in one file (release.py has two) fails it. `github:` surfaces in touches don't change this.
- G4: release_pr reads `gh pr view --json mergeStateStatus,reviewDecision`: required checks pending is a waiting state (`release_pr_waiting`, no error, retried by the next merge.py run); review required or blocked is the owner error (X4); the loop never passes `--admin`. Toy checks for both states.
- G5: the release targets the release PR's `mergeCommit.oid`, and VERSION is checked at that commit; a closed-and-restarted release PR regenerates VERSION and CHANGELOG on the new base.
- G6: byte fallbacks beyond goal.py: if guards.py nears 20,480 bytes, `cmd_set`, `cmd_queue` and `cmd_touches` move to a new `guards_ops.py` (goal.py delegates); release.py's cut keeps one scan call through the loader; toy tests split by area (depth, release, resume, budget, private, defects), each under 20,480 bytes and each taking a case argument like test-rows.sh.
- G7: private.py compiles patterns once, skips binary patches, caps each scanned line at 4,096 characters and stops at a 60 s overall limit, which refuses (PRIVATE_LIST, timeout named); `LOOP_PRIVATE_NAMES` is a file path only.
- G8: the D4 merge hold applies only when the base has the wiki folder and some page already uses the requirement ID's prefix; otherwise merge.py prints an advisory NOTE and merges.
- G9: the plan record stores HEAD's sha as `plan_head`, and X8's build-vs-review choice falls back to `build` when it is missing; `--again` refuses while the step's job pid is alive and clears the step's `.ran` and `.asked` markers; a widened touch that makes a goal large after review was recorded condensed shows on the board and in the PR body with `flow.py SLUG review --again`.
- G10: in size_of, files at the repo root are no area, and VERSION and CHANGELOG are never areas.
- G11: tests also cover: `--again` keeps accumulated tokens; a message-only private hit; bind self with a set id; comments-only list vs missing list on the board; gh shim answers for mergeStateStatus and a release view at another target.
- G12: `github:<surface>` matches the six-surface allowlist exactly and is never treated as a filesystem path in size or regen logic.
- G13: one spent-token rule in the flow.py stop and board_budget: the sum of per-step values when any exist, else `tokens.total` (written by background workers); an agreement test checks both.
- G14: dev/toy/fakegh is not edited (it maps to the Documentation page, outside touches); the new toy tests wrap it with a test-local gh shim for the rules endpoint, mergeStateStatus and release view, and simulate a protected base with a pre-receive hook in the toy origin that rejects pushes to main with a GH006 message. Supersedes D9's "fakegh serves the endpoint".
- G15 (regression rule): test-release.sh:116 (new file -> minor) and :120 (removed file -> NEED ask) and test-autorelease.sh:69 (breaking -> major) are rewritten to the new rule (patch, reason named) as intentional changes listed in the PR body; prbody keeps the `## Result` heading and `Skill flow:` lines the existing tests read; any existing test that reruns a recorded flow step adds `--again`; the full land and nightly lanes pass.
- G16: new toy files carry a `# reads:` header that check-reads.sh accepts, use a temp HOME and unset LOOP_PRIVATE_NAMES.
- G17: heavy cases (two-goal release race, both kill-and-resume cases) are nightly rows; each of DEL-5..DEL-9 keeps at least one land row.
- G18: flow.py's depth prompt and the check_record depth check read the goal's decided depth from the run record merged with the sidecar.
- G19: release scripts read per-goal settings (bump) through delivery's fit via the same sibling loader as private.py, never by parsing the sidecar themselves.
- Test plan artifact: the eng review test plan (2026-11-10) in the private project folder (lists every case above).
<!-- /autoplan-accepted:eng -->
## Review record

(autoplan appends below)

### Phase 0 (intake)

UI scope: no (one bare "component" match, no visual noun, no rendered file). DX scope: yes (terms require x1,
SKILL.md x2 = 3 matches over the threshold of 2; also a developer tool and agent-primary). Outside voice preflight:
Codex ready. Run id loop-delivery-prd-20261110-021514. Phase 0 init reused from the parent session.

### Phase 1 (CEO) accepted obligations

<!-- autoplan-accepted:ceo -->
- Dependency on docs-format: the DEL-6..DEL-9 requirement text reaches docs/wiki/Delivery.md only with goal docs-format (main's page holds DEL-1..DEL-5). This goal writes no requirement text. Before `pr` it merges origin/main; when docs-format is on the base, it re-renders the Delivery Tests table so the DEL-5..DEL-9 rows sit under their requirement headings; when it is not, the PR body says the DEL-6..DEL-9 rows show under Other until docs-format lands (the mechanism is the pr NOTE below). Verify: `tests.py list --markdown` groups every new row under DEL-5..DEL-9 once docs-format is on the base.
- Re-size on widened touches (E1): when `goal.py touches SLUG --add PATH` widens a goal's touches, `fit.size_of` is recomputed over the frozen done lines and all touches; a small goal can become large, never the reverse; the change is logged with its why. Toy check: a small goal widened to a second area reports large and its decided depth is full under `condensed`.
- Wiki publish scan (E2): `wiki.py` publish runs `private.scan` over the text of every page in the wiki folder (hits named `wiki:<page>:<line>`) before it clones or pushes; a hit records `wiki_error` naming the page and line and publishes nothing. Toy check: a planted name in an untouched wiki page stops the publish.
- Broken list fails closed (E3): a private-name list that exists but can't be read, or holds a line that is not a valid regex, makes every scan refuse (goal.py pr: no try used, exit 2; merge.py, autorelease and wiki publish: refuse or record the error, nothing pushed or merged), naming the file and line number, never the pattern. Toy check with an invalid regex line.
- One time rule (E4): `board_budget.line` measures time as the sum of `board_status.seconds_by_step(run, now)` and tokens as the sum of `board_status.tokens_by_step(run)`, the helpers health's cost rule uses; the budget is the goal's `state["budget"]`, else the repo settings. Toy check: the board line and health's cost rule agree on a finished goal's minutes and tokens.
- `private.py check` (E5): prints `PRIVATE LIST: N patterns from <source>` or `PRIVATE LIST: none at <source>` and exits 1 on a broken list; never prints a pattern. Toy check.
- Scan placement: `goal.py pr` runs the scan immediately before `git push`, after every commit `pr` itself makes (touches sync, version bump), over base..HEAD plus the PR title and body; autorelease scans the release commit and notes before any push to the base or to `release/vX`; `release_pr.py` scans the release PR title and body. Toy check: a private name in the body only (not the branch) refuses.
- Unexpanded path: every scan note and message names the list as `~/.workflow-loop/private-names` or `$LOOP_PRIVATE_NAMES`, never an expanded absolute home path. Toy check: the PR body with no list holds no `$HOME` path.
- Old run records: a goal frozen before this change (no `size`, no `budget` in its record) reads as large (full depth) and uses the repo budget; nothing crashes on the board, in `flow.py` or in `guards.check_record`. Toy check with a record lacking both keys.
- Monitoring page: if `wiki.py prepare` marks docs/wiki/Monitoring.md stale for this goal's monitoring edits, the worker asks the operation session to widen touches (`goal.py touches delivery-prd --add docs/wiki/Monitoring.md --why ...`) instead of editing outside its touches; Delivery.md changes stay outside its Requirements section.
- Release note for this goal states the rollout: releases default to patch; a repo on `review_depth: condensed` now holds large goals to full; DEL-6 condensing applies only where the repo setting is `condensed` (this repo stays `full`).
- Spec R1 fixes: E1 re-sizing lives in `guards.cmd_touches` only (goal.py's `touches` already delegates there) and updates `state["size"]` with a log line; a `depth_override` still wins over the new size.
- Budget always carried (spec R2): `goal.py new` always writes `state["budget"] = {"minutes", "tokens"}`, with 0 meaning none set; the board prints `budget: none set` when both are 0 (so the gap shows and `goal.py set --budget-*` fixes it) and only the set half when one is 0. The DEL-8 row counts an explicit none as a carried budget. Toy checks: a repo with no budget keys, and one with only a time budget.
- Protection match: a release push counts as refused for protection only when its stderr holds `GH006`, `GH013`, `protected branch`, `through a pull request` or `rule violations`; any other refusal keeps today's three tries and `release_error`. Toy check: a non-matching refusal opens no release PR.
- Release PR naming: branch `release/vX`, title `Release vX (<slug>)`, body the release notes; all three are scanned before the push and the PR create.
- Defect rows: #134's row proves that after a protected refusal the VERSION and CHANGELOG land through the release PR, exactly one GitHub release is created at the base commit, and the wiki publish still runs; #154's row proves the loop merges the release PR itself when it can and records "needs the owner to approve and merge it" when it can't; #170's row proves a removed file gives a patch bump. Each seen failing on the old code first.
- Killed step: the crashed step counts exactly one failed try (the dead pid gives no STEP line and `record` counts it); the toy test asserts `tries` went up by one.
- "The goal says minor or major" means the operation session runs `goal.py set SLUG --bump minor|major --why ...` right after freezing a goal whose text or queue line says so; delivery never parses the goal text for a bump.
- Rollout text goes in a commit subject (which the CHANGELOG copies) and in the PR body's Result section, not in CHANGELOG by hand.
- docs-format dependency is an operation action: the PR body states it, and the worker's pr step prints `NOTE: DEL-6..DEL-9 headings not on <base>; merge after docs-format` when they are missing, so the operation session holds the merge.
- Byte budget: all new logic lives in the new modules; each existing script gains at most one import and one call per hook. If goal.py still passes 20,480 bytes, `cmd_queue` moves to `fit.py` (goal.py keeps a one-line delegate). The toy test checks `wc -c` under 20,480 for every script the goal touches.
- Private module path: the release scripts load `private.py` from the sibling skill (`../../workflow-delivery/scripts/private.py`, the sibling-path pattern goal.py already uses for milestone.py) through one loader in `autorelease.py`; merge.py, autorelease, wiki publish and release_pr.py all fail closed when it is missing or broken. Toy check with the module moved away: nothing merged, pushed or published.
- `board_budget.py` imports only `board_status`, never `live_board`.
- DEL-6 reading (provisional taste T2, pending the gate): the DEL-6 regression row and the PR body state the reading "small goals run condensed where review_depth is condensed; review_depth full (this repo's owner setting) holds every goal to full; the per-goal override beats both". The row tests by-size under `condensed` and the override under `full`.
- Spec R2 fixes: (a) `goal.py new` prints `WARN: the goal text says minor/major; run goal.py set SLUG --bump ...` when the goal text names minor or major and no bump is set (no parsing into state); (b) one rule in the docs: no list means the scan passes with a note, a broken list or a missing module means refuse; (c) `resume_at` order: all five recorded -> `pr`; idea and plan recorded, review not -> `build or review`; else the first of idea, plan, review, qa, ship whose record is not done or skipped; (d) `again` clears the per-step recorded result, depth and verdicts of the step and every later step, never `depth_override`, `size`, `budget` or `tries`; (e) the killed step's try is counted by today's path: the next `flow.py SLUG STEP` sees the dead pid, removes the `.job`, writes `.ran`, and `goal.py record` finds no STEP line and calls `guards.failed_try` (tries +1); the toy test reads `tries` after that record and before any `resume` (which resets tries); (f) `private.scan(top, None, texts)` scans only the texts (wiki publish); (g) `cmd_set` lives in guards.py beside `cmd_touches` (goal.py delegates in one line) and fit.py keeps pure functions with no guards import, so role -> fit adds no cycle; (h) second byte fallback: the pr body, docs-format NOTE and re-render logic live in fit.py, goal.py keeps one call.
- Spec R3 fixes (at the cap, verified by text, not re-reviewed): (1) one budget rule everywhere (board_budget, the flow.py token stop, health-facing text): a `budget` key present in the run record wins, even at 0 (0 = none set for that half); a key absent (a record from before this change) means the repo settings; toy check: a stored 0 while the repo now sets a budget still shows none set; (2) `cmd_queue`'s fallback destination is guards.py beside `cmd_set` and `cmd_touches` (same one-line delegate), applied up front, so fit.py stays pure; (3) `cmd_set` is built once, in guards.py (the numbered section's fit placement is superseded); (4) `record` stores `fit.verdicts(text)` from the reply text it already reads, for done and skipped results only; (5) `goal.py set --depth` or `--bump` after the affected step is recorded (plan/review for depth, release for bump) refuses with no change and points to `flow.py SLUG STEP --again`; (6) an OPEN release PR is retried by the next `merge.py SLUG` run (by the watch or the operation); the first run that can't merge records `release_error` at once and every rerun retries; (7) the DEL-7 toy test pins a background worker (a session worker's reply with no STEP line is refused with no try, which the plan states as that mode's behavior); (8) the E4 agreement check passes one fixed `at` to both calls and compares whole minutes; (9) each defect row's description quotes its issue's title.
- D1 push-site inventory (both voices): every push or post in the three skills runs the private scan first: `goal.py pr` (push and PR create), `guards.write_finding` (pushes HEAD; on a hit or a broken list it keeps the finding commit local and prints `NOTE: finding stays local: private-name scan`), `wiki.py prepare --commit` (push), wiki publish (E2), autorelease (push and release create), `release_pr.py` (push and PR create), `release.py cut` (push and draft release notes) and `merge.py` (before merging). A scan whose git call fails refuses (fail closed). Negative control in the toy test: every file in the three skills holding `"push"`, `"pr", "create"` or `"release", "create"` must also call the scan, so a new unscanned site fails the test.
- D2 missing list visible: no list file means the scan passes with the note (PR body, run log) and the live board's Issues shows `no private-name list: nothing is scanned (create ~/.workflow-loop/private-names; a file holding only comments says off on purpose)`; a list holding only comments is off on purpose: the note says so and the board shows no issue. Toy checks for both.
- D3 release identity: the release branch is `release/vX-<slug>` (one per goal; force-update only that branch on a restart); before `gh release create`, `gh release view vX` adopts an existing release at the same target (a crash after create) and records `release_error` naming it when it belongs elsewhere; a release PR that can't merge because another release moved VERSION is closed and restarted with the next version. Toy checks: two goals releasing on one protected fake base get two versions and one release each; a crash after create is adopted on the rerun. The same reconcile applies to autorelease's direct path.
- D4 merge hold: `merge.py` refuses (records `release_error`, nothing merged) while a criterion row this goal adds names a requirement ID that no page in the wiki folder on origin/base names; this is the enforced form of the docs-format dependency (the pr NOTE stays as a hint). Toy check.
- D5 token accounting: `flow.py` adds each attempt's tokens to the step's total instead of replacing it, so failed tries and `--again` reruns count against the budget. Toy check: two attempts of one step sum.
- D6 budget semantics, stated in the delivery and monitoring docs: the token budget is a spending limit (no new step starts at or over it); the time budget is advisory (the board flags OVER time, nothing stops).
- D7 resume context: the resume message, mend's resume prompt and `goal.py show` give `resume_at` plus the worktree's uncommitted file count and HEAD short sha, so a resumed build reconciles partial edits. Toy check.
- D8 session-mode resume: a session worker killed mid-step keeps its records; `flow.py` on a recorded step refuses ALREADY_RECORDED; asking the unrecorded step again prints IN SESSION; a reply without a STEP line is refused with no try. Toy check beside the background-worker one.
- D9 protection detection: release asks `gh api repos/{owner}/{repo}/rules/branches/{base}` first and takes the release PR path up front on a `pull_request` rule; a 403/404 or no rule falls back to the stderr match. fakegh serves the endpoint. Toy check.
- D10 module split: `fit.py` holds decisions (size_of, depth_for, budget_of, resume_at, again); new `prbody.py` holds presentation (pr_body, verdicts, regen_warnings). Both pure, no guards import.
- D11 build-vs-adopt recorded in the design notes of the PR body: gitleaks/trufflehog not adopted (stdlib-only rule, no install on consumer repos, the list stays outside the repo); release-please/changesets not adopted (Node/Action dependency, conventional-commit contract, the loop already owns version, changelog and wiki).
- Supersession (later lines win): D3's `release/vX-<slug>` replaces the `release/vX` name in "Release PR naming" and section 4; D4's merge hold replaces the "operation action" NOTE as the enforced dependency; Spec R3 (2) and (3) place `cmd_queue` and `cmd_set` in guards.py, replacing the fit.py placements in section 1 and "Byte budget"; D10 moves `pr_body`, `verdicts` and `regen_warnings` from fit.py to prbody.py (section 1 and Spec R2 (h) read prbody.py); Spec R3 (1) is the budget rule that "One time rule (E4)" and "Old run records" follow.
<!-- /autoplan-accepted:ceo -->

### Phase 1 (CEO) review

Methodology: plan-ceo-review read in full from the autoplan methodology artifact
(autoplan-ceo-methodology-SlOMSj/methodology.md, sha 58d771ef…): ranges 1-600, 601-1200, 1201-1800, 1801-2257 (EOF,
2257 lines). Skip-listed sections loaded only. Mode: SELECTIVE EXPANSION (autoplan override).

#### Pre-review system audit

- Branch loop/delivery-prd, 2 commits over main (goal file, design). No stash. No TODOS.md in the repo (follow-ups live
  as GitHub issues and FINDINGS.md). Base main at e145b43 (v0.21.0).
- Running goals that overlap: docs-format (review; touches docs/wiki, workflow-docs, workflow-regression, regression.tsv,
  dev/toy) carries the DEL-1..DEL-9 page text (commit c2ada09, branch loop/docs-format only); lane-control (build;
  moves ~175 lines out of role.py into lane.py, edits goal.py 4 lines); estimate-model (review; edits live_board.py 34
  lines, adds board_status.size_of and graph.area/size, a second "goal size" notion).
- Retrospective: loop-guards (v0.21.0) added guards.py, no-try refusals, resume, touches; review-depth added
  role.depth_of + DEPTH lines. This plan extends both rather than replacing them.
- Taste calibration: good references guards.py (one module per concern, no-try refusals with codes), autorelease.py
  (each step records itself, retry repeats only what did not finish). Avoid: goal.py's size pressure (19,415 bytes) and
  live_board.py's long lambdas.
- Landscape: Aside/WebSearch skipped for this internal tooling (design premise 6 already skipped it); proceeding with
  in-distribution knowledge. Layer 1: release-please/changesets for release PRs, gitleaks/trufflehog for secret scans,
  CI budget meters. Layer 3: a loop that already owns version, changelog and wiki can do the release PR in ~200 lines
  stdlib; a private-name scan must keep its list outside the repo, which hosted scanners can't guarantee.
- Prior learning applied: bg-job-sigint-ignored (confidence 9/10, 2026-11-10): the kill-and-resume toy test must start the
  stand-in agent with Popen start_new_session and killpg, never `&` from a non-interactive shell.

#### 0A Premise challenge

Real problem: the loop pays full review for two-line goals, can mint a silent major bump (#170) and fails releases on
protected bases (#134/#154), reruns a recorded step after a crash, shows no budget while a goal runs, and pushes with no
private-name scan. The plan solves each directly, not a proxy. Do-nothing cost: wrong majors on consumer repos, stalled
releases on protected repos, private names on GitHub.

| premise | claim | receipt | verdict |
|---|---|---|---|
| P1 | review_depth is one repo-wide switch read from the base branch | skills/workflow-delivery/scripts/role.py:135 | verified |
| P2 | auto_need maps a removed file to ask and autorelease maps ask to major | skills/workflow-release/scripts/release.py:153, skills/workflow-release/scripts/autorelease.py:63 | verified |
| P3 | autorelease pushes straight to the base, 3 tries, no PR path | skills/workflow-release/scripts/autorelease.py:128 | verified |
| P4 | a dead step pid writes no STEP line and record counts a failed try | skills/workflow-delivery/scripts/flow.py:244, skills/workflow-delivery/scripts/goal.py:315 | verified |
| P5 | budgets are repo settings read after the fact by health | skills/workflow-health/scripts/cost.py:65, skills/workflow-delivery/scripts/flow.py:146 | verified |
| P6 | goal.py pr and merge.py push or merge with no scan | skills/workflow-delivery/scripts/goal.py:378, skills/workflow-release/scripts/merge.py:68 | verified |
| P7 | DEL-6..DEL-9 text is on main's Delivery page | docs/wiki/Delivery.md:33 (DEL-1..5 only); c2ada09 on loop/docs-format | FALSE: dependency |
| P8 | goal.py has room for the hooks | goal.py 19,415 bytes (wc -c) vs 20,480 | tight: fallback moves needed |
| P9 | flow.py records a step's tokens per attempt | skills/workflow-delivery/scripts/flow.py:260 replaces, not adds | FALSE: undercount on reruns |
| P10 | other push sites are covered | skills/workflow-delivery/scripts/guards.py:187 (finding pushes HEAD), skills/workflow-release/scripts/wiki.py:68, skills/workflow-release/scripts/release.py:352 | FALSE: uncovered sites |

unverified=0.

#### 0B Existing code leverage

| sub-problem | existing code | plan reuses? |
|---|---|---|
| no-try refusals | guards.refuse_no_try, codes (guards.py:95) | yes |
| operation-only commands | guards.operation_only (guards.py:259) | yes (cmd_set beside cmd_touches) |
| base-branch depth setting | role.depth_of (role.py:135) | yes, extended with state |
| step start / depth reset | role.begin (role.py:111) | yes |
| crash trace | flow.py .job pid + .ran, session .asked | yes |
| goal time and tokens | board_status.seconds_by_step / tokens_by_step (board_status.py:52,66) | yes after E4 |
| release bump arithmetic | release.bump (release.py:187) | yes |
| retrying release | autorelease.finish staged fields (autorelease.py:157) | yes, release_pr adds stages |
| sibling skill loading | goal.py milestone hook (goal.py:399) | yes for private.py |
| fake GitHub | dev/toy/fakegh | yes; needs rules endpoint, release view |

REALITY: premise-table finding 10 premises, 7 verified, 3 false (DEL-6..9 text not on main, token undercount, uncovered push sites) unverified=0 skills/workflow-delivery/scripts/flow.py:260
REALITY: already-done pass git log origin/main --since=2026-11-09 on the three skills shows only loop-guards work; no private scan, resume_at, budget or release PR exists e145b43
REALITY: surface-check finding goal.py set and flow.py --again are new (planned); sessions.py bind takes SLUG ID so `self` is a value, not a flag; regression.py red exists; gh rules endpoint needs fakegh support skills/workflow-monitoring/scripts/sessions.py:7
REALITY: binding-decisions pass the decision search --scope branch returned no entries; the design's premises 1-6 are the binding source and are kept except where a voice challenges them (UC1-UC3) .loop/goals/delivery-prd.design.md:76
REALITY: numbers finding goal.py 19,415 [measured: wc -c], role.py 18,601 [measured: wc -c], live_board.py 18,646 [measured: wc -c], release.py 18,606 [measured: wc -c]; headroom 1,065 bytes on goal.py; live_board and role change under other goals [re-measure before gate] skills/workflow-delivery/scripts/goal.py:1
REALITY: deferred-asks finding #170 asked that ask stops and asks the owner; the frozen DEL-5 replaces that with patch by default and no question (left out on purpose); #129 asked for a draft setting as an alternative, left out (docs follow the automatic path); #117 fully covered .loop/goals/delivery-prd.md:11
REALITY: pr-count pass no ship-policy.json; one PR for the goal as the loop opens; the release PR is the loop's own runtime artifact, not a second change PR skills/workflow-delivery/scripts/goal.py:391

#### 0C Dream state

```
  CURRENT STATE                  THIS PLAN                           12-MONTH IDEAL
  one depth switch; ask->major;  depth by size + override; patch      risk-aware depth tuned by escaped-defect data;
  direct push only; reruns on    default; release PR on protected     releases a coordinator serializes; resume from
  crash; budget after the fact;  bases; ALREADY_RECORDED + resume_at; artifact checkpoints; budgets as spend limits
  no private scan                budget on the board; scan at every   with cost per delivered goal; one publication
                                 push site in three skills            boundary for every outbound path
```

#### 0D / 0E / 0F / 0G

- 0D approach: A (patch callers), B (new modules + hooks, recommended), C (setup-level model). Auto: B (P1/P5).
- 0E mode: SELECTIVE EXPANSION (override). Mode: SELECTIVE EXPANSION; approved decisions: approach B. Count: about 23
  files (5 new, 18 edited) [estimated], over the 15-file rule's SCOPE REDUCTION threshold; most edits are one-line hooks.
- HOLD checks inside SELECTIVE: complexity (4 new modules, >8 files) is justified by the 20 KB rule and two parallel
  goals; minimum change set is the plan; invariants kept (frozen done lines, Delivery requirement text untouched).
- 0G cherry-picks: E1-E5 accepted, E6-E7 deferred, E8 skipped (see the CEO plan file). 10x: one publication boundary,
  release identity, measured depth.

#### 0H Spec review loop

3 launches (cap). R1 6/10 FAIL (4 blocking), R2 7/10 FAIL (1 blocking), R3 7/10 FAIL (1 blocking). Fixes applied each
round; round-3 items verified by text: issues verified: 9 of 9; spec not re-verified. Metrics appended to
spec-review.jsonl (iterations 3, found 35, reviewer-confirmed fixed 0, remaining 10, score 7). Document approval: auto
A (approve these documents, continue to 0I).

#### 0I Temporal interrogation

```
  HOUR 1 (foundations):  fit.py/prbody.py/private.py pure functions; byte budget; cmd_queue + cmd_set to guards first
  HOUR 2-3 (core):       resume_at order, again scope, ALREADY_RECORDED in flow.py; auto_need patch; budget key rule
  HOUR 4-5 (integration):release_pr state machine against fakegh (rules endpoint, release view, PR states);
                         private loader from release scripts; merge.py hold on missing requirement IDs
  HOUR 6+ (tests):       kill-and-resume (start_new_session/killpg), session-mode resume, two-goal release race,
                         red-on-old-code for 11 rows, Tests table render after docs-format
```
Effort: human ~4-5 days / CC ~3-4 hours. Feasibility blockers: docs-format must land for done line 6 (D4 hold);
goal.py headroom (fallbacks named).

#### Dual voices (Step 0.5)

Native CEO subagent: completed (INPUT hash e84e6ede… matches the snapshot). Codex (gpt-6-astra, plan-review frontier):
completed, OUTSIDE_STATUS completed, FINDINGS P0.

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Premises valid?                   no      no     CONFIRMED (DEL-6 reading, patch-only guard)
  2. Right problem to solve?           yes*    yes*   CONFIRMED (*reframe: unattended trust first)
  3. Scope calibration correct?        no      no     DISAGREE on remedy (Claude: split; Codex: re-plan boundaries)
  4. Alternatives sufficiently explored?no     no     CONFIRMED (risk sizing; adopt vs build)
  5. Competitive/market risks covered? no      no     CONFIRMED (invest in governance, not commodity infra)
  6. 6-month trajectory sound?         no      no     CONFIRMED (silent breaking patch; dependency hold)
```

Dispositions (finding -> decision):
- Both: uncovered push sites / missing list silent (Codex 1 Critical, Claude 2.5) -> ACCEPT D1 push-site inventory with
  grep control; D2 missing list visible on the board (fail-open kept: taste T5).
- Both: dependency hold is only a NOTE (Codex 3, Claude 3.2) -> ACCEPT D4 merge.py hold.
- Both: DEL-6 inert under full (Codex 4, Claude 2.1) -> USER CHALLENGE UC1.
- Both: size ignores risk (Codex 4, Claude 4.3) -> USER CHALLENGE UC2.
- Both: patch with no breaking guard (Codex 7, Claude 2.2) -> USER CHALLENGE UC3.
- Both: time budget undefined (Codex 5, Claude 3.4) -> ACCEPT D6 (token = limit, time = advisory, stated).
- Codex 2 release concurrency/crash -> ACCEPT D3 release identity per goal + reconcile.
- Codex 5 token undercount -> ACCEPT D5 accumulate per attempt.
- Codex 6 resume partial effects -> ACCEPT D7 resume shows dirty count + HEAD; base-merge invalidation deferred.
- Codex 8 fit.py cohesion -> ACCEPT D10 split prbody.py; packaging note (release already reads delivery run records).
- Codex 9 resume evidence narrow -> ACCEPT D8 session-mode resume check.
- Claude 2.4 protection from stderr -> ACCEPT D9 rules endpoint first.
- Claude 4.1/4.2 adopt gitleaks / release-please -> REJECT with recorded rationale D11 (stdlib only; list must stay
  outside the repo; Node/Action dependency; the loop owns version/changelog/wiki).
- Claude 1.1 split the goal -> TASTE T3 (single model; frozen goal): keep one goal.
- Claude 2.3 release PR self-merge opt-in -> TASTE T4 (single model; #134/#154 ask the loop to merge): keep merging.
- Claude 3.3 byte cap layout -> already accepted (cmd_queue/cmd_set to guards up front).

#### Review sections

##### Section 1: Architecture

Current scope: SELECTIVE EXPANSION (override); approach B; accepted E1-E5, D1-D11; deferred E6, E7; skipped E8; pending
UC1-UC3, T3-T5 for the gate.

```
  workflow-delivery                         workflow-release                    workflow-monitoring
  ┌──────────┐ hooks ┌────────┐            ┌───────────┐ loads ┌──────────┐    ┌────────────┐
  │ goal.py  │──────>│ fit.py │<─depth─────│ (none)    │       │private.py│    │live_board  │
  │ new/set/ │       │size,   │            │ merge.py ─┼──────>│(delivery)│    │ ├ depth    │
  │ record/pr│──────>│depth,  │            │ autorel. ─┼──────>│ scan,    │    │ └ budget ──┼─> board_budget.py
  └────┬─────┘       │budget, │            │ wiki.py  ─┼──────>│ check    │    └────────────┘     │ uses
       │             │resume, │            │ release.py┼──────>│          │                       v
       │ ──────────> │again   │            │ release_pr┼──────>└──────────┘            board_status.seconds_by_step
       │ prbody.py   └────────┘            └─────┬─────┘                               tokens_by_step
       │ (body, verdicts, regen)                 │ refused push (rules/stderr)
  guards.py: cmd_set, cmd_touches(+resize),      v
  cmd_queue, check_record(state), check_path     release_pr.py: release/vX-<slug> -> PR -> merge -> verify VERSION -> release
  flow.py: ALREADY_RECORDED, --again, budget,    (stages recorded: release_pr, release_pushed, release_url)
  tokens += per attempt
```

Data flows (four paths) for the scan: happy (no hit -> push); nil (no list -> pass + note + board issue); empty (list
of comments only -> disabled on purpose note); error (unreadable list, bad regex, module missing -> refuse, nothing
pushed). Release PR state machine:

```
  [pushed refused: protected] -> OPENED -> (merge ok) -> MERGED -> VERSION==vX? -> yes -> RELEASED
                                   |                                   no -> release_error (rerun reports same)
                                   +-> (can't merge) -> release_error "needs owner" -> rerun: OPEN retry | MERGED | CLOSED
                                   CLOSED -> clear release_pr, release_pushed -> restart (new version computed)
  Invalid: RELEASED -> anything (merge.py prints ALREADY released); two goals on one branch (branch carries the slug)
```

Coupling: release now loads a delivery module by sibling path (justified: release already reads delivery's run records;
fail closed when missing). Scaling: scans read base..HEAD diff once per push; a 10x larger diff is still seconds.
Single points of failure: the private list file (mitigated by E3/E5 and the board issue). Security: operation-only
`set` is advisory (LOOP_ROLE), accepted as the same boundary resume/touches use. Rollback: revert the release; repos
keep working without a list. Value test: `private.py check` and the board budget line are product observability, not
process artifacts. Findings: 3 (dependency hold, token undercount, release identity), all accepted (D3-D5).

##### Section 2: Error & Rescue Map

```
  METHOD/CODEPATH            | WHAT CAN GO WRONG                 | CLASS
  private.patterns           | list unreadable                   | OSError
                             | invalid regex line                | re.error
  private.scan               | git diff fails (bad base ref)     | CalledProcess (rc!=0)
  private loader (release)   | module missing / import error     | ImportError/OSError
  release_pr push            | refused (protection, non-ff)      | git rc!=0
  release_pr gh pr create    | gh auth / API error               | gh rc!=0
  release_pr gh pr merge     | required checks/review            | gh rc!=0
  release_pr verify          | VERSION on base != vX             | state mismatch
  create_release             | release already exists            | gh rc!=0
  rules endpoint             | 403/404 (no permission)           | gh rc!=0
  flow.py ALREADY_RECORDED   | record present                    | refusal (exit 2)
  goal.py set                | worker role / step recorded       | refusal
  board_budget.line          | record without budget / bad types | KeyError/TypeError
  wiki publish scan          | hit in a wiki page                | refusal

  CLASS               | RESCUED | ACTION                                   | USER SEES
  OSError list        | Y       | refuse, file + line, never pattern       | REFUSED ... PRIVATE_LIST
  re.error            | Y       | refuse naming line number                | REFUSED ... PRIVATE_LIST
  scan git failure    | Y       | refuse (fail closed), nothing pushed     | REFUSED with git stderr tail
  loader missing      | Y       | release_error / refuse, nothing merged   | Issues: release_error
  push refused        | Y       | protection -> release PR; else 3 tries   | release PR url / release_error
  gh create fail      | Y       | release_error, rerun resumes stage       | Issues
  merge blocked       | Y       | release_error "needs the owner"          | Issues
  VERSION mismatch    | Y       | release_error, no release                | Issues
  release exists      | Y       | adopt if same target, else release_error | RELEASED / Issues
  rules 403/404       | Y       | fall back to stderr match                | nothing
  ALREADY_RECORDED    | Y       | exit 2, no try, names resume_at          | REFUSED (no try used)
  set refusal         | Y       | no change, names fix                     | REFUSED
  budget missing key  | Y       | repo settings (absent) / none (0)        | budget line
  wiki hit            | Y       | wiki_error, nothing published            | Issues
```
GAPS: none after D1-D9 (scan git failure fail-closed added as an obligation).

##### Section 3: Security & Threat Model

- Private names leaking through an uncovered push (High likelihood before D1, High impact): mitigated by D1 inventory and
  grep control; residual: docs.py publish (workflow-docs) outside touches, deferred.
- Missing list (Med, High): visible board issue (D2); fail-closed rejected as taste T5.
- Regex DoS from a hostile list (Low: list is the owner's own file): bounded by line-by-line search; accepted.
- Hit output leaking the match (Med, High): hits print only place; obligation already recorded.
- A worker lowering its own depth or raising its budget (Med, Med): `set` operation-only (advisory LOOP_ROLE), base-branch
  config stays the hard line.
- Release PR self-merge routing around protection (Low-Med, Med): only where the ruleset allows the loop; T4.
- Injection: no shell=True added; gh/git argv lists. Audit: every set/scan refusal logged on the run record.

##### Section 4: Data Flow & Interaction Edge Cases

```
  INPUT(branch,diff,texts) -> VALIDATE(list loads) -> TRANSFORM(line-by-line regex) -> PERSIST(log hit places) -> OUTPUT(refuse|note)
    nil list -> note+board | empty list -> disabled note | bad regex -> refuse | git error -> refuse | huge diff -> streamed lines
```
Async ordering: two goals releasing at once share the base and the version. Invariant: one version per release, one
release per goal. Order 1: goal A bumps to vN+1, B computes vN+1 too; A's PR merges; B's merge sees VERSION conflict
(or VERSION on base == vN+1 from A, not B's) -> B's verify fails -> CLOSED/restart with vN+2. Order 2 symmetric. The
mechanism: per-goal branch names + post-merge VERSION check + tag existence check. Regression proof: toy test with two
goals and a pause between bump and merge (D3).
Interaction edges: double `merge.py SLUG` (staged fields make it idempotent; ALREADY released), `flow.py` twice on a
recorded step (ALREADY_RECORDED), `set` twice (last wins, both logged), resume of a goal with a live pid (existing guards).

##### Section 5: Code Quality

fit.py split into fit.py (decisions) and prbody.py (presentation) (D10). cmd_set/cmd_queue in guards (one delegate
each in goal.py). Duplicated area rule with estimate-model's graph.area flagged (E7 deferred). No method over 5
branches expected except release_pr's state switch (MERGED/OPEN/CLOSED/none), kept as a table-driven dispatch.

##### Section 6: Test Review

```
  NEW THING                         TYPE     HAPPY                     FAILURE                       EDGE
  size_of/depth_for                 unit     small->condensed          large->full                   no touches; non-skills repo; widened touches
  set (depth/bump/budget)           integ    override wins             worker refused; after record  unset LOOP_ROLE accepted
  resume_at / ALREADY_RECORDED      integ    names step                refusal no try                 all recorded -> pr
  kill-and-resume (background)      system   rerun completes           crash = +1 try                 --again keeps tries
  session-mode resume               system   reprompt                  no STEP refused no try         records kept
  auto_need patch                   unit     patch default             removed file -> patch          docs only -> leave
  release_pr                        system   one release               needs owner; VERSION mismatch  CLOSED restart; two goals; crash after create
  protection detect                 integ    rules endpoint            403 -> stderr fallback         non-matching refusal
  private scan                      integ    no hit -> push            hit refuses pr/merge/wiki/... bad regex; missing module; body-only hit
  push-site grep control            static   all sites scanned         new unscanned site fails      -
  board budget                      integ    line + OVER flags         none set                       one half; old record
  token accumulation                unit     attempts sum              -                              --again rerun
  merge.py requirement hold         integ    merges when IDs on page   refuses when absent            -
  verdicts in PR body (#38)         integ    listed per step           -                              no verdict lines
  github: touches, regen, bind self integ    accepted/warned/bound     bad surface; env unset         -
  byte budget                       static   every script < 20,480     -                              -
```
Assertions map exact counts ("exactly one release", "tries +1"). no_claim: fakegh stands in for GitHub (rules endpoint,
PR merge, release create); real protection behavior is not proven (no_claim=live GitHub ruleset behavior (fakegh only)).
2am-Friday test: two goals releasing on a protected fake base. Hostile QA: plant a name only in the PR body. Chaos: kill
during release_pr between merge and release create. Flakiness: time-based budget checks pass a fixed `at`.

##### Section 7: Performance

Scans add one `git diff base..HEAD` and one `git log` per push: under a second on this repo. Board budget reuses
seconds_by_step per running goal (already computed by the board). Rules endpoint is one gh call per release. No new
loops over all run records. No issues found beyond noting the diff read is linear in diff size.

##### Section 8: Observability

Logs: set, resize, scan note/refusal, release_pr stages, ALREADY_RECORDED all land in the run log. Board: depth line with
decided depth and why, budget line with OVER flags, Issues line for a missing private list. Debuggability after 3 weeks:
the run log plus release_* fields reconstruct the release. Runbooks: release_error texts name the fix ("needs the owner
to approve and merge it; then run merge.py SLUG"). Gap closed by D2 (missing list visible).

##### Section 9: Deployment & Rollout

No migrations. Old run records read as large / repo budget (obligation). Deploy-time risk: a goal mid-merge with a
cached release_part "major" from the old mapping still bumps major once (accepted; the release note names it). Rollback:
revert the release commit; nothing persistent changes shape. Post-deploy check: `private.py check`, one board refresh,
`goal.py show` on a running goal shows size/budget/resume_at. Merge order: after docs-format (D4 hold enforces it).

##### Section 10: Long-Term Trajectory

Debt: two area rules (E7), docs.py unscanned wiki path (deferred), health cost rule not per-goal (E6), review_depth help
text (setup). Reversibility 4/5 (all additive; the patch default is a behavior change that a revert restores). Phase 2:
risk-aware sizing (UC2) and measured depth (escaped defects per depth); a release coordinator if concurrency grows.
Platform: private.py and release_pr.py are reusable by any skill that pushes.

##### Section 11: Design & UX

SKIPPED (no UI scope).

#### Required outputs

##### NOT in scope
- E6 health cost rule reads per-goal budget (deferred: workflow-health outside touches).
- E7 shared area rule with estimate-model (deferred: unmerged, delivery must not import monitoring).
- docs.py wiki publish push (workflow-docs) scan (deferred: outside touches; wiki.py's merge path is covered by E2).
- Reviews invalidated by pr's base merge (deferred: existing behavior, needs its own design).
- review_depth help text in workflow-setup (deferred: outside touches).
- E8 `--size` override (skipped: YAGNI).
- gitleaks/trufflehog, release-please adoption (rejected: D11 rationale).
- Splitting the goal, release self-merge opt-in, fail-closed on a missing list (taste T3-T5: kept as planned).
- UC1-UC3 changes (pending the owner at the gate; plan direction stands).

##### What already exists
See 0B table.

##### Dream state delta
Leaves the loop at "trustworthy by construction for the paths it owns": every push site in delivery/release scans,
releases survive protection and concurrency, crashes cost one step. Still short of the ideal: depth is a size proxy,
time budget is advisory, and wiki publishing through docs.py sits outside the boundary.

##### Error & Rescue Registry
See Section 2 (14 codepaths, 0 critical gaps after accepted obligations).

##### Failure Modes Registry
```
  CODEPATH            | FAILURE MODE              | RESCUED? | TEST? | USER SEES?            | LOGGED?
  private.scan        | list missing              | Y (note) | Y     | PR note + board issue | Y
  private.scan        | bad regex / unreadable    | Y        | Y     | REFUSED PRIVATE_LIST  | Y
  private loader      | module missing            | Y        | Y     | release_error         | Y
  guards.write_finding| hit in branch             | Y        | Y     | NOTE finding local    | Y
  release_pr          | merge blocked             | Y        | Y     | release_error         | Y
  release_pr          | VERSION mismatch          | Y        | Y     | release_error         | Y
  release_pr          | two goals same version    | Y        | Y     | restart, next version | Y
  create_release      | crash after create        | Y        | Y     | adopted on rerun      | Y
  flow.py             | rerun of recorded step    | Y        | Y     | ALREADY_RECORDED      | Y
  flow.py tokens      | attempts undercounted     | Y (D5)   | Y     | budget line           | Y
  merge.py            | requirement IDs absent    | Y (D4)   | Y     | release_error waits   | Y
  docs.py publish     | unscanned wiki push       | N        | N     | silent                | N   <- deferred (outside touches)
```
CRITICAL GAP count: 1 (docs.py publish, outside touches; the merge path through wiki.py is scanned by E2, so it bites
only on a manual `docs.py publish`). Deferred with the follow-up list.

##### Completion Summary
```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION (autoplan override)     |
  | System Audit         | DEL-6..9 text only on docs-format; 3 other  |
  |                      | goals overlap; goal.py 1,065 bytes headroom |
  | Step 0               | approach B; E1-E5 accepted; 3 spec rounds   |
  | Section 1  (Arch)    | 3 issues found                              |
  | Section 2  (Errors)  | 14 error paths mapped, 0 GAPS               |
  | Section 3  (Security)| 7 issues found, 2 High severity             |
  | Section 4  (Data/UX) | 6 edge cases mapped, 0 unhandled            |
  | Section 5  (Quality) | 2 issues found                              |
  | Section 6  (Tests)   | Diagram produced, 0 gaps                    |
  | Section 7  (Perf)    | 0 issues found                              |
  | Section 8  (Observ)  | 1 gap found (closed by D2)                  |
  | Section 9  (Deploy)  | 2 risks flagged                             |
  | Section 10 (Future)  | Reversibility: 4/5, debt items: 4           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (9 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 14 rows, 0 CRITICAL GAPS                    |
  | Failure modes        | 12 total, 1 CRITICAL GAP (deferred)         |
  | TODOS.md updates     | 0 written (no TODOS.md; 5 follow-ups listed)|
  | Scope proposals      | 8 proposed, 5 accepted (+D1-D11 from voices)|
  | CEO plan             | written                                     |
  | Outside voice        | codex completed                             |
  | Lake Score           | N/A (no coverage-scored questions)          |
  | Diagrams produced    | 4 (architecture, release state, data flow, |
  |                      | dream state)                                |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 6 (UC1-UC3, T3-T5 for the gate)             |
  | Reality rows         | 7/7 rows, 0 unverified                      |
  +====================================================================+
```

### Phase 2 (Design)

Skipped: no UI scope detected (uiRequired false). Not a completed review.

### Phase 2.5 (DX) accepted obligations

<!-- autoplan-accepted:dx -->
- X1 (CAP4, write_finding channel): when the scan refuses a finding's push (hit, broken list, missing module), `guards.write_finding` keeps the commit local, exits non-zero from the calling command, records `finding_error` (place and list line, never text) on the run record, and the live board's Issues lists it with the fix. Toy check.
- X2 error contract: every new refusal ends with a stable code in the existing `(CODE)` style and puts the fix on its first or last line, states side effects (nothing pushed, or partial with what), and names caller-safe context (list source unexpanded, budget source, base ref). Codes: PRIVATE_NAME, PRIVATE_LIST, PRIVATE_MODULE, FINDING_LOCAL, ALREADY_RECORDED, SET_AFTER_RECORD, BUDGET_TOKENS, RELEASE_PR_BLOCKED, RELEASE_VERSION_MISMATCH, RELEASE_EXISTS, REQUIREMENT_MISSING, BIND_SELF_UNSET. delivery and release `references/commands.md` each carry a codes table with anchors. PRIVATE_MODULE names the sibling path it looked for and the fix (reinstall or put workflow-delivery beside workflow-release), with the import error text as context. Toy test greps each code in its refusal.
- X3 PRIVATE_NAME: the scan reads every commit's patch and message from base to HEAD (`git log -p`), not only the net diff, so a name added then removed in a later commit still refuses; each hit names its place and the list line number (never the text or pattern); the fix line gives the non-interactive squash (`git reset --soft $(git merge-base HEAD <base>) && git commit -m "<goal>"`, then `goal.py pr SLUG`) and the false-positive route (edit that line of the list). Toy check: a name added then removed in a later commit refuses.
- X4 release_error lines carry the release PR url and number, the owner's command (`gh pr merge <n> --merge`, then `merge.py SLUG`), side effects (branch pushed, PR open: partial) and a try count stored as `release_tries` and shown on the board.
- X5 the merge hold (D4) names the missing requirement IDs and the fix (merge the goal that adds their text, then `merge.py SLUG`), code REQUIREMENT_MISSING.
- X6 `sessions.py bind SLUG self` with `CLAUDE_CODE_HOST_SESSION_ID` unset is a usage error before any work: exit 2, BIND_SELF_UNSET, names the variable, fix `sessions.py bind SLUG <ID>`. Toy check.
- X7 the token stop names spent and limit, which budget applied (run record or repo settings), and the fix `goal.py set SLUG --budget-tokens N --why ...`, code BUDGET_TOKENS.
- X8 `resume_at` always returns a step name: with idea and plan recorded and review not, it returns `build` when no commit landed on the branch after the plan record, else `review`; every resume message prints the exact next command (`flow.py SLUG <step>`). Supersedes the "build or review" value in Spec R2 (c). Toy check for both cases.
- X9 delivery `references/commands.md` maps `--budget-minutes`/`--budget-tokens` to `time_budget_minutes`/`token_budget` in one table (flags not renamed).
- X10 the regen WARN ends with its action: `update or delete <script> in this goal, or ask the operation session to widen touches`.
- X11 delivery `references/commands.md` shows copy-paste examples: a private-names file and a comments-only "off" file, `private.py check` output, a `goal.py set` line, a `flow.py SLUG STEP --again` line, and the budget line in each state (none set, one half, OVER).
- X12 the docs say that `resume` resets the goal's tries (so try counts read before a resume).
- X13 the build follows the CEO Supersession line; sections 1 to 4 are read in their superseded form.
<!-- /autoplan-accepted:dx -->

### Phase 2.5 (DX) review

Methodology: plan-devex-review read in full from autoplan-dx-methodology-63GNu8/methodology.md (sha recorded by the
tool): ranges 1-600, 601-1200, 1201-1800, 1801-1905 (EOF, 1905 lines); skip-listed sections loaded only. The Hall of
Fame reference (204 lines) was read once in full rather than per pass (a deviation from "only the current pass",
recorded). Mode: DX POLISH (autoplan override). Product type: Claude Code Skill with Python stdlib CLIs (auto-confirmed).
Web research: not run for this internal tooling (consistent with the CEO landscape decision); reference benchmarks only.
Prior DX reviews: none for this branch (rubric agent-ready-v1).

#### 0A Persona

```
TARGET DEVELOPER PERSONA
========================
Who:       an AI coding agent running as a worker or operation session (primary); the solo owner (secondary)
Context:   calls goal.py / flow.py / merge.py / sessions.py / private.py unattended, mid-goal, after a crash or a refusal
Tolerance: zero ambiguity: reads errors literally, can't ask, retries blindly, pays per token
Expects:   one line saying what failed, the exact next command, whether anything was pushed, a stable code
```

#### 0B Empathy narrative

I am the worker session for a goal. I finish review and run `goal.py pr`. It refuses: `REFUSED (no try used) ...
PRIVATE_NAME` with `commit:3f2a1bc` and `skills/x/y.py:41`. I open line 41, see a session name in a comment, delete it,
commit, and run pr again. It refuses again on `commit:3f2a1bc`: the old commit still holds it. The message never told me
that pushing a branch pushes every commit, or how to rewrite it without an interactive rebase I am not allowed to run.
Later my session is killed mid-qa. The operation resumes me; `goal.py show` says `resume_at: build or review`, which is
not a command I can run. I guess review. My budget line says `OVER time`, but nothing stops me, and I can't tell from
the docs whether that is a problem. (Predicted from the plan text; no build exists yet.)

#### 0C Competitive benchmark (reference, not measured)

| Tool | Start -> result | Time + evidence | DX choice | Source |
|---|---|---|---|---|
| gitleaks pre-push | install -> first scan | reported ~2 min | rules file, exit 1 with file:line | in-distribution knowledge |
| release-please | add Action -> release PR | reported ~10 min | PR per release, labels | in-distribution knowledge |
| GitHub Actions budget/timeout | set timeout-minutes -> job stops | ~1 min | hard stop, no board | in-distribution knowledge |
| This plan (owner arms DEL-9) | create list -> `private.py check` -> board clear | estimated ~3 min, 3 steps | check command, board issue when missing | plan E5, D2 |

Target (auto, P5): Competitive (2-5 min) for "owner arms the private scan and sees it armed".

#### 0D Magical moment

`private.py check` prints `PRIVATE LIST: 12 patterns from ~/.workflow-loop/private-names`, and a planted name makes
`goal.py pr` refuse naming only the place and list line, never the text. Vehicle: the existing CLI (DX POLISH, no new
surface). Accepted.

#### 0F Journey map

```
STAGE           | DEVELOPER DOES                          | FRICTION POINTS                         | STATUS
1. Discover     | reads delivery SKILL.md / commands.md   | set, --again, codes undocumented        | fixed (X11 docs + codes table)
2. Install      | ships with the next template release    | none new; old records keep working      | ok
3. Hello World  | writes the list, runs private.py check  | none after E5                           | ok
4. Real Usage   | goal runs; pr scans; board shows budget | PRIVATE_NAME fix unclear (history)      | fixed (X3)
5. Debug        | reads refusals and release_error        | missing codes/fix lines, write_finding  | fixed (X1, X2, X4-X7)
6. Upgrade      | next release, patch by default          | condensed repos see large goals full    | ok (release note obligation)
```

#### 0G First-time confusion report

```
FIRST-TIME DEVELOPER REPORT
Persona: worker agent
T+0:00  goal.py pr -> PRIVATE_NAME commit:3f2a1bc, file:41                    -> X3 adds squash fix line
T+0:30  edits file, commits, pr again -> same commit hit                       -> X3 (every commit scanned, fix says squash)
T+1:00  killed mid-qa, resumed -> resume_at "build or review"                  -> X8 returns a step name + command
T+2:00  flow.py qa again -> ALREADY_RECORDED? no, qa unrecorded -> runs        -> ok
T+3:00  merge.py -> release_error "needs the owner" without PR number          -> X4 adds PR url, gh command, side effects
```

#### Dual voices

Native DX subagent: completed (INPUT dx 4552def2… matches the snapshot). Codex: unavailable, usage limit hit
(turn.failed "usage limit"; quota_exhausted: no further Codex calls this run). Phase tagged [single-model].

```
DX DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          yes     N/A    N/A (outside voice unavailable)
  2. API/CLI naming guessable?         partly  N/A    N/A
  3. Error messages actionable?        no      N/A    N/A (single-voice CAP4 flagged)
  4. Docs findable & complete?         no      N/A    N/A
  5. Upgrade path safe?                partly  N/A    N/A
  6. Dev environment friction-free?    yes     N/A    N/A
```
Single-voice critical: CAP4 guards.write_finding channel (accepted as X1).

#### Pass 1: Getting Started — 6/10 -> 7/10

Owner path: write `~/.workflow-loop/private-names`, run `private.py check`, open the board. Three steps, ~3 min
(estimated). Gap to 10: setup could offer to seed the list from the existing hook (outside touches). No new decision.

#### Pass 2: API/CLI design — 6/10 -> 7/10

`set` with `--depth/--bump/--budget-*`, `--again`, `bind SLUG self` are guessable. Findings: `resume_at` returns
"build or review" (not a step) -> X8; flag names differ from setting names (`--budget-minutes` vs
`time_budget_minutes`) -> X9 documents the mapping (renaming flags is churn); regen WARN gives no action -> X10. Escape
hatches: per-goal depth and budget exist; a per-goal private-line allowance was proposed by the native voice and
rejected (it would push past a match, against frozen DEL-9); a `release_path` override setting is deferred (setup's
validator is outside touches).

#### Pass 3: Error messages — 4/10 (CAP4) -> 7/10

```
ERROR PATH MATRIX (agent-ready-v1)
Path                          | Class     | what | fix  | recovery | code | context | trace | redaction | channel | Cap
goal.py pr PRIVATE_NAME       | validation| pass | fail | N/A      | pass | N/A     | N/A   | pass      | pass    | CAP6:fix (X3)
guards.write_finding hit      | partial   | fail | fail | fail     | fail | fail    | N/A   | pass      | fail    | CAP4:channel (X1)
release_pr needs owner        | env       | fail | pass | fail     | fail | fail    | N/A   | pass      | pass    | CAP6:recovery (X4)
merge.py private module gone  | unexpected| fail | fail | pass     | fail | fail    | fail  | pass      | pass    | CAP6:fix (X2)
flow.py ALREADY_RECORDED      | validation| pass | pass | N/A      | pass | N/A     | N/A   | pass      | pass    | none
flow.py token stop            | env       | pass | fail | pass     | fail | fail    | N/A   | pass      | pass    | CAP6:fix (X7)
merge.py requirement hold     | env       | fail | fail | pass     | fail | N/A     | N/A   | pass      | pass    | CAP6:fix (X5)
bind self, env unset          | usage     | fail | fail | N/A      | fail | N/A     | N/A   | pass      | fail    | CAP6:fix (X6)
```
Corrected lines (examples):
- `REFUSED (no try used): private-name scan hit at commit:3f2a1bc and skills/x/y.py:41 (list line 7); nothing was pushed (PRIVATE_NAME). Fix: remove it, then squash so no commit keeps it: git reset --soft $(git merge-base HEAD origin/main) && git commit -m "<goal>"; then goal.py pr SLUG. False positive: edit line 7 of ~/.workflow-loop/private-names.`
- `REFUSED: release PR https://github.com/o/r/pull/201 can't merge (required review); branch release/v0.21.1-slug pushed, PR open (side effects: partial; try 2) (RELEASE_PR_BLOCKED). Fix for the owner: approve and merge it (gh pr merge 201 --merge), then run merge.py SLUG.`
- `FINDING NOT PUSHED: private-name scan hit at .loop/findings.md:12 (list line 3); the finding commit stays local (FINDING_LOCAL). Fix: remove the name from the finding text, then push the branch.` with exit 1 and `finding_error` on the run record.
Safety model: every new refusal states side effects; nothing pushes after a refusal; no verbose mode needed beyond the run log.

#### Pass 4: Documentation — 5/10 -> 7/10

The plan reads as a diff of itself (Supersession line) -> X13: the build follows the Supersession line, and the Eng
phase consolidates. Docs get copy-paste examples (X11) and a codes table with anchors (X2).

#### Pass 5: Upgrade & migration — 6/10 -> 7/10

Old run records degrade to full depth and repo budget; release note names the patch default and the condensed change;
resume resets tries is documented (X12). Gap to 10: no deprecation of `ask` for out-of-tree callers of `auto_need`
(none exist in the repo; checked by grep: release.cmd_ask and autorelease only).

#### Pass 6: Dev environment — 7/10 -> 7/10

Stdlib only, toy tests with fakegh, non-interactive env already forced in every script (GIT_TERMINAL_PROMPT=0,
stdin to /dev/null). Fix lines avoid interactive commands (no `git rebase -i`). No issues beyond X3's non-interactive
fix.

#### Pass 7: Community — 5/10 -> 5/10

MIT, GitHub issues are the channel (#38, #117 etc.). This plan neither adds nor removes community surfaces. No issues
found in scope.

#### Pass 8: DX measurement — 4/10 -> 6/10

Board budget line, verdicts in the PR body, token accounting per attempt make cost visible. No TTHW instrumentation for
the owner's arm-the-scan path; `private.py check` is the measurement point. Gap: no count of refusals by code over time
(health could read run logs; outside touches, deferred).

#### Claude Code Skill DX checklist

Error recovery: resume from last step (planned). Agent-readable errors: X2 table. Bounded autonomy: operation-only set,
fail-closed scans. State storage: run records and sidecars (existing). No AskUserQuestion surfaces added.

#### DX Scorecard

```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
| Getting Started      |  7/10  |  6/10  |  +1    |
| API/CLI/SDK          |  7/10  |  6/10  |  +1    |
| Error Messages       |  7/10  |  4/10  |  +3    |
| Documentation        |  7/10  |  5/10  |  +2    |
| Upgrade Path         |  7/10  |  6/10  |  +1    |
| Dev Environment      |  7/10  |  7/10  |  =     |
| Community            |  5/10  |  5/10  |  =     |
| DX Measurement       |  6/10  |  4/10  |  +2    |
+--------------------------------------------------------------------+
| TTHW                 | ~3 min (est.) | n/a | new  |
| Competitive Rank     | Competitive                                 |
| Magical Moment       | designed via private.py check + place-only refusal |
| Product Type         | Claude Code Skill (CLI)                     |
| Mode                 | POLISH                                      |
| Overall DX           |  7/10  |  5/10  |  +2    |
+====================================================================+
| Zero Friction covered | Learn by Doing covered (examples) | Fight Uncertainty covered (X2) |
| Opinionated + Escape Hatches covered (set, --again) | Code in Context gap (no sample repo) |
| Magical Moments covered | Agents Are Users covered (codes, non-interactive fixes) |
+====================================================================+
```
Prior column = this review's pre-fix pass scores (no earlier DX review exists).

#### DX Implementation Checklist

```
[ ] Owner arms the scan in < 5 min: list file + private.py check + board clear
[ ] Every new refusal ends with (CODE) and a fix on its first or last line (X2 table)
[ ] PRIVATE_NAME scans every commit's patch and gives the non-interactive squash fix
[ ] write_finding refusal exits 1, records finding_error, shows on the board
[ ] release_error lines carry PR url/number, the owner's gh command, side effects, try count
[ ] resume_at always a step name, message prints the exact next command
[ ] commands.md: codes table with anchors; sample list file (and off file); check output; set and --again examples; budget line states
[ ] flag-to-setting mapping table for budgets
[ ] resume resets tries, documented
```

#### NOT in scope (DX)
- Per-goal private-line allowance (rejected: pushes past a match, against frozen DEL-9).
- `release_path: auto|direct|pr` setting (deferred: setup validator outside touches).
- Seeding the private list from the existing hook in setup (deferred: outside touches).
- Refusal counts by code in health (deferred: outside touches).

#### What already exists (DX)
guards' `(CODE)` suffix convention on refusals (e.g. NOT_WORKER, RESUME_STATUS), refuse_no_try's exit 2, the
`NEXT:` line convention in goal.py/flow.py, autorelease's `release_error` under Issues, the no-terminal env block in
every script, fakegh for toy tests.

### Phase 3 (Eng) accepted obligations

<!-- autoplan-accepted:eng -->
- G1 (critical, lost update): `goal.py set` and the E1 re-size write `depth_override`, `bump`, `budget` and the widened `size` to the operation sidecar `<runs>/<slug>.extra.json` under its flock (extending the sidecar with a `set` map), never to the run record; every reader (depth_for, auto_need, board_budget, the flow.py token stop, set's own after-record check) merges sidecar over run record. Toy check: a `set` racing a worker `record` keeps both.
- G2: the scan reads only added lines (`+`, not `+++` headers, not removed or context lines) of each commit's patch plus every commit message, so a goal that removes a leaked name is not refused; when the branch is already on origin the PRIVATE_NAME fix says the owner must decide (the loop never force-pushes). Toy checks: removed-line-only passes; added-then-removed refuses; message-only hit refuses.
- G3: every write to GitHub in the three skills is a scan site: `git push`, and gh `create`, `edit`, `comment`, `merge`, and `api` with POST/PATCH; the toy control is an AST check per call site (the enclosing function must call the scan), so a second unscanned push in one file (release.py has two) fails it. `github:` surfaces in touches don't change this.
- G4: release_pr reads `gh pr view --json mergeStateStatus,reviewDecision`: required checks pending is a waiting state (`release_pr_waiting`, no error, retried by the next merge.py run); review required or blocked is the owner error (X4); the loop never passes `--admin`. Toy checks for both states.
- G5: the release targets the release PR's `mergeCommit.oid`, and VERSION is checked at that commit; a closed-and-restarted release PR regenerates VERSION and CHANGELOG on the new base.
- G6: byte fallbacks beyond goal.py: if guards.py nears 20,480 bytes, `cmd_set`, `cmd_queue` and `cmd_touches` move to a new `guards_ops.py` (goal.py delegates); release.py's cut keeps one scan call through the loader; toy tests split by area (depth, release, resume, budget, private, defects), each under 20,480 bytes and each taking a case argument like test-rows.sh.
- G7: private.py compiles patterns once, skips binary patches, caps each scanned line at 4,096 characters and stops at a 60 s overall limit, which refuses (PRIVATE_LIST, timeout named); `LOOP_PRIVATE_NAMES` is a file path only.
- G8: the D4 merge hold applies only when the base has the wiki folder and some page already uses the requirement ID's prefix; otherwise merge.py prints an advisory NOTE and merges.
- G9: the plan record stores HEAD's sha as `plan_head`, and X8's build-vs-review choice falls back to `build` when it is missing; `--again` refuses while the step's job pid is alive and clears the step's `.ran` and `.asked` markers; a widened touch that makes a goal large after review was recorded condensed shows on the board and in the PR body with `flow.py SLUG review --again`.
- G10: in size_of, files at the repo root are no area, and VERSION and CHANGELOG are never areas.
- G11: tests also cover: `--again` keeps accumulated tokens; a message-only private hit; bind self with a set id; comments-only list vs missing list on the board; gh shim answers for mergeStateStatus and a release view at another target.
- G12: `github:<surface>` matches the six-surface allowlist exactly and is never treated as a filesystem path in size or regen logic.
- G13: one spent-token rule in the flow.py stop and board_budget: the sum of per-step values when any exist, else `tokens.total` (written by background workers); an agreement test checks both.
- G14: dev/toy/fakegh is not edited (it maps to the Documentation page, outside touches); the new toy tests wrap it with a test-local gh shim for the rules endpoint, mergeStateStatus and release view, and simulate a protected base with a pre-receive hook in the toy origin that rejects pushes to main with a GH006 message. Supersedes D9's "fakegh serves the endpoint".
- G15 (regression rule): test-release.sh:116 (new file -> minor) and :120 (removed file -> NEED ask) and test-autorelease.sh:69 (breaking -> major) are rewritten to the new rule (patch, reason named) as intentional changes listed in the PR body; prbody keeps the `## Result` heading and `Skill flow:` lines the existing tests read; any existing test that reruns a recorded flow step adds `--again`; the full land and nightly lanes pass.
- G16: new toy files carry a `# reads:` header that check-reads.sh accepts, use a temp HOME and unset LOOP_PRIVATE_NAMES.
- G17: heavy cases (two-goal release race, both kill-and-resume cases) are nightly rows; each of DEL-5..DEL-9 keeps at least one land row.
- G18: flow.py's depth prompt and the check_record depth check read the goal's decided depth from the run record merged with the sidecar.
- G19: release scripts read per-goal settings (bump) through delivery's fit via the same sibling loader as private.py, never by parsing the sidecar themselves.
- Test plan artifact: the eng review test plan (2026-11-10) in the private project folder (lists every case above).
<!-- /autoplan-accepted:eng -->

### Phase 3 (Eng) review

Methodology: plan-eng-review read in full from autoplan-eng-methodology-SKxAbZ/methodology.md: ranges 1-600, 601-1200,
1201-1800, 1801-2143 (EOF, 2143 lines); skip-listed sections loaded only. Scope gate: target is the active plan
(.loop/goals/delivery-prd.plan.md), selected by the autoplan driver. Test framework: bash toy tests under dev/toy with
fakegh, rows in .loop/regression.tsv (no CLAUDE.md testing section; detected from dev/toy and regression.py).
Retrospective: the last goal on these files (loop-guards) needed two review cycles for lock and race fixes (pool lock,
resume recheck under lock); concurrency on shared state is a recurring problem area, so G1 below is treated as critical.

#### Step 0: Scope challenge

What already solves each sub-problem: see the CEO 0B table, plus: the operation-only sidecar
(`<runs>/<slug>.extra.json` under an flock, guards.py:9 and :137) is the existing answer to "the operation writes while
the worker writes"; `board_status.seconds_by_step`/`tokens_by_step` (board_status.py:52,66); test-rows.sh's
case-argument pattern and `# reads:` header (dev/toy/test-rows.sh:2); check-reads.sh closure check.

Complexity: about 25 changed files [estimated] (6 new: fit.py, prbody.py, private.py, release_pr.py, board_budget.py,
guards_ops.py if needed; plus split toy tests) and 5-6 new modules. Over the 8-file / 2-class gate. Structure question
(plan-eng-review-structure, auto-decided): Original arrangement (approach B with the prbody split) kept; the smaller
arrangement (fit+prbody merged, budget inside live_board) breaks the 20 KB rule on live_board.py (18,646 bytes,
[measured: wc -c]) and mixes decisions with presentation. Feature cuts: none (scope never reduced, P2). Scope Challenge
result: scope accepted as-is.

Search check: no new infrastructure pattern needing research; the release-PR state machine and regex scanning are
stdlib and in-repo patterns [Layer 1]. TODOS cross-reference: the repo has no TODOS.md.

| premise | claim | receipt | verdict |
|---|---|---|---|
| E1 | operation commands write only the sidecar under an flock, never the run record | skills/workflow-delivery/scripts/guards.py:9 | verified |
| E2 | goal.py save is a plain read-modify-write with atomic replace, no lock | skills/workflow-delivery/scripts/goal.py:101 | verified: lost-update risk for `set` |
| E3 | a background worker writes `tokens.total`, flow.py writes per-step tokens | skills/workflow-monitoring/scripts/worker.py:133, skills/workflow-delivery/scripts/flow.py:263 | verified: two shapes |
| E4 | board tokens ignore `total`; flow's stop sums every int including `total` | skills/workflow-monitoring/scripts/board_status.py:66, skills/workflow-delivery/scripts/flow.py:148 | verified: two rules |
| E5 | dev/toy/fakegh maps to the Documentation wiki page | .loop/docs.tsv:5 | verified: editing fakegh stales a page outside touches |
| E6 | existing toy tests assert the old bumps | dev/toy/test-release.sh:116, dev/toy/test-release.sh:120, dev/toy/test-autorelease.sh:69 | verified: intentional changes |
| E7 | existing tests read "Skill flow:" in the PR body | dev/toy/test-autorelease.sh:128, dev/toy/test-defect.sh:165 | verified: format to keep |
| E8 | guards.write_finding pushes HEAD with no scan | skills/workflow-delivery/scripts/guards.py:187 | verified |
| E9 | release.py has two push sites | skills/workflow-release/scripts/release.py:352, skills/workflow-release/scripts/release.py:369 | verified |
| E10 | resume resets tries | skills/workflow-delivery/scripts/guards.py:117 | verified |

unverified=0.

REALITY: premise-table finding 10 premises verified; 5 change the plan (sidecar race, two token shapes, fakegh page mapping, old-bump tests, two release.py push sites) unverified=0 skills/workflow-delivery/scripts/guards.py:9
REALITY: already-done pass origin/main since 2026-11-09 holds only loop-guards changes on these files; none of size_of, private scan, release_pr, resume_at, board budget exists e145b43
REALITY: surface-check finding `gh pr view --json mergeStateStatus,reviewDecision,mergeCommit` and `gh api repos/{o}/{r}/rules/branches/{b}` are real gh surfaces but fakegh serves neither (dev/toy/fakegh/gh:18); `goal.py set`, `flow.py --again`, `private.py check` are new; `sessions.py bind SLUG self` reuses the ID positional skills/workflow-monitoring/scripts/sessions.py:7
REALITY: binding-decisions pass the decision search returned nothing for this branch; the CEO and DX accepted blocks are the binding decisions and are kept; UC1-UC3 stay pending .loop/goals/delivery-prd.plan.md:1
REALITY: numbers finding guards.py 16,424 [measured: wc -c], goal.py 19,415 [measured: wc -c], release.py 18,606 [measured: wc -c], live_board.py 18,646 [measured: wc -c]; guards.py absorbing cmd_set, cmd_queue, scan calls and error text may pass 20,480 [estimated] [re-measure before gate] skills/workflow-delivery/scripts/guards.py:1
REALITY: deferred-asks finding #117 asks nothing more than covered; #129's draft-as-setting alternative left out (docs follow the automatic path); #170's "stop and ask" replaced by frozen DEL-5's patch default; #134/#154 fully covered skills/workflow-release/scripts/autorelease.py:63
REALITY: pr-count pass no ship-policy.json; one goal PR; the release PR is runtime output skills/workflow-delivery/scripts/goal.py:391

#### Dual voices

Native eng subagent: completed (INPUT eng 6b2d7195… matches the snapshot). Codex: unavailable (usage limit reached in
Phase 2.5; quota_exhausted, no call made). [single-model].

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               yes*    N/A    N/A (*with G1-G5)
  2. Test coverage sufficient?         no      N/A    N/A
  3. Perf risks + budget/bench named?  no      N/A    N/A (scan time limit missing)
  4. Security threats covered?         no      N/A    N/A (gh write sites, removed-line hits)
  5. Error paths handled?              partly  N/A    N/A
  6. Deployment risk manageable?       yes     N/A    N/A
```
Single-voice HIGH findings flagged: gh write surfaces outside D1, removed-line hits, checks-pending misread as owner error.

#### Section 1: Architecture

```
                         ┌───────────────────── workflow-delivery ─────────────────────┐
  operation session ──>  │ goal.py set/touches ─> guards_ops/guards: cmd_set, cmd_touches│──flock──> <slug>.extra.json
                         │                         (sidecar: depth_override, bump,       │            (operation-owned)
                         │                          budget, size after widen)            │
  worker session ────>   │ goal.py new/record/pr ─> fit.py (size_of, depth_for, budget,  │──────────> <slug>.json
                         │ flow.py STEP [--again]    resume_at, again, settings merge)   │            (worker-owned)
                         │                        ─> prbody.py (body, verdicts, regen)   │
                         │                        ─> private.py (scan +lines/msgs/texts, │
                         │                            check, fail closed, time limit)    │
                         └──────────────────────────────▲────────────────▲───────────────┘
                                 one sibling loader      │                │ (settings via fit, not by parsing the sidecar)
  ┌──────────── workflow-release ──────────────┐         │                │
  │ autorelease.load_delivery() ───────────────┼─────────┘                │
  │ merge.py: scan, D4 hold, merge             │                          │
  │ release.auto_need: patch default, bump     │                          │
  │ autorelease: push base | protected? ──> release_pr.py                 │
  │   release_pr: rules endpoint, release/vX-<slug>, PR, mergeStateStatus,│
  │   merge (never --admin), VERSION at mergeCommit, release at mergeCommit│
  │ wiki.py: full-tree scan, prepare --commit scan, first-page fix        │
  │ release.py cut: scan before push and draft                            │
  └────────────────────────────────────────────┘                          │
  ┌──────────── workflow-monitoring ───────────┐                          │
  │ live_board ─> board_budget ─> board_status │  (time, tokens: per-step sum else total)
  │ mend resume prompt (resume_at + dirty/HEAD)┼──────────────────────────┘
  │ session_bind bind SLUG self                │
  └────────────────────────────────────────────┘
```

Design twice (new public modules): shape A (chosen) is library calls at each push or post site with one loader; shape B
is a git pre-push hook installed by setup. B covers every git push in every skill (docs.py too) but misses gh posts
(PR body, release notes, comments), lives outside touches (setup) and is harder to test. A hides the list format,
regex compilation, time limit and redaction behind `scan()`/`check()`: deeper interface. Kept A; B recorded as a later
backstop. Red flags: split ownership of the run record (G1, fixed by the sidecar); two ways to compute spent tokens
(G13, one rule, tested in both places); information leakage of the sidecar format into release (G19, release reads
settings through fit); hand-synced push-site list (the control derives sites from code by AST, G3). No shallow or
pass-through module beyond goal.py's one-line delegates (accepted for the byte rule).

Findings:
- [CRITICAL] (confidence: 9/10) skills/workflow-delivery/scripts/goal.py:101 — `goal.py set` and the E1 re-size would rewrite the worker's run record (`write(temp, json.dumps(state...)); os.replace(temp, path)`) while the worker may save a stale copy, losing the override or size; guards.py:9 already routes operation writes to the flock'd sidecar. Accepted G1.
- [CRITICAL] (confidence: 8/10) native — new `github:` write surfaces and gh edit/comment/merge calls are outside D1 and the per-file control misses a second site in one file (release.py:352 and :369). Accepted G3.
- [CRITICAL] (confidence: 8/10) native — `gh pr merge` fails while required checks are pending; X4/R3(6) would record an owner error. Accepted G4.
- [INFORMATIONAL] (confidence: 8/10) native — release target should be the release PR's merge commit, not the base tip after fetch. Accepted G5.
- [INFORMATIONAL] (confidence: 7/10) native — D4 hold would block repos with no wiki or no ID scheme. Accepted G8.
- [INFORMATIONAL] (confidence: 9/10) .loop/docs.tsv:5 — editing dev/toy/fakegh stales the Documentation page outside touches. Accepted G14.
Dispositions: all accepted (auto-decided, P1/P5).

#### Section 2: Code quality

- [INFORMATIONAL] (confidence: 9/10) skills/workflow-monitoring/scripts/worker.py:133 vs skills/workflow-delivery/scripts/flow.py:148 — `state["tokens"] = dict(..., total=...)` and `sum(v for v in ...values() if isinstance(v, int))`: two token shapes, two spend rules. Accepted G13 (one rule: per-step sum, else `total`).
- [INFORMATIONAL] (confidence: 8/10) guards.py growth past 20 KB [estimated]: accepted G6 (guards_ops.py fallback named).
- [INFORMATIONAL] (confidence: 7/10) native — size_of root files undefined. Accepted G10.
- [INFORMATIONAL] (confidence: 7/10) native — `github:` must match the allowlist exactly and never be treated as a path. Accepted G12.
- Shared-code rubric: the spent-token one-liner has two verified callers (flow.py stop, board_budget) across two skills
  with no shared module boundary; extraction rejected (cross-skill import for one line), duplication guarded by one
  agreement test (G13). Stale diagrams in touched files: none found (the touched scripts carry docstring tables, no
  ASCII diagrams).

#### Section 3: Test review

```
CODE PATHS                                                   USER FLOWS
[+] fit.size_of / depth_for                                  [+] Operation sets a goal
  ├── [GAP→PLANNED ★★★] small/large/no touches/root/non-skills    ├── [GAP→PLANNED] set --depth by worker refused
  ├── [GAP→PLANNED] widened touches -> large (sidecar)             ├── [GAP→PLANNED] set after recorded step refused
  └── [GAP→PLANNED] override beats size and setting               └── [GAP→PLANNED] concurrent set + worker record keeps both (G1)
[+] flow.py ALREADY_RECORDED / --again                       [+] Crash and resume
  ├── [GAP→PLANNED] refusal names resume_at, no try                ├── [GAP→PLANNED][→E2E] background kill mid-review: +1 try, rerun completes (nightly)
  ├── [GAP→PLANNED] --again clears later, keeps tries, tokens      ├── [GAP→PLANNED][→E2E] session kill: records kept, IN SESSION again
  └── [GAP→PLANNED] --again refuses while .job pid alive           └── [GAP→PLANNED] resume_at build vs review by plan_head
[+] flow.py tokens                                           [+] Release
  ├── [GAP→PLANNED] attempts add up                                ├── [GAP→PLANNED][→E2E] protected base: one release at merge commit (#134)
  └── [GAP→PLANNED] stop uses per-step sum else total              ├── [GAP→PLANNED] checks pending: waiting, no error (G4)
[+] release.auto_need                                              ├── [GAP→PLANNED] review required: owner error with PR number (#154)
  ├── [★★ TESTED→CHANGE] new file: minor -> patch (test-release.sh:116)  ├── [GAP→PLANNED][→E2E] two goals: two versions (nightly)
  ├── [★★ TESTED→CHANGE] removed file: ask -> patch (test-release.sh:120, #170) └── [GAP→PLANNED] crash after create adopted
  └── [★★ TESTED] docs only: leave (test-release.sh:118)
[+] private.scan                                             [+] Private scan
  ├── [GAP→PLANNED] + lines only; removed line not a hit           ├── [GAP→PLANNED] pr refuses: body-only hit, message-only hit
  ├── [GAP→PLANNED] added then removed in later commit -> hit      ├── [GAP→PLANNED] merge.py, wiki publish, cut, write_finding refuse
  ├── [GAP→PLANNED] bad regex / unreadable / module gone -> refuse ├── [GAP→PLANNED] no list: note + board issue; comments-only: off
  └── [GAP→PLANNED] time limit -> refuse                           └── [GAP→PLANNED] static AST control: every write call scanned
[+] board_budget                                             [+] Board
  ├── [GAP→PLANNED] none set / one half / OVER flags               └── [GAP→PLANNED] budget and depth lines under running and held goals
  └── [GAP→PLANNED] agrees with health at a fixed `at`
[+] merge.py D4 hold: [GAP→PLANNED] refuses when IDs absent and wiki uses the scheme; NOTE otherwise
[+] prbody: [★★ TESTED→KEEP] "Skill flow:" (test-autorelease.sh:128, test-defect.sh:165); [GAP→PLANNED] verdicts (#38)
[+] guards.check_path github:, regen WARN, bind self (#117): [GAP→PLANNED] each, incl. env unset
[+] wiki first-page fix, docs say published (#129): [GAP→PLANNED]
[+] byte budget: [GAP→PLANNED] every touched script and new toy file < 20,480

COVERAGE (current code): 4/46 paths with an existing test (9%), all four on release and PR body; every new path planned.
QUALITY: ★★★:0 ★★:4 ★:0 | GAPS: 42 planned (6 E2E-style, 0 eval)
```
LLM/eval scope: none (the flow prompt adds a VERDICT line request; no prompt-template eval suite exists in this repo).
Regression rule: three existing assertions change on purpose (G15) and two body markers are kept; full land and nightly
lanes must stay green. Tests made obsolete: none retired; test-release.sh:116 and :120 and test-autorelease.sh:69 are
rewritten to the new expectations. Test plan artifact written (path in the accepted block).

#### Section 4: Performance

- [INFORMATIONAL] (confidence: 7/10) private.scan over `git log -p` and every wiki page: linear in history size; a
  backtracking pattern can hang `pr` or the watch. Budget: compile once, skip binary patches, cap scanned line length at
  4,096 characters, 60 s overall limit (fail closed) [estimated]. Accepted G7.
- Board budget reuses per-goal seconds_by_step already computed for the board: no added loop. Rules endpoint: one gh
  call per release. No database, no N+1.

#### Worktree parallelization

| Step | Modules touched | Depends on |
|---|---|---|
| A delivery core | skills/workflow-delivery/scripts | — |
| B release | skills/workflow-release/scripts | A (private.py, fit settings API) |
| C monitoring | skills/workflow-monitoring/scripts | A (resume_at, budget rule) |
| D tests, rows, docs | dev/toy, .loop/regression.tsv, docs, references | A, B, C |

Lane A first; then B + C in parallel; then D. Conflict flags: role.py and goal.py also change under lane-control,
live_board.py under estimate-model: merge origin/main before each lane.

#### Failure modes registry

```
  CODEPATH              | FAILURE                         | TEST? | HANDLING             | USER SEES        | CRITICAL?
  guards.cmd_set        | lost update vs worker save      | Y(G1) | sidecar + flock      | override kept    | no (fixed)
  private.scan          | removed-line false hit          | Y(G2) | + lines only         | no refusal       | no
  private.scan          | catastrophic regex              | Y(G7) | time limit, refuse   | PRIVATE_LIST     | no
  gh edit/comment       | unscanned post                  | Y(G3) | scan every write     | refusal          | no
  release_pr            | checks pending                  | Y(G4) | waiting state        | board: waiting   | no
  release_pr            | tag at wrong commit             | Y(G5) | merge commit target  | correct release  | no
  merge.py D4           | repo without wiki blocked       | Y(G8) | advisory NOTE        | NOTE             | no
  flow --again          | live job / stale .ran           | Y(G9) | refuse / clear       | refusal          | no
  docs.py publish       | unscanned manual wiki push      | N     | none (outside touch) | silent           | YES (deferred)
```
Critical gaps: 1 (docs.py publish run by hand; the merge path through wiki.py is scanned). Deferred: outside touches.

#### NOT in scope (Eng)
- docs.py publish scan (workflow-docs) and a git pre-push hook backstop (setup): outside touches.
- Reviews invalidated by pr's base merge: existing behavior, separate design.
- milestone.py posts (workflow-health): carry the already-scanned PR title only.
- TODOS.md: the repo has none and the goal may not add one; deferrals are listed here and in the CEO/DX sections for
  the operation session to file as issues.

#### What already exists (Eng)
Sidecar + flock for operation writes (guards.py:137); refuse_no_try and `(CODE)` refusals; role.begin depth reset;
flow.py dead-pid try path; autorelease staged fields; fakegh (wrapped, not edited); test-rows.sh case pattern; `# reads:`
headers and check-reads.sh; regression.py red.

#### Completion summary
- Step 0: Scope Challenge — scope accepted as-is (structure: original arrangement)
- Reality rows: 7/7 applicable rows emitted, 0 unverified premises
- Architecture Review: 6 issues found
- Code Quality Review: 4 issues found
- Test Review: diagram produced, 42 gaps identified (all planned)
- Performance Review: 1 issue found
- NOT in scope: written
- What already exists: written
- TODOS.md updates: 0 written (no TODOS.md; 7 follow-ups listed across phases)
- Failure modes: 1 critical gap flagged (deferred, outside touches)
- Unresolved decisions: 0 in this review (UC1-UC3 and taste items belong to the gate)
- Outside voice: codex unavailable (usage limit)
- Parallelization: 4 lanes, 2 parallel / 2 sequential
- Lake Score: N/A (no coverage-scored questions asked)

### Phase 4 (final gate)

Status: pending the owner (unattended run; nothing approved). Gate items: uc1 DEL-6 reading under review_depth full
(recommended b: keep the code, switch this repo to condensed after it lands), uc2 risk-aware sizing (recommended b),
uc3 breaking-change stop on the patch default (recommended b), taste d1-d5 (auto defaults a: own area rule for now,
one goal, loop merges its release PR where allowed, missing list passes with a board issue, release_path deferred),
plan1 approval (recommended a). User challenges keep the original direction until the owner answers.
Cycle: actual 33m (estimate 30m); CEO dual voice, DX and Eng single-model (Codex usage limit).

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | 0 | Skip the review tool upgrade prompt (1.92 -> 1.99) | Mechanical | P6 | Unattended run; the owner's rules say skip and log | Upgrading mid-run |
| 2 | 0 | Treat the run as unattended though the preamble echoed interactive | Mechanical | P6 | The parent session's instructions set full auto: no AskUserQuestion, stop at the gate | Prose briefs mid-run |
| 3 | 0 | DX phase runs (developer tool, agent-primary, 3 term matches) | Mechanical | P1 | scope returned dxRequired true | Skipping DX |
| 4 | CEO | Mode SELECTIVE EXPANSION (rule would say SCOPE REDUCTION at about 22 files) | Mechanical | P6 | autoplan override fixes the mode; the 22 files are mostly one-line hooks plus 4 new modules | SCOPE REDUCTION |
| 5 | CEO | Approach B (new modules, one-line hooks) over A (patch callers) and C (setup-level model) | Mechanical | P1/P5 | A breaks the 20 KB limit and collides with two goals; C is outside touches | A, C |
| 6 | CEO | Accept E1 re-size on widened touches | Mechanical | P2 | In blast radius, a few lines | Size fixed at freeze forever |
| 7 | CEO | Accept E2 wiki publish full-tree scan | Mechanical | P1/P2 | DEL-9 covers every push; closes R2-6 | Known gap for old pages |
| 8 | CEO | Accept E3 broken list fails closed | Mechanical | P1 | A broken list passing is a silent failure | Fail open |
| 9 | CEO | Accept E4 board time from board_status helpers | Mechanical | P4 | One definition of goal time with health | Wall-clock since freeze |
| 10 | CEO | Accept E5 `private.py check` | Mechanical | P1 | Lets the owner see DEL-9 is armed | No self-check |
| 11 | CEO | Defer E6 health cost rule reading per-goal budget | Mechanical | P3 | workflow-health is outside touches | Editing outside touches |
| 12 | CEO | Defer E7 shared area rule with estimate-model | Taste | P5 | estimate-model unmerged; delivery must not import monitoring | Import graph.area now |
| 13 | CEO | Skip E8 `--size` override | Mechanical | P5 | `--depth` already overrides the outcome | Second knob |
| 15 | CEO | Spec R1: apply 11 fixes (resize owner, budget edge cases, protection strings, PR title, defect rows, killed-step try, bump source, rollout text, dependency note, byte budget, private loader) | Mechanical | P1/P5 | Each closes a cited reviewer gap inside the accepted scope | Leaving them to the build |
| 16 | CEO | DEL-6 under review_depth full: keep the owner's full setting, state the reading in the row and PR body (taste T2) | Taste | P6 | The owner chose full; switching repo settings is outside touches and the owner's call | Defaulting small goals to condensed in this repo |
| 17 | CEO | Spec R2: budget always carried with explicit none; 8 minor fixes (bump WARN, no-list rule, resume_at order, again scope, killed-step path, texts-only scan, cmd_set in guards, byte fallback) | Mechanical | P1/P5 | Closes the round-2 blocking gap on DEL-8 and the cited minor gaps | A default budget value invented by the plan |
| 18 | CEO | Spec R3 (cap): one budget rule (key present wins, absent = repo); cmd_queue fallback to guards; cmd_set once in guards; verdict source; set after a recorded step refuses; release PR retry trigger; DEL-7 test pins a background worker; fixed `at`; issue titles in rows | Mechanical | P5/P3 | Closes the round-3 blocking ambiguity and its minors; cap reached, verified by text | A fourth reviewer launch |
| 19 | CEO | Dual voices: accept D1 push-site inventory + grep control | Mechanical | P1 | Both voices; guards.write_finding pushes HEAD unscanned (guards.py:187) | Narrowing DEL-9's promise |
| 20 | CEO | Accept D2 missing list visible on the board (fail-open kept) | Taste | P6 | Codex calls fail-open critical; fail-closed would block every repo with no list | Fail closed on a missing list (T5) |
| 21 | CEO | Accept D3 release identity per goal + reconcile | Mechanical | P1 | Codex: two goals can share release/vX; crash after create | Single-writer assumption |
| 22 | CEO | Accept D4 merge.py hold on absent requirement IDs | Mechanical | P1 | Both voices: a NOTE is not a hold under auto_merge | NOTE only |
| 23 | CEO | Accept D5 token accumulation per attempt | Mechanical | P1 | flow.py:260 replaces a step's tokens | Leave undercount |
| 24 | CEO | Accept D6 token = limit, time = advisory, stated | Mechanical | P5 | Both voices asked to define it | Silent ambiguity |
| 25 | CEO | Accept D7 resume shows dirty count + HEAD | Mechanical | P1 | Codex: partial build effects | Label-only resume |
| 26 | CEO | Accept D8 session-mode resume check | Mechanical | P1 | Codex: crash evidence pinned to one mode | Background only |
| 27 | CEO | Accept D9 rules endpoint before stderr match | Mechanical | P1 | Claude: stderr wording drifts | stderr only |
| 28 | CEO | Accept D10 prbody.py split | Mechanical | P5 | Codex: fit.py mixes decisions and presentation | One module |
| 29 | CEO | Reject adopting gitleaks/release-please (D11 rationale) | Mechanical | P4/P3 | stdlib only; list stays private; loop owns release | Adopt external tools |
| 30 | CEO | Keep one goal (do not split trust/fit) | Taste | P6 | Claude only; the owner froze the done lines; a split needs new goals | Split (T3) |
| 31 | CEO | Keep the loop merging its release PR where allowed | Taste | P6 | Claude only; #134/#154 ask for exactly that | Opt-in self-merge (T4) |
| 32 | CEO | DEL-6 reading under full: User Challenge UC1 | User Challenge | - | Both voices: the reading makes DEL-6 inert in this repo | Auto-deciding |
| 33 | CEO | Risk-aware sizing: User Challenge UC2 | User Challenge | - | Both voices: size ignores risky paths | Auto-deciding |
| 34 | CEO | Breaking-change guard on patch default: User Challenge UC3 | User Challenge | - | Both voices: patch relies on memory for breaking changes | Auto-deciding |
| 35 | DX | Mode DX POLISH; product type Claude Code Skill (CLI); persona AI agent worker/operation session | Mechanical | P6 | autoplan override; README and SKILL.md say agents run goals | DX EXPANSION, human persona |
| 36 | DX | TTHW target Competitive (2-5 min) for arming the private scan; magical moment via private.py check | Mechanical | P5 | lowest-effort vehicle on existing CLI | New surface |
| 37 | DX | Web research skipped (reference benchmarks) | Mechanical | P3 | internal tooling, matches CEO landscape decision | Aside/WebSearch |
| 38 | DX | Codex DX voice unavailable (usage limit); phase single-model; no more Codex this run | Mechanical | P6 | turn.failed usage limit = quota_exhausted | Retrying Codex |
| 39 | DX | Accept X1 write_finding exits non-zero + finding_error + board | Mechanical | P1 | CAP4 channel: a local-only finding looked like success | NOTE only |
| 40 | DX | Accept X2 codes table and fix-first/last error lines | Mechanical | P1 | agent-ready contract; follows guards' (CODE) convention | Free-form messages |
| 41 | DX | Accept X3 scan every commit's patch + squash fix | Mechanical | P1 | net diff misses a name added then removed; pushing sends every commit | Net diff only |
| 42 | DX | Accept X4-X7 release/hold/bind/budget error lines | Mechanical | P1 | CAP6 fix/recovery gaps | Leave to build |
| 43 | DX | Accept X8 resume_at always a step name (build vs review by commits after plan) | Mechanical | P5 | "build or review" is not a runnable command | Two-word value |
| 44 | DX | Accept X9-X12 docs (flag map, regen action, examples, tries reset) | Mechanical | P5 | docs findable, copy-paste | No examples |
| 45 | DX | Reject per-goal private-line allowance | Mechanical | P6 | pushing past a match breaks frozen DEL-9 | Allowance flag |
| 46 | DX | Defer release_path override setting | Taste | P3 | setup validator outside touches; D9 + stderr fallback cover detection | Add setting now |
| 47 | Eng | Structure: original arrangement kept; no feature cuts (scope accepted as-is) | Mechanical | P2/P5 | smaller arrangement breaks live_board's 20 KB and mixes concerns | Smaller arrangement |
| 48 | Eng | Codex eng voice unavailable (quota); single-model | Mechanical | P6 | usage limit from Phase 2.5 | Retry |
| 49 | Eng | Accept G1 sidecar for set/resize | Mechanical | P1/P5 | guards.py:9 pattern; goal.py save has no lock | Run-record writes |
| 50 | Eng | Accept G2-G5 (added lines only, every gh write scanned, checks-pending wait, merge-commit target) | Mechanical | P1 | native HIGH findings verified against code | Leave to build |
| 51 | Eng | Accept G6-G13 (byte fallbacks, scan limits, D4 scoping, plan_head, root files, tests, allowlist, token rule) | Mechanical | P1/P5 | each closes a cited gap | - |
| 52 | Eng | Accept G14 test-local gh shim, fakegh untouched | Mechanical | P5 | fakegh maps to the Documentation page (docs.tsv:5) | Editing fakegh |
| 53 | Eng | Accept G15-G19 (regression rewrites, reads headers, nightly heavy rows, decided depth read, settings via fit) | Mechanical | P1 | regression rule; lane checks | - |
| 54 | Eng | TODOS.md not written (no file, outside touches); follow-ups listed in NOT in scope | Mechanical | P3 | goal may not add repo files outside touches | Creating TODOS.md |
| 14 | CEO | Record the docs-format dependency as an obligation, not a scope change | Mechanical | P1 | DEL-6..9 headings exist only on loop/docs-format (c2ada09); the Tests table can't list rows under absent headings | Writing requirement text here |
