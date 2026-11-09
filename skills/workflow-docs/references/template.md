# Feature page template

The one definition of a feature page: a short PRD. `criteria.py`, `prd.py` and `docs.py audit` read the `rules` block
below, so changing a rule here changes the check; nothing else holds these numbers. A missing or broken block makes
them refuse.

```rules
sections: Problem, Requirements, Non-goals, Success metrics, Tests
problem_lines: 3
metrics_lines: 3
usage_section: Usage
review_line: Review
scenario: Given ..., when ..., then ...
milestone_line: Milestone
```

## Layout

The first line is `<!-- workflow-docs -->`, then `# <Feature>`, then one `Milestone: <url>` line (left out until the
milestone exists), then the PRD review line, then the sections in the order of `sections`, and nothing else. The
optional `usage_section` goes between Problem and Requirements.

- **Review line**: `Review: **Unreviewed**`, or `Review: **Reviewed YYYY-MM-DD** <!-- prd P=… R=… N=… M=… U=… -->`
  written by `criteria.py review PAGE --user`: one 8-hex fingerprint each for Problem, Requirements, Non-goals, Success
  metrics and Usage. Only the owner reviews a PRD. While it is Reviewed, a change to Problem, Requirements, Non-goals
  or Success metrics fails the check (`LOCKED`), and a change to Usage alone (edited, added or removed) shows as
  `CHANGED` until the owner reviews the PRD again. Requirement stamps are not part of the fingerprints.
- **Problem**: at most `problem_lines` lines (a line is a paragraph, however it wraps): who the feature is for and
  what it solves.
- **Usage** (optional): when the feature has commands, what the owner asks the agent, in a line or two: a
  skill command in backticks, e.g. ``- `/workflow-delivery go "goal" --done "line"` starts a goal.``, or a plain request
  in quotes. Left out when nothing applies; never empty. A line never names a `.py` or `.sh` file or a python/bash
  command; each `/skill verb` must be in that skill's `## Command map`, which maps it to the routine it runs.
- **Requirements**: up to the repo's limit (`criteria_max` in `.loop/config.json`, default 6), one line each, each
  `- ID: **Unreviewed** text` or `- ID: **Reviewed DATE** text`. The owner reviews them; a Reviewed line's wording is
  locked. No script names.
- **Non-goals**: at least one line: what the feature deliberately won't do.
- **Success metrics**: one to `metrics_lines` lines: how we know it works, each measurable.
- **Tests**: made by `criteria.py render`, never by hand. For each requirement, a `#### ID` heading, its words, then
  one line per regression row linked to it: its `scenario` (the row's description), the row linked to
  `.loop/regression.tsv`, when it runs, its last result and date, and when it was seen failing; `**not enforced**`
  when no row passes. Defect tests (rows with category defect) follow under `### Defect tests` in the same form, with
  the issue or finding they keep fixed.

## Scenario lines

A regression row's description is one scenario: `Given <context>, when <action>, then <outcome>.` A description in
another form still renders, marked `(not yet Given/When/Then)`, and `docs.py audit` lists it as `SCENARIO` until it is
rewritten.

## Example

```markdown
<!-- workflow-docs -->
# Billing

Milestone: https://github.com/owner/repo/milestone/9

Review: **Unreviewed**

## Problem

Owners of paid repos need cards charged once a month without a person in the loop.

## Usage

- `/billing charge` charges every card that is due.

## Requirements

- BIL-1: **Unreviewed** A due card is charged once, and a failed charge is retried the next day.

## Non-goals

- No refunds; a person handles those.

## Success metrics

- No card is charged twice in a month.

## Tests

#### BIL-1

A due card is charged once, and a failed charge is retried the next day.

- Given a card due today, when billing runs twice, then it is charged once — [bil-once](../../.loop/regression.tsv), both, PASS 2026-11-08, seen failing 2026-11-07
```

## Required docs

- Each feature page has one `Milestone:` line linking its GitHub milestone, and a `Backlog` milestone exists.
- Every released version has a release note: a GitHub release for its tag, or its section in `CHANGELOG.md`.
