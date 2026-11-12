# Plan: render-readme-guard

Goal: `.loop/goals/render-readme-guard.md` (done lines frozen). Design: the idea step's reply (approach A). Status: reviewed (CEO + Eng, one outside voice), amendments folded in and marked (review); stopped at the final gate, nothing approved.

## Implementation plan

### What is wrong (v0.27.21, 304ba8de)

- `render.refresh()` writes the template, Settings and Automation blocks. Its `with_blocks()` replaces a block where its markers are and otherwise appends it. Every caller inserts: `render.render()` (`criteria.py render`, run by lane prep), `docs.py publish`, and `docs.py check` through `stale_blocks()`, which calls a missing block STALE and says to run render. A repo adopted before v0.27.17 (steward) has no markers, so a lane render appended them after the README's last section and the lane commit touched README.md.
- Steward maps every page to README.md. `docs.py problems()` counts every commit on a mapped path since the page's last commit, so that one generated-block commit made every page STALE.
- `render.render()` reads the feature pages and builds their Tests rewrite before it calls `refresh()`, then writes the rewrite. On a Home that is a feature page (the adopt toy's converted Home) the Tests write overwrites what refresh wrote, so right after setup `docs.py check` says `STALE Settings: docs/wiki/Home.md`, and the next render inserts again. A PRD-format Home cannot hold a `## Settings` section anyway: its section list is fixed.
- adopt-set-1..5 on main no longer fail on "setup left the tree dirty" (that part passes). They fail at `v1 package refused` (`dev/package.py`: 118 files over the cap, `automation` missing from listing.commands), which package-cap-3 fixes. The v1 package is used only by SET-3, SET-4 and SET-5, but is built for every part.

### Step 1: render.py — insert only on request, refresh first

- `with_blocks(text, blocks, insert=False)`: replace each block where its markers are; only with `insert` put a missing block in place (template after the first paragraph, the others appended).
- `refresh(root, check=False, insert=False)`: a block with no markers is neither written nor reported unless `insert`. `front_files(root)` offers Home only when it is the DOC-4 features page (a `## Features` line); a PRD-format Home is never given blocks, even one that holds markers from v0.27.17-21 (P4; review).
- `stale_blocks(root)` keeps calling `refresh(root, True)`: only an existing block that differs is STALE ("differs from a fresh render"); a missing one is a repo not yet migrated and says nothing. SKILL.md's STALE row says setup (`render.py blocks`) inserts a missing block (review).
- Size (review): render.py was already 19709 bytes on main (96%, health's warn band); the change keeps it under the 20480 hard limit and SET-3's 20 KB check by putting the staleness helper elsewhere and keeping docstrings short. A split of render.py is a follow-up.
- `render()` calls `refresh(root, args.check)` (insert off) before it reads the pages, so a Tests rewrite starts from the refreshed text.
- A small CLI at the bottom: `render.py blocks` runs `refresh(root, insert=True)` when the config has `"criteria": true`, printing `WROTE <file> (<name> block)` per insert, else `BLOCKS OK`. That is the one inserting entry point, for setup. No change to criteria.py (package-cap-3's lane, outside touches).

### Step 2: counting.py + docs.py — publish never inserts; block-only commits don't stale pages

- `cmd_publish`: `render.refresh(root)` stays insert off (the default), so publish refreshes but never inserts.
- `counting.real(root, changed, paths)` (review: not in render.py, which is at its size limit; counting.py already holds docs.py's page map): one `git log --no-walk --name-only` call lists every changed commit's files (split on newlines, so paths with spaces hold); a commit that touched only README.md / Home.md files, each identical before and after once the three blocks are removed and runs of blank lines collapsed (so setup's own insert is neutral too), is dropped. New, deleted and renamed files, and root commits, stay real changes.
- `problems()`: the existing `changed = git("log", ...)` line is wrapped in `counting.real(...)`: no new line. docs.py was already 18702 bytes on main (91%, size-140 is a KNOWN row owned by regression-green-2); this adds 81 bytes (review: the plan's "stays under 90%" premise was wrong).

### Step 2b: pageformat.py — the template line is blanked too (review)

- `unblocked()` blanks the template block as well. Setup can write a README that opens with `## How to use` (an empty README); the template line, inserted after the first paragraph, then sits inside How to use, and DOC-5 counted its lines as extra intro lines.

### Step 3: seed.py — setup inserts, so the adoption commit carries the blocks

- In `apply()`, right before `tool(repo, "workflow-docs", "criteria.py", "render")`, call `tool(repo, "workflow-docs", "render.py", "blocks")`. setup.py commits what `tx.changed()` lists, and README.md is already committed by setup today (verified in a toy run: README.md is in the adoption commit), so no setup.py change.

### Step 4: dev/toy/test-adopt.sh — build the package only for the parts that use it

- Wrap `mk "$d/v1" ...; $pk ... || no "v1 package refused"` in `if want SET-3 || want SET-4 || want SET-5; then ... fi`. With no ID every part still runs it.
- adopt-set-1 and adopt-set-2 then pass on main; remove their two `.loop/regression-known.tsv` entries. adopt-set-3..5 pass once package-cap-3 merges; their entries are handled as the operation session decides (re-pointed to package-cap-3, or this PR merges main after package-cap-3 and removes them).

### Step 4b: dev/toy/test-settings-table.sh (review, critical)

- It adopts with `--bare` (no markers) and expected the first render to insert the blocks; it now runs `render.py blocks` first, as setup does.

### Step 5: tests — dev/toy/test-docs-blocks.sh, one check per done line

A criteria-on toy (make.sh, `"criteria": true`, one feature page mapped to README.md, a DOC-4 Home with `## Features`, a README with `## How to use`), no block markers:

1. `criteria.py render` leaves README.md and Home.md byte-identical (`cmp` against copies), and `docs.py check` prints no `STALE Settings`/`STALE Automation`/`STALE README line`. (done 1)
2. Setup (criteria on) inserts the blocks into README and the DOC-4 Home and leaves the tree clean (done 4); `docs.py check` prints no `FORMAT README`/`FORMAT Home` line, and a README that opens with How to use passes DOC-5 with the blocks in (done 2; review).
3. Commit that; change a setting value in `.loop/config.json` and commit it alone; `criteria.py render` refreshes the README block; commit only README.md/Home.md; `docs.py check` prints no `STALE <feature>` line, while a hand edit to README outside the blocks, committed, does make the page STALE (the negative control). (done 3)

Rows in `.loop/regression.tsv`, each guarding its done line (`render-readme-guard:N`) so they list in the Documentation Tests table: `blocks-no-insert` (1), `blocks-format` (2), `blocks-no-cascade` (3), `blocks-setup-clean` (4, independent of the package rules; review); plus adopt-set-1..5 as they are (4, 5). Breaks: revert 2a7c0fdb (no-insert), revert 7f2180df (format), revert 09078873 (no-cascade), drop seed.py's `render.py blocks` line (setup-clean), revert 99c97191 (adopt-set-1/2). Done 7 is checked by `git diff --diff-filter=A origin/main -- skills/` in qa (no row: a merged branch can't add a file again). Each row is proven red with `regression.py red <row> --break "<revert of its fix>"`, then the Documentation page's Tests table and docs/wiki/Tests.md are re-rendered (done 6). No file is added under skills/ (done 7).

### Step 6: docs

- `docs/wiki/Documentation.md` Usage: one sentence that a render refreshes the Settings and Automation blocks only where their markers already are, and setup (or `render.py blocks`) inserts them. Requirement lines unchanged unless the review asks for a new DOC line for the three rows; if it does, it is added Unreviewed.

### NOT in scope

- The package rules (file cap, listing.commands): package-cap-3.
- criteria.py, setup.py, lanekit.py: unchanged.
- Migrating steward itself: its owner re-runs setup, which now inserts the blocks once and commits them.

## Review record

- CEO + Eng review in session, plus one independent Claude adversarial reviewer (read-only, code-grounded). Codex not run. Design skipped (no UI). DX skipped (no developer-facing change: one internal CLI verb used by setup).
- Accepted (all applied): test-settings-table.sh runs `render.py blocks` (critical); helper out of render.py, render.py under the hard limit; docs.py change folded into its existing line; template line blanked in `unblocked()` with a title-less README case; Home gated on `## Features` only; one-call file listing split on newlines; blank-line collapse so an insert commit is neutral; STALE message and SKILL.md row corrected; a done-4 row independent of the package.
- Not taken: CRLF preservation in render.put (pre-existing since v0.27.17, outside this goal); markers inside fenced code (no page puts them there; low).
- Open: adopt-set-3..5 pass only once package-cap-3 merges; asked the operation session whether to re-point their KNOWN entries to package-cap-3 or wait and merge main.

<!-- autoplan-accepted:ceo -->
- adopt-set-1/2 pass on this branch and their KNOWN entries go; adopt-set-3..5 follow the operation session's answer.
- Done 4 has a row independent of the package rules (blocks-setup-clean).
<!-- /autoplan-accepted:ceo -->
<!-- autoplan-accepted:eng -->
- test-settings-table.sh inserts with render.py blocks before its first render, and passes.
- render.py stays under 20480 bytes; docs.py adds no line.
- A README that opens with How to use passes DOC-5 with the blocks in (tested).
- A setup insert commit and a refresh commit both leave README-mapped pages fresh; a real README edit stales them (tested).
<!-- /autoplan-accepted:eng -->
