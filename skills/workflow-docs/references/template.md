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
problem_banned: script, function, regex, json, tsv, stdout
requirement_groups: Functional, Non-functional
format: home, frontdoor, usage, bullets, problem, tests
```

## Layout

The first line is `<!-- workflow-docs -->`, then `# <Feature>`, then one `Milestone: <url>` line (left out until the
milestone exists), then the PRD review line, then the sections in the order of `sections`, and nothing else. The
optional `usage_section` goes between Problem and Requirements. `format` lists which shape checks (DOC-4..DOC-9) run,
default all; each refusal reads `FORMAT <Page>:<line>: <Section>: DOC-n <what> (got <value>). Fix: <how>`.

- **Review line**: `Review: **Unreviewed**`, or `Review: **Reviewed YYYY-MM-DD** <!-- prd P=… R=… N=… M=… U=… -->`
  written by `criteria.py review PAGE --user`: one 8-hex fingerprint each for Problem, Requirements, Non-goals, Success
  metrics and Usage. Only the owner reviews a PRD. While it is Reviewed, a change to Problem, Requirements, Non-goals
  or Success metrics fails the check (`LOCKED`), and a change to Usage alone (edited, added or removed) shows as
  `CHANGED` until the owner reviews the PRD again. Requirement stamps are not part of the fingerprints; sub-bullets are.
- **Problem** (`problem`, DOC-8): 1 to `problem_lines` bullets (`- `), the user's problem in their words, at least one
  in the first person (I, my, me). No backticks, no path (`/x/`), no file extension (`.py`, `.sh`, `.json`, `.tsv`,
  `.md`) and no word from `problem_banned` (whole word, any case).
- **Usage** (optional, `usage`, DOC-6): an API reference. One entry per command, each a single bullet
  ``- `<syntax>` — <what it does>``: the exact syntax, what it prints on success (a backticked output, or "prints"/
  "ends with"), and each refusal with its message and exit code, and nothing else but blank lines. The command's first word (or a `/skill verb`, or the routine after python3) must be in that skill's
  `## Command map`, either column. Left out when nothing applies; never empty.
- **Requirements** (`bullets`, DOC-7): grouped under exactly the `requirement_groups` headings, in order:
  `### Functional` (what it does), then `### Non-functional` (qualities and limits: privacy, safety, reliability,
  performance, size and time limits), with nothing before the first. A group with no requirement holds the single line
  `None`. Up to the repo's limit (`criteria_max` in `.loop/config.json`, default 10) counted over both groups, one
  line each, `- ID: **Unreviewed** text` or `- ID: **Reviewed DATE** text`, and under each at least one sub-bullet:
  exactly two spaces, `  - `, each one checkable behavior. An Unreviewed line
  is a title of at most 20 words; a Reviewed line's wording is locked (DOC-2), and its stamp covers the line only, never
  its sub-bullets. Words are whitespace tokens after `[text](url)` becomes text and backticks are stripped. An orphan
  or deeper-nested sub-bullet is always refused. No script names.
- **Non-goals**: at least one line: what the feature deliberately won't do.
- **Success metrics**: one to `metrics_lines` lines: how we know it works, each measurable.
- **Tests** (`tests`, DOC-9): made by `criteria.py render`, never by hand: one table
  `| Test | Kind | Guards | Checks | Last result |`. Test links the row's entry on the full Tests page,
  `[row](Tests#t-<slug>)` (the row id lower-cased, anything but `a-z0-9-` turned into `-`; two rows sharing a slug are
  refused). Kind is requirement or defect; Guards is the requirement's ID, or the defect's issue link and state; Checks
  is the row's `scenario`; Last result is its last result and date. A requirement with no passing row gets a row whose
  Last result is `not enforced`. Defect rows follow in the same table.

## Home, the README front door and the full Tests page

- **Home** (`home`, DOC-4): the marker, `# <repo>`, `## Features` and one table
  `| Feature | What it does | How to use | Milestone |`, nothing else, with one row per feature page. Feature is
  `[Page](Page)`; How to use is `[README](https://github.com/OWNER/REPO#how-to-use-<feature>)`, an anchor of the README's
  `### How to use <Feature>` heading; Milestone links `…/milestone/N`.
- **README** (`frontdoor`, DOC-5): `## How to use`, then one `### How to use <Feature>` per feature page, each with at most
  one intro line and a table `| You say | What happens |`. A You-say cell is a quoted phrase the owner says: no
  backticks, and no `/`, `python` or `bash` at its start.
- **Tests page** (DOC-10): `docs/wiki/Tests.md`, generated by `criteria.py render` and never mapped in `.loop/docs.tsv`:
  the marker, `# Tests`, then per feature `## <Feature>` and a table
  `| Test | Kind | Guards | Result | Date | Run | Seen failing |` whose first cell holds `<a id="t-<slug>"></a>` and the
  row id. Run links the run that recorded the result (the runs file's fourth column: a URL, or a commit), else `local`.
  The check reports `STALE Tests` when it differs from a fresh render.

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

- I run paid repos, and I can't charge every card once a month without doing it by hand.

## Usage

- `/billing charge` — Charges every card that is due. Prints one `CHARGED <card>` line per card. Refuses nothing.

## Requirements

### Functional

- BIL-1: **Unreviewed** A due card is charged once.
  - A card due today is charged once, however often billing runs.
  - A failed charge is retried the next day.

### Non-functional

None

## Non-goals

- No refunds; a person handles those.

## Success metrics

- No card is charged twice in a month.

## Tests

| Test | Kind | Guards | Checks | Last result |
|---|---|---|---|---|
| [bil-once](Tests#t-bil-once) | requirement | BIL-1 | Given a card due today, when billing runs twice, then it is charged once. | PASS 2026-11-08 |
```

## Required docs

- Each feature page has one `Milestone:` line linking its GitHub milestone, and a `Backlog` milestone exists.
- Every released version has a release note: a GitHub release for its tag, or its section in `CHANGELOG.md`.
