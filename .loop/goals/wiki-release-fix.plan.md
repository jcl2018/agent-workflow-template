# Plan: wiki-release-fix

Goal: `.loop/goals/wiki-release-fix.md` (done lines frozen). Design: `.loop/goals/wiki-release-fix.design.md` (APPROVED).
Status: autoplan stopped at its final gate (gate_rev 2), not approved. The recommended gate outcome (`rec`) is folded into Steps 2 and 3 below and marked "(gate rec)". See the Review record.

## Implementation plan

### What is wrong

On main at v0.27.17, `bash dev/toy/ci-env.sh bash dev/toy/test-wiki.sh` fails with `FAIL: goal did not reach a pull request`, so the `wiki-release` row (`.loop/regression.tsv`, DEL-5) is red. The code was wrong, not the test. v0.27.17 (settings-table) made two slips in `skills/workflow-docs/scripts`:

1. `render.render()` (what `criteria.py render` runs) calls `refresh()` with no criteria gate. `refresh()` writes the template, Settings and Automation blocks into README.md and Home.md. `docs.py check`, `docs.py publish` and the workflow-docs SKILL.md all gate those blocks on `"criteria": true`. The test-wiki toy is criteria-off (`setup.py --bare`) and its README holds no blocks, so the ungated render appended all three to README. The QA lane's prep (`lanekit.py prep`) runs `criteria.py render`. README is not a prep path, so the lane refused with LANE_DIRTY and the goal never reached a pull request.
2. `pageformat.frontdoor()` (DOC-5) read README with the generated blocks in it. render appends the Settings block after README's last section, so `<!-- settings:begin -->` lands under `## How to use` and DOC-5 counted it as a second intro line. `pageformat.home()` (DOC-4) already blanked the blocks, but frontdoor did not. Checked on da4bb9c, before the pageformat fix: `test-docs-format.sh` prints `FAIL: good README` and `FAIL: good pages: FORMAT README:19: How to use: DOC-5 only one intro line per section (got '<!-- settings:begin -->')`. `test-docs-issues.sh` prints the same DOC-5 failure for `none`, `good pages` and `guide`.

### Step 1: the fix (done, two commits)

- 7e47366, `render.py`, one line: iterate `refresh(root, args.check)` only when `config_of(root).get("criteria")` is truthy. `docs.py check` and `publish` already use this gate. Criteria-off repos get the pre-v0.27.17 behaviour back: render touches only the Tests tables. Criteria-on repos are unchanged.
- 4af8853, `pageformat.py`, +8/-3: one shared `unblocked(text)` that blanks the generated blocks and keeps line numbers. It moved out of `home()` and `frontdoor()` now uses it too.
- No new file under skills/. No change to `setup.py`, `lanekit.py`, `refresh()` or `docs.py`.

### Step 2: a direct render assertion in dev/toy/test-wiki.sh

Add this right after the `auto_merge` config heredoc. At that point only `.loop/config.json` is dirty and Home.md does not exist yet.

```bash
# criteria-off toy: render must leave README alone (v0.27.17 appended the template, Settings and Automation blocks)
if out=$(python3 "$here/skills/workflow-docs/scripts/criteria.py" render 2>&1); then
  git diff --quiet HEAD -- README.md && ok "a criteria-off render leaves README alone" \
    || bad "criteria-off render wrote README ($(grep README <<<"$out" | tr '\n' ' ')). Fix: render.render() must gate refresh() on criteria"
else
  bad "criteria-off render failed: $out"
fi
git checkout -q -- README.md
```

- A render crash prints only its own FAIL line, with the error, and no contradictory PASS. (gate rec d3: the render failure is kept apart from the assertion.)
- `git diff --quiet HEAD` uses git's own exit status, so a failed git call cannot print the clean-README PASS. (gate rec d2)
- The FAIL line names the blocks render wrote (render prints `WROTE README.md (settings block)`) and says where the fix goes.
- `git checkout -- README.md` restores README either way. A regression is then not committed by the next `git add -A`, and the end-to-end path (the goal reaches a pull request) still exercises it.
- Add `skills/workflow-docs/scripts/criteria.py` to the script's `# reads:` header.
- No new row is needed. `wiki-release` and `wiki-release-pycache` already fail on any `^FAIL` line from test-wiki.sh.
- Rejected from gate rec d2 and d3 (P5, explicit over clever): stable error codes, retries and recovery steps in a toy test. The FAIL line already names the cause and the fix.

### Step 3: guard the DOC-5 slip by tightening the existing format-frontdoor row (gate rec d1)

Today no row covers the pageformat fix. The `test-docs-format.sh` lines that fail on da4bb9c (`good pages`, `good README`) are not grepped by any row. The reviewed draft added a new DOC-5 row. That row would also re-render the Tests table on `docs/wiki/Documentation.md`, which is outside this goal's files, and both outside-voice rounds showed that its grep (`PASS: DOC-5 a front door of quoted phrases passes`) also passes when the checker crashes. So tighten the existing `format-frontdoor` row instead (land, DOC-5, `.loop/regression.tsv:257`). Only its command changes:

```bash
out=$(bash dev/toy/test-docs-format.sh 2>&1); echo "$out" | grep -q "PASS: DOC-5 a backtick command in You say fails naming README, the section and DOC-5" && echo "$out" | grep -q "PASS: pages in the format pass the docs check" && ! echo "$out" | grep -q "^FAIL"
```

- `PASS: pages in the format pass the docs check` is printed only on an affirmative `DOCS OK`, so a crash or any DOC-5 complaint turns the row red. `! grep ^FAIL` follows the wiki-release row's pattern.
- The rendered tables show id, kind, guards and scenario, never the command. So neither `docs/wiki/Tests.md` nor `Documentation.md` changes.
- Prove it red with the regression skill. It records the date: `python3 skills/workflow-regression/scripts/regression.py red format-frontdoor --break "git revert --no-edit 4af8853"`. Commit the row before running it. Expect a red result, not `STILL GREEN`.
- Known limit: the generated block in the fixture comes from test-docs-format.sh's own render, and the row does not assert it. The da4bb9c run shows the block is there (the FAIL text quotes `<!-- settings:begin -->` at README:19). An explicit fixture assertion would mean editing `test-docs-format.sh`, which is outside this goal's files. Follow-up.

### Step 4: verify

1. `bash dev/toy/ci-env.sh bash dev/toy/test-wiki.sh` passes with no `FAIL:` line, including the new PASS line (done line 1).
2. Negative controls: with 7e47366's gate reverted on a scratch copy, test-wiki.sh prints `FAIL: criteria-off render wrote README (...)`. The eng reviewer already ran this on a scratch copy. `regression.py red format-frontdoor --break "git revert --no-edit 4af8853"` comes back red.
3. `test-docs-format.sh`, `test-settings-table.sh`, `test-criteria.sh` and `test-prd.sh` pass. test-settings-table covers the criteria-on blocks: they still render, go stale, refresh and publish.
4. `bash dev/toy/check-reads.sh` reports no `LANES-TRACE-UNDECLARED` for the wiki rows.
5. `git diff --name-status origin/main -- skills/` shows only `M skills/workflow-docs/scripts/render.py` and `M skills/workflow-docs/scripts/pageformat.py`, with no `A` line (done line 3).
6. Done line 2: the commit messages and the PR body say the code was wrong (not test-wiki.sh) and name the two v0.27.17 changes as the cause. The PR body says the ungated refresh appended the blocks to a README that had none.

### Behavior changes (for the PR body)

- `criteria.py render` in a criteria-off repo no longer writes the template, Settings or Automation blocks into README.md or Home.md. Before, it always did, since v0.27.17. Blocks already there are left as they are and are no longer refreshed or checked.
- DOC-5 (README `## How to use`) ignores the generated blocks, as DOC-4 already did for Home.

### Files

- `skills/workflow-docs/scripts/render.py`: one line (done).
- `skills/workflow-docs/scripts/pageformat.py`: `unblocked()` shared by home and frontdoor (done).
- `dev/toy/test-wiki.sh`: the Step 2 lines plus one `# reads:` path.
- `.loop/regression.tsv`: the `format-frontdoor` command, plus the seen-failing date that `red` records.

### Not in scope (follow-ups for the operation session to queue)

- P1: criteria-on repos can hit LANE_DIRTY at QA prep. This repo is one (`criteria: true`, `auto_merge: true`). It happens whenever prep's render writes README/Home blocks. Setup's own render (`seed.py` runs `criteria.py render`, and `setup.py` never stages README.md) leaves a freshly adopted criteria-on repo with README modified. A config or workflow change mid-goal does the same. It has been present since v0.27.17 and this goal does not change it. Repro: a fresh toy, `setup.py` without `--bare`, then `git status` shows ` M README.md`. Likely fix: setup stages README when render wrote it, and prep commits block-only front-file diffs. A toy test should check that every file render writes after a config change is one prep accepts.
- `test-docs-issues.sh` `FAIL: guide reset: STALE Settings`: it fails the same way on clean main.
- `test-defect.sh` and `test-deployments.sh`: they fail the same way on main.
- One shared helper for the criteria gate, which is now copied in render.py, docs.py check/problems, docs.py publish and audit.py. Also a NOTE when a criteria-off repo holds blocks that no longer refresh.
- `unblocked()` blanks every marker pair, so a duplicate block could hide DOC-5 content. This was already true of DOC-4. Follow-up: reject duplicate blocks.
- An explicit generated-block fixture assertion in `test-docs-format.sh`.
- Moving the gate into `refresh()`, widening lanekit's prep paths, and any change to `setup.py` or `lanekit.py`.

## Review record

Run: the autoplan driver, full, developer-tool mode. Phases: CEO, DX, Eng (Eng last). Design was skipped because there is no UI scope (`ui=no`, no rendered file). Two rounds, the cap. Round 1 reviewed snapshot `5f592fd3` (render fix only). Round 2 reviewed `cdc47c03`, after the coordinator added 4af8853 (pageformat). Each round of each phase had two voices: a native Claude subagent (claude-opus-5-5) and Codex (`codex exec`, gpt-6.1-sol, read-only sandbox). Codex could not write its result file in the read-only sandbox, so its full stdout review was bound (receipt verified, INPUT hash matched).

### Verdicts per phase (round 2, the reviewed plan)

| Phase | Native (Claude) | Outside (Codex) | Consensus |
|---|---|---|---|
| CEO | 0 High, 3 Medium, 2 Low: approve scope; track criteria-on LANE_DIRTY at P1; the new row was weak | 1 Medium: the new row passes on a checker crash | both flagged the row: fixed in Step 3 |
| DX | 8/10, 2 Medium, 1 Low: row level unset; never proven red; PASS after a crashed render | 2 Critical, 1 High (CAP4/CAP6): crash and git-failure false PASS; no recovery | crash/false-PASS: fixed in Steps 2 and 3. Codes and retries: rejected (P5) |
| Eng | 4 findings, none blocking; ran Step 2 on a scratch copy (passes, and fails with the gate reverted); criteria-on adoption also dirties README | 5 Medium: row crash, duplicate blocks, level, seen-red, Documentation.md re-render | row and Documentation.md: fixed by tightening format-frontdoor. Duplicate blocks: follow-up |

Round 1 (draft plan without pageformat) got the same themes: criteria-on LANE_DIRTY (both voices; Codex marked it a user challenge on scope), the Home half of the check was vacuous (Home.md absent), the FAIL line named no fix, and the then-uncommitted pageformat edit. The round 2 plan resolved all of them, or deferred them in Not in scope.

### Cross-phase themes

- Criteria-on LANE_DIRTY (CEO and Eng, both rounds): kept out of scope as the owner directed (one-line fix), and queued above as P1 with a repro.
- Test assertions that pass vacuously (CEO, DX and Eng): Step 2 uses git's exit status and keeps a render failure apart. Step 3 needs an affirmative DOCS OK and no FAIL.

<!-- autoplan-accepted:ceo -->
- Keep the fix to 7e47366 and 4af8853. Track the criteria-on LANE_DIRTY case as a P1 follow-up with the repro in Not in scope. List both behavior changes in the PR body.
<!-- /autoplan-accepted:ceo -->
<!-- autoplan-accepted:dx -->
- The test-wiki.sh assertion keeps a render failure apart from the README check, uses git's exit status, names the written blocks and the fix in its FAIL line, and restores README afterwards.
- The DOC-5 guard needs an affirmative DOCS OK and no FAIL line, at level land, and is proven red with `regression.py red`.
<!-- /autoplan-accepted:dx -->
<!-- autoplan-accepted:eng -->
- Tighten format-frontdoor's command instead of adding a row, so Documentation.md and Tests.md do not change. Verify steps 1 to 6 as listed, including check-reads.sh and the skills diff showing only the two M lines.
<!-- /autoplan-accepted:eng -->

### Decision audit trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|---|---|---|---|---|---|
| 1 | CEO | Keep scope at the fix plus a regression check | Mechanical | P6, owner direction | The owner's scope limits the goal to one line plus at most one check; criteria-on is pre-existing | Codex user challenge: widen to a criteria-on repair (left with the owner; queued as P1) |
| 2 | DX | Check README only; Home is absent at that point | Mechanical | P5 | Home.md is first written at test-wiki.sh:91 | A Home fixture (more toy setup for one condition) |
| 3 | DX | FAIL line names the blocks and the fix; render failure kept apart | Mechanical | P1 | DX native F1/F3, outside F3 | Coded errors and retries (P5) |
| 4 | Eng | Restore README after the check | Mechanical | P1 | Otherwise a regression is committed and the end-to-end path stops guarding it | None |
| 5 | Eng | Fold the coordinator's pageformat commit into the plan; revise and re-review all phases | Mechanical | P1 | The reviewed plan has to match the shipped diff | Ship without review of 4af8853 |
| 6 | Eng | Tighten format-frontdoor instead of adding a DOC-5 row | Taste | P3, P4 | Same guard, stays inside the allowed files (a new row re-renders Documentation.md) and reuses a land row | New row `frontdoor-generated-blocks` |
| 7 | Eng | Defer duplicate-block hardening and the explicit fixture assertion | Mechanical | P3 | Pre-existing in DOC-4; test-docs-format.sh is outside the allowed files | Doing them here |

### Gate (final, not approved)

gate_rev 2: d1 (validator crash satisfies the row), d2 (git failure prints PASS), d3 (render failure recovery), p1 (approval). Recommended outcome: `rec` = p1b, approve with d1a, d2a and d3a. These are folded into Steps 2 and 3 above. The coded-error and retry parts of d2 and d3 are rejected under P5. Because those changes are below High once applied, the driver would apply them without another review round. Nobody answered the gate. Approval stays with the owner or the review step.
