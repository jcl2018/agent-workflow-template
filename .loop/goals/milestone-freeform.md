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
