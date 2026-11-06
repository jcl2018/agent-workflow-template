<!-- workflow-docs -->
# Documentation

Skill: `workflow-docs`. Keeps wiki pages in `docs/wiki/` (reviewed in pull requests) and finds stale ones. Script:
`docs.py`.

## Init

`init` is a step list in `skills/workflow-docs/SKILL.md`. It has no script command of its own: `docs.py` has `survey`,
`add`, `check`, `publish` and `restore`.

1. Survey: `python3 scripts/docs.py survey` shows what exists.
2. Add: choose pages (three is a good start: how to use the repo, how it's run, how it's released), name the paths each
   describes, and use a name the survey doesn't list, so the wiki's other pages stay as they are:
   `python3 scripts/docs.py add Using-the-workflow --paths ".loop/config.json,README.md"`.
3. Write each page: replace its placeholder text with what is really in the repo (real commands, real paths, real
   outputs). Keep the first line. If you didn't see it in the repo, don't write it.
4. Commit the pages and `.loop/docs.tsv` on a branch.

First-page rule: if the wiki has no pages yet, the user must create its first page in the browser, because GitHub only
makes the wiki's repo then. Tell them, then stop.

## Commands

```text
survey                          show the wiki's pages and this repo's page map
add PAGE --paths A,B            add a page and the paths it describes
check [--base REF]              list missing, stale, unmapped and unwritten pages; exit 1 if any
publish [--dry-run] [--adopt PAGE]   copy the pages to the GitHub wiki, commit and push
restore                         revert the last publish, if nothing came after it
```

`.loop/docs.tsv` maps each page to the paths it describes. `check` prints `STALE`, `MISSING`, `UNWRITTEN` or
`UNMAPPED`, and `DOCS OK` when clean. `publish` refuses while `check` finds problems, never deletes a page, and won't
replace a page without the marker `<!-- workflow-docs -->` unless you name it with `--adopt`. `restore` refuses if the
wiki changed since.

## Example

```bash
python3 scripts/docs.py add Delivery --paths "skills/workflow-delivery"
python3 scripts/docs.py check
python3 scripts/docs.py publish --dry-run
```
