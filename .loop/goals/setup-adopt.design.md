# Design: setup-adopt

Status: shaped by office-hours with the recommended answer at every question. Nothing approved, merged or pushed.
The goal's done lines are frozen; this design meets them. Delivery fills in the done lines' met marks and Verify by hand.

## Problem

`workflow-setup` writes only `config.json`, an empty queue and an empty findings file (`setup.py`, 6.8 KB). A repo that
adopts the loop still has to hand-make feature pages, criteria, tests, milestones, the regression workflow and health
rules. And once installed, there is no way to see or take a newer package version without overwriting repo data.

## Premises (taken as agreed)

1. Adopt means adapt: existing files are read and extended, never overwritten. Anything not marked
   `<!-- workflow-docs -->` or already in `.loop/` is left alone.
2. Installed skills and repo data are separate trees (`loop-files.md`). Update touches the skills tree only.
3. Scripts must stay under 20 KB each (largest today: `regression.py` 20.1 KB, `release.py` 20.4 KB, already near or
   over the cap, so new logic goes in new small modules).
4. Reuse over invention: `docs.py`, `criteria.py`, `milestone.py`, `regression.py`, `health.py` already own their file
   formats. Setup calls them; it does not re-implement them.
5. Setup stays dry-run first, writes only on branch `workflow-setup`, never merges.

## Approach (recommended, taken): survey module + per-area seeders, one `adopt` entry

1. **Survey** (line 1): new `skills/workflow-setup/scripts/survey.py` returns a plain structure: base branch, checks,
   agent, existing docs (README, `docs/`, wiki), test files and runner, tags/versions for milestones, CI config. It also
   classifies a repo as `new` (no commits of substance) or `existing`.
2. **Plan report** (line 1): `setup.py --dry-run` prints what survey found and a list of `add:` / `convert:` lines, one
   per file, before any write. `convert` means an existing file is adapted (a marker line added, a table appended),
   `add` means a new file.
3. **Seeders** (line 1), each a small module under `skills/workflow-setup/scripts/`:
   - `seed_docs.py`: one feature page per top-level area in `docs/wiki/`, each with criteria lines and a Tests table
     generated through `criteria.py render`; existing pages get the marker and a criteria section appended.
   - `seed_regression.py`: `.loop/regression.tsv` rows from the detected test runner, so the regression workflow runs.
   - `seed_milestones.py`: milestones from tags or `VERSION`, via `milestone.py`'s format.
   - `seed_health.py`: health rules config keys in `.loop/config.json` (script size 20 KB, stale windows).
   Re-running changes nothing (idempotent), as today.
4. **Package** (line 2): `dev/package.py` already builds the zip; it gains a stamped `VERSION` and `PACKAGE.json`
   (version plus per-skill file hash list), a check that every `skills/*` is included, and a size check on every script.
   Install is "copy `skills/` into any SKILL.md agent folder"; `dev/install-local.sh` is the reference.
5. **Update** (line 3): `skills/workflow-setup/scripts/update.py`. Compares the installed `PACKAGE.json` to a newer
   package (path or release URL, owner-supplied), prints old to new version and the CHANGELOG entries between them and
   the changed skill files, and with confirmation replaces only the skills tree. It never reads or writes `.loop/`,
   `docs/`, or private settings (e.g. `.claude/settings.local.json`); a test asserts those hashes are unchanged.
6. **Design guide** (line 4): `docs/design-guide.md`, shipped in the package: how the loop (delivery), operation and
   workers (monitoring), criteria and tests (docs, regression), and health (health, release) fit; one diagram of the
   data flow through `.loop/` files. Linked from README.
7. **Test** (line 5): `dev/toy/test-adopt.sh` in the toy style: make a fresh toy repo (`make.sh`), run setup, assert the
   branch and files, run setup again (no diff), install package v-old, run update to v-new, assert skills changed and
   repo data hashes did not; then the repo checks pass.
8. Bump `VERSION` and `listing.json` (commands add `adopt` if the verb name changes, `update`); update
   `skills/loop-files.md` with any new files and config keys.

## Alternatives considered

- **A. Extend `setup.py` only** (S, low risk): fast, but pushes it past 20 KB and mixes survey, seeding and update.
- **B. Recommended**: modules per area (M, med risk).
- **C. A new `workflow-adopt` skill** (L): cleaner naming, but an eighth skill, a larger catalog and package change,
  and the goal's Touches names `workflow-setup`.

## Risks

- Converting existing docs can mangle prose: convert only appends or inserts marker lines, never rewrites text.
- Update replacing skills mid-run of a worker: refuse when `.loop/runs` shows a live worker.
- Package hash list drifts from the tree: the build recomputes it, and the toy test checks it.

## Not in scope

Auto-merge of the adopt branch, remote update channels or auto-update, migrating non-SKILL.md agent formats beyond copy.

## Open decisions for the owner

- Name of the update verb and where the newer package comes from (default: `update --from <path-or-url>`).
- Whether `workflow-setup` keeps both commands or `update` becomes its own skill (default: same skill).
