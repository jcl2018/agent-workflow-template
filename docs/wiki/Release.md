<!-- workflow-docs -->
# Release

Skill: `workflow-release`. After a goal has a pull request and its checks hold. Script: `release.py`.

## Commands

```text
ask SLUG
leave SLUG
cut SLUG [--bump patch|minor|major] [--user]
show SLUG
```

- `ask` shows the changed docs, the wiki link and the verify steps, then prints `cut <slug>` and `leave <slug>`. A
  monitored batch goal without `release: ask` answers `leave` by itself.
- `leave` keeps the work unreleased and changes nothing versioned.
- `cut` refuses without numbered steps under `## Verify by hand`, if any step has no `Expect:` line, or with a mapped
  page that is stale since the goal's base or missing. After fixing a page, commit it and run `goal.py check` again.
  `cut` then moves the version (`patch` by default), writes the changelog, commits, pushes and creates a **draft**
  GitHub release. You publish it. A batch goal refuses `cut` without `--user`, which means your own words said to cut.
- `cut` also refuses when a criterion on a wiki page (see Documentation) has a regression row that is missing, a draft
  or failing. A repo with no criteria is unaffected.
- `show` prints the `release` field, and the version and draft URL after a cut.

After a cut, the agent publishes the wiki with `workflow-docs` if `.loop/docs.tsv` exists. If that fails, the draft
stands.

## Automatic draft releases

Set `"release_auto": true` in `.loop/config.json` to let a monitored batch goal decide from its diff. `ask` prints
`NEED <leave|patch|minor|ask>: <reason>` and records it. Docs, tests and `.loop` changes leave. A fix cuts a `patch`
draft, and a new non-doc file or a `feat` commit cuts a `minor` draft, with no `--user`. A breaking change (a `BREAKING`
or `!:` commit, or a removed file) always waits for you, and so does a goal marked `release: ask`. Every refusal of
`cut` still applies, and then you decide. Without `release_auto`, a batch goal leaves as before. The release is always a
draft.

No release is published and nothing merges without you.

## Example

```bash
python3 scripts/release.py ask add-median
python3 scripts/release.py cut add-median --bump minor --user
```
