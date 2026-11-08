# Feature page template

The one definition of a feature page. `criteria.py` and `docs.py audit` read the `rules` block below, so changing a
rule here changes the check; nothing else holds these numbers. A missing or broken block makes them refuse.

```rules
sections: Summary, Criteria, Tests
summary_lines: 3
max_criteria: 5
tests_columns: Criterion, Test, What it checks, Runs, Last result, Seen failing
defect_columns: Defect, Test, What it checks, Runs, Last result, Seen failing
milestone_line: Milestone
```

## Layout

The first line is `<!-- workflow-docs -->`, then `# <Feature>`, then one `Milestone: <url>` line, then the sections
in the order of `sections`, and nothing else.

- **Summary**: at most `summary_lines` lines (a line is a paragraph, however it wraps), saying what the feature is for.
- **Criteria**: at most `max_criteria` lines, each `- ID: **Unreviewed** text` or `- ID: **Reviewed DATE** text`.
  The owner marks them Reviewed, and a Reviewed line's wording is locked. No script names.
- **Tests**: a table made by `criteria.py render`, never by hand, with the `tests_columns`. Defect tests (regression rows
  with category defect) follow it under a `### Defect tests` heading, with the `defect_columns`, on the page whose code they guard.

## Tests columns

| Column | Means |
|---|---|
| Criterion | The criterion's id and words, so the table reads alone |
| Defect | In the defect table instead of Criterion: the issue or finding the test keeps fixed, linked to it |
| Test | The regression row that proves it, linked to `.loop/regression.tsv`; `**not enforced**` when no row passes |
| What it checks | The row's description, in plain words |
| Runs | When it runs: both (every push and nightly), nightly, or by a person |
| Last result | Its last status and date from `.loop/regression-runs.tsv`; `not run` if never |
| Seen failing | The date the test was first seen failing, or `no` |

## Required docs

- Each feature page has one `Milestone:` line linking its GitHub milestone, and a `Backlog` milestone exists.
- Every released version has a release note: a GitHub release for its tag, or its section in `CHANGELOG.md`.
