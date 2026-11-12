<!-- plan review restore point: <local path> -->
## URGENT, outside this plan
None.

## Implementation plan
# Design: skill-size-2, four scripts back under the size warning line

Written by the idea step (idea skill, unattended, recommended answers) on 2026-11-10
Branch: loop/skill-size-2
Status: APPROVED (unattended worker run, recommended answers)
Mode: Builder
Supersedes: skill-size (PR #163, merged)

## Problem Statement

Health's size group warns when a script reaches 90% of the 20 KB limit (18,432 of 20,480 bytes). It has filed
issues 138 to 142 for five scripts. On origin/main (e145b43) the sizes are:

| Script | Bytes | Issue | State |
|---|---|---|---|
| skills/workflow-delivery/scripts/goal.py | 19,415 | 138 | warns |
| skills/workflow-docs/scripts/criteria.py | 20,356 | 139 | warns (99%) |
| skills/workflow-docs/scripts/docs.py | 15,007 | 140 | already below the line |
| skills/workflow-regression/scripts/regression.py | 20,246 | 141 | warns (98%) |
| skills/workflow-release/scripts/release.py | 18,606 | 142 | warns |

Issue 116 (two SKILL.md files over 150 lines) was fixed by the first skill-size goal (PR #163). Both files are 149
and 143 lines, and row `skill-size-116` proves it.

## Constraints

- No behaviour change. Every split is a pure move: function bodies are moved byte for byte into a new sibling
  module, and the old module imports them back under the same names. Then `goal.X`, `release.docs_trouble`,
  `criteria.rules` and the other names that tests and sibling scripts call (merge.py, wiki.py,
  autorelease.py, docs.py, prd.py, audit.py, counting.py, test-prd.sh, test-criteria.sh, test-docs-command.sh,
  test-summary.sh) still resolve.
- Moved code never imports its old module back. When a script runs as `__main__`, a back-import loads a second
  copy of the module with its own state. Only leaf blocks move: functions whose dependencies are the standard
  library, each other, a sibling module that does not import the old module (for example `role` or `pageformat`),
  or a tiny primitive that is copied as well (for example `git` or `run`, a few lines each, kept identical in both
  files).
- Each of the four files ends below 18,432 bytes with at least about 1 KB of headroom, so the next goal doesn't
  trip the warning straight away. Each new module is well under 18,432 bytes too.
- SET-3 ("every script self-contained and under 20 KB") holds: new modules use only the standard library and live
  next to the script they serve. Sibling imports already exist (lanes.py imports narrow, regression.py imports
  actions and lanes), and `lanes.py` follows sibling imports for affected-row selection, so new modules land in
  the right test lanes.
- Pure-move commits: one commit per file, holding the moved lines, the new module's docstring and imports, the
  copied primitives, the import-back line and, in release.py only, a `sys.path.insert` of its own folder. A
  reviewer can then check with `git diff --color-moved`.
- Other goals are editing these files now: docs-format (criteria.py, docs.py, regression.py), lane-control
  (regression.py, goal.py), delivery-prd (goal.py, release.py). Each file's split waits until the goal editing it has merged, and is cut
  from that merged content.
- Touches: the line names skills/workflow-delivery, skills/workflow-docs, dev/toy and .loop/regression.tsv. The
  operation session has already added skills/workflow-regression/scripts and skills/workflow-release/scripts, and
  is asked to add docs/wiki (Setup, Delivery, Documentation and Regression pages change).

## Premises

1. The 90% warning line is the real target. The done line says "under the 20 KB limit", which all five files
   already meet, but the issues only close when health stops warning. (Operation session agreed.)
2. A pure move with an import back is the only kind of split that is provably behaviour-free. Trimming or
   rewording code is not, so it is out of scope.
3. Issue 116 is proved by the existing `skill-size-116` row, not redone. docs.py (issue 140, filed at 20,281 bytes)
   needs no split if it stays at most 17,408 bytes after docs-format merges (17,114 on that branch); it gets a new
   size row either way.
4. The full regression suite, run once in qa, is the proof of no behaviour change, together with a new defect row
   per issue that fails on a padded copy of its script and passes on the split one.

## Approaches Considered

### Approach A: Leaf-block moves into sibling modules, with names imported back (chosen)

For each file, pick a cohesive block that does not call back into the module, move it byte for byte to a new
sibling, and write `from <new> import a, b, c  # noqa` in the old file.

Likely blocks, re-checked against each file as it stands after the other goals merge:

- goal.py: the run-record and goal-file primitives (`no`, `run`, `git`, `read`, `write`, `now`, `state_dir`,
  `state_path`, `load`, `save`, `root`, `config`, `goal_file`, `done_lines`, `done_sha`, `base_ref`; 2,534 bytes on
  main) into a new `goalfile.py`, which imports `role` for `save` and never imports goal. `frozen`, `held`,
  `fail_stop`, `failed_try`, `cmd_wait` and `cmd_answer` stay: they hand `sys.modules[__name__]` to guards.py.
  Fallback if delivery-prd grew the file: also move `FLOW`, `FLOW_FILE`, `NO_FLOW`, `SLUG`, `TEMPLATE`, `flow_set`
  and `valid`.
- criteria.py: docs-format already moved the tests-format and scenario-table block into render.py (17,666 bytes on
  loop/docs-format, 766 under the line; a pre-merge figure). Move the page-rules block (`SHEET`, `CRITERIA_MAX_DEFAULT`, `rules`,
  `criteria_max`; 2,279 bytes) into a new `pagerules.py`. `SHEET` keeps resolving because the new file sits in the
  same folder, and render.py's `criteria.SHEET` and `criteria.rules()` resolve through the import-back.
- regression.py: lane-control already moved the issue-sync block (`gh`, `sync_issues`, `MARK`) out (18,217 bytes on
  loop/lane-control, a pre-merge figure), and docs-format also edits cmd_run (the two branches conflict there). Move the goal and page
  readers (`done_lines`, `criteria_ids`, `criterion_rows`, 1,141 bytes, with a copy of the two-line `path_of`) into a
  new `rowreaders.py`. Fallback: also `chosen` and `clean`.
- release.py: the changelog and version block (`VERSION`, `bump`, `verify_steps`, `subjects`, `changelog_text`,
  `restore`; 2,572 bytes, with copies of `run` and `git`) into a new `cutlog.py`. The docs and criteria checks
  (`doc_rows`, `docs_trouble`, `criteria_trouble`) and `run` stay: test-prd.sh sets `release.doc_rows` and
  `release.run` and expects `criteria_trouble` to see them. Fallback: also `now`, `state_path`, `load`, `save`,
  `finished` and `read_config`.

Effort S per file, risk low, and the moves are easy to review.

### Approach B: Trim code in place (shorter docstrings, merged helpers)

Rejected: this isn't a pure move, so behaviour might change. Each trim also buys only a little headroom, and the
files would be back at the line after the next feature.

### Approach C: Raise the warning line or the limit

Rejected: health's rule and SET-3 set the 20 KB contract, and the issues ask for the files to be split.

## Recommended Approach

Approach A. Order the work by merge: each file is split as soon as the goal editing it has merged into main, and
the branch merges main right before `goal.py pr`. Add one defect row per issue (138 to 142), linked to its issue.
Each row checks the script and its new module against health's own size rule and checks that the moved names
resolve on the old module; it is seen failing on a padded copy of the script and passes after the split. Record
each done line on the Setup PRD page as a Given/When/Then scenario under SET-3 (DOC-3). For done lines 1 and 2,
point at the existing `skill-size-116` and `skill-kept` rows.

## Open Questions

None for the owner. The touches widening is already requested from the operation session.

## Success Criteria

- `wc -c` shows goal.py, criteria.py, regression.py and release.py each at most 17,408 bytes, with docs.py below
  18,432.
- `health.py check` prints no size WARN for those five files.
- The full land suite passes on the split HEAD, and the new defect rows were seen failing first.

## Dependencies

- docs-format, lane-control and delivery-prd merge first. A file whose blocking goal has not merged is not split;
  the worker stops with `goal.py wait` naming that goal instead of splitting from an older base.
- Touches already include skills/workflow-regression/scripts and skills/workflow-release/scripts; the operation
  session is asked to add docs/wiki.

## The Assignment

After each blocking goal merges, merge main and split its file in one pure-move commit.

<!-- plan review-accepted:ceo -->
- Each split starts from merged main: after the goal editing that file merges (docs-format for criteria.py, docs.py and regression.py; lane-control for regression.py and goal.py; delivery-prd for goal.py and release.py), merge main into loop/skill-size-2, re-measure with `wc -c`, and re-derive the leaf block and the stay-put names from the merged file, and move the named block (plus its named fallback if needed) until the file is at most 17,408 bytes (1 KB under 18,432); each new module stays under 17,408 too. If the named block no longer exists or the block plus fallback is not enough (delivery-prd may move goal.py code itself), pick another leaf block by the same rules and record the choice in the commit message; if no leaf block fits, stop with `goal.py finding` naming the file.
- New modules: goal.py -> `goalfile.py`, criteria.py -> `pagerules.py`, regression.py -> `rowreaders.py`, release.py -> `cutlog.py`. Each imports only the standard library and siblings that are not its old module (goalfile.py may import `role`); none imports its old module. The old module gets one line `from <new> import <names>  # noqa: E402,F401` after its last top-level import and before the first module-level use of a moved name, so every moved name resolves as `<old>.<name>`. release.py, which has no `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`, gains that line in the same commit, because dev/toy/test-release.sh:86 loads it by file path from the repo root; no other file needs it (only release.py is loaded that way).
- Moved versus copied, per file: goal.py moves all its block (no copies; `run` and `git` move too); criteria.py moves all (no copies); regression.py copies `path_of`; release.py copies `run` and `git`.
- Names that stay put: goal.py keeps `frozen`, `held`, `fail_stop`, `failed_try`, `cmd_wait`, `cmd_answer` (they pass `sys.modules[__name__]` to guards.py); release.py keeps `doc_rows`, `docs_trouble`, `criteria_trouble` and `run` (test-prd.sh:239-240 sets `release.doc_rows` and `release.run`).
- docs.py: if it is over 17,408 bytes after docs-format merges, it gets a leaf-block move by the same rules into a new `docsparts.py` (then added to the reads header and the size-140 case); otherwise it is not edited.
- Each new module's docstring says which module its names came from and that the old module imports them back for existing callers.
- One pure-move commit per file: the moved lines, the new module's docstring and import lines, the import-back line, and the copied two-to-five-line primitives (`run`, `git`, `path_of`) only. `git diff --color-moved=zebra HEAD~1` shows nothing else; the old module no longer has a `def` or assignment for any moved name.
- The goal file gains a `## Closes` section (outside Done lines, so the done-line hash is unchanged). It opens with one sentence saying what the PR does (splits goal.py, criteria.py, regression.py and release.py by pure moves; docs.py is split only if needed, so issue 140 may close with no code change; role.py and four workflow-monitoring scripts still warn and are not in scope), then `Closes #138`, `Closes #139`, `Closes #140`, `Closes #141`, `Closes #142` one per line, and `Refs #116` (already closed by PR #163, still proved by `skill-size-116`).
- Five defect rows, ids `size-138`, `size-139`, `size-140`, `size-141`, `size-142`: level land, category defect, goal SET-3, link the issue URL, command `bash dev/toy/test-defect.sh size-<N>`, description a Given/When/Then sentence. Each case (1) copies only its script and new module into a temp root at the same `skills/<skill>/scripts/` path and passes only when `health.size_rows(<temp root>)` gives no WARN or FAIL row (so it follows health's line without listing every skill folder, which the lanes-trace row would flag); (2) lists the new module's top-level `def` and assignment names with `ast`, minus that file's copied primitives, requires that set to equal the names in the old module's import-back line, then imports the old module with `$here/skills/<skill>/scripts` on sys.path, takes `new = sys.modules["<new>"]`, and checks `getattr(old, n) is getattr(new, n)` for each; (3) greps the old file for no `^def <name>\b` and no `^<NAME> =` per moved name; (4) for each copied primitive (`run`, `git`, `path_of`), checks its source in the new module is byte-identical to the old module's. size-140 without `docsparts.py` checks only (1). Each case also runs a built-in negative control on a temp copy (drop one name from the import-back line, and leave one `def` behind) and fails unless checks (2) and (3) catch both, so all three checks are seen failing, not only the size half. `size-138` to `size-142` are added to test-defect.sh's `cases=` list so a no-argument run includes them.
- Commit the new cases and rows first (`regression.py red` runs the row in a detached worktree of HEAD), then see each row red with `regression.py red size-<N> --break "<cmd>"`, where the break pads its script past health's `WARN_AT` (for example appending a comment line of 18,432 `#` characters). Restoring the pre-split file is not used: on merged main criteria.py and regression.py may already be under 18,432, and red would print STILL GREEN.
- dev/toy/test-defect.sh's `# reads:` header names the five scripts, the four new modules and health.py, so lanes select the size rows when any of them changes.
- `criteria.py render` runs after the rows are added, so docs/wiki/Setup.md's Tests show size-138 to size-142 wherever `criteria.py render` puts SET-3 defect rows on merged main (a list on main today, a table after docs-format), and `criteria.py render --check` reports no stale page; done lines 1 and 2 stay proved by `skill-size-116` and `skill-kept`.
- docs/wiki/Delivery.md (naming `goalfile.py` and `cutlog.py`, since docs.tsv maps both skill folders to it), Documentation.md (`pagerules.py`, and `docsparts.py` if made) and Regression.md (`rowreaders.py`) each get one sentence in their Usage section naming the new module, and `docs.py check` and `criteria.py render --check` show no contract finding for them. These page commits come after the last split, row and header commits, so `docs.py check` shows no STALE page at pr.
- Order and blockers: a file is split only after its blocking goal merged; if one has not merged when the rest is done, the worker stops with `goal.py wait` naming that goal rather than splitting from an older base. The operation session is asked to widen touches with docs/wiki; if that is refused, the worker stops with `goal.py wait` before `criteria.py render` or any page edit.
- SKILL.md files: this goal never edits one. If `skill-size-116` turns red after a merge, the worker records `goal.py finding` naming the goal that merged, rather than trimming SKILL.md here.
- Sizes quoted from loop/lane-control and loop/docs-format are pre-merge guesses (lane-control predates guards.py); the re-derive step after each merge is the binding rule.
- The PR title is the frozen goal text ("Fix issue 116: ...") cut to 70 characters by `goal.py pr`; it is accepted as is, and the PR body (the goal file with its `## Closes` section) says what the PR does.
- NOT in scope: splitting role.py and the four workflow-monitoring scripts that also warn (not in the issue mapping); removing render.py's back-import of criteria (docs-format owns it); lowering health's warn line.
- Verification before pr: `health.py check` may still WARN for role.py and the four workflow-monitoring scripts (not in scope); the success criterion covers only the five files. `wc -c` shows each split script and new module at most 17,408 bytes and docs.py under 18,432; `health.py check` shows no size WARN for them; `regression.py run nightly` (land and nightly rows) passes on HEAD; each consumer test runs in full and ends ALL PASS or exit 0: dev/toy/test-release.sh, test-prd.sh, test-criteria.sh, test-docs-command.sh, test-summary.sh, test-regression.sh, test-goal.sh, test-guards.sh, test-defect.sh; `defect.py owed skill-size-2` prints NONE OWED.
<!-- plan review-accepted:ceo -->

<!-- plan review-accepted:dx -->
- Rename the release.py module from `cutlog.py` to `changelog.py` everywhere (accepted CEO requirements that name `cutlog.py` now mean `changelog.py`): Delivery wiki sentence, reads header, size-142 case, commit message.
- The import-back line sits directly after the old module's last top-level import (moved names are leaves) and carries a trailing comment pointing new leaf helpers to the new module, for example `from goalfile import (...)  # noqa: E402,F401  leaf helpers live in goalfile.py`.
- Each new module's docstring also says: to affect moved code in a test, patch `<new>.<name>`, not `<old>.<name>`. Each size case fails if any dev/toy file assigns `<old>.<moved name> =`.
- Each size case reports through test-defect.sh's existing `no()` helper (exit 1) with the file, the actual value and a last-line fix: size (`<script> is <bytes> bytes, at or over health's WARN_AT <n>. fix: move another leaf block from <old>.py into <new>.py (rules: docs/designs/skill-size-2.md), then rerun bash dev/toy/test-defect.sh size-<N>`), name parity (`<new>.py defines <name> but <old>.py's import-back line lacks it. fix: add <name> to the from <new> import line`), leftover def (`<old>.py still defines <name> at line <L>. fix: delete that def; <new>.<name> is imported back`), primitive drift (`copied primitive <p> differs between <old>.py and <new>.py. fix: keep both copies identical; update both`), and negative control (`negative control: <mutation> was NOT caught by check <k>; the test is broken, not the split. fix: repair check <k> in dev/toy/test-defect.sh`).
- `goal.py wait` for an unmerged blocker lists the split and unsplit files with their current bytes, names the blocking goal, says split files are complete and stay committed, and gives the resume step (after that goal merges, re-run the step; it merges main and re-derives only unsplit files). `goal.py finding` for "no leaf block fits" carries the file, its bytes after merge, the 17,408 target, each candidate block with its size and why it was rejected.
- The goal file's `## Verify by hand` gets numbered steps, each with an `Expect:` line: (1) `wc -c` on the four split scripts and docs.py, Expect: each split script at most 17,408 and docs.py under 18,432; (2) `python3 skills/workflow-health/scripts/health.py check`, Expect: no size WARN line for the five files; (3) `for n in 138 139 140 141 142; do bash dev/toy/test-defect.sh size-$n || echo FAIL $n; done`, Expect: no FAIL line; (4) `python3 skills/workflow-delivery/scripts/defect.py owed skill-size-2`, Expect: NONE OWED.
- The qa verification is written once as a single copy-paste command block (wc -c, health check, `regression.py run nightly`, each consumer test, defect owed), run as is by qa.
- 17,408 is a build-time headroom target checked once in qa by `wc -c`; the permanent rows enforce health's WARN_AT only.
<!-- plan review-accepted:dx -->

<!-- plan review-accepted:eng -->
- Per file, commit order is: the pure-move split commit; then the case and its row (with reads header and `cases=` entry); then run `bash dev/toy/test-defect.sh size-<N>` with no break and require it to pass; only then `regression.py red size-<N> --break "<pad script past WARN_AT>"`. With the module present, padding a comment can only trip check (1), so the recorded red is the size failure.
- Before each split commit, check `git merge-base --is-ancestor <blocking goal's merge commit on main> HEAD`; if it fails, do not split (the `goal.py wait` rule applies).
- Check (3) is an `ast` walk of the old module's top level (including statements inside top-level `if`/`try` blocks) collecting every def, class, assignment, annotated assignment and tuple target name; it fails if any is a moved name. It replaces the grep.
- Checks (2), (3) and (4) run in a separate `python3 -B` process per case with the skill's scripts folder put on sys.path explicitly, so goal.py's import-time environment and stdin changes never touch the test-defect.sh process; each case cleans its temp root with a `trap`.
- Each case fails if its new module's basename exists in any other `skills/*/scripts/` folder.
- goalfile.py's docstring says to import it through goal.py, which sets the no-prompt environment for git and gh before importing it.
- `changelog.py` is the only module name for the release.py split; every `cutlog.py` mention in the plan means `changelog.py`. The release.py move commit has several moved hunks (the block is not contiguous); reviewers use `git diff --color-moved=zebra`.
- The re-derive step after each merge picks the smallest leaf block that brings the file to at most 17,408 bytes; for goal.py the named block leaves about 300 bytes of margin (estimated), so the fallback block is expected if lane-control or delivery-prd adds code.
- Deferred work is listed in the goal report; no TODOS.md is created (the repo has none; health issues and queued goals are its backlog).
<!-- plan review-accepted:eng -->
## Review record

### CEO phase (Phase 1), Step 0

Methodology read: methodology.md ranges 1-600, 601-1200, 1201-1800, 1801-2257 (2257 of 2257 lines, through EOF).
Session: unattended plan review, recommended answers, no approvals. Codex preflight: `CODEX_MODE: ready`.
Mode: SELECTIVE EXPANSION (plan review override). Review depth: implementation-ready.

#### Pre-review system audit

- Branch loop/skill-size-2 is origin/main e145b43 plus the goal file and the idea design. No stashes in use by this goal.
- In-flight branches that edit the same files (three-dot diff against main):
  - loop/docs-format: criteria.py (-189/+..., 17,666 bytes; it already moved the tests-format and scenario-table block
    into a new render.py), docs.py (17,114 bytes), regression.py (runs.py takes the runs-file write; 19,922 bytes on its
    older base).
  - loop/lane-control: regression.py (issue-sync block moved out, 18,217 bytes), goal.py (one 4-line change in
    cmd_record).
  - loop/delivery-prd: only its goal file so far; its done lines (DEL-5..DEL-9) will add code to goal.py and release.py.
  - docs-format and lane-control conflict on regression.py's cmd_run (patch of one onto the other: 2 of 3 hunks fail).
- Health today (`health.py check`, run in this worktree): WARN size for goal.py 19,415, criteria.py 20,356,
  regression.py 20,246, release.py 18,606, and also role.py 18,601 and four workflow-monitoring scripts (not in this
  goal's issue mapping).
- Issue 140 body says docs.py was 20,281 bytes when health filed it (2026-11-10 08:13): health ran on a tree where
  docs.py was mid-edit. On main it is 15,007.
- No CLAUDE.md or TODOS.md in this repo. Deferrals go to the NOT in scope list here and the goal's report; health
  files size issues itself.

#### Retrospective check

The first skill-size goal (PR #163) moved SKILL.md detail into references and needed a follow-up commit "Delivery and
Documentation pages name the moved detail" to clear STALE docs. The same will happen here: docs.tsv maps Delivery to
skills/workflow-delivery and skills/workflow-release, Documentation to skills/workflow-docs, Regression to
skills/workflow-regression, so any commit in those folders makes the pages STALE until a page changes.

#### Taste calibration

- Good: guards.py's pattern of taking the goal module as `g` (`guards.fail_stop(sys.modules[__name__], ...)`): an explicit
  dependency, no back-import. docs-format's runs.py: a small leaf module with only stdlib imports.
- Avoid: docs-format's render.py imports criteria while criteria lazily imports render (a back-import; when criteria.py
  runs as `__main__` a second criteria module loads). The split here must not copy that.

#### Landscape check

Aside probe: `ASIDE_CLI_ERROR: exit 1`; fell back to WebSearch (one query, sanitized). [Layer 1] Moving code into a
submodule and re-exporting names from the old module is the standard compatible split. [Layer 2] A 2026 case study
(github.com/matiaszanolli/Auralis issue 6198) and the `monkeypatching` package docs both warn that patching the old
module's name does not change what moved code reads. [Layer 3] Here that is concrete, not theoretical: test-prd.sh:239-240
sets `release.doc_rows` and `release.run` and expects `criteria_trouble` to see them, so those names and their reader
must stay in release.py.

#### Premise table

| Premise | Claim | Receipt | Verdict |
|---|---|---|---|
| P1 | The 90% line (18,432 bytes) is the target, not the 20 KB limit | skills/workflow-health/scripts/health.py:40-41 (`WARN_AT = LIMIT * 9 // 10`); `gh issue view 140` | valid |
| P2 | A pure move with names imported back is behaviour-free | goal.py:171-184 hand `sys.modules[__name__]` to guards; dev/toy/test-prd.sh:239-240 patches release globals | valid with two limits: those names stay put |
| P3 | 116 and 140 are already met | .loop/regression.tsv:175 (`skill-size-116`, seen red 2026-11-09); docs.py 17,114 on loop/docs-format | 116 valid; 140 conditional on docs-format's final size |
| P4 | Full suite plus one defect row per issue proves it | lanes.py:8 (narrow mapping by `# reads:`), dev/toy/test-defect.sh:2-5 | valid if the rows' reads header names the split files |
| P5 | The named blocks per file are still the right ones | criteria.py on loop/docs-format:159-166 (table and cmd_render already delegate to render.py); regression.py on loop/lane-control has no `sync_issues` | wrong for criteria.py and regression.py: corrected |
| P6 | `goal.py pr` enforces one defect row per fixed issue | goal.py:360-362 calls `defect.owed(root(), read(goal_file(slug)))`; defect.py:22 needs "fixes/closes #N" | true only if the goal file says `Closes #N`; it says "Fix issue 116" (no `#`), so nothing is owed today |

unverified=0

#### Reality rows

REALITY: premise-table finding P5 (two stale block choices) and P6 (goal file has no #N refs) corrected; unverified=0 skills/workflow-delivery/scripts/goal.py:360
REALITY: already-done pass `git log origin/main --since=2026-11-09` on the five files shows no split since the issues were filed skills/workflow-health/scripts/health.py:41
REALITY: surface-check pass `regression.py add/red/run`, `health.py check`, `criteria.py render`, `goal.py pr`, `defect.py owed` all exist with the flags named skills/workflow-regression/scripts/regression.py:6-14
REALITY: binding-decisions pass `decision-search --scope branch` returned nothing; frozen done lines and the owner-approved issue mapping (2026-11-10) bind .loop/goals/skill-size-2.md:13
REALITY: numbers finding sizes re-measured per branch [measured: git show <branch>:<file> | wc -c]; goal.py and release.py sizes after delivery-prd are [re-measure before gate] skills/workflow-release/scripts/release.py:1
REALITY: deferred-asks pass issues 138-142 ask only to split; nothing left out; 140 may need no code change .loop/goals/skill-size-2.md:16
REALITY: pr-count pass no .skill suite/ship-policy.json, so one PR for the goal; all splits ride the one goal branch docs/designs/skill-size-2.md:58

#### 0C. Dream state

```
  CURRENT STATE                    THIS PLAN                           12-MONTH IDEAL
  5 size issues open; 4 scripts    4 leaf-block moves, 4 new modules,  every script well under the line, splits
  over 18,432; health WARN noise   5 defect rows tied to health's own  happen inside the goal that grows a file,
  hides real WARNs                 rule; 116/138-142 close on merge    health size group stays PASS
```

The plan moves toward the ideal: the size rows reuse health's rule, so the next goal that grows a split file past the
line fails its land lane instead of filing an issue later.

#### 0D. Approach

No new approach decision was needed: Approach A (leaf-block moves, names imported back) stands. The block choices
inside it were corrected as facts (baseline edits below), not as a new choice.

#### 0E. Mode

Mode: SELECTIVE EXPANSION; approved decisions: none. plan review override; about 12 changed files (4 scripts, 4 new
modules, test-defect.sh, regression.tsv, goal file, Setup/Delivery/Documentation/Regression pages): harden the split,
consider small additions one at a time.

#### 0F/0G. Hold checks and cherry-picks

Hold checks: 4 new modules is the minimum (one per warned file). Minimum change: the moves, the rows, the Closes lines,
the page lines. Stated invariants kept: no behaviour change, no back-imports, 1 KB headroom.

| # | Proposal | Effort | Decision | Reasoning |
|---|---|---|---|---|
| E1 | Size rows call health's `size_rows()` instead of a hard-coded 18,432 | S | ACCEPTED (P2, P4) | one rule, in blast radius; if health's line moves, rows follow |
| E2 | Each size row also checks every moved name is still an attribute of the old module | S | ACCEPTED (P1, P2) | catches a dropped import-back line, the one way a pure move breaks callers |
| E3 | Split role.py and the four workflow-monitoring scripts that also warn | M | DEFERRED (P3) | outside this goal's issue mapping and touches; lane-control shrinks role.py |
| E4 | Remove render.py's back-import of criteria | S | DEFERRED (P3) | docs-format owns render.py; not a pure move |
| E5 | Lower health's warn line so splits keep more headroom | S | SKIPPED (P4) | Approach C was rejected; changes HLT-2's contract |

Required repairs (not expansions): the goal file needs a `## Closes` section (P6), the size rows need the split files in
test-defect.sh's `# reads:` header (P4), and the three wiki pages need one line each to clear STALE.

#### Decision ledger

| ID and owner | Contract and evidence | Current | Proposed | Status | Exact approval and scope |
|---|---|---|---|---|---|
| C1 approach (CEO) | Approach A, design doc | leaf moves | none | approved | design APPROVED; unattended recommended answer |
| C2 block choices (CEO) | P5 receipts | stale blocks | corrected blocks via baseline edits | approved | plan review P1 mechanical fact fix |
| C3 Closes section (CEO) | goal.py:360, defect.py:22 | none | `## Closes` with #116, #138-#142 | approved | plan review P1, mechanical repair |
| C4 E1 size rows via health (CEO) | health.py:71-85 | hard-coded bytes | `size_rows()` | approved | plan review P2 |
| C5 E2 name check (CEO) | goal.py:30-33 imports, test-prd.sh:237 | none | per-row attribute check | approved | plan review P2 |
| C6 E3 other warned scripts | health check output | none | defer | deferred | plan review P3 |
| C7 E4 render.py back-import | render.py:13 on docs-format | none | defer | deferred | plan review P3 |
| C8 E5 warn line | Approach C | none | skip | declined | plan review P4 |
| C9 docs pages (CEO) | .loop/docs.tsv, commit dec19ec | none | one line per page | approved | plan review P1, repair |

Approval readiness: PASS (C1-C9; each cites an unattended recommended answer or plan review principle).


<!-- plan review-baseline-edits:ceo {"sourceSha256":"646af73c5a799d2629931fd6cdcdeacbb2f64f159ba84fb7901a012580d043be","replacements":[{"oldText":"- goal.py: the goal-file text helpers (`TEMPLATE`, `done_lines`, `done_sha`, `frozen`, `held`), or\n  `flow_set`/`valid`.","newText":"- goal.py: the run-record and goal-file primitives (`no`, `run`, `git`, `read`, `write`, `now`, `state_dir`,\n  `state_path`, `load`, `save`, `root`, `config`, `goal_file`, `done_lines`, `done_sha`, `base_ref`; 2,534 bytes on\n  main) into a new `goalfile.py`, which imports `role` for `save` and never imports goal. `frozen`, `held`,\n  `fail_stop`, `failed_try`, `cmd_wait` and `cmd_answer` stay: they hand `sys.modules[__name__]` to guards.py.\n  Fallback if delivery-prd grew the file: also move `FLOW`, `FLOW_FILE`, `NO_FLOW`, `SLUG`, `TEMPLATE`, `flow_set`\n  and `valid`."},{"oldText":"- criteria.py: the tests-format and scenario-table block (`tests_format`, `scenario`, `table`, `issue_cell`,\n  `RUNS`/`SEEN`).","newText":"- criteria.py: docs-format already moved the tests-format and scenario-table block into render.py (17,666 bytes on\n  loop/docs-format, 766 under the line; a pre-merge figure). Move the page-rules block (`SHEET`, `CRITERIA_MAX_DEFAULT`, `rules`,\n  `criteria_max`; 2,279 bytes) into a new `pagerules.py`. `SHEET` keeps resolving because the new file sits in the\n  same folder, and render.py's `criteria.SHEET` and `criteria.rules()` resolve through the import-back."},{"oldText":"- regression.py: the issue-sync block (`gh`, `sync_issues`, `MARK`).","newText":"- regression.py: lane-control already moved the issue-sync block (`gh`, `sync_issues`, `MARK`) out (18,217 bytes on\n  loop/lane-control, a pre-merge figure), and docs-format also edits cmd_run (the two branches conflict there). Move the goal and page\n  readers (`done_lines`, `criteria_ids`, `criterion_rows`, 1,141 bytes, with a copy of the two-line `path_of`) into a\n  new `rowreaders.py`. Fallback: also `chosen` and `clean`."},{"oldText":"- release.py: the changelog and version block (`bump`, `subjects`, `changelog_text`, `restore`), or the docs and\n  criteria checks.","newText":"- release.py: the changelog and version block (`VERSION`, `bump`, `verify_steps`, `subjects`, `changelog_text`,\n  `restore`; 2,572 bytes, with copies of `run` and `git`) into a new `cutlog.py`. The docs and criteria checks\n  (`doc_rows`, `docs_trouble`, `criteria_trouble`) and `run` stay: test-prd.sh sets `release.doc_rows` and\n  `release.run` and expects `criteria_trouble` to see them. Fallback: also `now`, `state_path`, `load`, `save`,\n  `finished` and `read_config`."},{"oldText":"`criteria.tests_format` and the other names","newText":"`criteria.rules` and the other names"},{"oldText":"- Other goals are editing these files now: docs-format (criteria.py, docs.py), lane-control (regression.py),\n  delivery-prd (goal.py, release.py).","newText":"- Other goals are editing these files now: docs-format (criteria.py, docs.py, regression.py), lane-control\n  (regression.py, goal.py), delivery-prd (goal.py, release.py)."},{"oldText":"3. Issue 116 and the docs.py half of issue 140 are proved with rows that already pass, not redone.","newText":"3. Issue 116 is proved by the existing `skill-size-116` row, not redone. docs.py (issue 140, filed at 20,281 bytes)\n   needs no split if it stays at most 17,408 bytes after docs-format merges (17,114 on that branch); it gets a new\n   size row either way."},{"oldText":"Only leaf blocks move: functions whose dependencies are the standard\n  library, each other, or a tiny primitive that is copied as well (for example `git` or `run`, a few lines each,\n  kept identical in both files).","newText":"Only leaf blocks move: functions whose dependencies are the standard\n  library, each other, a sibling module that does not import the old module (for example `role` or `pageformat`),\n  or a tiny primitive that is copied as well (for example `git` or `run`, a few lines each, kept identical in both\n  files)."},{"oldText":"- Pure-move commits: one commit per file, holding just the move and the import-back line. A reviewer can then\n  check with `git diff --color-moved`.","newText":"- Pure-move commits: one commit per file, holding the moved lines, the new module's docstring and imports, the\n  copied primitives, the import-back line and, in release.py only, a `sys.path.insert` of its own folder. A\n  reviewer can then check with `git diff --color-moved`."},{"oldText":"The\n  operation session is widening them to add skills/workflow-regression/scripts and skills/workflow-release/scripts.","newText":"The\n  operation session has already added skills/workflow-regression/scripts and skills/workflow-release/scripts, and\n  is asked to add docs/wiki (Setup, Delivery, Documentation and Regression pages change)."},{"oldText":"Approach A. Order the work by merge: each file is split as soon as the goal editing it has merged into main, and\nthe branch merges main right before `goal.py pr`. Add one defect row per issue (138, 139, 141, 142), linked to its\nissue. Each row checks that its file is below 18,432 bytes, is seen failing on the old code, and passes after the\nsplit. Record each done line on the Setup PRD page as a Given/When/Then scenario under SET-3 (DOC-3). For done\nlines 1 and 2, point at the existing `skill-size-116` and `skill-kept` rows, and add a docs.py size row for\nissue 140.","newText":"Approach A. Order the work by merge: each file is split as soon as the goal editing it has merged into main, and\nthe branch merges main right before `goal.py pr`. Add one defect row per issue (138 to 142), linked to its issue.\nEach row checks the script and its new module against health's own size rule and checks that the moved names\nresolve on the old module; it is seen failing on a padded copy of the script and passes after the split. Record\neach done line on the Setup PRD page as a Given/When/Then scenario under SET-3 (DOC-3). For done lines 1 and 2,\npoint at the existing `skill-size-116` and `skill-kept` rows."},{"oldText":"- docs-format, lane-control and delivery-prd merge first, or their in-flight edits to these files are left alone.","newText":"- docs-format, lane-control and delivery-prd merge first. A file whose blocking goal has not merged is not split;\n  the worker stops with `goal.py wait` naming that goal instead of splitting from an older base."},{"oldText":"- The operation session widens touches to skills/workflow-regression/scripts and skills/workflow-release/scripts.","newText":"- Touches already include skills/workflow-regression/scripts and skills/workflow-release/scripts; the operation\n  session is asked to add docs/wiki."},{"oldText":"together with a new defect row\n   that fails on the old sizes and passes on the new ones.","newText":"together with a new defect row\n   per issue that fails on a padded copy of its script and passes on the split one."},{"oldText":"- `wc -c` shows goal.py, criteria.py, regression.py and release.py each below 18,432 bytes, with docs.py still\n  below it too.","newText":"- `wc -c` shows goal.py, criteria.py, regression.py and release.py each at most 17,408 bytes, with docs.py below\n  18,432."}]} -->

<!-- plan review-accepted:ceo -->
- Each split starts from merged main: after the goal editing that file merges (docs-format for criteria.py, docs.py and regression.py; lane-control for regression.py and goal.py; delivery-prd for goal.py and release.py), merge main into loop/skill-size-2, re-measure with `wc -c`, and re-derive the leaf block and the stay-put names from the merged file, and move the named block (plus its named fallback if needed) until the file is at most 17,408 bytes (1 KB under 18,432); each new module stays under 17,408 too. If the named block no longer exists or the block plus fallback is not enough (delivery-prd may move goal.py code itself), pick another leaf block by the same rules and record the choice in the commit message; if no leaf block fits, stop with `goal.py finding` naming the file.
- New modules: goal.py -> `goalfile.py`, criteria.py -> `pagerules.py`, regression.py -> `rowreaders.py`, release.py -> `cutlog.py`. Each imports only the standard library and siblings that are not its old module (goalfile.py may import `role`); none imports its old module. The old module gets one line `from <new> import <names>  # noqa: E402,F401` after its last top-level import and before the first module-level use of a moved name, so every moved name resolves as `<old>.<name>`. release.py, which has no `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))`, gains that line in the same commit, because dev/toy/test-release.sh:86 loads it by file path from the repo root; no other file needs it (only release.py is loaded that way).
- Moved versus copied, per file: goal.py moves all its block (no copies; `run` and `git` move too); criteria.py moves all (no copies); regression.py copies `path_of`; release.py copies `run` and `git`.
- Names that stay put: goal.py keeps `frozen`, `held`, `fail_stop`, `failed_try`, `cmd_wait`, `cmd_answer` (they pass `sys.modules[__name__]` to guards.py); release.py keeps `doc_rows`, `docs_trouble`, `criteria_trouble` and `run` (test-prd.sh:239-240 sets `release.doc_rows` and `release.run`).
- docs.py: if it is over 17,408 bytes after docs-format merges, it gets a leaf-block move by the same rules into a new `docsparts.py` (then added to the reads header and the size-140 case); otherwise it is not edited.
- Each new module's docstring says which module its names came from and that the old module imports them back for existing callers.
- One pure-move commit per file: the moved lines, the new module's docstring and import lines, the import-back line, and the copied two-to-five-line primitives (`run`, `git`, `path_of`) only. `git diff --color-moved=zebra HEAD~1` shows nothing else; the old module no longer has a `def` or assignment for any moved name.
- The goal file gains a `## Closes` section (outside Done lines, so the done-line hash is unchanged). It opens with one sentence saying what the PR does (splits goal.py, criteria.py, regression.py and release.py by pure moves; docs.py is split only if needed, so issue 140 may close with no code change; role.py and four workflow-monitoring scripts still warn and are not in scope), then `Closes #138`, `Closes #139`, `Closes #140`, `Closes #141`, `Closes #142` one per line, and `Refs #116` (already closed by PR #163, still proved by `skill-size-116`).
- Five defect rows, ids `size-138`, `size-139`, `size-140`, `size-141`, `size-142`: level land, category defect, goal SET-3, link the issue URL, command `bash dev/toy/test-defect.sh size-<N>`, description a Given/When/Then sentence. Each case (1) copies only its script and new module into a temp root at the same `skills/<skill>/scripts/` path and passes only when `health.size_rows(<temp root>)` gives no WARN or FAIL row (so it follows health's line without listing every skill folder, which the lanes-trace row would flag); (2) lists the new module's top-level `def` and assignment names with `ast`, minus that file's copied primitives, requires that set to equal the names in the old module's import-back line, then imports the old module with `$here/skills/<skill>/scripts` on sys.path, takes `new = sys.modules["<new>"]`, and checks `getattr(old, n) is getattr(new, n)` for each; (3) greps the old file for no `^def <name>\b` and no `^<NAME> =` per moved name; (4) for each copied primitive (`run`, `git`, `path_of`), checks its source in the new module is byte-identical to the old module's. size-140 without `docsparts.py` checks only (1). Each case also runs a built-in negative control on a temp copy (drop one name from the import-back line, and leave one `def` behind) and fails unless checks (2) and (3) catch both, so all three checks are seen failing, not only the size half. `size-138` to `size-142` are added to test-defect.sh's `cases=` list so a no-argument run includes them.
- Commit the new cases and rows first (`regression.py red` runs the row in a detached worktree of HEAD), then see each row red with `regression.py red size-<N> --break "<cmd>"`, where the break pads its script past health's `WARN_AT` (for example appending a comment line of 18,432 `#` characters). Restoring the pre-split file is not used: on merged main criteria.py and regression.py may already be under 18,432, and red would print STILL GREEN.
- dev/toy/test-defect.sh's `# reads:` header names the five scripts, the four new modules and health.py, so lanes select the size rows when any of them changes.
- `criteria.py render` runs after the rows are added, so docs/wiki/Setup.md's Tests show size-138 to size-142 wherever `criteria.py render` puts SET-3 defect rows on merged main (a list on main today, a table after docs-format), and `criteria.py render --check` reports no stale page; done lines 1 and 2 stay proved by `skill-size-116` and `skill-kept`.
- docs/wiki/Delivery.md (naming `goalfile.py` and `cutlog.py`, since docs.tsv maps both skill folders to it), Documentation.md (`pagerules.py`, and `docsparts.py` if made) and Regression.md (`rowreaders.py`) each get one sentence in their Usage section naming the new module, and `docs.py check` and `criteria.py render --check` show no contract finding for them. These page commits come after the last split, row and header commits, so `docs.py check` shows no STALE page at pr.
- Order and blockers: a file is split only after its blocking goal merged; if one has not merged when the rest is done, the worker stops with `goal.py wait` naming that goal rather than splitting from an older base. The operation session is asked to widen touches with docs/wiki; if that is refused, the worker stops with `goal.py wait` before `criteria.py render` or any page edit.
- SKILL.md files: this goal never edits one. If `skill-size-116` turns red after a merge, the worker records `goal.py finding` naming the goal that merged, rather than trimming SKILL.md here.
- Sizes quoted from loop/lane-control and loop/docs-format are pre-merge guesses (lane-control predates guards.py); the re-derive step after each merge is the binding rule.
- The PR title is the frozen goal text ("Fix issue 116: ...") cut to 70 characters by `goal.py pr`; it is accepted as is, and the PR body (the goal file with its `## Closes` section) says what the PR does.
- NOT in scope: splitting role.py and the four workflow-monitoring scripts that also warn (not in the issue mapping); removing render.py's back-import of criteria (docs-format owns it); lowering health's warn line.
- Verification before pr: `health.py check` may still WARN for role.py and the four workflow-monitoring scripts (not in scope); the success criterion covers only the five files. `wc -c` shows each split script and new module at most 17,408 bytes and docs.py under 18,432; `health.py check` shows no size WARN for them; `regression.py run nightly` (land and nightly rows) passes on HEAD; each consumer test runs in full and ends ALL PASS or exit 0: dev/toy/test-release.sh, test-prd.sh, test-criteria.sh, test-docs-command.sh, test-summary.sh, test-regression.sh, test-goal.sh, test-guards.sh, test-defect.sh; `defect.py owed skill-size-2` prints NONE OWED.
<!-- plan review-accepted:ceo -->

#### 0H. CEO plan and spec review loop

CEO plan: <local path>
Spec review: 3 launches (cap). Scores 6, 6, 7 (latest 7/10, FAIL). Found 39 issues, 28 confirmed fixed by the next
round, 11 from round 3 applied and checked against the amended plan text (issues verified: 12 of 12 edits), spec not
re-verified. Metrics appended to analytics/spec-review.jsonl. Main fixes: pad-based red breaks (restoring merged-main
files would stay green), size check on a temp copy (lanes-trace), ast-based name parity with a negative control,
release.py `sys.path.insert` (test-release.sh:86 loads it by path), wiki commits last, `goal.py wait` for an unmerged
blocker or refused docs/wiki touches, `goal.py finding` for a missing leaf block or a red skill-size-116.
Document approval (0H): auto-decided A, approve both documents and continue to 0I (unattended recommended answer).

#### 0I. Temporal interrogation

```
  HOUR 1 (foundations):  merge main after each blocker; wc -c; re-derive the leaf block and stay-put names.
  HOUR 2-3 (core):       four pure-move commits; import-back anchor; release.py sys.path line; ast name parity.
  HOUR 4-5 (integration): test-defect.sh cases + reads header + rows; commit; red with padding; criteria.py render.
  HOUR 6+ (polish/tests): wiki Usage sentences last; nightly suite + consumer tests; defect.py owed; Closes section.
```
Effort: human team about 1 day; CC + skill suite about 1-2 hours of build, gated by the three blocking merges.
Feasibility blockers: none in the plan; the schedule depends on docs-format, lane-control and delivery-prd merging
(delivery-prd is still at its idea step).

<!-- AUTONOMOUS DECISION LOG -->
## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | CEO | Mode SELECTIVE EXPANSION | Mechanical | override | plan review rule | other modes |
| 2 | CEO | Keep Approach A (leaf moves, import-back) | Mechanical | P5 | only provably behaviour-free split | B trim, C raise line |
| 3 | CEO | Correct criteria.py/regression.py blocks (already moved by docs-format/lane-control) | Mechanical | P1 | stale facts | design's blocks |
| 4 | CEO | goal.py keeps frozen/held/fail_stop/failed_try/cmd_wait/cmd_answer | Mechanical | P5 | they pass sys.modules[__name__] to guards | moving them |
| 5 | CEO | release.py keeps doc_rows/docs_trouble/criteria_trouble/run | Mechanical | P5 | test-prd.sh:239-240 patches release globals | docs-check block move |
| 6 | CEO | Add `## Closes` #116, #138-#142 to goal file | Mechanical | P1 | defect gate and auto-close need #N | none |
| 7 | CEO | E1 size rows reuse health.size_rows | Taste (borderline) | P2/P4 | one rule | hard-coded 18,432 |
| 8 | CEO | E2 name parity check in rows | Taste (borderline) | P1 | catches dropped import-back | no check |
| 9 | CEO | Defer E3 (role.py, monitoring scripts) | Mechanical | P3 | outside issue mapping | add to scope |
| 10 | CEO | Defer E4 (render.py back-import) | Mechanical | P3 | docs-format owns it | fix here |
| 11 | CEO | Skip E5 (lower warn line) | Mechanical | P4 | contradicts HLT-2 | change rule |
| 12 | CEO | Red breaks pad the script past WARN_AT | Mechanical | P5 | restore would stay green | git checkout restore |
| 13 | CEO | Size check on a temp copy | Mechanical | P5 | lanes-trace flags full glob | size_rows(repo) |
| 14 | CEO | release.py gains sys.path.insert | Mechanical | P5 | test-release.sh:86 path load | leave as is |
| 15 | CEO | Unmerged blocker or refused docs/wiki touches -> goal.py wait | Mechanical | P6 | never split from stale base | split anyway |
| 16 | CEO | Wiki Usage sentences, committed last | Mechanical | P1 | clears STALE | no page edits |
| 17 | CEO | PR title stays the frozen goal text | Mechanical | P6 | done lines/goal frozen; body explains | retitle |
| 18 | CEO | 0H document approval A | Mechanical | P6 | unattended recommended | revise, pause |

| 19 | CEO | Refs #116 instead of Closes #116 (already CLOSED) | Mechanical | P5 | `gh issue view 116`: CLOSED | Closes #116 |
| 20 | CEO | Closes section leads with a scope sentence (still-warning scripts, 140 maybe no code) | Mechanical | P1 | PR title is frozen goal text | none |
| 21 | CEO | Copied primitives byte-identical check in rows; new-module docstring names origin | Mechanical | P2 | drift guard, cheap | shared common.py (new coupling) |
| 22 | CEO | Keep one PR for the goal; no per-blocker partial PRs | Taste | P5/P6 | goal.py pr is per goal, done lines frozen, no ship-policy split; partial ship needs new goals | per-blocker PRs (native voice) |
| 23 | CEO | Keep one defect row per issue | Taste | P5 | defect gate and Tests table read one link per row; matches skill-size-116 | one parametrized row (native voice) |
| 24 | CEO | Defer health auto-split tool and SET-3 measure revisit | Mechanical | P3 | outside blast radius | add now |

#### Step 0.5 dual voices

Native CEO voice (Claude subagent, foreground): completed, INPUT ceo 8b9879f6...57f8 matches the snapshot hash. Findings:
HIGH whack-a-mole (five other scripts still warn; this is the second size goal); HIGH calendar risk from three
blockers (asks for partial shipping or size done lines in the blocking goals); MEDIUM size-cut modules and copied
primitives may drift; MEDIUM proof surface is large (asks for one parametrized row); MEDIUM Approaches B/C dismissed
quickly (asks for a SET-3 measure TODO); MEDIUM premises 1/3 (PR title misleading, 140 may close with no code); MEDIUM
blocking goals already shrink these files; LOW `sys.path.insert` name collision, `Closes #116` may be stale.

Codex CEO voice: unavailable. `codex exec` started (model gpt-6-astra, AUTH_OK) and failed with "You've hit your usage
limit ... try again at 6:01 AM" (turn.failed). Per the gate learning this is quota_exhausted: no more Codex calls
this run; every phase is [single-model] / [subagent-only].

```
CEO DUAL VOICES — CONSENSUS TABLE: [subagent-only]
  Dimension                            Claude  Codex  Consensus
  1. Premises valid?                   mostly  N/A    N/A
  2. Right problem to solve?           partly  N/A    N/A
  3. Scope calibration correct?        no(+)   N/A    N/A
  4. Alternatives sufficiently explored? no    N/A    N/A
  5. Competitive/market risks covered? no      N/A    N/A
  6. 6-month trajectory sound?         partly  N/A    N/A
Outside unavailable (quota): six Consensus cells N/A, never CONFIRMED.
```

Dispositions: accepted the PR-body scope sentence, `Refs #116`, still-warning note, copied-primitive identity check and
module docstrings (rows 19-21). Taste (rows 22-23): keep one PR and one row per issue; the native voice's alternatives
are reasonable but per-blocker PRs need new goals (done lines are frozen) and one row per issue is what the defect gate
and the Tests table expect. Deferred (row 24): a health auto-split tool and revisiting SET-3's per-file measure. No User
Challenge: a single voice cannot form one, and no finding contradicts the owner's direction. Single-voice HIGH flagged:
the three-blocker schedule risk; it stays a known risk, handled by `goal.py wait`.

#### Review sections

Current scope: mode SELECTIVE EXPANSION (override). Accepted: Approach A with corrected blocks (C1, C2), Closes/Refs
section (C3, rows 19-20), E1 and E2 (C4, C5), copied-primitive check and docstrings (row 21), wiki lines (C9). Deferred:
E3, E4, health auto-split, SET-3 measure. Rejected: E5. Pending: none.

**Section 1: Architecture.** Dependency graph after the split (arrows = imports):

```
  goal.py ──> goalfile.py ──> role.py          criteria.py ──> pagerules.py ──(lazy)──> pageformat.py
     │  └──> defect.py, guards.py, role.py         ▲  (render.py ──> criteria.py: existing back-import, not ours)
     └── guards.py gets goal via sys.modules (unchanged)
  regression.py ──> rowreaders.py (stdlib only; own copy of path_of)
     └──> actions.py, lanes.py, (slots.py, runs.py after merges)
  release.py ──> cutlog.py (stdlib only; own copies of run, git)
     ▲  merge.py, wiki.py, autorelease.py import release (names resolve via import-back)
```
New coupling: one edge per file, all one-way. No new stateful object, endpoint or data flow; data paths (state JSON,
regression.tsv, changelog) are the same code in a new file. Rollback: revert the four move commits (5 minutes); nothing
persistent changes. Single point of failure: the import-back line; guarded by check (2). Value test: the size rows are
consumed by the land lane (they fail a future goal that grows a split file); the PR-body scope sentence is read by the
reviewer. 1 finding (stale blocks, fixed in Step 0).

**Section 2: Error & Rescue Map.**

```
  CODEPATH                         | WHAT CAN GO WRONG                          | CLASS
  old module import-back line      | moved name missing from the line           | AttributeError at call site
  release.py loaded by file path   | cutlog not on sys.path                     | ModuleNotFoundError
  new module imports old module    | second module copy under __main__          | silent state split
  size row in temp root            | health.py changes size_rows signature      | TypeError -> row FAIL
  regression.py red with padding   | break leaves file under WARN_AT            | STILL GREEN, row unrecorded
  goalfile.save -> role.report     | role import fails                          | ImportError at goal.py start
  ---------------------------------+--------------------------------------------+-------------------------
  CLASS                | RESCUED? | RESCUE ACTION                                   | USER SEES
  AttributeError       | Y (test) | check (2) ast set equality + negative control   | row FAIL naming the name
  ModuleNotFoundError  | Y        | sys.path.insert in release.py; test-release.sh  | consumer test FAIL
  silent state split   | Y (rule) | "never imports old module"; review of imports   | nothing (prevented)
  TypeError            | Y        | row fails loudly; health owner fixes            | land lane FAIL
  STILL GREEN          | Y        | pad 18,432 bytes, rerun red                     | red refuses, prints why
  ImportError          | Y (test) | test-goal.sh/test-guards.sh in verification     | consumer test FAIL
```
0 GAPS. No catch-all handlers added; the plan adds no runtime error handling at all (pure moves).

**Section 3: Security.** Examined: new files are stdlib-only modules in existing skill folders; no new input, endpoint,
secret, dependency or subprocess call (moved `run`/`git` are the same code). `sys.path.insert(0, own folder)` in
release.py puts only the skill's own folder first, as goal.py and regression.py already do; a planted `cutlog.py`
elsewhere on the path cannot shadow it because the own folder comes first. No issues found.

**Section 4: Data flow & edge cases.** The only new flow is the size row:
`script + module -> copy to temp root -> health.size_rows -> rows -> PASS/FAIL`. Shadow paths: module missing (no split
yet) -> size-140 path checks size only; other rows FAIL with "no module" (correct: the split is owed); empty file ->
size 0 PASS (impossible in practice); temp dir not writable -> mktemp fails, row FAIL loudly; health.py moved -> import
error, row FAIL. Interaction edge cases: two goals splitting the same file concurrently -> touches + blocker order
prevent it; a later goal re-adding a def that was moved -> check (3) FAILs. 0 unhandled.

**Section 5: Code quality.** Fits existing patterns (guards.py, runs.py, slots.py are sibling modules; every script
keeps its own run/git per SET-3). Naming: `goalfile`, `pagerules`, `rowreaders`, `cutlog` say what they hold. Duplicated
behaviour: copied run/git/path_of are the repo convention and now drift-checked (row 21). No over-engineering: no shared
`common.py` (would be a new cross-file coupling). 1 finding (drift), fixed.

**Section 6: Tests.**

```
  NEW THING                    | TEST TYPE          | HAPPY                    | FAILURE                      | EDGE
  goal.py split                | integration (toy)  | test-goal/guards ALL PASS| size-138 padded -> FAIL      | name dropped -> neg control
  criteria.py split            | integration (toy)  | test-criteria/prd/docs   | size-139 padded -> FAIL      | SHEET path from new file
  regression.py split          | integration (toy)  | test-regression          | size-141 padded -> FAIL      | path_of copy identical
  release.py split             | integration (toy)  | test-release (path load) | size-142 padded -> FAIL      | monkeypatch test-prd 239
  docs.py (140)                | integration (toy)  | size-140                 | padded -> FAIL               | docsparts only if needed
  Closes/Refs section          | gate               | defect.py owed NONE OWED | missing row -> OWED          | #116 Refs not counted
```
Assertions: each row asserts "no WARN/FAIL size row for exactly these two files" (no_claim: does not prove callers
outside dev/toy behave the same; full suites cover that), name-set equality and identity (no_claim: dynamic getattr by
string elsewhere), no leftover defs, primitive identity. Flakiness: none (no time, network or randomness). 2am test:
nightly suite + consumer tests ALL PASS. Hostile QA: drop a name from import-back -> negative control. Chaos: run
release.py by path from the repo root (test-release.sh 3d). 0 gaps after Step 0 fixes.

**Section 7: Performance.** One extra module import per script start (a few ms); health size rows add 5 land rows of
well under a second each. No issues found.

**Section 8: Observability.** Failures surface as named row FAILs (`size-<N>`) and as health WARNs; red prints STILL
GREEN when a break does not bite. Debuggable from the commit message (block chosen) and `git diff --color-moved`. No
new runtime logging needed for a pure move. No issues found.

**Section 9: Deployment.** Ships in the package's next release through the normal merge/cut path; no migration, no
flag. Old and new code never coexist in one install (the skill folder is copied whole). Rollback: revert the commits
and cut a patch. Risk flagged: release ordering after three blocking goals (schedule, not correctness).

**Section 10: Long-term trajectory.** Reversibility 5/5. Debt: four import-back shims and three copied primitives
(guarded). Path dependency: future edits must go to the new module for moved names; docstrings say so. The native voice's
point stands: size fixes recur; a health auto-split helper and a SET-3 measure revisit are deferred, not dropped.
Retrospective: E1/E2 were the right picks; nothing rejected turned out to be needed.

**Section 11: Design & UX.** SKIPPED (no UI scope).

#### Required outputs (CEO)

NOT in scope (deferred): E3 split role.py and four workflow-monitoring scripts (outside the issue mapping); E4 remove
render.py's back-import (docs-format owns it); a health auto-split helper; revisiting SET-3's per-file measure.
Rejected: E5 lower the warn line (contradicts HLT-2); per-blocker partial PRs (needs new goals); one parametrized row
(defect gate and Tests table expect one link per row). No TODOS.md exists; the deferrals are listed here and in the
goal report.

What already exists: guards.py (module-injection pattern; stays), runs.py/slots.py/render.py (prior sibling splits),
health.size_rows (reused by the rows), regression.py red (seen-red proof), defect.py owed + goal.py pr gate (reused via
Closes), criteria.py render (Setup Tests), lanes.py/narrow.py import following (new modules join lanes),
test-defect.sh case pattern (`skill-size`, `skill-kept`).

Dream state delta: after this plan, the four files sit about 1-2 KB under the line with rows that fail a future
over-growth in the land lane; still short of the ideal where health proposes the split itself and the five other
warned scripts are clean.

Error & Rescue Registry: see Section 2 (6 codepaths, 0 critical gaps).

```
  Failure Modes Registry
  CODEPATH              | FAILURE MODE                 | RESCUED? | TEST? | USER SEES?         | LOGGED?
  import-back line      | name dropped                 | Y        | Y     | row FAIL           | Y (row output)
  release.py path load  | cutlog not found             | Y        | Y     | test-release FAIL  | Y
  new->old import       | duplicate module state       | Y (rule) | Y (2) | n/a (prevented)    | n/a
  copied primitive      | drift                        | Y        | Y     | row FAIL           | Y
  red break             | STILL GREEN                  | Y        | Y     | red refuses        | Y
  blocker not merged    | split from stale base        | Y        | n/a   | goal waits (wait)  | Y (run log)
  docs pages            | STALE at pr                  | Y        | Y     | docs check names it| Y
```
7 rows, 0 CRITICAL GAPS.

Diagrams: system architecture (Section 1), error flow (Section 2), test map (Section 6). Data flow is the single size
row flow (Section 4); no state machine, deployment or rollback diagram needed (no state, no migration; rollback is a
revert). Stale diagram audit: the files touched hold no ASCII diagrams.

REALITY lines: see Step 0 (7 rows).

```
  +====================================================================+
  |            MEGA PLAN REVIEW — COMPLETION SUMMARY                   |
  +====================================================================+
  | Mode selected        | SELECTIVE EXPANSION                         |
  | System Audit         | blocks stale on 2 files; no #N in goal file |
  | Step 0               | corrected blocks, Closes, E1+E2 accepted    |
  | Section 1  (Arch)    | 1 issue found (fixed)                       |
  | Section 2  (Errors)  | 6 error paths mapped, 0 GAPS                |
  | Section 3  (Security)| 0 issues found, 0 High severity             |
  | Section 4  (Data/UX) | 6 edge cases mapped, 0 unhandled            |
  | Section 5  (Quality) | 1 issue found (fixed)                       |
  | Section 6  (Tests)   | Diagram produced, 0 gaps                    |
  | Section 7  (Perf)    | 0 issues found                              |
  | Section 8  (Observ)  | 0 gaps found                                |
  | Section 9  (Deploy)  | 1 risk flagged (blocker schedule)           |
  | Section 10 (Future)  | Reversibility: 5/5, debt items: 2           |
  | Section 11 (Design)  | SKIPPED (no UI scope)                       |
  +--------------------------------------------------------------------+
  | NOT in scope         | written (7 items)                           |
  | What already exists  | written                                     |
  | Dream state delta    | written                                     |
  | Error/rescue registry| 6 rows, 0 CRITICAL GAPS                     |
  | Failure modes        | 7 total, 0 CRITICAL GAPS                    |
  | TODOS.md updates     | 0 (no TODOS.md; 4 deferrals listed)         |
  | Scope proposals      | 5 proposed, 2 accepted                      |
  | CEO plan             | written                                     |
  | Outside voice        | codex unavailable (usage limit)             |
  | Lake Score           | N/A (no scored questions asked)             |
  | Diagrams produced    | 3 (architecture, error flow, test map)      |
  | Stale diagrams found | 0                                           |
  | Unresolved decisions | 0                                           |
  | Reality rows         | 7/7 rows, 0 unverified                      |
  +====================================================================+
```

PLAN_REALITY: phase=ceo rows=7/7 missing=none unverified=0 verdict=complete

#### Implementation Tasks (CEO)

- [ ] **T1 (P1, human: ~1h / CC: ~10min)** — goal file — add `## Closes` (scope sentence, Closes #138-#142, Refs #116)
  - Surfaced by: Step 0 premise P6 (goal.py:360, defect.py:22)
  - Files: .loop/goals/skill-size-2.md
  - Verify: `defect.py owed skill-size-2` lists #138-#142 until rows exist, then NONE OWED
- [ ] **T2 (P1, human: ~2h / CC: ~15min)** — workflow-docs — split criteria.py -> pagerules.py after docs-format merges
  - Surfaced by: Step 0 P5 (block already moved by docs-format)
  - Files: skills/workflow-docs/scripts/criteria.py, skills/workflow-docs/scripts/pagerules.py
  - Verify: test-criteria.sh, test-prd.sh, test-docs-command.sh, test-summary.sh ALL PASS; size-139
- [ ] **T3 (P1, human: ~2h / CC: ~15min)** — workflow-regression — split regression.py -> rowreaders.py after docs-format and lane-control merge
  - Surfaced by: Step 0 P5
  - Files: skills/workflow-regression/scripts/regression.py, skills/workflow-regression/scripts/rowreaders.py
  - Verify: test-regression.sh, test-prd.sh ALL PASS; size-141
- [ ] **T4 (P1, human: ~2h / CC: ~15min)** — workflow-delivery — split goal.py -> goalfile.py after lane-control and delivery-prd merge
  - Surfaced by: Step 0 (stay-put names for guards.py)
  - Files: skills/workflow-delivery/scripts/goal.py, skills/workflow-delivery/scripts/goalfile.py
  - Verify: test-goal.sh, test-guards.sh, test-defect.sh ALL PASS; size-138
- [ ] **T5 (P1, human: ~2h / CC: ~15min)** — workflow-release — split release.py -> cutlog.py (+ sys.path.insert) after delivery-prd merges
  - Surfaced by: spec review round 2 (test-release.sh:86)
  - Files: skills/workflow-release/scripts/release.py, skills/workflow-release/scripts/cutlog.py
  - Verify: test-release.sh, test-prd.sh ALL PASS; size-142
- [ ] **T6 (P1, human: ~3h / CC: ~20min)** — dev/toy + rows — size-138..142 cases (temp-root size, ast name parity, leftover defs, primitive identity, negative control), reads header, cases list, rows, commit, red with padding
  - Surfaced by: E1, E2, spec review rounds 1-3
  - Files: dev/toy/test-defect.sh, .loop/regression.tsv
  - Verify: `regression.py red size-<N> --break ...` prints SEEN RED; `bash dev/toy/test-defect.sh` ALL PASS
- [ ] **T7 (P2, human: ~1h / CC: ~10min)** — wiki — `criteria.py render`; one Usage sentence each on Delivery, Documentation, Regression; commit last
  - Surfaced by: Retrospective (docs.tsv staleness)
  - Files: docs/wiki/Setup.md, docs/wiki/Delivery.md, docs/wiki/Documentation.md, docs/wiki/Regression.md
  - Verify: `docs.py check` no STALE; `criteria.py render --check` clean
- [ ] **T8 (P1, human: ~1h / CC: ~10min)** — verification — wc -c, health check, nightly suite, consumer tests, defect owed
  - Surfaced by: spec review round 2
  - Files: none
  - Verify: as listed in the accepted requirements

### Phase 2 (Design): skipped

No UI scope (init scope `uiRequired=false`; the plan changes Python scripts, a toy test, regression rows and wiki
text). Skipped, not a completed review.

### DX phase (Phase 2.5)

Methodology read: plan review-dx-methodology-vrfzhi/methodology.md ranges 1-600, 601-1200, 1201-1800, 1801-1905 (1905 of
1905 lines). Hall of Fame sections Pass 1-8 and the Claude Code Skill checklist read. DX scope: `dxRequired=true` by
terms (command, library, import x4, SKILL.md; 8 matches). Mode: DX POLISH (override). Product type: Claude Code Skill
package (Python scripts run by agents), auto-confirmed (unattended). Outside voice: Codex unavailable (usage limit hit
in Phase 1; no further Codex calls this run).

#### 0A. Persona

```
TARGET DEVELOPER PERSONA
========================
Who:       an AI coding agent working a later goal in this repo (worker session), plus the owner reviewing its PR
Context:   it must change behaviour that now lives in goalfile.py / pagerules.py / rowreaders.py / changelog.py,
           or it hits a red size-<N> row after growing one of the split files
Tolerance: reads errors literally, cannot ask, retries blindly; a vague red row costs a failed try
Expects:   grep finds the def; a red row says which file, which name, and the edit that fixes it
```
(Auto-decided A: AI coding agent, from README and loop-files: goals run in unattended worker sessions.)

#### 0B. Empathy narrative

I'm the worker for a later goal that adds a field to the goal state. I open goal.py and look for `save`; it isn't
defined there, only used. Line 34 says `from goalfile import (... save ...)  # noqa`. I open goalfile.py, its docstring
says these names moved from goal.py and are imported back, so I edit `save` there. My change pushes goal.py past
18,432 because I also added a command; size-138 goes red. Today's plan says the row "passes only when" but not what
it prints, so I would see `size-138: ...` with no fix and guess. If it prints the byte count, the line, and "move
another leaf block into goalfile.py, see docs/designs/skill-size-2.md", I fix it in one try. (Observed: goal.py import
style, test-defect.sh `no()` helper prints `<case>: <text>` and exits 1. Predicted: the confusion when messages are
unspecified.)

#### 0C. Benchmark and target

| Tool | Start -> result | Time + evidence | DX choice | Source |
|---|---|---|---|---|
| This repo, guards.py precedent | find a moved goal function | about 1 min, estimated | module docstring + `g.` calls | skills/workflow-delivery/scripts/guards.py:1-20 |
| This repo after split (plan) | find a moved function, fix a red size row | about 1-2 min, estimated | docstring, import-back comment, row fix line | plan |
| Python stdlib re-export practice | find a moved name | about 1 min | `__init__` re-exports, docs | WebSearch result (Auralis issue 6198) |

Target: Champion (< 2 min) from "red row or missing def" to "correct file edited", auto-decided (A). Clock starts when
the agent reads the row output or greps for the def.

#### 0D. Magical moment

A red `size-<N>` row whose last line is the exact fix (`fix: move another leaf block from goal.py into goalfile.py by
the rules in docs/designs/skill-size-2.md, then rerun bash dev/toy/test-defect.sh size-138`). Vehicle: existing
test-defect.sh `no()` output (existing capability). Auto-decided A.

#### 0E. Mode: DX POLISH (override; enhancement to an existing package).

#### 0F. Journey map

```
STAGE           | DEVELOPER DOES                               | FRICTION POINTS                         | STATUS
----------------|----------------------------------------------|-----------------------------------------|--------
1. Discover     | greps for a def, finds the import-back line  | no pointer to where new helpers go      | fixed (import-back comment)
2. Install      | skill folder copied whole by setup           | partial copy -> ModuleNotFoundError     | ok (setup copies whole folder; residual)
3. Hello World  | edits the moved function in the new module   | patching old.name no longer reaches it  | fixed (docstring + grep check)
4. Real Usage   | grows a split file in a later goal           | red row text unspecified                | fixed (row messages with fix line)
5. Debug        | reads row output / goal wait text            | wait text lacks resume step             | fixed (wait/finding text)
6. Upgrade      | package users upgrade                        | none: names and CLIs unchanged          | ok
```

#### 0G. First-time developer report

```
Persona: worker agent on a later goal
T+0:00  grep -n "def save" skills/workflow-delivery/scripts/goal.py -> nothing; sees `from goalfile import`
T+0:20  opens goalfile.py; docstring names goal.py as origin -> edits save there
T+0:40  writes a test that sets goal.run = fake; moved git ignores it (confusion) -> docstring says patch goalfile.run
T+1:30  size-138 red: message names bytes, line, fix -> moves a block, reruns, green
T+2:00  done
```
All four confusion points are fixed in the accepted DX requirements below.

#### Dual voices

Native DX voice (Claude subagent): completed, INPUT dx bab1641e...7fdf matches the snapshot. Findings: Medium no
reverse pointer in old module; Medium `cutlog`/`docsparts` names; Medium monkeypatch hazard undocumented; Medium
import-back placement ambiguous; High CAP6 row failure text unspecified; High CAP6 negative-control message; High CAP6
`goal.py wait` recovery; High CAP6 `goal.py finding` context; Medium 17,408 not enforced by rows; Medium no
copy-paste verify block; Medium PR title; Medium no partial-PR escape; Medium primitive-drift text.

Codex DX voice: unavailable (usage limit, quota exhausted earlier this run; not re-invoked).

```
DX DUAL VOICES — CONSENSUS TABLE: [subagent-only]
  Dimension                           Claude  Codex  Consensus
  1. Getting started < 5 min?          yes     N/A    N/A
  2. API/CLI naming guessable?         mostly  N/A    N/A
  3. Error messages actionable?        no      N/A    N/A
  4. Docs findable & complete?         mostly  N/A    N/A
  5. Upgrade path safe?                yes     N/A    N/A
  6. Dev environment friction-free?    yes     N/A    N/A
Missing voice = N/A, never CONFIRMED. No single-voice critical (no CAP4).
```

#### Passes

**Pass 1 Getting started: 7 -> 8.** Find-and-edit path is short (grep + docstring). Gap: old module gave no pointer for
new helpers; fixed with a trailing comment on the import-back line. 10 would be a generated module map in the wiki;
out of scope (DX POLISH).

**Pass 2 API/CLI/SDK: 6 -> 8.** No CLI changes (goal.py, release.py, regression.py, criteria.py commands and flags are
untouched). Names: `cutlog` is unclear -> renamed `changelog.py` (holds bump, verify steps, subjects, changelog text,
restore; all feed the changelog entry) [taste: alternative `versionlog.py`]; docs.py fallback module gets a content name
chosen with its block (placeholder `docsparts.py` until then). Import-back placement simplified: directly after the
last top-level import (moved names are leaves, so nothing earlier can use them). Monkeypatch rule documented in each
new module's docstring; each size case greps dev/toy for `<old>.<moved name> =` assignments and fails if one exists.

**Pass 3 Errors: 5 -> 6 (capped).**

```
ERROR PATH MATRIX (agent-ready-v1)
Path                         | Class      | what | fix | recovery | code | context | trace | redaction | channel | Cap
size-N size check            | validation | pass | pass| N/A      | pass | N/A     | N/A   | pass      | pass    | -
size-N name parity           | validation | pass | pass| N/A      | pass | N/A     | N/A   | pass      | pass    | -
size-N leftover def          | validation | pass | pass| N/A      | pass | N/A     | N/A   | pass      | pass    | -
size-N primitive drift       | validation | pass | pass| N/A      | pass | N/A     | N/A   | pass      | pass    | -
size-N negative control      | unexpected | pass | pass| pass     | pass | pass    | N/A   | pass      | pass    | -
goal.py wait (blocker)       | partial    | pass | pass| pass     | N/A* | pass    | N/A   | pass      | pass    | -
goal.py finding (no block)   | partial    | pass | pass| pass     | N/A* | pass    | N/A   | pass      | pass    | -
missing sibling module       | unexpected | pass | fail| fail     | fail | pass    | pass  | pass      | pass    | CAP6:import:fix
```
(code: the row id `size-N` is the stable code and the design doc is the anchor; *wait/finding use goal.py's existing
record format.) After fixes all new paths pass except the pre-existing failure mode of a partially copied skill folder:
Python prints `ModuleNotFoundError: No module named 'goalfile'` with a traceback and no fix. Same as today's
goal.py -> guards.py import; setup copies whole folders. Corrected line would need a try/except around the import,
which breaks the pure-move rule [taste: keep pure move, residual CAP6].
Corrected row lines (accepted):
- `size-138: skills/workflow-delivery/scripts/goal.py is 18,950 bytes, at or over health's WARN_AT 18,432. fix: move another leaf block from goal.py into goalfile.py (rules: docs/designs/skill-size-2.md), then rerun bash dev/toy/test-defect.sh size-138`
- `size-138: goalfile.py defines base_ref but goal.py's import-back line lacks it. fix: add base_ref to the from goalfile import line in goal.py`
- `size-138: goal.py still defines save at line 110 after the move. fix: delete that def; goalfile.save is imported back`
- `size-142: copied primitive run differs between release.py and changelog.py. fix: keep both copies identical; update both`
- `size-138: negative control: dropping base_ref from the import-back line was NOT caught by check 2; the test is broken, not the split. fix: repair check 2 in dev/toy/test-defect.sh`

**Pass 4 Docs: 6 -> 8.** Usage sentences, docstrings, Closes scope sentence. Added: the goal file's `## Verify by hand`
gets numbered steps with `Expect:` lines (release.py `verify_steps` needs them; today the section is empty, so
`release.py ask` would show NONE YET and `cut` refuses), and the qa verification is one copy-paste command block.

**Pass 5 Upgrade: 8 -> 8.** Every public name still resolves on its old module; CLIs unchanged; the release step writes
the changelog. A downstream test that patched an old-module global for moved code would silently stop affecting it;
covered by the docstring and the grep check in this repo; outside repos are not known to patch these modules.

**Pass 6 Dev environment: 8 -> 8.** Each case runs alone (`bash dev/toy/test-defect.sh size-138`), stdlib only, no
network; lanes pick the rows through the reads header. No issues beyond Pass 3.

**Pass 7 Community: 5 -> 5.** Internal refactor; no community surface changes. No issues found: nothing in the plan
touches contribution docs, examples or channels.

**Pass 8 Measurement: 6 -> 7.** The size rows plus health's size group are the feedback loop; the 17,408 headroom is a
build-time target checked once in qa by `wc -c`, stated as such (rows enforce health's line only). TTHW is not
instrumented; not proposed (would be a new policy).

**Claude Code Skill checklist:** error recovery (wait/finding with resume text) covered; agent-readable errors covered
by the row lines above; state storage, consent, auto-upgrade, composition, session continuity, bounded autonomy
unchanged by this plan.

```
+====================================================================+
|              DX PLAN REVIEW — SCORECARD                             |
+====================================================================+
| Dimension            | Score  | Prior  | Trend  |
|----------------------|--------|--------|--------|
| Getting Started      |  8/10  |  7/10  |  ↑     |
| API/CLI/SDK          |  8/10  |  6/10  |  ↑     |
| Error Messages       |  6/10  |  5/10  |  ↑ (CAP6 residual) |
| Documentation        |  8/10  |  6/10  |  ↑     |
| Upgrade Path         |  8/10  |  8/10  |  =     |
| Dev Environment      |  8/10  |  8/10  |  =     |
| Community            |  5/10  |  5/10  |  =     |
| DX Measurement       |  7/10  |  6/10  |  ↑     |
+--------------------------------------------------------------------+
| TTHW                 | ~1.5 min | ~3 min | ↑ (estimated) |
| Competitive Rank     | Champion (estimated)                        |
| Magical Moment       | designed via row fix line                   |
| Product Type         | Claude Code Skill                           |
| Mode                 | POLISH                                      |
| Overall DX           |  7/10  |  6/10  |  ↑     |
+====================================================================+
| Zero Friction  covered | Learn by Doing covered | Fight Uncertainty covered |
| Opinionated + Escape Hatches covered (fallback blocks, finding) | Code in Context covered |
| Magical Moments covered | Agents Are Users covered (row lines, wait text) |
+====================================================================+
```
Prior column = this review's pre-fix scores (no earlier DX review of this plan).

```
DX IMPLEMENTATION CHECKLIST
[ ] A red size row's last line is the exact fix (file, bytes, name or line)
[ ] Each new module docstring: origin module, imported back, patch <new>.<name>
[ ] Import-back line directly after last top-level import, trailing comment points new helpers to the new module
[ ] No dev/toy test assigns <old>.<moved name>
[ ] goal.py wait / finding text lists split and unsplit files with bytes and the resume step
[ ] Goal file Verify by hand has numbered steps with Expect: lines
[ ] One copy-paste qa command block
[ ] Wiki Usage sentences name each new module
```

NOT in scope (DX): a generated module map page; a try/except around new imports (breaks pure move); TTHW telemetry;
partial-PR escape (CEO taste row 22). What already exists: test-defect.sh `no()` helper, goal.py wait/finding records,
guards.py docstring style, release.py verify_steps.

| 25 | DX | Product type Claude Code Skill, persona worker agent, target Champion, vehicle row fix line | Mechanical | P6 | unattended recommended | other personas |
| 26 | DX | Row failure lines with fix, negative-control line, primitive-drift line | Mechanical | P1 | agent-ready contract | unspecified text |
| 27 | DX | wait/finding text lists files, bytes, resume step | Mechanical | P1 | CAP6 recovery/context | bare wait |
| 28 | DX | Rename cutlog.py -> changelog.py | Taste | P5 | guessable; holds changelog-entry helpers | cutlog.py, versionlog.py |
| 29 | DX | Import-back directly after last import, with pointer comment | Mechanical | P5 | removes ambiguity | two-condition rule |
| 30 | DX | Docstring patch rule + grep for old.moved assignments | Mechanical | P2 | silent test no-op guard | none |
| 31 | DX | Verify by hand steps + copy-paste qa block | Mechanical | P1 | release cut needs steps | none |
| 32 | DX | Keep pure move; residual CAP6 for missing sibling module | Taste | P5 | matches existing guards import | try/except wrapper |
| 33 | DX | 17,408 is a qa-time target, rows enforce health's line | Mechanical | P5 | stated explicitly | row checks 17,408 |

<!-- plan review-accepted:dx -->
- Rename the release.py module from `cutlog.py` to `changelog.py` everywhere (accepted CEO requirements that name `cutlog.py` now mean `changelog.py`): Delivery wiki sentence, reads header, size-142 case, commit message.
- The import-back line sits directly after the old module's last top-level import (moved names are leaves) and carries a trailing comment pointing new leaf helpers to the new module, for example `from goalfile import (...)  # noqa: E402,F401  leaf helpers live in goalfile.py`.
- Each new module's docstring also says: to affect moved code in a test, patch `<new>.<name>`, not `<old>.<name>`. Each size case fails if any dev/toy file assigns `<old>.<moved name> =`.
- Each size case reports through test-defect.sh's existing `no()` helper (exit 1) with the file, the actual value and a last-line fix: size (`<script> is <bytes> bytes, at or over health's WARN_AT <n>. fix: move another leaf block from <old>.py into <new>.py (rules: docs/designs/skill-size-2.md), then rerun bash dev/toy/test-defect.sh size-<N>`), name parity (`<new>.py defines <name> but <old>.py's import-back line lacks it. fix: add <name> to the from <new> import line`), leftover def (`<old>.py still defines <name> at line <L>. fix: delete that def; <new>.<name> is imported back`), primitive drift (`copied primitive <p> differs between <old>.py and <new>.py. fix: keep both copies identical; update both`), and negative control (`negative control: <mutation> was NOT caught by check <k>; the test is broken, not the split. fix: repair check <k> in dev/toy/test-defect.sh`).
- `goal.py wait` for an unmerged blocker lists the split and unsplit files with their current bytes, names the blocking goal, says split files are complete and stay committed, and gives the resume step (after that goal merges, re-run the step; it merges main and re-derives only unsplit files). `goal.py finding` for "no leaf block fits" carries the file, its bytes after merge, the 17,408 target, each candidate block with its size and why it was rejected.
- The goal file's `## Verify by hand` gets numbered steps, each with an `Expect:` line: (1) `wc -c` on the four split scripts and docs.py, Expect: each split script at most 17,408 and docs.py under 18,432; (2) `python3 skills/workflow-health/scripts/health.py check`, Expect: no size WARN line for the five files; (3) `for n in 138 139 140 141 142; do bash dev/toy/test-defect.sh size-$n || echo FAIL $n; done`, Expect: no FAIL line; (4) `python3 skills/workflow-delivery/scripts/defect.py owed skill-size-2`, Expect: NONE OWED.
- The qa verification is written once as a single copy-paste command block (wc -c, health check, `regression.py run nightly`, each consumer test, defect owed), run as is by qa.
- 17,408 is a build-time headroom target checked once in qa by `wc -c`; the permanent rows enforce health's WARN_AT only.
<!-- plan review-accepted:dx -->

### Eng phase (Phase 3)

Methodology read: plan review-eng-methodology-rtbL7E/methodology.md ranges 1-600, 601-1200, 1201-1800, 1801-2143 (2143
of 2143 lines). Scope gate: plan review target = ACTIVE_PLAN (Implementation plan). Outside voice: Codex unavailable
(usage limit, quota exhausted in Phase 1; not re-invoked).

#### Step 0: Scope challenge

What already exists: health.size_rows (health.py:71-85), regression.py add/red (regression.py:114, 228), defect.py owed
(defect.py:40), goal.py pr gate (goal.py:360-362), guards.py module injection (guards.py `g.` calls: FLOW, SLUG,
MAX_TRIES, base_ref, config, done_sha, git, goal_file, load, no, read, root, run, save, state_dir, write; all still
resolve as goal attributes through the import-back), lanes.modules follows `from x import` (lanes.py:44-46),
test-defect.sh `no()` helper and case list (test-defect.sh:13-23), criteria.py render.

Minimum change: four move commits, one test file, five rows, goal-file sections, four wiki lines. Complexity: about 13
changed files (4 scripts, 4 new modules, test-defect.sh, regression.tsv, goal file, Setup/Delivery/Documentation/
Regression wiki pages counted as 4) and 4 new modules (no classes/services; plain function modules). The gate trips
(8+ files). Structure question (eng review-structure) auto-decided: Original arrangement (one module per split
file) kept; a single shared module across skills would break SET-3's per-skill self-containment and add cross-folder
imports. No feature cuts proposed (override: never reduce). Scope record: feature answers none; structure: A (original,
auto-decided); accepted scope: as CEO+DX accepted; pending remedies: none. Result: scope accepted as-is.

Search check: [Layer 1] move + re-export is the standard split; [Layer 2] patching the old module does not reach moved
code (WebSearch, Phase 1); [Layer 3] here the patch hazard is concrete (test-prd.sh:239-240). No TODOS.md exists.
Distribution: new modules ship inside the skill folders the package already copies whole; no new artifact or CI.

| Premise | Claim | Receipt | Verdict |
|---|---|---|---|
| E1 | role.py imports no goal | role.py:5-12 (stdlib only) | true |
| E2 | rowreaders block is a leaf | regression.py:132-168 (`done_lines`, `criteria_ids`, `criterion_rows` use `path_of`, re, json, glob, os) | true |
| E3 | SHEET resolves from pagerules.py | criteria.py:45 on main (`os.path.dirname(os.path.abspath(__file__))`) | true |
| E4 | only release.py is loaded by path | test-release.sh:86; grep `spec_from_file_location` | true |
| E5 | red has no green baseline | regression.py:228-251 | true: ordering matters |
| E6 | guards reads goal attributes via `g.` | guards.py (16 attribute names) | true: import-back keeps them |
| E7 | goal.py lands near 17,100 after the block | 19,415 - 2,534 + ~230 import line [estimated] | about 300 bytes under target |

unverified=0

REALITY: premise-table pass 7 claims, unverified=0 skills/workflow-regression/scripts/regression.py:228
REALITY: already-done pass no split on origin/main since 2026-11-09; main moved to eb43798 (toy-cleanup) without touching the five files skills/workflow-delivery/scripts/goal.py:1
REALITY: surface-check pass `regression.py red ID --break CMD`, `run nightly`, `defect.py owed SLUG`, `goal.py wait/finding`, `criteria.py render --check` all exist skills/workflow-regression/scripts/regression.py:13
REALITY: binding-decisions pass no branch decisions logged; frozen done lines and owner-approved issue mapping respected .loop/goals/skill-size-2.md:16
REALITY: numbers finding goal.py headroom after the named block is about 300 bytes [estimated]; post-merge sizes [re-measure before gate] skills/workflow-delivery/scripts/goal.py:1
REALITY: deferred-asks pass issues 138-142 ask only for the split; nothing left out .loop/goals/skill-size-2.md:16
REALITY: pr-count pass one PR (no ship-policy) docs/designs/skill-size-2.md:58

#### Dual voices

Native eng voice (Claude subagent): completed, INPUT eng a4b919b0...eea6 matches the snapshot. Findings: High red can
record a false red if rows are committed before the split; Medium goal.py headroom about 300 bytes; Medium cutlog vs
changelog wording; Medium check (3) grep too narrow; Medium cases import real scripts in-process; Low-Medium module
basenames must be unique across skills; Low goalfile lacks goal.py's env guard for direct importers; Low release block
is several hunks; Low no automated merged-base check; Info temp-root cleanup.

Codex eng voice: unavailable (usage limit; not re-invoked).

```
ENG DUAL VOICES — CONSENSUS TABLE: [subagent-only]
  Dimension                           Claude  Codex  Consensus
  1. Architecture sound?               yes     N/A    N/A
  2. Test coverage sufficient?         after fixes N/A N/A
  3. Perf risks + budget/bench named?  n/a(no hot path) N/A N/A
  4. Security threats covered?         yes     N/A    N/A
  5. Error paths handled?              yes     N/A    N/A
  6. Deployment risk manageable?       yes     N/A    N/A
Missing voice = N/A, never CONFIRMED. Single-voice High: red ordering (accepted fix).
```

#### Section 1: Architecture

```
  BEFORE                                   AFTER
  goal.py ──> defect, guards, role         goal.py ──> goalfile.py ──> role.py
     ▲ guards.g (sys.modules)                 │  └──> defect, guards, role
  criteria.py ──(lazy)──> pageformat          ▲ guards.g -> goal.<name> (import-back attrs)
     ▲ render.py, docs.py, prd.py, audit,   criteria.py ──> pagerules.py ──(lazy)──> pageformat
       counting import criteria                ▲ render.py, docs.py, prd.py, audit, counting (unchanged)
  regression.py ──> actions, lanes(, slots, runs) regression.py ──> rowreaders.py (+ actions, lanes, ...)
  release.py (no siblings)                 release.py ──> changelog.py ; sys.path.insert(own folder)
     ▲ merge.py, wiki.py, autorelease.py      ▲ merge.py, wiki.py, autorelease.py (unchanged)
```
Design twice: shape A (chosen) per-file leaf module, old module re-exports; shape B the guards.py style (move
non-leaf commands into a module taking the old module as `g`, e.g. `goalpr.cmd_pr(g, args)`). B frees more bytes
(cmd_pr 3.5 KB) but rewrites every call inside (`save(` -> `g.save(`), so it is not a pure move. A hides a leaf block
behind the same names; depth argument: the interface does not grow at all. Red flags: (2) information leakage: none;
(4) pass-through: the import-back is a re-export, not a forwarding function; (5) split ownership: none (no state);
(6) two ways to do one task: copied run/git/path_of are two copies, guarded by the drift check; (7) importable
internals: goalfile.py importable directly without goal.py's no-prompt env setup -> docstring note (accepted below);
(8) hand-synced list: the import-back names vs the new module's names, guarded by the ast parity check. Production
failure per new path: a partial skill install misses the new module -> ModuleNotFoundError at start (same as today's
guards import; setup copies whole folders). Findings: 1 (importable internals), accepted.

#### Section 2: Code quality

[INFORMATIONAL] (confidence: 8/10) plan, check (3) — grep for `^def name` / `^NAME =` misses annotated, tuple, nested
or lowercase assignments; quoted motivating line: "(3) greps the old file for no `^def <name>\b` and no `^<NAME> =`".
Accepted: run an `ast` walk of the old module's top-level (including `if` blocks) and require no overlap with the
moved names. [INFORMATIONAL] (confidence: 7/10) plan cutlog/changelog lines — accepted: `changelog.py` is the only
name (DX rename); every earlier `cutlog.py` mention means `changelog.py`. [INFORMATIONAL] (confidence: 7/10) release.py
block spans release.py:187-205 and 267-297 (doc_rows/docs_trouble/criteria_trouble/wiki_link/base_of/docs_lines sit
between) — accepted: the move commit has several moved hunks; review with `--color-moved=zebra`. Shared code: the
copied primitives stay copies (repo convention, SET-3); no extraction. Stale diagrams: none in touched files.
Dispositions: 3 accepted.

#### Section 3: Tests

Framework: bash toy tests under dev/toy (no CLAUDE.md testing section; `regression.py` rows call them).

```
CODE PATHS                                              USER FLOWS (worker agent)
[+] goal.py -> goalfile.py                              [+] Later goal grows a split file
  ├── import-back names       [GAP->size-138 (2)]          ├── [GAP->size-N (1)] red row with fix line
  ├── leftover defs           [GAP->size-138 (3) ast]      └── [GAP->negative control] checks themselves
  ├── behaviour of commands   [★★★ test-goal, test-guards]
[+] criteria.py -> pagerules.py                         [+] Package install
  ├── rules()/criteria_max    [★★★ test-criteria, docs-command] └── [★★ test-adopt copies skills whole]
  └── import-back             [GAP->size-139]
[+] regression.py -> rowreaders.py                      [+] Release by path
  ├── criteria_ids            [★★ test-prd:242]            └── [★★★ test-release 3d importlib]
  ├── path_of copy identical  [GAP->size-141 (4)]
[+] release.py -> changelog.py
  ├── bump/changelog_text     [★★★ test-release 3d]
  ├── criteria_trouble patch  [★★ test-prd:239-243 (stays in release.py)]
  └── sys.path.insert         [★★ test-release 3d]
[+] docs.py (no split)        [GAP->size-140 size only]
[+] red proof ordering        [GAP->procedure: split, case+row, green, red]
COVERAGE after plan: all paths have a planned or existing test; gaps above are filled by the size cases.
```
Regression rule: existing behaviour at risk is covered by the consumer suites run in full (accepted CEO requirement);
no new behaviour contract. Value cards: in the test plan artifact. Test plan artifact:
<local path>
Findings accepted: red ordering with green-before-red (High, confidence 9/10, regression.py:228-251 "if done.returncode
== 0: print STILL GREEN"); per-case `python3 -B` subprocess for the import checks (Medium, 7/10, goal.py:35-37 env and
dup2 side effects); basename uniqueness across skills (Low, 7/10, test-prd.sh:229-231 four folders on one sys.path);
temp roots cleaned with `trap` (Info).

#### Section 4: Performance

No hot path: the moves add one module import per script start (milliseconds); five land rows each copy two files and
run health's size rule (well under a second). No queries, caches or loops over large data. No issues found.

#### Failure modes

```
  CODEPATH                 | FAILURE                           | TEST?            | ERROR HANDLING      | SILENT?
  import-back line         | name dropped                      | size-N (2)+neg   | row FAIL with fix   | no
  old module               | stale def shadows import          | size-N (3) ast   | row FAIL with fix   | no
  release.py path load     | changelog not found               | test-release 3d  | traceback, exit 1   | no
  copied primitive         | drift                             | size-N (4)       | row FAIL with fix   | no
  red proof                | false red (module missing)        | procedure order  | green-before-red    | no
  direct import goalfile   | git prompt hangs (no env guard)   | n/a (no caller)  | docstring warning   | no (documented)
  partial skill install    | ModuleNotFoundError               | n/a              | traceback           | no
```
0 critical gaps.

Worktree parallelization: Sequential implementation, no parallelization opportunity (each split waits on its own
blocking goal's merge; the shared test file and regression.tsv serialize the rest).

NOT in scope (all phases): split role.py and the four workflow-monitoring scripts (outside issue mapping); remove
render.py's back-import (docs-format owns it); lower health's warn line; health auto-split helper; revisit SET-3's
per-file measure; generated module map page; try/except around new imports; TTHW telemetry; per-blocker partial PRs;
one parametrized size row. TODOS.md: none exists in this repo; these deferrals are reported in the goal report instead
of auto-creating a TODOS.md (repo convention: health files issues, the operation session queues goals).

| 34 | Eng | Structure: keep one module per split file | Mechanical | P5 | SET-3 per-skill self-containment | shared cross-skill module |
| 35 | Eng | Split commit, then case+row commit, green run, then red | Mechanical | P1 | red has no green baseline | rows first |
| 36 | Eng | Check (3) via ast on the old module | Mechanical | P5 | grep misses forms | grep |
| 37 | Eng | Import checks in a separate python3 -B process per case; trap cleanup | Mechanical | P5 | goal.py import side effects | in-process |
| 38 | Eng | Basename uniqueness across skills in each case | Mechanical | P2 | shared sys.path in tests | none |
| 39 | Eng | goalfile.py docstring: import via goal.py only (env guard lives there) | Mechanical | P5 | importable internals flag | move env guard |
| 40 | Eng | `git merge-base --is-ancestor <blocker merge sha> HEAD` before each split | Mechanical | P1 | enforces merged-base rule | trust only |
| 41 | Eng | changelog.py the only name; release move is several hunks | Mechanical | P5 | removes ambiguity | none |
| 42 | Eng | No TODOS.md auto-create; deferrals in goal report | Taste | P5 | repo has no TODOS.md; issues/goals are the backlog | create TODOS.md |

<!-- plan review-accepted:eng -->
- Per file, commit order is: the pure-move split commit; then the case and its row (with reads header and `cases=` entry); then run `bash dev/toy/test-defect.sh size-<N>` with no break and require it to pass; only then `regression.py red size-<N> --break "<pad script past WARN_AT>"`. With the module present, padding a comment can only trip check (1), so the recorded red is the size failure.
- Before each split commit, check `git merge-base --is-ancestor <blocking goal's merge commit on main> HEAD`; if it fails, do not split (the `goal.py wait` rule applies).
- Check (3) is an `ast` walk of the old module's top level (including statements inside top-level `if`/`try` blocks) collecting every def, class, assignment, annotated assignment and tuple target name; it fails if any is a moved name. It replaces the grep.
- Checks (2), (3) and (4) run in a separate `python3 -B` process per case with the skill's scripts folder put on sys.path explicitly, so goal.py's import-time environment and stdin changes never touch the test-defect.sh process; each case cleans its temp root with a `trap`.
- Each case fails if its new module's basename exists in any other `skills/*/scripts/` folder.
- goalfile.py's docstring says to import it through goal.py, which sets the no-prompt environment for git and gh before importing it.
- `changelog.py` is the only module name for the release.py split; every `cutlog.py` mention in the plan means `changelog.py`. The release.py move commit has several moved hunks (the block is not contiguous); reviewers use `git diff --color-moved=zebra`.
- The re-derive step after each merge picks the smallest leaf block that brings the file to at most 17,408 bytes; for goal.py the named block leaves about 300 bytes of margin (estimated), so the fallback block is expected if lane-control or delivery-prd adds code.
- Deferred work is listed in the goal report; no TODOS.md is created (the repo has none; health issues and queued goals are its backlog).
<!-- plan review-accepted:eng -->

#### Implementation Tasks (Eng)

- [ ] **T1 (P1, human: ~1h / CC: ~5min)** — process — commit order split -> case+row -> green -> red; merge-base check
  - Surfaced by: Section 3 (regression.py:228-251)
  - Files: .loop/regression.tsv, dev/toy/test-defect.sh
  - Verify: `bash dev/toy/test-defect.sh size-<N>` passes before red; red prints SEEN RED
- [ ] **T2 (P1, human: ~2h / CC: ~15min)** — dev/toy — ast-based checks (2) and (3), python3 -B subprocess, trap, basename uniqueness
  - Surfaced by: Sections 2-3
  - Files: dev/toy/test-defect.sh
  - Verify: negative control fails when a name is dropped or a def kept
- [ ] **T3 (P2, human: ~15min / CC: ~2min)** — workflow-delivery — goalfile.py docstring import note
  - Surfaced by: Section 1 red flag 7
  - Files: skills/workflow-delivery/scripts/goalfile.py
  - Verify: read the docstring
_No new tasks from Performance._

PLAN_REALITY: phase=eng rows=7/7 missing=none unverified=0 verdict=complete

Eng completion summary:
- Step 0: Scope Challenge — scope accepted as-is (structure auto-decided: original arrangement)
- Reality rows: 7/7 applicable rows emitted (PLAN_REALITY complete), 0 unverified premises
- Architecture Review: 1 issue found (importable internals; docstring)
- Code Quality Review: 3 issues found (check (3) form, module name wording, multi-hunk move)
- Test Review: diagram produced, 4 gaps identified (red ordering, subprocess isolation, basename uniqueness, cleanup), all accepted
- Performance Review: 0 issues found
- NOT in scope: written; What already exists: written
- TODOS.md updates: 0 written (no TODOS.md in repo; 10 deferrals listed in NOT in scope)
- Failure modes: 0 critical gaps flagged
- Unresolved decisions: 0
- Outside voice: codex unavailable (usage limit)
- Parallelization: 1 lane, 0 parallel / 1 sequential
- Lake Score: N/A (no scored questions asked; unattended auto-decisions)
