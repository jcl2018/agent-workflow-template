# Milestones become free form, used to plan by version (for example v1.0) for visualization; nothing requires a feature page, issue or pull request to have a milestone (owner, 2026-11-11: "the milestone should be probably planned by vision ... I think there's a restriction that each feature should have a milestone. I think you can remove that restriction because it's like free form ... We don't need to essentially use that")

- Slug: milestone-freeform
- Touches: skills/workflow-docs, skills/workflow-health, skills/workflow-setup, skills/workflow-delivery, skills/workflow-regression, dev/toy, .loop/regression.tsv, .loop/config.json, docs/wiki

## Done lines

Frozen. A wrong done line needs a new goal.

1. DOC-10's milestone clause, the Home table's Milestone column, HLT-4, Automation's "on the milestone of the feature" lines and SET-1's "a milestone per feature plus Backlog" are reworded so milestones are optional and free form, each changed line Unreviewed, with the wording shown in the PR
2. No check, health rule, docs check, goal.py pr or setup step fails, warns or refuses because a feature page, issue or pull request has no milestone, and no code creates a per-feature milestone; issues are still tagged with their feature or group
3. A milestone that exists is still shown where useful (Home, the board), and a version milestone like v1.0 works as before
4. Each removed check has a regression row seen failing on the old rule (a missing milestone flagged) and passing on the new one

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Read Documentation DOC-10 and Health HLT-4 (and DOC-4, HLT-2, AUT-2, AUT-3, SET-1) in docs/wiki.
   Expect: each says a milestone is optional and free form (for example v1.0), none calls it required or per feature, and each of the seven lines reads `Unreviewed`.
2. Run `python3 skills/workflow-docs/scripts/docs.py check` in this repo (its pages keep their existing `Milestone:` link, shown as before); then run `bash dev/toy/test-docs-command.sh` and `bash dev/toy/test-docs-format.sh`.
   Expect: `DOCS OK: 9 pages` with no warning about a milestone; the toy runs print `PASS milestone-freeform:no-milestone-page-ok` and `PASS milestone-freeform:home-milestone-optional` (a page without a Milestone line, and a Home row with an empty Milestone cell, pass).
3. Run `bash dev/toy/test-milestones.sh` (a fixture repo with the fake gh) and read its health file/preview section.
   Expect: issues are filed labelled only `health` and `health:<group>`, with no milestone made or set and no `feature:` label call while `feature_labels` is off; with it on, a `feature:Calc` label is created first and applied; `milestone.py new v1.0 --live` and `move 1 v1.0` work; the run ends with `PASS milestone-freeform:health-file-no-milestone` and `PASS milestone-freeform:milestone-v1-free-form`.

## Wording changes

Each changed requirement line, before and after. Every one ends Unreviewed; each page's Review line is `Review: **Unreviewed**` too (the owner un-review, words quoted in the commit). Seals (`<!-- reviewed ... -->`, `<!-- prd ... -->`) are gone until the owner re-reviews.

### Documentation

Review line before: `Review: **Reviewed 2026-11-10** <!-- prd P=3add8b00 R=c3b7093f N=81dd3484 M=4599a537 U=689852ab -->`; after: `Review: **Unreviewed**`

**DOC-4 before**
```
- DOC-4: **Reviewed 2026-11-10** Home is one table <!-- reviewed 4ee8099b -->
  - Home holds one table with four columns: Feature, What it does, How to use (a link to the README section), Milestone.
  - Nothing else is on Home.
```
**DOC-4 after**
```
- DOC-4: **Unreviewed** Home is one table
  - Home holds one table with four columns: Feature, What it does, How to use (a link to the README section), Milestone (optional: empty, or a link to the free-form milestone the feature is planned on).
  - Nothing else is on Home.
```

**DOC-10 before**
```
- DOC-10: **Reviewed 2026-11-10** One Tests page, every issue on a milestone, every release noted <!-- reviewed 4ea5bba8 -->
  - One full Tests page is generated, listing every test with its latest result.
  - Every open issue is on its feature's milestone, or on Backlog only when it fits no feature.
  - Every release has a release note.
```
**DOC-10 after**
```
- DOC-10: **Unreviewed** One Tests page, every release noted, milestones optional
  - One full Tests page is generated, listing every test with its latest result.
  - Every release has a release note.
  - A milestone is optional and free form, used to plan by version (for example v1.0); nothing requires a feature page, issue or pull request to have one, and no check fails or warns for lacking one.
```

### Health

Review line before: `Review: **Reviewed 2026-11-10** <!-- prd P=5376f52c R=a0157a0e N=e89b4f3b M=96c50b43 U=faad868e -->`; after: `Review: **Unreviewed**`

**HLT-2 before**
```
- HLT-2: **Reviewed 2026-11-10** The rules <!-- reviewed 268500bd -->
  - Health checks exactly these groups, each with the angle its tests take:
  - Requirements (my angle: is every promise I approved proven?): every Reviewed requirement has a test seen failing and passing now; done lines have tests; none stays not enforced over 7 days.
  - Traceability (an auditor's angle: can I follow any work end to end?): requirement to test to last run; issue to milestone to feature; pull request to goal to done lines; release to the issues it fixed.
  - Consistency (a reader's angle: do the pages agree?): IDs unique across pages; no reference to a missing ID; a command named the same in Usage and the README; no two requirements that contradict.
  - Docs (a newcomer's angle: does each page match the template and the code?): template sections and limits; Usage matches the real commands and output; Home complete; every open issue on a milestone.
  - Freshness (my angle when I come back: is anything out of date?): the nightly suite ran in the last 24 hours; no merged work unreleased over 3 days; pages updated after their code changed; no finding older than 30 days.
  - Tests (a skeptic's angle: do the tests prove anything?): every row seen failing once; no flaky rows; no row skipped over 7 days; slowest rows named; no test touches the network.
  - Performance (my clock's and my wallet's angle: is it fast and cheap enough?): goal runs and the full suite within their time limits; goals within their time and token budgets; the health check within its limit.
  - Security and privacy (a leak's angle: can anything private escape?): no private names, paths, emails or keys in tracked files; secrets only in the environment or secrets; the commit scan hook installed; workflows with least permissions.
  - Size (a maintainer's angle: can someone still read this?): scripts under 20 KB with a warning from 90%; SKILL.md under 150 lines; requirements per page within the limit.
  - Hygiene (a janitor's angle: is anything left lying around?): open findings within the cap; no wait on me over 24 hours; no merged or stale branches or worktrees; no idle worker sessions.
  - Adoption (another repo's angle: would this work installed fresh?): config valid; every check runs at least one test; template version current; scheduled workflows present and firing.
  - Controls (the checker's own angle: can each rule fire?): every rule has a negative control run against a deliberately broken copy.
  - Mine (my private angle): rules I add in a private setting.
  - At most 12 groups plus Mine; adding one means retiring one or raising the cap on purpose.
```
**HLT-2 after**
```
- HLT-2: **Unreviewed** The rules
  - Health checks exactly these groups, each with the angle its tests take:
  - Requirements (my angle: is every promise I approved proven?): every Reviewed requirement has a test seen failing and passing now; done lines have tests; none stays not enforced over 7 days.
  - Traceability (an auditor's angle: can I follow any work end to end?): requirement to test to last run; issue to feature; pull request to goal to done lines; release to the issues it fixed.
  - Consistency (a reader's angle: do the pages agree?): IDs unique across pages; no reference to a missing ID; a command named the same in Usage and the README; no two requirements that contradict.
  - Docs (a newcomer's angle: does each page match the template and the code?): template sections and limits; Usage matches the real commands and output; Home complete.
  - Freshness (my angle when I come back: is anything out of date?): the nightly suite ran in the last 24 hours; no merged work unreleased over 3 days; pages updated after their code changed; no finding older than 30 days.
  - Tests (a skeptic's angle: do the tests prove anything?): every row seen failing once; no flaky rows; no row skipped over 7 days; slowest rows named; no test touches the network.
  - Performance (my clock's and my wallet's angle: is it fast and cheap enough?): goal runs and the full suite within their time limits; goals within their time and token budgets; the health check within its limit.
  - Security and privacy (a leak's angle: can anything private escape?): no private names, paths, emails or keys in tracked files; secrets only in the environment or secrets; the commit scan hook installed; workflows with least permissions.
  - Size (a maintainer's angle: can someone still read this?): scripts under 20 KB with a warning from 90%; SKILL.md under 150 lines; requirements per page within the limit.
  - Hygiene (a janitor's angle: is anything left lying around?): open findings within the cap; no wait on me over 24 hours; no merged or stale branches or worktrees; no idle worker sessions.
  - Adoption (another repo's angle: would this work installed fresh?): config valid; every check runs at least one test; template version current; scheduled workflows present and firing.
  - Controls (the checker's own angle: can each rule fire?): every rule has a negative control run against a deliberately broken copy.
  - Mine (my private angle): rules I add in a private setting.
  - At most 12 groups plus Mine; adding one means retiring one or raising the cap on purpose.
```

**HLT-4 before**
```
- HLT-4: **Reviewed 2026-11-10** Findings become issues on their feature's milestone <!-- reviewed 2ab4d59e -->
  - Each finding, from a rule or from the review, is one GitHub issue on the milestone of the feature it's about (Backlog only when it fits none), tagged with its group or kind.
  - A preview lists exactly what would be opened, updated, closed or reopened, and nothing is written until I confirm or name the groups or features to file.
  - A repeat updates its issue, a fix closes it, a return reopens it, and an existing open issue that already covers a finding is linked, not duplicated.
```
**HLT-4 after**
```
- HLT-4: **Unreviewed** Findings become issues tagged with their feature and group
  - Each finding, from a rule or from the review, is one GitHub issue tagged with its group or kind and the feature it is about; it sits on a milestone only when I put it there.
  - A preview lists exactly what would be opened, updated, closed or reopened, and nothing is written until I confirm or name the groups or features to file.
  - A repeat updates its issue, a fix closes it, a return reopens it, and an existing open issue that already covers a finding is linked, not duplicated.
```

### Automation

Review line before: `Review: **Reviewed 2026-11-10** <!-- prd P=2f4bd05a R=759415cb N=d6d10cdd M=dad3088c U=cef8c285 -->`; after: `Review: **Unreviewed**`

**AUT-2 before**
```
- AUT-2: **Reviewed 2026-11-10** Regression every few hours <!-- reviewed a9d85df6 -->
  - The full regression suite runs on the schedule (every 4 hours by default) and on every release.
  - A failing test opens or updates one issue labeled defect, on the milestone of the feature it guards, naming the test and the requirement; it closes by itself when the test passes again.
```
**AUT-2 after**
```
- AUT-2: **Unreviewed** Regression every few hours
  - The full regression suite runs on the schedule (every 4 hours by default) and on every release.
  - A failing test opens or updates one issue labeled defect, tagged with the feature it guards, naming the test and the requirement; it closes by itself when the test passes again.
```

**AUT-3 before**
```
- AUT-3: **Reviewed 2026-11-10** Health every few hours <!-- reviewed b9abc41d -->
  - The health check runs on the schedule, after regression, with all its rule groups, and the repo review too when an agent key is set as a secret (otherwise skipped, and the report says so).
  - Every finding becomes one issue tagged with its group, on the milestone of the feature it is about (Backlog only when none fits), updated, closed or reopened as things change, never duplicated.
```
**AUT-3 after**
```
- AUT-3: **Unreviewed** Health every few hours
  - The health check runs on the schedule, after regression, with all its rule groups, and the repo review too when an agent key is set as a secret (otherwise skipped, and the report says so).
  - Every finding becomes one issue tagged with its group and its feature, updated, closed or reopened as things change, never duplicated.
```

### Setup

Review line before: `Review: **Reviewed 2026-11-10** <!-- prd P=7f1b1066 R=a1dcdd47 N=9c385754 M=471a58c6 U=726b84e2 -->`; after: `Review: **Unreviewed**`

**SET-1 before**
```
- SET-1: **Reviewed 2026-11-10** One command adopts a repo <!-- reviewed 890df4f8 -->
  - One command sets up a new or existing repo: the loop config, PRD feature pages in the docs format, the Home table and README How to use, a milestone per feature plus Backlog, the nightly regression in GitHub Actions, the health groups, and every setting with its default.
  - It shows what it found and would change first, then applies it on a branch through the loop, adapting what is there instead of overwriting.
  - It never blocks: what doesn't fit is listed and filed as issues on the right milestone, and the rest is adopted.
  - Health is the first and last step: before adopting, a health check records where the repo starts; after adopting, the full health check (every group, Adoption included) must come back green or name each gap with its fix, and that verdict is the adoption result, because if health works, the rest works.
```
**SET-1 after**
```
- SET-1: **Unreviewed** One command adopts a repo
  - One command sets up a new or existing repo: the loop config, PRD feature pages in the docs format, the Home table and README How to use, the nightly regression in GitHub Actions, the health groups, and every setting with its default.
  - It shows what it found and would change first, then applies it on a branch through the loop, adapting what is there instead of overwriting.
  - It never blocks: what doesn't fit is listed and filed as issues tagged with the right feature, and the rest is adopted.
  - Health is the first and last step: before adopting, a health check records where the repo starts; after adopting, the full health check (every group, Adoption included) must come back green or name each gap with its fix, and that verdict is the adoption result, because if health works, the rest works.
```

### Home table (no Review line; not un-reviewed)

The header stays `| Feature | What it does | How to use | Milestone |`. The Milestone cell is no longer validated: empty, text such as v1.0, or a link all pass (docs-check refusal removed). Text changes: Documentation, Health and Automation rows.

```diff
-| [Documentation](Documentation) | Keeps the wiki, README and milestones in one enforced format, and publishes them on every release. | [README › Documentation](https://github.com/jcl2018/agent-workflow-template#how-to-use-documentation) | [Documentation](https://github.com/jcl2018/agent-workflow-template/milestone/3) |
+| [Documentation](Documentation) | Keeps the wiki and README in one enforced format, and publishes them on every release. | [README › Documentation](https://github.com/jcl2018/agent-workflow-template#how-to-use-documentation) | [Documentation](https://github.com/jcl2018/agent-workflow-template/milestone/3) |
-| [Health](Health) | Checks the repo with fixed rules and a full reviewer, and files every finding on its feature's milestone. | [README › Health](https://github.com/jcl2018/agent-workflow-template#how-to-use-health) | [Health](https://github.com/jcl2018/agent-workflow-template/milestone/4) |
+| [Health](Health) | Checks the repo with fixed rules and a full reviewer, and files every finding as an issue tagged with its feature. | [README › Health](https://github.com/jcl2018/agent-workflow-template#how-to-use-health) | [Health](https://github.com/jcl2018/agent-workflow-template/milestone/4) |
-| [Automation](Automation) | Runs regression and health on a schedule, files each failure and finding on its feature's milestone, and emails you one digest per round. | [README › Automation](https://github.com/jcl2018/agent-workflow-template#how-to-use-automation) | [Automation](https://github.com/jcl2018/agent-workflow-template/milestone/10) |
+| [Automation](Automation) | Runs regression and health on a schedule, files each failure and finding as an issue tagged with its feature, and emails you one digest per round. | [README › Automation](https://github.com/jcl2018/agent-workflow-template#how-to-use-automation) | [Automation](https://github.com/jcl2018/agent-workflow-template/milestone/10) |
```

### Retired rows (each asserted the removed rule)

| Retired row | Old rule it asserted | Replaced by |
|---|---|---|
| issue-no-milestone-fails | an open issue with no milestone FAILs in docs-check | no-milestone-issue-ok |
| issue-milestone-passes | an issue with a milestone passes | no-milestone-issue-ok |
| issue-closed-ignored | a closed issue with no milestone is ignored | no-milestone-issue-ok |
| issue-gh-fail-unread | an unreadable issue list is an UNREAD row | no-milestone-issue-ok |
| issue-truncated-unread | 1000 open issues is UNREAD truncated | no-milestone-issue-ok |
| milestone-links | the audit links a page to its milestone and finds a missing Backlog | no-milestone-page-ok |
| pr-in-milestone | goal.py pr puts the pull request in its feature milestone | pr-no-milestone |
| aut-backlog-milestone | the health workflow makes Backlog before filing | health-workflow-no-milestone |
| ci-issue-backlog | the CI block puts an unplaced regression issue on Backlog | regression-issue-no-milestone |
| digest-backlog | the digest issue is created on Backlog | digest-no-milestone |
| update-in-place | a later health run moves an issue to its feature milestone | health-file-no-milestone |

Rewritten to the tag semantics (ids kept, each seen failing again): milestones-once, hlt4-feature-milestones, aut-email-file, aut-email-regression, aut-email-digest. docs-milestone-line-issue-130 keeps its row and passes either way.

### Day-one note

Until the owner labels issues (the `feature_labels` setting is off, so no feature label is made or applied by this goal), an issue on Backlog, v1.0 or no milestone groups as `No feature` in triage and the digest; an issue on a milestone named like a page keeps that feature. The digest headings change from milestones to features accordingly.

### Not in this goal

Live backfill of feature labels on open GitHub issues; a docs check flagging two page names that share their first 42 characters; the `feature_labels` setting is off by default.

### Seen-red evidence (the row's own failing line on the broken tree, no traceback from the break)

| Row | Failing line on the old rule |
|---|---|
| no-milestone-issue-ok | `FAIL docs #3 milestone: Loose ends -> fix: gh issue edit 3 --milestone` |
| no-milestone-page-ok | `FAIL: milestone line` (a MILESTONE line printed) |
| home-milestone-optional | `FAIL: home milestone` (a Home refusal for a non-link cell) |
| pr-no-milestone | `FAIL: pr milestone` (a `pr edit --milestone` call) |
| health-file-no-milestone, hlt4-feature-milestones, aut-email-file | `FAIL: file leaves an issue the owner put on a milestone where it is, and makes and sets none` (a `--milestone` on the created issue) |
| regression-issue-no-milestone, aut-email-regression | `FAIL: milestone call` (a `--milestone` on the defect issue) |
| digest-no-milestone | `FAIL: digest milestone flag` |
| aut-email-digest | the digest heading check (a `### No milestone` section) |
| setup-no-milestone-step | `FAIL: setup mentions a milestone` (the NEXT line) |
| health-workflow-no-milestone | `FAIL: milestone step` |
| milestone-v1-free-form | `FAIL: grouping: v1.0 Backlog No feature Calc Calc No feature` |
| milestones-once | `FAIL: idempotent` |
| milestone-wording-unreviewed | `FAIL: wording: DOC-10 says "on its feature's milestone"; ...` |
| milestone-rows-seen-red | a cleared `seen_red` cell on pr-no-milestone |
