# Design: health-hygiene

Generated on 2026-11-09
Branch: loop/health-hygiene
Repo: jcl2018/agent-workflow-template
Status: DRAFT
Mode: Builder

Meets the frozen done lines in `.loop/goals/health-hygiene.md`; changes none of them. In short:

1. A new requirement HLT-6 on the Health PRD, Unreviewed, in the owner's wording.
2. Every rule has a negative control; a control that stays green is reported as "cannot fire"; a rule without one is refused.
3. Each regression run records its total and per-row time; health warns when the land lane is over a budget setting and names the slowest rows; the judge's performance review covers test time as well as tokens.
4. Health reports worktrees with no live goal and local branches on no remote (older than a setting), each with its removal command, and removes nothing.
5. A toy test proves each part fires on a bad fixture and stays quiet on a clean one.
6. Each done line becomes Given/When/Then scenarios under HLT-6, each linked to its regression row.

## Problem Statement

Health checks the repo, but nothing checks health. A rule can be broken in a way that stays quietly green:
a regex that no longer matches, a sibling script whose output changed, a threshold that can never be crossed.
The repo is also growing in ways no rule sees. Measured on this machine on 2026-11-09:

- The land lane in the newest lane record ran 189 rows in about 1148 s (19 minutes). The slowest rows are around
  29 s each (`operate-all`, `docs-only`, `no-pid-left-alone`, `breaking-asks`, `landed-left-alone`). Nothing reports
  that the lane is slow or which rows to move to nightly.
- `git worktree list` shows 63 worktrees, and 12 local branches have no upstream. Nothing tells the owner which of
  them are left over from finished goals, or how to remove them.
- `health.py` is 16964 B against the 20 KB cap. New rules cannot land inside it.

## What Makes This Cool

Health proves itself every time it runs. Each rule carries a tiny fixture that must make it fire. If a rule goes
quiet on its own fixture, the report says "this rule cannot fire" in place of a green line nobody should trust.
The same run also tells the owner how much test time and disk the repo carries, and exactly which commands would
give it back. It never removes anything itself.

## Constraints

- Every script stays under 20 KB (health.py is at 16964 B), so new logic goes in new modules beside it, imported the
  way `report.py`, `cost.py` and `mine.py` already are.
- `check` stays read-only: a control fixture lives in a private temporary folder that is deleted afterwards, and
  nothing in the repo, its worktrees or its branches is changed.
- Two runs on an unchanged repo print the same lines (HLT-1). Times vary between runs, so the test-time row compares
  a recorded lane total against a budget and reports the recorded numbers. It never times the check itself.
- HLT-2 lists the rules today. HLT-6 adds to them, so `MAX_RULES` is raised on purpose, with a comment saying why,
  as was done for cost.
- No new dependencies; standard library and git only.

## Premises

1. A negative control must run the real rule function on a fixture made to break it. A list of "this rule has a
   test" is not enough, because the failure to catch is a rule that silently stopped matching. (Agreed:
   recommended.)
2. The test-time data already exists. `lanes.save` stores each row's seconds in the lane record. The missing parts
   are the lane's total time, a budget setting, and a reader in health. (Agreed: recommended.)
3. Only loop worktrees are in scope: those under the git folder's `loop/worktrees/`. The main checkout, the
   worktree health runs in, and worktrees made outside the loop (app sessions, by hand) are never listed. A loop
   worktree is live when a run record names it and the run is running, waiting, failed or stopped (it may be
   resumed), or done with a release that is not `merged`, `cut` or `leave` (its pull request is still open). Every
   other loop worktree is stale: no run names it, or its run has merged. A branch is stale when it has no upstream,
   is not checked out in any worktree, is not the current branch, is not already merged into the base (the existing
   `branches` rule reports those, so a branch is never listed twice), and its last commit is older than
   `stale_branch_days`. (Agreed: recommended.)
4. Health prints a removal command and never runs it, and never prints a forcing one without saying what it loses.
   A stale worktree gets `git worktree remove <path>` (no `--force`); a dirty one is reported as dirty, with the
   note that the command refuses until its changes are committed or dropped; a missing directory gets
   `git worktree prune`. A stale branch has commits that exist only here, so it gets
   `git branch -D <name>` with the warning "deletes N commits that exist only on this machine; push it first to
   keep them" and the count of those commits. (Agreed: recommended.)
5. Age-based rules depend on the clock. HLT-1's "same answer twice" holds for two runs on the same day; a branch
   crossing `stale_branch_days` between runs is a real change. (Agreed: recommended.)

## Approaches Considered

### Approach A: Minimal (rules inside health.py)
Add three rule functions to health.py and a dict mapping each rule to a fixture.
Effort S, risk medium: health.py would cross 18432 B and warn on itself, and the fixtures would crowd the main script.
Rejected because it breaks the size rule it is meant to protect.

### Approach B: Two modules beside health.py (recommended)
- `controls.py`: a registry `CONTROLS = {rule: fixture function}`. Every rule already takes the repo root as its
  only argument (`size_rows(root)`, `criteria_rows(root)`, `docs_rows(root)`, `defect_rows(root)`,
  `hygiene_rows(root)`, `cost_rows(root)`, `mine_rows(root)`); the sibling scripts it calls (`regression.py sync`,
  `docs.py check`, `cost.py`) run with that root as their folder, and run records are found through the root's git
  folder. So each control builds a small throwaway git repo in a private temp folder (`git init`, a minimal
  `.loop/config.json`, and the one file or record that breaks the rule) and calls the real rule with that root:
  - size: a 21 KB script under `skills/x/scripts`; criteria rows: a page requirement with no regression row;
    done lines: a goal file with a done line and no row; defect tests: a closed finding with no defect row;
    docs check: a mapped page that is missing; findings: six open findings; waiting: a run record waiting for
    more than a day (an old `updated` stamp); branches: a `loop/` branch merged into `main`; cost: a run record
    over its time budget; mine: a private rules file (through `LOOP_HEALTH`) whose rule exits 2.
  - the three new rules: test time: a fake lane record over the budget; worktrees: a `loop/worktrees/<x>`
    worktree no run names; local branches: a branch with no upstream whose commit is backdated with
    `GIT_COMMITTER_DATE`.
  `check` runs every control and prints a `controls` row per rule: PASS when it fired, FAIL "cannot fire" when the
  rule stayed green on its own fixture, UNREAD when the fixture could not be built. FAIL and UNREAD make the verdict
  not green, like any other FAIL or UNREAD. A rule in `RULES` with no control makes health.py refuse to load: it
  prints one `REFUSED: rule <name> has no negative control` line, prints no report, and exits 1. The fixtures are
  kept tiny (the whole controls group is bounded at about 3 s) and run only in the `controls` group, which
  `check --group` can skip. Filed controls findings are tagged `health:controls`.
- `lean.py`: two row producers.
  - **Test time.** Reads the land lane record of the current branch (`lanes.record_path`); with none, the newest
    land lane record under `loop/tests/` by its `at` time, naming its branch. So the measured lane is reported on
    main too. It WARNs when the recorded total is over `test_budget_seconds` (a `.loop/config.json` setting,
    default 600) and names the five slowest rows with their seconds as candidates to move to nightly. A record
    written before this change has no `total_seconds`, so the total is the sum of its rows' seconds. No record at
    all is INFO, never PASS.
  - **Stale worktrees and branches.** As defined in premises 3 and 4, each a WARN with its command and warning.
- `lanes.save` also records `total_seconds` (the sum over the rows, kept with the rows) so the total survives reuse.
- `judge.py` adds the land lane's total and slowest rows to its performance facts, so its savings cover test time
  as well as tokens (done line 3; the toy test checks the facts it is given name the slowest rows).
Effort M, risk low-medium (the fixtures for docs and criteria call the real sibling scripts, so they need a repo
those scripts accept). Reuses the module pattern, `lanes.record_path`/`load`, the run records hygiene already reads,
and cost.py's place in the report.

### Approach C: Controls as regression rows
Make each rule's negative control a toy-test row in `.loop/regression.tsv`. Cheaper at check time, but health would
not report "cannot fire" itself, which the second done line requires. Rejected.

## Recommended Approach

Approach B. It keeps health.py under the warn line, puts each new concern in one small module, and makes the
controls run the real rule code every time.

Report placement: controls appear as their own `controls` group, and test time and stale worktrees/branches join
the `hygiene` group, as `test-time`, `worktrees` and `local-branches` rules. `report.py` gains the new rules in its
`RULES` table, and `file.py` tags them like any hygiene finding. The HLT-6 requirement text goes on the Health PRD
as Unreviewed (done line 1), and the owner's approval quoted by the operation session is then recorded with
`criteria.py review`.

## Open Questions

- Default budgets: 600 s for the land lane and 14 days for local branches are guesses. The land lane is about
  1148 s today, so health will warn on this repo from day one. That is intended: it names the rows to move.

## Success Criteria

- `health.py check` prints a `controls` group with one PASS per rule. Breaking a rule's matcher turns its control into
  `FAIL ... cannot fire`, and adding a rule without a control makes the script refuse to load.
- A lane record over its budget gives one WARN naming the five slowest rows, and a record under it gives none.
- A worktree with no live goal and an old branch with no upstream each give a WARN with the exact removal command,
  and nothing is removed.
- A toy test proves each part fires on a bad fixture and stays quiet on a clean one. Each done line has a
  Given/When/Then scenario under HLT-6 on the Health page, linked to its regression row.

## Distribution Plan

Ships in the skills pack as before (`dev/package.py`); the two new scripts join `skills/workflow-health/scripts/`.
The existing release step covers versioning.

## Next Steps

1. `lanes.save`: record `total_seconds`. `lean.py`: test time and stale worktrees/branches.
2. `controls.py`: a fixture per existing rule, the load-time refusal, and the `controls` group in `check`.
3. Wire into health.py (`RULES`, groups) and `report.py`; extend `judge.py` facts with test time.
4. `dev/toy/test-health-hygiene.sh`: a bad and a clean fixture for each part. Add its rows, the HLT-6 requirement
   and its scenarios, and the new settings in the settings reference.

## What I noticed about how you think

- The goal asks health to prove it can fail before it is trusted to pass. That is the same discipline as the repo's
  "seen failing once" rule for tests, now applied to the checker.
- "Never removes anything itself" keeps the owner in control of anything destructive, as the filing goal did with
  issues.

## Reviewer Concerns

Disposition: COMPLETED

Stop: PASS

No blocking findings remain. The 4 open minor finding(s) below are recorded for the user, not fixed.

### R2-1 — consistency (minor)

**Problem**

> Approach B now gives controls for the three new rules (test time, worktrees, local branches), but Next Steps step 2 still says 'a fixture per existing rule', which reads as excluding the new rules that the load-time refusal requires controls for.

**Remedy**

> Change Next Steps step 2 to 'a fixture per rule, including the three new hygiene rules'.

### R2-2 — completeness (minor)

**Problem**

> Premise 3 equates 'release not merged, cut or leave' with 'pull request still open'. A `leave` (or `cut`) release does not by itself show the pull request was merged or closed, so a loop worktree whose PR is still open could be listed as stale. The impact is limited (the printed command only removes a clean worktree; the branch survives), but the liveness rule rests on an unstated assumption about release states.

**Remedy**

> State which release states imply the PR is closed or merged, or treat a worktree as live while its run's PR is open regardless of release state.

### R2-3 — completeness (minor)

**Problem**

> A branch with no upstream that is unmerged into the base may still have all its commits reachable from some remote branch, so 'commits that exist only here' is not always true; the case N = 0 is not described. Locked worktrees (which `git worktree remove` also refuses) are not mentioned alongside dirty ones.

**Remedy**

> Compute N as commits not on any remote ref (e.g. `git rev-list <b> --not --remotes`), drop or soften the warning when N = 0, and report locked worktrees like dirty ones.

### R2-4 — clarity (minor)

**Problem**

> The fallback location `loop/tests/` is not stated relative to anything (repo root or git common folder), and how a record with a missing or unparsable `at` stamp is ordered is not said.

**Remedy**

> Name the folder as the git common folder's `loop/tests/` (matching `lanes.record_path`) and say that records without a readable `at` are skipped.
