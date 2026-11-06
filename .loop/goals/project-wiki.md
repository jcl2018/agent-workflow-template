# Write the project wiki and bring the roadmap up to date

- Slug: project-wiki
- Level: standard
- Touches: docs/wiki, .loop/docs.tsv, README.md, docs/ROADMAP.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs/wiki has pages Home, Getting-started, Delivery, Monitoring, Documentation, Regression, Release and Files, each mapped in .loop/docs.tsv to the skill or files it describes
2. Home lists every feature with a link to its page and says what is proven and what is not, using only claims found in FINDINGS.md, DECISIONS.md, or the dev tests
3. Each feature page gives its real commands and flags, matching the feature's SKILL.md and script help, with one real example
4. Getting-started takes a new user from install to one finished goal, using dev/install-local.sh and the setup, go and watch commands
5. docs/ROADMAP.md marks the first and second batches as built, lists what is left, and no longer names commands that were removed
6. README.md links to the wiki and the release page and copies no page content beyond its command summary
7. Every page starts with the workflow-docs marker, and the private name scan finds nothing in docs or README
8. The repo checks pass

## Verify by hand

1. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: it prints `DOCS OK: 8 pages`.
2. Open `docs/wiki/Home.md` and follow each feature link.
   Expect: eight pages exist, each starting with `<!-- workflow-docs -->`.
3. Run `grep -n "start" docs/ROADMAP.md | grep '`start'`.
   Expect: no output; the removed `start` command is gone.

## Design

Eight pages in docs/wiki, each starting with `<!-- workflow-docs -->`. Every command and flag is copied from the
SKILL.md files and each script's `--help`. Proof claims come only from README, FINDINGS.md, DECISIONS.md and the
dev/toy tests. Risk: a page going stale or naming a removed command (`start`). Mitigation: `docs.py check` and a grep
for removed names. No personal names or accounts go in docs or README; I scan for them by grep.

## Plan

1. Write the eight pages and `.loop/docs.tsv` via `docs.py add` (done lines 1-4, 7).
2. Rewrite docs/ROADMAP.md: batches built, what is left, drop `start` (done line 5).
3. Add wiki and release links to README.md (done line 6).
4. Grep docs and README for personal names; run `docs.py check` and `goal.py check` (done lines 7-8).

## Evidence

- The private name scan (a case-insensitive grep of docs, README.md and .loop/docs.tsv for the owner's names and accounts) prints nothing.
- `docs.py check` prints `DOCS OK: 8 pages`; all 8 pages start with `<!-- workflow-docs -->`.
- The first `goal.py check` runs failed only in toy tests that read the agent's `LOOP_BATCH=1` environment variable
  (a batch goal refuses `cut` without `--user`). With `LOOP_BATCH` unset, the same checks pass, and no repo file differs.
- Home's proof claims now cite only FINDINGS.md, DECISIONS.md and the dev tests (no README or ROADMAP source).
- Flag cross-check: every `--flag` named in docs/wiki appears in the skill scripts, except `--allowed`, which is the
  prefix of `--allowedTools` in prose:
  `grep -rhoE '\-\-[a-z-]+' docs/wiki/*.md | sort -u` against `grep -ohE '"--[a-z-]+"' skills/*/scripts/*.py | sort -u`.
- `.loop/findings.md` restored to main's version so the PR carries no stray change.
