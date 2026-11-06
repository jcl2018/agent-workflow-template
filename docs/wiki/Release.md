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
  monitored batch goal answers `leave` by itself.
- `leave` keeps the work unreleased and changes nothing versioned.
- `cut` refuses without a numbered step with an `Expect:` line under `## Verify by hand`, or with a stale mapped page. It
  then moves the version (`patch` by default), writes the changelog, commits, pushes and creates a **draft** GitHub
  release. You publish it. A batch goal refuses `cut` without `--user`, which means your own words said to cut.

Nothing merges or publishes without you.

## Example

```bash
python3 scripts/release.py ask add-median
python3 scripts/release.py cut add-median --bump minor --user
```
