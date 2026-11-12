# One command checks that a repo is fully migrated to the current template: every file setup writes is present and current, every setting is known, the Settings table and template link are on Home and README, the repo has its one local "<repo>-health-regression" task every 4 hours (health and full regression on the Mac, public or private) plus its registry routines (owner, 2026-11-12), required checks are reported, and the PRD format is current; it prints each gap with its fix and is what each repo's migration is judged by (owner, 2026-11-11: "add prepare fully migration check before once that setup adoption is done, and for all the existing repo, do the migration to fully tighten it"; then: "how should we suggest when we work on another repo if there's update in the template repo? How to enforce it?")

- Slug: migration-check
- Touches: skills/workflow-setup, skills/workflow-health, dev/toy, .loop/regression.tsv, docs/wiki/Setup.md, docs/wiki/Health.md, docs/wiki/Tests.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. `setup.py migration-check` lists every gap with a one-line fix and exits 0 only when none remain; toy repos prove a clean repo passes and each kind of gap is named
2. health's Adoption group runs the same check
3. it writes nothing
4. every adopted repo carries template_version (set by update --apply), and a repo with none counts as behind
5. when work starts in a repo behind the installed template (the entry/START read at session start and goal.py new), one line says: this repo is at vY, the template is at vX, run the migrate goal; it warns and never blocks, except goal.py new refuses when the major version differs
6. health's existing template-version rule files an issue for a repo behind the template on its local 4-hourly run, and the operation session, after each template release, queues one migrate-<repo> goal per behind repo whose done line is migration-check passing
7. update.py --check reads a repo's base-branch config correctly when the checkout is on another branch (steward reported 'no .loop/config.json on its base branch' though main has it)
8. migration-check fails a repo whose Automation section is missing or wrong, or whose health and regression routines are off without an explicit off setting
9. migration-check lists every published wiki page that has no source page in docs/wiki (retired, renamed or old-format pages) and every stale page, as gaps with the page name (owner, 2026-11-11: "when you do the migration, you want to delete all the stale or old pages")
10. migration-check fails a repo whose registered routine has no Runbook on its feature page
11. a repo adopted before v0.27.17 gets its README and Home Settings and Automation blocks inserted by the migration (render.py blocks), since re-running setup says NO CHANGE and update never inserts them (found by render-readme-guard)

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. In a repo adopted before v0.27.17, run `python3 skills/workflow-setup/scripts/setup.py migration-check`. Time the run; on the toy repos a run takes about one second.
   Expect: GAP lines for the missing Settings and Automation blocks, the missing `template_version` and the missing local task, each with a Fix line, and exit 1.
2. In that repo run `python3 skills/workflow-setup/scripts/update.py --apply`, merge the branch it prints, then run the check again with `--pr`.
   Expect: `MIGRATION OK (--pr: state codes not checked)` and exit 0; the full check then lists only the local task and wiki gaps, each with its fix.
3. Run `python3 skills/workflow-health/scripts/automation.py local install`, remove each orphan wiki page the check names (`git rm -- <page>.md` in a clone of the wiki, commit, push), run `docs.py publish`, then run the full check.
   Expect: `MIGRATION OK` and exit 0.
4. In a repo that is behind the installed template, start a goal with `goal.py new`.
   Expect: the one line `this repo is at vY, the template is at vX, run the migrate goal`, and a REFUSED only when the major versions differ (a `migrate-` slug is let through).
5. After a template release, run `python3 skills/workflow-monitoring/scripts/operate.py run --once` in the operation session.
   Expect: one `migrate-<repo>` line in the `.loop/queue.md` of each followed repo that is behind, and none for a repo that is current.
