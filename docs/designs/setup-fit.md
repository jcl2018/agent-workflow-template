# Design: Fix the Setup gaps found by adopting three real repos

Branch: loop/setup-fit
Status: DRAFT (unattended run; recommended answers taken, nothing approved)
Mode: Builder

## Problem
Adopting three real repos exposed six gaps in workflow-setup / workflow-docs / the package scan. The goal file's six done lines are frozen; this design meets them as written.

## Premises (taken as agreed)
1. The fixes belong in the existing scripts (`survey.py`, `setup.py`, `seed.py`, `docs.py`, `dev/package.py`), each staying under the 20 KB script cap (setup.py 7.6 KB, docs.py 13.8 KB, package.py 12.9 KB; docs.py has the least headroom).
2. Setup stays read-only until it writes its branch; every new rule prints in the dry run first.
3. Nothing is guessed silently: what setup cannot determine it reports with the exact line to add.

## Approach (recommended: B)
- A. Patch each gap inline in the current functions. Smallest diff, but `setup.py` and `docs.py` grow toward the cap.
- B (recommended). Put detection in `survey.py` (CI/script test commands, feature list, version/changelog habit, gitignore conflicts) and keep `setup.py`/`seed.py` as consumers. Docs check reads the feature list from `.loop/docs.tsv`. Small new module only if a script nears 20 KB.
- C. A model-driven survey. Rejected: setup must be deterministic and call no model.

## Design by done line
1. **Real test commands.** `survey_checks` reads `.github/workflows/*.yml` `run:` lines and `scripts/` / `Makefile` / `package.json` test targets; keeps lines that look like test runs. A candidate is dropped (and reported) if a dry probe shows it collects zero tests (e.g. `pytest` exit 5, an empty glob, `npm test` placeholder `no test specified`). Never writes a check that runs zero tests; with none found, checks stay empty and the dry run says so.
2. **Bare agent_command.** When `agent_command` has no allow-tools flag, setup prints a REFUSED-to-finish line (non-zero exit after writing the branch, or a hard `REFUSED` for the run) with the exact line to add, e.g. `--allowedTools=Bash,Read,Write,Edit` for claude, `-s workspace-write` plus `writable_roots` for codex. Setup never edits the command itself (existing rule: the user chooses).
3. **Feature pages.** Replace "every top-level code folder" with feature sources in order: milestones (ROADMAP/milestone headings), tracks, then folders holding code at a meaningful depth. Pages are written to `.loop/docs.tsv`; the docs check (`docs.py` PREFIXES/"not allowed" rule) accepts any page listed in docs.tsv rather than a fixed set, with `Home` still implicit.
4. **Version/changelog habit and .gitignore.** Detect VERSION file vs tag vs package manifest, and the CHANGELOG heading style; record it in config so release follows it. Run `git check-ignore` over every path setup would write; for each blocked one print the exact `!path` exception to add (report only, not auto-edit).
5. **Package leak scan.** `dev/package.py` reads a list of private prefixes from a private file under `~/.workflow-loop/` (same place as the other private settings, mode 0600, never committed) and fails the package on any match, in addition to the built-in SECRETS patterns. Missing file = a named notice, not a silent pass.
6. **Toy test.** New `dev/toy/test-setup-fit.sh` builds a fake repo (CI workflow with tests, a bare `claude -p`, a milestone list, a `.gitignore` blocking `.loop/`) and asserts each of lines 1-5; no model is called. Follows `test-adopt.sh` style (`no()` failures, PASS lines).

## Decisions taken (recommended answers)
- Detection lives in `survey.py`; setup consumes it.
- Zero-test probe is advisory-by-removal: drop the check and report why.
- .gitignore conflicts are reported with the exception line, never auto-edited.
- Leak prefixes live in a new key in the existing private settings file, not in the repo.

## Open for owner
- Exact private-setting name and file for leak prefixes, since the local leak hook's own file was not found on this machine and its format could not be read.
- Whether a missing `agent_command` allow-list should fail the run (exit 1) or finish with a loud warning; recommended is fail after writing the branch.

## Reuse
`seed.decide`, `settings.py` private-setting writer, `test-adopt.sh` scaffolding, `dev/toy/make.sh`.
