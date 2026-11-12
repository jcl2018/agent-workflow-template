# Plan: pending-none

## Implementation plan

Goal: a step reply's `PENDING: none`, `PENDING: nothing` or empty `PENDING:` line never makes a goal wait on the owner
(design: `.loop/designs/pending-none.md`; done lines in `.loop/goals/pending-none.md`, frozen).

1. Add `pending_items(text)` to `skills/workflow-delivery/scripts/guards.py`.
   - Match `^\W*PENDING:[ \t]*(.*)$` with `re.M`, so the item stays on its own line. An empty `PENDING:` no longer
     captures the DEPTH or STEP line below it.
   - Collapse whitespace in each item, as `cmd_record` does now.
   - Drop an item that, with leading and trailing non-word characters removed (`re.sub(r"^\W+|\W+$", "", item)`, so
     `**none**`, `(none)`, a backticked `none` and `none.` all count), fully matches
     `none | nothing | n/a | na | no decisions | no decision`, case-insensitive. Anything else, such as
     `none left` or `nothing to decide yet`, stays a real item: the helper errs toward waiting.
   - Name the pattern `NO_ITEM = re.compile(r"(none|nothing|n/?a|no decisions?)?", re.I)`: the trailing `?` makes the
     empty item a full match, so an empty `PENDING:` is dropped too (a probe of the helper without it left `['']`).
     Drop an item with `NO_ITEM.fullmatch(re.sub(r"^\W+|\W+$", "", item))`. A probe of this helper against 13 replies
     (none, nothing, empty, `**none**`, `n/a`, `N/A.`, `No decisions`, `none left`, real items, a mixed reply, an
     indented bullet, a lowercase `pending:` and CRLF) gave the expected list for each once the empty case is covered.
     guards.py is at 19604 of 20480 bytes and the helper measures about 375 bytes. Write the helper
     first and measure it with `wc -c`. Fallback if it leaves less than 100 bytes of room: put `pending_items` and
     `NO_ITEM` in a new small `skills/workflow-delivery/scripts/reply.py` that imports nothing from guards or role, and
     call it from `goal.py` and `role.py` (no lazy import needed). It is inside the touches list.
2. Use it in `goal.py cmd_record` (line 281): `pending = guards.pending_items(text)`. This shrinks goal.py.
   - Nothing else in `cmd_record` changes. `STEP: pending` with no real item still waits ("see its reply"), and
     `STEP: done` with a `PENDING: none` line records and goes on. With `auto_approve` on, a dropped item is not
     reported as "auto-approved: none". The wait message already carries each real item's text (`goal.py` 315), so a
     reply the helper does not recognize, such as `PENDING: no open questions`, waits visibly and names itself.
3. Use it in `role.need_lane` (line 229): the failed-step exception becomes
   `found[-1] == "failed" and not guards.pending_items(text)`.
   - `guards` imports `role`, so `role.py` imports `guards` inside the function, as it already does at line 161.
   - role.py is at 20095 bytes; the change adds about 40.
4. Toy tests, using fixtures that already exist.
   - `dev/toy/test-goal.sh`, next to the "what a step leaves for the owner" block, with the gated config (`auto_approve`
     off). The existing `low` goal stays on its own branch until the `git switch -q main` that ends its block, and `goal new --here`
     refuses off the base branch. So put the new cases in their own block after that switch, and run
     `git switch -q main` before each `$goal new <slug> --here` (it cuts the goal's branch and switches to it). Give each
     variant its own fresh goal and record its idea step with the toy `step` helper, setting the reply as
     `FAKE_SKILL_OUT='<reply>' step <slug> idea` (the helper prints it through `printf %b`, so `\n` is a newline). Loop
     over the variants `PENDING: none`, `PENDING: nothing`, `PENDING: **none**`, `PENDING: n/a` and `PENDING:`, each followed by
     `\nDEPTH: full\nSTEP: done`. After the loop, one aggregate `ok "PENDING none, nothing, **none**, n/a and empty
     record and go on"` is the line row 1 greps (a row needs exactly one text, so the per-variant asserts feed it).
     - For each: assert `RECORDED`, status `running`, no `waiting`, and the flow's next step is named (`NEXT: flow.py <slug> plan`). Done line 1
       says "records the step and goes on", so the empty-line case (the one that used to swallow the next line) gets
       its own `check`, and its recorded flow entry starts with `done` and holds no swallowed text.
     - A sixth fresh goal, at idea: `PENDING: none` on one line, `PENDING: approve the plan` on the next, then
       `DEPTH: full` and `STEP: done` last, still waits (the depth-line rule, `guards.py` 78-83, refuses a done reply with
       no DEPTH line before any wait, so every `STEP: done` reply in these toys carries one), and the ask names only the real item (done line 2, mixed case): assert that the ask contains `approve the plan` and
       does not contain `none`, so a later change to the depth-line rule cannot make the case wait for another reason. It ends in
       `STEP: done` on purpose, so only the real item can cause the wait. The existing real-item case ends in
       `STEP: pending`, which waits by itself and cannot tell the two apart. One aggregate `ok` line ("a real PENDING
       item among none lines still waits, with its own ask") is the text row 2 greps. Each aggregate `ok` is printed only when every one of its asserts passed (a failing
       variant prints `bad` and no aggregate, so the row greps nothing and fails).
     - A direct check of the helper's return values, one line in the same block: `PENDING: none left` returns
       `['none left']`, `PENDING: N/A.`, `PENDING: No decisions`, `PENDING: --` (bare punctuation reduces to empty, so it is dropped on
       purpose) and a bare `PENDING:` return `[]`, and a real item is returned whole.
       `PENDING:` stays case-sensitive as the old regex was; only the item words are case-insensitive.
     - A seventh fresh goal, at idea, settles the two edge replies. `PENDING: none\nDEPTH: full` with no STEP line stays
       a format slip: on the non-session path the toy runs it is a failed try ("gave no STEP line", the same result the
       existing `nothing useful` case has), because nothing says the step finished; it used to wait only because the
       word none counted as an item. On the session path the same reply is already `refuse_no_try` with no try used
       (`goal.py` lines 283-285), and that path is unchanged. Then `PENDING: none\nSTEP: pending` still waits, with the ask
       "see its reply", because the step itself asked to wait. This is a deliberate exception to done line 1 (that line is about a step
       that ends `done`), also under `auto_approve`, where it records with the step's own "pending gate" wording.
       Both are asserted so the choice is on record.
   - The existing `PENDING: approve the plan as written` case stays as the guard for done line 2 (a real item waits,
     the ask carries the item, the words are unchanged).
   - In the "No gates" block (`auto_approve` on): after the existing `open` goal's cases, `git switch -q main`, start a new
     goal `ng` with `$goal new ng --here`, and record its idea step with `PENDING: none\nDEPTH: full\nSTEP: done`: it
     prints `RECORDED`, never `AUTO-APPROVED ... none`. The existing `PENDING: approve the design` auto-approve case
     stays as is. Match the recorded flow entry as a prefix (`^done`), because `check_record` can append a stamp.
   - `dev/toy/test-lanes.sh`, beside the q1/q2 lines (193-196): a third reply `PENDING: none\nSTEP: failed\n` is not
     refused with `LANE_MISSING` (the failed step needs no lane): assert that the output has no `LANE_MISSING` and does
     have `NOT_RUN_BY_FLOW`, the next refusal it reaches. Add it as its own `check`, not by changing the
     existing `= 2` count over q1 and q2 (`PENDING: x\nSTEP: failed` still gets `LANE_MISSING`). Add the file's
     `# Value:` comment above it. This guards the second reader and has no done line, so it gets no regression row.
   - Add `skills/workflow-delivery/scripts/guards.py` and `role.py` to test-goal.sh's `# reads:` header (it lists
     goal.py and flow.py only), and `guards.py` to test-lanes.sh's header (it lists role.py, not guards.py), so the lane
     reuse knows a change to the helper reaches these rows.
5. Two regression rows in `.loop/regression.tsv`, one per done line, added with `regression.py add ... --goal pending-none:N`, then each
   run broken with `regression.py red ID --break CMD` so it carries a seen-failing date. `red` breaks a copy of
   `HEAD`, so the helper, the call sites and the toy cases are committed first (by the implementing step); the break
   command is a `sed` on that copy.
   - `pending-none-goes-on` (done line 1): the five replies in the loop record and go on. Goal `pending-none:1`.
   - `pending-real-waits` (done line 2): a real item still waits, with the ask unchanged. Goal `pending-none:2`.
   - Level `land`, because a goal's lane runs the affected land rows and the nightly rows would not prove the goal.
     The command is `bash dev/toy/test-goal.sh 2>&1 | grep -qF "PASS: <text>"`, where `<text>` is the exact aggregate `ok`
     string, kept as a constant. Confirm in the `red` run that the broken toy finishes inside the row timeout (a SIGTERM
     flake under load is on record in this area).
   - The goal column is `pending-none:N`, never `DEL-3` or `DEL-9` (DEL-9 is another requirement here). A row names its done
     line, so the `need_lane` check, which is not a done line, is a plain toy check and not a row.
   - Each `--break` rewrites the helper in the throwaway copy only, with its own break: row 1 breaks it by returning
     every matched item unfiltered (a `none` waits again), row 2 by returning an empty list (a real item no longer
     waits). Write the helper's final `return` as one fixed line so the `sed` finds it, and make each break fail loudly if it
     changed nothing (`sed -i.bak ... file && ! cmp -s file file.bak`). Both breaks are named in the commit, and each must turn exactly its own row red and leave the other row green.
   - The commit message says that `PENDING: none` with no STEP line is now a failed try, not a wait.
6. Docs.
   - `docs/wiki/Tests.md` is generated: run `python3 skills/workflow-docs/scripts/criteria.py render` (there is no
     `docs.py render`; `docs.py check` only reports a stale page) so the two rows appear. `Touches` already names it.
   - `docs/wiki/Delivery.md`: no requirement text changes (DEL-3 is Reviewed and its words are locked). Its Tests table
     is generated; re-render, and only add words to Usage if a `record` entry there describes PENDING lines.
7. Verify.
   - `bash dev/toy/test-goal.sh`, `bash dev/toy/test-lanes.sh`, `regression.py criteria`, `criteria.py render --check`, `docs.py check` and the
     size checks (guards.py, role.py, goal.py under 20480 bytes).
   - A by-hand check with a real reply file: `PENDING: none` then `STEP: done` records; `PENDING: pick a name` waits.

Checked: the only readers of a `PENDING:` reply line in delivery are `goal.py` 281 and `role.py` 229 (`fit.keep` and
`guards.check_record` never see it; the monitoring `PENDING` is mend.py's own word). `references/commands.md` line 497
describes the failed-step rule as "no `PENDING:` line"; it reads slightly stale after this change (it should say "no real
PENDING item") and is outside the touches list, so it is a named follow-up, and the PR body says so.

NOT in scope: `flow.py` prompt text (it already tells the step to list real decisions only); the lines at
`flow.py` 272 and 354 that echo `PENDING:` and `STEP:` lines for display (an echoed `PENDING: none` is harmless);
the monitoring and release scripts; any change to how `auto_approve` or `STEP: pending` work; one reply parser for
STEP, PENDING and DEPTH (deferred: a candidate follow-up goal, outside this goal's touches and the size caps).


<!-- autoplan-accepted:ceo -->
- `guards.pending_items(text)` returns the real owner decisions of a reply: one item per `PENDING:` line, items matched on that line only, an item that is empty or only none, nothing, n/a or no decision(s) (case-insensitive, surrounding non-word characters ignored, so `**none**` and `(none)` count) dropped. Test: the five replies in the toy loop (done line 1), and a real item still returned.
- `goal.py cmd_record` and `role.need_lane` both use it; neither keeps its own PENDING regex. Test: toy goal records with `PENDING: none`, and a failed step with `PENDING: none` needs no lane (a toy check, no row).
- A reply with `PENDING: none` and no STEP line is a failed try like any reply with no STEP line; `PENDING: none` with `STEP: pending` still waits ("see its reply"). Test: the seventh fresh goal in the toy block.
- A real PENDING item waits exactly as before, with the same ask and words (done line 2). Test: the existing real-pending case plus a mixed none-and-real reply.
- Under auto_approve, `PENDING: none` with `STEP: done` records and is never reported as auto-approved. Test: the "No gates" block case.
- The helper is measured first and moves to `reply.py` if it leaves under 100 bytes of room; each aggregate `ok` prints only if every assert passed; each row's break turns only its own row red; the commit message names the no-STEP change.
- Two regression rows keyed `pending-none:1` and `pending-none:2`, level land, each with a seen-failing date; guards.py, goal.py and role.py stay under 20480 bytes.
<!-- /autoplan-accepted:ceo -->

<!-- autoplan-accepted:eng -->
- The empty `PENDING:` item is dropped: `NO_ITEM` has an empty alternative (a probe without it returned `['']`). Test: the empty-reply variant in the toy loop and the helper-values check.
- Every `STEP: done` toy reply carries a `DEPTH: full` line, including the mixed none-and-real reply, so the depth-line rule cannot refuse it before the wait. Test: the mixed goal waits with the real item's ask.
- Tests.md is rendered with `criteria.py render` and checked with `criteria.py render --check` and `docs.py check`; there is no `docs.py render`.
- Bare punctuation (`PENDING: --`) is dropped by design and tested; each break fails loudly if its `sed` changed nothing; the mixed-goal assert is strict (the ask holds `approve the plan` and not `none`).
- Rows get their seen-failing date with `regression.py red`, which breaks a copy of HEAD, so the implementation is committed before `red` runs; each row's break turns only its own row red.
<!-- /autoplan-accepted:eng -->
## Review record

- Plan review: complete (autoplan: CEO and Eng ran; Design and DX skipped, no UI or developer-tool scope). Approved by no one: the run approves, merges, pushes and commits nothing.
- Outside voice (Codex): skipped, it needs network.

### CEO phase, Step 0

Mode: SELECTIVE EXPANSION (autoplan default). Added capability inside one fix; nothing was added.

Premise table (receipts are file:line in this worktree):

| premise | claim | receipt | verdict |
|---|---|---|---|
| P1 | `cmd_record` reads items with `^\W*PENDING:\s*(.+)$` | goal.py:281 | verified |
| P2 | `\s*` spans a newline, so an empty `PENDING:` takes the next line | goal.py:281 (regex) | verified |
| P3 | any item makes the goal wait, or "auto-approved: none" with auto_approve | goal.py:287,303-304,313 | verified |
| P4 | `need_lane` has its own `PENDING:` test | role.py:229 | verified |
| P5 | role.py may import guards lazily | role.py:161 | verified |
| P6 | guards.py and role.py have room under 20480 bytes | wc -c: 19604, 20095 | verified |
| P7 | the toy fixture for a real PENDING item runs with auto_approve off | test-goal.sh:87 before :131 | verified |
| P8 | flow.py prompt already asks for real decisions only | flow.py:65 | verified |

REALITY: premise-table pass 8 premises, unverified=0, goal.py:281
REALITY: already-done pass no pending_items helper or fix on origin/main in the touched files (local origin/main log, no fetch: no network) guards.py:1
REALITY: surface-check pass only `goal.py record`, `regression.py add|red`, `docs.py render|check` named, all in --help goal.py:1
REALITY: binding-decisions pass none recorded for this branch; the goal's frozen done lines bind the plan goal.md:1
REALITY: numbers pass sizes measured with wc -c ([measured: wc -c]) guards.py:1
REALITY: deferred-asks pass no linked issue, none left out goal.md:1
REALITY: pr-count pass one PR for one fix goal.md:1

0A premise challenge: the real problem is a wasted owner round trip when a step says nothing is pending. The plan solves
it at the one reader (`pending_items`), not by changing the prompt text, which is right: a model will keep writing
"PENDING: none" however the prompt reads, so the parser must tolerate it. Do-nothing cost: three round trips seen so far.

0B existing code leverage: `role.py:161` already imports guards lazily (the pattern to copy). The `PENDING` line is
parsed in two places (goal.py:281, role.py:229) and in two display echoes (flow.py:272,354); one helper covers both
readers. goal.py `STEP` regex stays.

0C dream state: CURRENT two ad hoc regexes, one of them wrong. THIS PLAN one helper both readers use. 12-MONTH IDEAL one
reply parser (STEP, PENDING, DEPTH) in a single module. This plan moves toward it; the full parser is out of scope.

0D alternatives: A) the plan (helper, tolerant list). B) fix only the regex (`[ \t]*`) and drop literal "none" in goal.py
alone: smaller, but `need_lane` keeps its own wrong test and the "none" rule has no single home. C) tighten the flow.py
prompt only: leaves the parser wrong and out of scope. A wins on completeness and DRY (P1, P4); B and C are rejected.

0E/0F/0G scope: no expansion is proposed. HOLD checks: 3 source files plus 2 toy files, the tsv, 2 generated wiki
pages, under 8; no new class. One real simplification was taken: the three replies run through the existing goal
helpers instead of a new test file. Deferred: a single reply parser (see TODOS below), not blocking.

0I temporal: hour 1 write the helper and the two call sites; hours 2-3 the toy cases (the surprise is that `low` is
mid-flow, so fresh goals are needed); hours 4-5 regression rows and `regression.py red` (the break command must edit a
copy); hour 6 wiki render and the size checks (guards.py gets within about 30 bytes of the cap).

<!-- autoplan-accepted:ceo -->
- `guards.pending_items(text)` returns the real owner decisions of a reply: one item per `PENDING:` line, items matched on that line only, an item that is empty or only none, nothing, n/a or no decision(s) (case-insensitive, surrounding non-word characters ignored, so `**none**` and `(none)` count) dropped. Test: the five replies in the toy loop (done line 1), and a real item still returned.
- `goal.py cmd_record` and `role.need_lane` both use it; neither keeps its own PENDING regex. Test: toy goal records with `PENDING: none`, and a failed step with `PENDING: none` needs no lane (a toy check, no row).
- A reply with `PENDING: none` and no STEP line is a failed try like any reply with no STEP line; `PENDING: none` with `STEP: pending` still waits ("see its reply"). Test: the seventh fresh goal in the toy block.
- A real PENDING item waits exactly as before, with the same ask and words (done line 2). Test: the existing real-pending case plus a mixed none-and-real reply.
- Under auto_approve, `PENDING: none` with `STEP: done` records and is never reported as auto-approved. Test: the "No gates" block case.
- The helper is measured first and moves to `reply.py` if it leaves under 100 bytes of room; each aggregate `ok` prints only if every assert passed; each row's break turns only its own row red; the commit message names the no-STEP change.
- Two regression rows keyed `pending-none:1` and `pending-none:2`, level land, each with a seen-failing date; guards.py, goal.py and role.py stay under 20480 bytes.
<!-- /autoplan-accepted:ceo -->

### CEO phase, voices and review sections

Voices: native CEO reviewer completed (7 medium findings); Codex outside voice skipped (needs network). Mode `[subagent-only]`.

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Dimension                             Claude  Codex  Consensus
  1. Premises valid?                    ok      N/A    N/A
  2. Right problem to solve?            ok      N/A    N/A
  3. Scope calibration correct?         ok      N/A    N/A
  4. Alternatives sufficiently explored? gap    N/A    N/A  (allowlist vs reply schema)
  5. Competitive/market risks covered?  ok      N/A    N/A  (internal tooling)
  6. 6-month trajectory sound?          gap     N/A    N/A  (spelling drift of "none")
```

Native findings and dispositions (all auto-decided; none is a User Challenge, none changes the frozen done lines):
1. Allowlist, not structure (taste): kept. A leading-none-plus-note rule would have to guess which notes carry a decision (P5, explicit over clever). The miss costs one visible wait. Follow-up (reply parser, prompt wording) stays in NOT in scope.
2. A false wait is visible: the wait message carries the item text (goal.py:315). Added to the plan, step 2.
3. The no-STEP change: kept, named in the commit message (plan step 5).
4. Byte budget: the plan now measures first and has a fallback module `reply.py` (step 1).
5. Test volume: each aggregate `ok` prints only if all its asserts passed, and each break turns only its own row red (step 4, step 5).
6. Two readers remain: the follow-up is recorded in NOT in scope; commands.md line 497 stays true.
7. Regret scenario `PENDING: none, all clear`: waits visibly (see 2); accepted.

Section 1 Architecture: the change is one function and two call sites.
```
 reply file --> guards.pending_items --> goal.cmd_record (wait / auto-approve / record)
                      ^
                      +-------------- role.need_lane (failed-step exception)
 (fallback: reply.py holds the helper; guards and role import it)
```
Data flow, four paths: happy (`STEP: done`, no item) records; nil (no PENDING line) records; empty (`PENDING:` or none-like)
records, and the next line is no longer swallowed; error (no STEP line) is a failed try. No state machine is added.
Section 2 Error and rescue registry (one new function; it raises nothing):

| codepath | what can go wrong | rescued | user sees |
|---|---|---|---|
| pending_items | unrecognized none-phrase | waits (by design) | WAITING with the item text |
| pending_items | no STEP line with a none item | failed try | TRY n OF 3 FAILED, "gave no STEP line" |
| need_lane | none item with STEP: failed | no lane needed | normal failed-try output |

Section 3 Security: no new input source; the helper reads a file the flow already reads; regex is linear (no nested
quantifier). Nothing is logged that was not before; items are whitespace-collapsed as before. No issues found.
Section 4 Edge cases: markup (`**none**`), trailing dots, `n/a`, leading blank lines (`^\W*` crosses them, as before), `\r`
(collapsed by split). Covered by the toy loop and the helper check. Section 5 Quality: one regex, one set; no new class;
`NO_ITEM` named for what it is. Section 6 Tests: diagram below. Section 7 Performance: one regex over a reply file; none.
Section 8 Observability: the existing `save(state, "... pending: ...")` log line and the wait message. Section 9 Rollout:
a script edit, no migration, no flag; rollback is a revert. Section 10 Trajectory: reversibility 5/5; debt: the
reply parser is still split (STEP regex in three files); the follow-up is named. Section 11 Design: SKIPPED (no UI scope).

```
 codepath / reply                          test
 PENDING: none|nothing|**none**|n/a|empty  test-goal.sh loop (row pending-none-goes-on)
 none + real item + STEP: done             test-goal.sh mixed goal (row pending-real-waits)
 real item, STEP: pending                  existing line-87 case
 none, no STEP line                        test-goal.sh edge goal (failed try)
 none + STEP: pending                      test-goal.sh edge goal (waits)
 none + STEP: done, auto_approve on        test-goal.sh "ng" goal (RECORDED)
 none + STEP: failed (need_lane)           test-lanes.sh third reply
 helper values (none left kept)            test-goal.sh helper check
```

Failure modes registry:

| codepath | failure mode | rescued | test | user sees | logged |
|---|---|---|---|---|---|
| pending_items | spelling the list misses | yes (waits) | helper check | WAITING + item | yes |
| cmd_record | none item + done | yes | loop | RECORDED | yes |
| need_lane | none item + failed | yes | lanes check | failed try | yes |

Critical gaps: 0. NOT in scope and What already exists: see the plan body (role.py:161 lazy import, the existing line-87 and
nothing-useful toy cases, regression.py add/red, docs.py render are reused). Dream state delta: one reply parser is the
ideal; this moves one of its three pieces. Stale diagram audit: no ASCII diagram lives in the touched files.

CEO Completion Summary:
```
  | Mode selected        | SELECTIVE EXPANSION                      |
  | Step 0               | no expansion; 2 deferrals, 1 skip         |
  | Section 1..10        | 0 critical; findings above (7 medium)     |
  | Section 11 (Design)  | SKIPPED (no UI scope)                     |
  | NOT in scope         | written (5 items)                         |
  | What already exists  | written                                   |
  | Dream state delta    | written                                   |
  | Error/rescue registry| 3 rows, 0 CRITICAL GAPS                   |
  | Failure modes        | 3 total, 0 CRITICAL GAPS                  |
  | TODOS.md updates     | 0 (no TODOS.md; follow-ups in NOT in scope)|
  | Scope proposals      | 7 proposed, 5 accepted (EXP + SEL)        |
  | CEO plan             | summary kept in the run folder            |
  | Outside voice        | codex skipped (network); native completed |
  | Lake Score           | N/A                                       |
  | Diagrams produced    | 2 (architecture, test)                    |
  | Unresolved decisions | 0                                         |
  | Reality rows         | 7/7 rows, 0 unverified                    |
```
PLAN_REALITY: ceo (see the REALITY lines above; the check helper is run at close)

### Eng phase, Scope Challenge

Step 0 result: scope accepted as-is. Complexity: 3 source files (guards.py, goal.py, role.py) plus an optional fallback
module, 2 toy files, the tsv, 2 generated wiki pages = 8 changed files at most and 1 optional new module, no new class or
service (an estimate, counted once). That is at the 8-file line only if the fallback module and both generated pages are
counted; the structure question is auto-decided (`plan-eng-review-structure`): the smaller arrangement (helper in
guards.py, no new module) is the plan's own default, the original arrangement adds `reply.py` only when the byte
budget forces it. Both keep every approved behavior and test.

Eng probes (bounded, current behavior only; nothing in the repo was changed):
1. A probe of the proposed helper over 13 replies showed the empty item survives a plain none-list (`['']`), so the pattern
   needs the empty alternative. Fixed in the plan (step 1).
2. `guards.check_record` runs for a `STEP: done` reply even when a real item is present, and refuses a reply with no DEPTH
   line (guards.py:78-83), so the mixed toy reply needs a DEPTH line. Fixed in the plan (step 4).
3. `docs.py render` does not exist; Tests is rendered by `criteria.py render` (criteria.py:13). Fixed (step 6, 7).
4. `regression.py red` breaks a copy of HEAD (regression.py:213), so rows need the implementation committed first. Added (step 5).
5. `import guards` works from outside the repo (test-guards.sh:225 does it), so the helper check can import it.

REALITY: premise-table pass 9 premises, unverified=0 (adds: empty item survives, check_record DEPTH rule, red breaks HEAD) guards.py:78
REALITY: already-done pass no pending_items on origin/main (local log, no fetch: no network) guards.py:1
REALITY: surface-check finding docs.py render was named and does not exist; corrected to criteria.py render criteria.py:13
REALITY: binding-decisions pass none recorded; frozen done lines bind goal.md:1
REALITY: numbers pass guards.py 19604, role.py 20095, goal.py 19100, helper about 375 bytes ([measured: wc -c, probe]) guards.py:1
REALITY: deferred-asks pass no linked issue goal.md:1
REALITY: pr-count pass one PR goal.md:1

<!-- autoplan-accepted:eng -->
- The empty `PENDING:` item is dropped: `NO_ITEM` has an empty alternative (a probe without it returned `['']`). Test: the empty-reply variant in the toy loop and the helper-values check.
- Every `STEP: done` toy reply carries a `DEPTH: full` line, including the mixed none-and-real reply, so the depth-line rule cannot refuse it before the wait. Test: the mixed goal waits with the real item's ask.
- Tests.md is rendered with `criteria.py render` and checked with `criteria.py render --check` and `docs.py check`; there is no `docs.py render`.
- Bare punctuation (`PENDING: --`) is dropped by design and tested; each break fails loudly if its `sed` changed nothing; the mixed-goal assert is strict (the ask holds `approve the plan` and not `none`).
- Rows get their seen-failing date with `regression.py red`, which breaks a copy of HEAD, so the implementation is committed before `red` runs; each row's break turns only its own row red.
<!-- /autoplan-accepted:eng -->

### Eng phase, voices and review sections

Voices: native eng reviewer completed (5 low to medium findings, no blockers); Codex outside voice skipped (needs network).
Mode `[subagent-only]`.

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               yes     N/A    N/A
  2. Test coverage sufficient?         yes     N/A    N/A   (after fixes)
  3. Perf risks + budget/bench named?  yes     N/A    N/A   (size caps named and measured; no hot path)
  4. Security threats covered?         yes     N/A    N/A   (linear regex, local file)
  5. Error paths handled?              yes     N/A    N/A
  6. Deployment risk manageable?       yes     N/A    N/A   (script edit, revert to roll back)
```

Native findings and dispositions (auto-decided, all applied to the plan):
1. Bare punctuation (`PENDING: --`) is dropped: kept and documented, added to the helper-values check. Principle P5.
2. `references/commands.md` line 497 reads slightly stale: outside the touches list, so a named follow-up; the PR body says so.
3. Rows run the whole toy: PASS strings kept as exact constants; the `red` run confirms the broken toy fits the row timeout.
4. A `sed` break can silently no-op: each break ends in `&& ! cmp -s file file.bak`; the helper's `return` is one fixed line.
5. The mixed case could wait for the wrong reason: the assert is strict (the ask holds `approve the plan` and not `none`).
Earlier eng probes (empty item, DEPTH rule, `criteria.py render`, `red` on HEAD) were corrected before dispatch.

Section 1 Architecture (design-twice: no new module or public surface unless the byte budget forces `reply.py`, so the check
is one line; the second shape is `reply.py`, which hides the same behavior behind the same one-function surface and
removes the lazy import, at the cost of one more file. Pick: guards.py first, `reply.py` as the measured fallback.
Red flags screened: shallow module no; information leakage no (one regex, one list); pass-through no; split ownership
no (after the change one function owns the PENDING grammar); two ways to do one task no (both readers call it); hand-synced
list no).
```
  goal.py cmd_record --\
                        >-- guards.pending_items --(NO_ITEM, 1 regex)
  role.py need_lane  --/        (role imports guards lazily, as at role.py:161; guards imports role at the top)
```
Coupling: goal.py already imports guards (goal.py:33); role.py already lazy-imports it (role.py:161). No new coupling.
Section 2 Code quality: one function of three lines, one constant; DRY gain: two regexes become one (goal.py:281, role.py:229);
no diagram in the touched files goes stale. Section 3 Test review (diagram below, plus the artifact on disk). Section 4
Performance: one regex over one reply file per recorded step; no budget or bench needed (not a hot path); sizes measured.

```
CODE PATHS                                                USER FLOWS (a worker records a step)
[+] guards.pending_items (new)                            [+] reply says none
  ├── [★★★ TESTED] none/nothing/**none**/n/a/empty            ├── [★★★ TESTED] done, gated: RECORDED (loop)
  ├── [★★★ TESTED] none left / real item kept                 ├── [★★★ TESTED] done, auto_approve: RECORDED (ng goal)
  ├── [★★★ TESTED] mixed none + real item                     ├── [★★  TESTED] STEP: pending: waits (edge goal)
  └── [★★  TESTED] bare punctuation, CRLF (helper check)       └── [★★  TESTED] no STEP line: failed try (edge goal)
[+] goal.cmd_record (changed line 281)                    [+] reply has a real item
  ├── [★★★ TESTED] wait path, ask names the real item         ├── [★★★ TESTED] existing line-87 case
  └── [★★★ TESTED] auto_approve path                          └── [★★★ TESTED] mixed case, ask strict
[+] role.need_lane (changed line 229)                     [+] failed step
  ├── [★★  TESTED] none + failed: no LANE_MISSING             └── [★★  TESTED] test-lanes third reply (NOT_RUN_BY_FLOW)
  └── [★★★ TESTED] PENDING: x + failed: LANE_MISSING (existing q2)
COVERAGE: 12/12 planned paths with a planned test (these are plan proposals, not yet written)
```
No E2E or eval is needed: no LLM or prompt change (flow.py prompt text is untouched).

Failure modes registry:

| codepath | failure mode | rescued | test | user sees | logged |
|---|---|---|---|---|---|
| pending_items | pattern drops a real decision | no: "none"-like words only, full match | helper check (`none left` kept) | would hide a decision; the full-match rule prevents it | n/a |
| pending_items | empty item kept (`['']`) | fixed (empty alternative) | loop empty variant | no wait | yes |
| cmd_record | none + done under gate | yes | loop | RECORDED | yes |
| need_lane | none + failed | yes | lanes check | normal failed try | yes |
| regression break | sed no-ops | yes (cmp check) | red run | row stays unseen-failing, loud | yes |

Critical gaps: 0.
NOT in scope: see the plan body. What already exists: role.py:161 lazy import, goal.py:315 wait message, the line-87 and
`nothing useful` toy cases, `regression.py add|red`, `criteria.py render`. Worktree parallelization: sequential
implementation, no parallelization opportunity (one module, three files).

Implementation Tasks (eng):
- [ ] T1 (P1, human: ~1h / CC: ~10min) — workflow-delivery — add `pending_items` and `NO_ITEM` to guards.py, use it in goal.py and role.py. Verify: probe of 13 replies, `wc -c` under 20480.
- [ ] T2 (P1, human: ~2h / CC: ~20min) — dev/toy — add the toy loop, mixed, edge, ng, helper-values and lanes cases, plus the reads headers. Verify: `bash dev/toy/test-goal.sh`, `bash dev/toy/test-lanes.sh`.
- [ ] T3 (P2, human: ~30min / CC: ~5min) — regression — add two rows, run `red` with each break. Verify: `regression.py criteria`.
- [ ] T4 (P2, human: ~15min / CC: ~3min) — docs — `criteria.py render`, `docs.py check`. Verify: `criteria.py render --check`.
- [ ] T5 (P3, follow-up) — references/commands.md line 497 wording; one reply parser. Outside this goal's touches.

Eng Completion Summary:
```
  Step 0: Scope Challenge — scope accepted as-is
  Reality rows: 7/7 applicable rows emitted, 0 unverified premises
  Architecture Review: 0 issues found (design-twice and red flags screened)
  Code Quality Review: 0 issues found
  Test Review: diagram produced, 5 gaps identified by the reviewers, all closed in the plan
  Performance Review: 0 issues found
  NOT in scope: written
  What already exists: written
  TODOS.md updates: 0 items (no TODOS.md; 2 follow-ups named in the plan)
  Failure modes: 0 critical gaps flagged
  Unresolved decisions: 0 in this review
  Outside voice: codex skipped (network); native completed
  Parallelization: 1 lane, 0 parallel / 1 sequential
  Lake Score: N/A
```

### Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Mode SELECTIVE EXPANSION, no expansion added | Mechanical | P3 | a fix with a known cause | HOLD, REDUCTION |
| 2 | CEO | One helper for both readers | Mechanical | P4 DRY | two regexes, one wrong | regex-only fix in goal.py |
| 3 | CEO | Keep a none-word allowlist, not a structural rule | Taste | P5 | guessing which notes carry a decision is clever | leading-none-plus-note rule |
| 4 | CEO | Defer the single reply parser and skip the flow.py prompt change | Mechanical | P3 | outside touches and size caps | both |
| 5 | CEO | `PENDING: none` with no STEP line is a failed try on the non-session path | Taste | P5 | nothing says the step finished; same as any no-STEP reply | keep waiting |
| 6 | CEO | Wider token set and markup tolerance (`n/a`, `**none**`) | Mechanical | P1 | models write these; one regex | none, nothing and empty only |
| 7 | CEO | Spec review stopped at its three-launch cap; all findings applied | Mechanical | P6 | cap in the method | a fourth launch |
| 8 | Eng | Empty alternative in `NO_ITEM` | Mechanical | P1 | probe showed `['']` | plain list |
| 9 | Eng | Helper in guards.py, `reply.py` as the measured fallback | Taste | P3 | 375 bytes fits; fallback kept if it does not | new module now |
| 10 | Eng | `criteria.py render`, not `docs.py render` | Mechanical | P5 | the named command does not exist | none |
| 11 | Eng | need_lane check is a plain toy check, not a regression row | Mechanical | P5 | a row names a done line; it is not one | a row keyed pending-none:1 |
| 12 | Eng | commands.md line 497 left as a named follow-up | Mechanical | P3 | outside the touches list | widening touches |
| 13 | Gate | Codex outside voice skipped in both phases | Mechanical | P6 | needs network; native voices ran | none |

### Final gate summary (not approved; nothing was approved, merged, pushed or committed)

Taste decisions surfaced (auto-decided, owner may override): D3 allowlist over a structural rule; D5 no-STEP reply is a
failed try; D9 helper in guards.py with `reply.py` as the fallback. User Challenges: none. Owner-only decisions: none.
Cross-phase themes: the none-word list is the recurring soft spot (CEO finding 1 and 7, Eng finding 1); it waits visibly,
so it is cheap to detect. Deferred: a single reply parser for STEP, PENDING and DEPTH; the commands.md wording. This repo
has no TODOS.md, so both are written in the plan body only.

Aggregated implementation tasks:
- [ ] T1 (P1, human: ~1h / CC: ~10min) — workflow-delivery — add `pending_items` and `NO_ITEM`, use in goal.py and role.py
- [ ] T2 (P1, human: ~2h / CC: ~20min) — dev/toy — add the toy loop, mixed, edge, ng, helper-values and lanes cases
- [ ] T3 (P2, human: ~30min / CC: ~5min) — regression — add two rows, `red` each with its own break
- [ ] T4 (P2, human: ~15min / CC: ~3min) — docs — render Tests with `criteria.py render` and check

## Review record

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` (via autoplan) | Scope & strategy | 1 | CLEAR (not logged: no approval) | mode SELECTIVE_EXPANSION, 0 critical gaps, 7 findings resolved |
| Outside Review | codex (skipped, needs network) | Independent 2nd opinion | 0 | skipped | no completed external review |
| Eng Review | `/plan-eng-review` (via autoplan) | Architecture & tests (required) | 1 | CLEAR (not logged: no approval) | 5 issues, 0 critical gaps, all applied |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | skipped (no UI scope) | none |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | skipped (no developer-facing scope) | none |

**OUTSIDE COVERAGE:** Codex, CEO phase: skipped (network). Codex, Eng phase: skipped (network). Native subagent reviewers completed in both phases.
**VERDICT:** CEO + ENG reviewed by native voices only; no human approval given or sought by this run.

NO UNRESOLVED DECISIONS
