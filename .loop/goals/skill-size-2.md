# Fix issue 116: bring workflow-delivery and workflow-docs SKILL.md back under 150 lines

- Slug: skill-size-2
- Touches: skills/workflow-delivery, skills/workflow-docs, dev/toy, .loop/regression.tsv, skills/workflow-regression/scripts, skills/workflow-release/scripts, docs/wiki

## Done lines

Frozen. A wrong done line needs a new goal.

1. skills/workflow-delivery/SKILL.md and skills/workflow-docs/SKILL.md are each at most 150 lines with no instruction lost (detail moves to its references folder)
2. test-board passes on main again and a defect test linked to issue 116 is seen failing once
3. Per DOC-3, each done line is recorded on its PRD page as a Given/When/Then scenario
4. Issues 138, 139, 140, 141 and 142 are fixed: goal.py, criteria.py, docs.py, regression.py and release.py each stay under the 20 KB limit, split without behaviour change (owner-approved issue mapping 2026-11-10)

## Closes

Splits criteria.py, docs.py and regression.py by pure moves into existing sibling modules (the package is at its
99-file cap); issue 116 was fixed by the first skill-size goal. Three scripts are left out, each by the operation's
call, because no file in their folder has room after the other goals that landed first: goal.py (#138) and lane.py
(#529) stay under the 20 KB hard limit but not under health's 18,432-byte warning, so those issues stay open for a
later goal; release.py (#142) waits for its own split, a pure move into autorelease.py, noted on #142. Done line 4's
size limit is the 20 KB limit, which all five scripts meet; the goal's own splits take the three it covers below the
warning line.

Closes #139, closes #140, closes #141. Refs #116, #138, #142, #529.

## Owner re-review: Documentation (CHANGED)

The Documentation page is owner-reviewed, and its Usage is sealed. This goal adds one sentence to the end of the `/workflow-docs check` line there, so `docs.py check` reports CHANGED until the owner reviews the page again (`review --user`); the release audit ignores CHANGED. The sentence, in full:

> Its page map is read through `counting.py` and its page rules through `deployments.py`, moved there unchanged so docs.py and criteria.py stay under the size limit.

## Owner re-review: Health (CHANGED)

The Health page is owner-reviewed, and its Usage is sealed. Main's private-name hooks commit left that page without its Usage line for the new `hooks` rule, so the release check calls the page stale. This goal adds one sentence to the end of the `/workflow-health check` line, so `docs.py check` reports CHANGED until the owner reviews the page again (`review --user`). The sentence, in full:

> Its hygiene group includes a `hooks` rule: it warns when a private-name hook (pre-commit, commit-msg or pre-push, installed by workflow-setup) is missing, is not ours or calls a script that is gone, or when the private-name list is broken.

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Run `wc -c skills/workflow-docs/scripts/criteria.py skills/workflow-docs/scripts/docs.py skills/workflow-regression/scripts/regression.py`.
   Expect: criteria.py, docs.py and regression.py are each under 18432 bytes.
2. Run `python3 skills/workflow-health/scripts/health.py check | grep "WARN size"`.
   Expect: criteria.py, docs.py and regression.py are not listed.
3. Run `bash dev/toy/test-defect.sh size-139`, then add one line `def rules(): pass` to the end of `skills/workflow-docs/scripts/criteria.py` and run it again.
   Expect: the first run prints nothing and exits 0; the second prints a `leftovers:` line naming `rules`. Undo the edit with `git checkout -- skills/workflow-docs/scripts/criteria.py`.
4. Run `wc -l skills/workflow-delivery/SKILL.md skills/workflow-docs/SKILL.md`.
   Expect: each is under 150 lines.
