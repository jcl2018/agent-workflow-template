<!-- workflow-docs -->
# Documentation

Skill: `workflow-docs`. Keeps wiki pages in `docs/wiki/` (reviewed in pull requests) and finds stale ones. Script:
`docs.py`.

## Init

`init` is the skill's first step, not a `docs.py` subcommand. It runs `survey`, then `add` for each page you choose (three
is a good start: how to use the repo, how it's run, how it's released). You replace each placeholder with what is really
in the repo, keep the first line, and commit the pages and `.loop/docs.tsv` on a branch. If the GitHub wiki has no pages,
you must create its first page in the browser.

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
