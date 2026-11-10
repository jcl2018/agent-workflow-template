# Regression: commands and flows

Moved from the wiki page, which is now only a summary, criteria and tests.

## Commands

```text
add <id> --level <level> --command "<command>" [--goal <criterion>|<slug>:<n>] [--category criterion|defect --link <url>]
sync [--write]
criteria
red <id> --break "<command>"
run [land|nightly|<id>] [--timeout S] [--live]
workflow
```

| Level | Runs in |
|---|---|
| `land` | `run land` and `run nightly` |
| `nightly` | `run nightly` |
| `draft` | Nothing, until given a real command |
| `covered` | Nothing; proved elsewhere |

- `add` adds or replaces a row. `--goal` ties it to a criterion or a goal's done line, and a changed command must be
  proved again. `--category defect --link <issue or pull request URL, or finding:SLUG>` makes it a defect test: it keeps a
  fixed issue, finding or bug fixed, shows under "Defect tests" on the page of the criterion in `--goal`, and never counts as
  proof of that criterion. A row with no category reads as a criterion test; a defect row with no link is flagged by `sync`.
- `sync` lists done lines, and wiki criteria (a row whose id or `--goal` is the criterion id), with no row (`GAP`), `DRAFT` rows and `UNPROVEN` rows; `--write` adds drafts.
- `criteria` runs the row of every wiki criterion and prints any that is missing, a draft or failing.
- `red` copies `HEAD` to a temporary worktree, applies the break and records the date if the test fails. `STILL GREEN`
  means the test proves nothing. Only a `YYYY-MM-DD` date counts as seen failing; an empty cell, `-` or other text
  counts as never, in `sync`, `run`, the wiki Tests lines and delivery's defect-test check.
- `run` prints `PASS`, `FAIL`, `KNOWN`, `FIXED` or `UNPROVEN` (blocks). Known failures sit in
  `.loop/regression-known.tsv`. It keeps one issue per failing row; without a token it only prints `WOULD` lines.
- `workflow` writes `.github/workflows/regression.yml` (nightly, on `v*` tags, by hand). The job has 90 minutes; each
  row runs in its own process group with a 15-minute limit and starts only if that limit still fits an 88-minute
  budget (`REGRESSION_ROW_SECONDS` and `REGRESSION_JOB_SECONDS` in the step's environment override them). A row that
  doesn't fit is skipped (`SKIPPED`) and fails with an issue. Each result is saved as the row ends, and a last step
  that always runs writes the run summary: one header with totals and the run time, then one table per feature, or the
  plain results if that fails. Rows run with no GitHub token and none of the runner's own files in their environment
  (`regression.py run` too), and the checkout uses `persist-credentials: false`.
- `tests.py list` prints every test in one fixed format, grouped by feature (`--markdown` tables, `--tsv` lines);
  `summary` writes the GitHub run summary from a run's results; `issues --write` records each defect test's issue or
  pull request state. The wiki Tests lines and the health report use the same fields.

### Example

```text
/workflow-regression red check-1 --break "<a command that breaks the code>"
/workflow-regression run land
```

### Stage charts

Amber marks where the command stops for the owner. [Home](Home) says what each status means. "Toy test" means a throwaway repo with stand-ins for GitHub.

#### `add`

```mermaid
flowchart LR
  a["Add or replace the row"]
  b["A changed command must be proved again"]
  a --> b
```

Status: built and proven: Add or replace the row. Built only: A changed command must be proved again. Planned: none.
Stops for the owner: none.
Proof: toy tests and this repo's rows. Nothing tests that a changed command loses its proof.

#### `sync`

```mermaid
flowchart LR
  a["Find done lines and criteria with no row"]
  b["Find draft and unproven rows"]
  c["With --write, add drafts"]
  d{{"Owner or agent gives each draft a real command"}}
  a --> b
  b --> c
  c --> d
  classDef owner fill:#fde68a,stroke:#b45309,color:#1f2937
  class d owner
```

Status: built and proven: Find done lines and criteria with no row; Find draft and unproven rows; With --write, add drafts. Built only: Owner or agent gives each draft a real command. Planned: none.
Stops for the owner: Owner or agent gives each draft a real command.
Proof: toy tests, and it runs on this repo, where it still lists old goals' done lines with no row.

#### `criteria`

```mermaid
flowchart LR
  a["Run the row of every criterion"]
  b["Print any missing, draft or failing"]
  a --> b
```

Status: built and proven: Run the row of every criterion; Print any missing, draft or failing. Built only: none. Planned: none.
Stops for the owner: none.
Proof: a real run on this repo is on record. No toy test calls it.

#### `red`

```mermaid
flowchart TD
  a["Copy HEAD to a temporary worktree"]
  b["Apply the break"]
  c["Run the test"]
  d["Failed: record the date"]
  e["Still green: the test proves nothing"]
  a --> b
  b --> c
  c --> d
  c --> e
```

Status: built and proven: Copy HEAD to a temporary worktree; Apply the break; Run the test; Failed: record the date; Still green: the test proves nothing. Built only: none. Planned: none.
Stops for the owner: none.
Proof: toy tests. This repo's 15 criterion rows each carry a date.

#### `run`

```mermaid
flowchart TD
  a["Run the rows at this level"]
  b["Print PASS, FAIL, KNOWN, FIXED or UNPROVEN"]
  c["Keep one issue per failing row"]
  d["No token: print WOULD lines only"]
  e{{"Owner reads a blocking failure"}}
  a --> b
  b --> c
  b --> d
  b -->|blocks| e
  classDef owner fill:#fde68a,stroke:#b45309,color:#1f2937
  class e owner
```

Status: built and proven: Run the rows at this level; Print PASS, FAIL, KNOWN, FIXED or UNPROVEN; Keep one issue per failing row; No token: print WOULD lines only; Owner reads a blocking failure. Built only: none. Planned: none.
Stops for the owner: Owner reads a blocking failure.
Proof: toy tests with a stand-in for GitHub. Two real issues with this label sit on a second repo, but no record ties them to a run.

#### `workflow`

```mermaid
flowchart LR
  a["Refuse to replace another workflow"]
  b["Write the nightly workflow"]
  c["Workflow runs in CI"]
  a --> b
  b --> c
```

Status: built and proven: Refuse to replace another workflow; Write the nightly workflow; Workflow runs in CI. Built only: none. Planned: none.
Stops for the owner: none.
Proof: toy tests run its inline block. On this repo a manual run on GitHub passed all 64 rows; the first run failed 2 and opened 2 issues, and the passing run closed them. The nightly and tag triggers haven't fired yet.

#### `tests.py`: `list [--markdown|--tsv]`, `summary`, `issues [--write]`

```bash
python3 scripts/tests.py list
```

Every test in one fixed format, grouped by feature: the wiki page that holds the requirement a row guards, in page
order, then `Other` for rows that guard none. Each test shows its name, kind (`requirement` or `defect`), what it guards
(the requirement's ID and words, or the issue or pull request link with its recorded state and date, or the finding),
what it checks, when it runs (`both`, `nightly`, `by a person`), its last result and date, and when it was seen failing.
Plain output has one `FEATURE <name>` line per group; `--markdown` gives one table per feature; `--tsv` gives one line
per test for scripts. The wiki Tests lines, the health report and the GitHub run summary all use this format.

`summary --results FILE --took S` writes the GitHub run summary from a run's results (`id<TAB>state` lines, states
`PASS`, `FAIL`, `SKIPPED`, `KNOWN`); a malformed file or run time is refused with the line to fix. `issues --write`
reads each defect test's issue or pull request state with `gh` into `.loop/regression-issues.tsv`; if `gh` can't sign
in it says so and writes nothing, and a single link it can't read keeps its last recorded state. Only this command writes that file (no run does, so a state change on GitHub never
dirties a checkout); commit it with the re-rendered wiki Tests (`criteria.py render`).

## Narrow rows

A reusing run (`run --reuse`, the qa, ship and pr lanes) reruns a row only when a file it reads changed. A test script
says what it runs in its top comment block, and `lanes.py` follows from there without widening to folders.

```bash
#!/bin/bash
# reads: skills/workflow-health/scripts/health.py skills/workflow-setup/scripts/setup.py
# reads: skills/workflow-health/scripts/
# What this test checks ...
```

- Grammar: `# reads:` at the start of a line in the leading comment block; repo-relative paths, separated by spaces,
  unquoted; a trailing `/` marks a folder. Several lines add up. `# reads: skills/` means the script reads every skill
  (it stays wide); it is the per-script opt-out.
- What follows a declared file: a shell file adds the repo paths it names (no folder widening; comment lines and lines
  ending in `# lanes: no read` read nothing); a Python file adds its same-folder imports, every file whose base name it
  quotes (`"docs.py"`), and quoted folders of its own skill. A skill folder a shell file names (`M=.../scripts`) needs a
  declared file in it, and its files whose names appear in the script (`$M/board.py`, `import board`) are followed. A
  skill folder read as a whole needs that folder declared: a glob (`"$here"/skills/x/scripts/*.py`), a recursive or
  listing command (`grep -r`, `find`, `ls`, `cp -R`), the folder or its variable used bare (`"$d"`, `$d/sub`, also when
  `d` is set in a sourced file), or a `cd` into it followed by such a command. Naming a folder with `cd`, `mkdir`,
  `PYTHONPATH=` or `sys.path` reads nothing. A folder outside `skills/` stays a dependency as a whole. Not seen: a
  skill path behind another variable (`"$OLDPWD/skills/x"`); declare such reads by hand.
- A script that runs tools on this repo's own files (`cd "$here"`, `git -C "$here"`, `--root "$here"`) runs on every
  change: those tools may read any file. A table edit reruns the edited rows plus the rows that read this repo's
  `.loop/regression.tsv`. A deleted file anywhere outside the release and loop files means a full run.
- A row whose header cannot be worked out runs on every change (`ALWAYS <id>: <code> ...`). A script with no header
  keeps the wide mapping. `LANES_WIDE=1` forces the wide mapping for every row: the first step when a narrowed lane
  seems to miss a row. The first run after `lanes.py` or `narrow.py` changes is full: the record carries their hash.

```text
lanes_cli.py check [SCRIPT...]                 every header problem; default: each dev/toy/test-*.sh a row names
lanes_cli.py affected [--level L] PATH...      dependency impact: AFFECTED n of m rows (ids), ALWAYS/UNMAPPED/DELETED
lanes_cli.py deps COMMAND [--why PATH]         a row command's dependencies, or the chain of files to PATH
```

`affected` reads no record, so failed rows, ancestry and edited table rows (which a reusing run also reruns) are
outside it. All three take `--root DIR` (default: the git top level), exit 2 on a usage error and 1 on problems.

| Code | Means | Fix |
|---|---|---|
| `LANES-DECL-NONE` | A test script a row names has no header | Add `# reads:` with the skill files it runs |
| `LANES-DECL-MISSING` | A declared path does not exist | Fix or remove it |
| `LANES-DECL-PATTERN` | A `$`, `*` or `?` in a declared path | Declare files, or the globbed folder |
| `LANES-DECL-ESCAPE` | A declared path leaves the repo | Repo-relative paths only |
| `LANES-DECL-PLACE` | `# reads:` below the top comment block | Move it up |
| `LANES-DECL-FOLDER` | Names a skill folder, declares no file in it | Declare the files it runs from there |
| `LANES-DECL-GLOB` | Reads a skill folder as a whole without declaring it | Declare the folder |
| `LANES-DECL-FOLDER-UNBACKED` | Declares a skill folder it never globs or reads whole | Declare its files instead |
| `LANES-DECL-TREE` | Reads all of `skills/` without declaring `skills/` | Declare `skills/` (stays wide) |

**New test script, three steps:** write the header; `python3 scripts/lanes_cli.py check dev/toy/test-new.sh`; then
`python3 scripts/lanes_cli.py affected <a file it runs>` shows its rows. Register rows with `regression.py add ...
--level land`.

**Nightly read trace.** `bash dev/toy/check-reads.sh [ROW-ID...]` (row `lanes-trace`) runs each row under a Python
audit hook and fails a row whose run read a skill file outside its closure (`LANES-TRACE-UNDECLARED`, with the line
to add), whose Python launch the hook never saw (`LANES-TRACE-NOHOOK`), or whose command failed. It covers Python reads
only; bash reads are covered by the static rules above.
