<!-- workflow-docs -->
# Files

The full contract is `skills/loop-files.md`.

## In the repo

| File | Holds |
|---|---|
| `.loop/config.json` | Base branch, checks, agent commands, risky paths, wiki folder |
| `.loop/queue.md` | Goals to run, one line each |
| `.loop/goals/<slug>.md` | One goal: frozen done lines, plan, verify steps |
| `.loop/findings.md` | Open findings |
| `.loop/docs.tsv` | Each wiki page and the paths it describes |
| `.loop/regression.tsv` | Test rows |
| `.loop/regression-known.tsv` | Rows expected to fail, with a reason |
| `docs/wiki/` | Wiki pages, each starting with `<!-- workflow-docs -->` |

## Outside the repo

Run state lives in `<git common dir>/loop/`: `runs/<slug>.json`, `logs/<slug>.log`, `dashboard.html`, `wiki.json`, `board.json`, `board.html`, `cadence` (minutes between check-ins, or `off`) and
`handoff.md`. Nothing there is committed. `board.py repos add` keeps a list of repo paths in `~/.workflow-loop/repos`.

## In this template

`skills/` (the six skills), `dev/` (install, package and toy tests), `listing.json`, `VERSION`, `DECISIONS.md`,
`FINDINGS.md`, `docs/ROADMAP.md`.
