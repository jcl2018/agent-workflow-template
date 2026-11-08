# Design: defect-tests

Status: shaped by office-hours with the recommended answer at every question. Nothing approved, merged or pushed.
The goal's done lines are frozen; this design meets them. Delivery fills in the goal's "Verify by hand".

## Problem

Regression has one kind of test: it proves a criterion. A fix leaves nothing behind that proves it stays fixed (issues
35 and 58 and pull requests 61 and 62 all recurred or were missed). The delivery flow also still has a `checks` step and
a `require_checks` switch, so a pull request body can say "Checks: ... none ran" or claim checks passed with none run,
and a worker can end at its pull request without running the release step. Size matters: `release.py` is 20376 bytes and
`regression.py` 20093 against the 20 KB (20480) cap, `goal.py` 17921, so new logic goes in new files and each touched
script must stay flat or shrink.

## Approach (recommended, taken)

1. **Rows get a category and a link** (lines 1, 4). `.loop/regression.tsv` gains two columns, `category`
   (`criterion` | `defect`) and `link` (the criterion's words stay derived from `goal`; for a defect row, the GitHub
   issue URL/number or a `.loop/findings.md` finding id). `regression.py` reads the header, so old files without the
   columns read as `criterion`. `regression.py check` fails a row with no category, or a defect row with no link.
   Existing 88 rows are migrated mechanically to `criterion`. The wording of REG-1 and REG-2 is applied exactly as
   frozen in line 1 (`criteria.py review --user`, Reviewed 2026-11-08), in `docs/wiki/Regression.md` and its seal.
2. **Tests tables split** (line 4). The table renderer (`criteria.py`, via the existing `render`) writes criterion tests
   under "Tests" and defect tests under a "Defect tests" subsection on the page whose code the issue guards (the row's
   `goal` column names the owning criterion's page; a defect row with `goal` `-` goes to the page named by its `touches`
   or, failing that, Regression). Columns follow the REG-2 format: category, guards, what it checks, when, last result
   and date, seen failing. A defect row never makes a criterion "not enforced"; it only adds proof.
3. **Delivery adds the defect test** (line 5). When a goal's text or done lines name an issue or finding it fixes
   (`#N`, `fixes #N`, or a finding id), the build step prompt requires a defect row and the toy-style test. `goal.py pr`
   refuses to open the pull request until `regression.py red <id>` shows the new defect row `seen_red` dated and the row
   passes on the fix. The "old code" half uses the existing `red --break` on a copy of the tree, so no checkout is
   touched. New code lives in a new `skills/workflow-delivery/scripts/defect.py` (called from `goal.py` in a few
   lines), because `goal.py` has little headroom.
4. **No checks step** (line 3). `goal.py` loses the `checks` step, `check` command, `checks_sha`, and the
   `require_checks` gate in `pr`; `.loop/config.json` and `setup.py` drop `checks` and `require_checks`; docs
   (`SKILL.md`, `commands.md`, wiki, `loop-files.md`) lose them. The flow goes build to review; review is the only gate.
   The pull request body stops saying anything about checks; its `## Result` lists the skill flow only. This is a net
   deletion in `goal.py`, which pays for item 3.
5. **Every step mappable** (line 3). `flow.py` `STEPS` becomes `idea` (office-hours), `plan`, `build`, `review`, `qa`,
   `ship`, `pr`, `release`. The private flow file (outside the repo) keeps its `steps` map; a built-in default suite maps
   each step to the owner's preferred skills, and a per-step key in the private file overrides it. Flow validation
   (`flow.py` line 68) requires the file to exist and the command/probe to be set, not every step to be listed.
   Each step runs its skill in its unattended mode via the existing prompt. DEL-1 is rewritten word for word as frozen
   in line 2.
6. **Health rule** (line 6). One new rule `defect-tests` in `health.py`: for each closed GitHub issue (via `gh`) or
   closed finding, FAIL/WARN if no regression row has that issue or finding in `link`. `RULES` has a `MAX_RULES` cap, so
   retire or fold one existing rule into the new one (recommended: fold `criteria-proof`'s check into `criteria-rows`).
   No token or no `gh` gives UNREAD, never PASS. Because `health.py` is 16 KB, the rule goes in a new
   `skills/workflow-health/scripts/defects.py`.
7. **Worker runs release** (line 7). The worker's last step becomes `release.py` run in-session: version bump, release
   note, docs, and merge where `auto_merge` is on. Today the worker stops at `status: done` with the PR; it will not
   mark a goal done until the release step records `released`, and a stop before that is a failed try. The release code
   is not grown: `worker.py` calls the existing `release.py`/`merge.py` entry points.
8. **Defect tests for four known defects** (line 8), each a defect row with a link:
   - issue 35 (scripts hang with no terminal instead of failing) tied to a no-tty toy case,
   - issue 58 (`wiki-release` regression row failing) tied to its toy case,
   - the worker that skipped its own release step (pull requests 61, 62) tied to a worker-finishes-with-release toy
     case,
   - the pull request body that said checks passed with no checks, tied to a body-has-no-checks-claim toy case.
   Each is seen failing once on a broken copy and passing on the fix.
9. **Toy tests** (line 9). New `dev/toy/test-defect.sh` with one `PASS:` line per done line, plus the four defect cases;
   `regression.tsv` rows for them are `category=defect` or `criterion` as fits. Repo checks (health size, docs audit,
   criteria review seals) must pass.

## Alternatives considered

- **Separate defect file** (`.loop/defects.tsv`): simpler to split but doubles the run/ledger/issue-sync code. Rejected.
- **A defect is just a criterion row with a note**: no code, but cannot satisfy lines 4 and 6 (own part of the page,
  closed-issue check). Rejected.
- **Chosen**: one table, two columns, one renderer split.

## Risks

- Script size caps: `regression.py` and `release.py` have under 400 bytes headroom. New logic goes in new files; if
  `regression.py` cannot absorb the two columns, move TSV reading into a small `rows.py` sibling.
- Removing `checks` changes frozen history in old goal files and tests (`test-goal.sh`); those toy cases are updated in
  the same goal, and the `no-flow-refused` and `never-merges` rows must still pass.
- Issue 58 reads as an auto-opened regression issue for the `wiki-release` row; its root cause is not in its body.
  The defect test guards the row's failure as written. If delivery finds a different intent, it records that as a
  finding rather than guessing.

## Assignment

Run `/CJ_goal_*`-style delivery on this design: build items 4, 5 first (net deletions), then 1, 2, 3, 6, 7, then the
four defect rows and the toy test.
