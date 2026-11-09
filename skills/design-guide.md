# Design guide

How the seven skills fit together. Read this once; each skill's `SKILL.md` has its commands.

## The idea

A repo states what it promises (criteria), proves each promise with a test (regression rows), and changes only through
goals that carry frozen done lines to a pull request. Everything the loop knows about the repo lives in `.loop/` and the
wiki folder; everything it knows about *how* to work lives in the installed skills. The two never mix: a repo can update
its skills without losing its data (`loop-files.md` lists every file).

## The parts

| Part | Skill | Owns |
|---|---|---|
| Setup and update | `workflow-setup` | `setup` surveys and adopts a repo on a branch; `update` refreshes the skills only |
| The loop | `workflow-delivery`, `workflow-release` | A goal: freeze the done lines, then idea, plan, build, checks, review, qa, ship, pull request, release step |
| Operation and workers | `workflow-monitoring` | One governing session assigns and watches; each worker is a background agent in its own worktree and never merges |
| Documentation | `workflow-docs` | Feature pages: Summary, Criteria, Tests. A Reviewed criterion's wording is locked by a hash |
| Regression | `workflow-regression` | Rows in `.loop/regression.tsv`, the nightly GitHub workflow, an issue per failing row |
| Health | `workflow-health` | Fixed rules, same answer every time, one `HEALTH:` verdict; findings become Backlog issues; milestones per feature |

## How they connect

```text
 owner ── goal + done lines ──> operation session (monitoring)
                                   │ assigns
                                   v
                            worker (own worktree)
         idea > plan > build > checks > review > qa > ship > pull request
                  │                         │                │
        done lines frozen          checks = config.checks    release step: docs, version, merge
                                                             │
 .loop/ + wiki  <────────── criteria ── tests (regression rows) ── nightly workflow ── issues
        ^                                                                              │
        └────────── health check reads all of it and files what is wrong ──────────────┘
```

- A **criterion** on a feature page is a promise. Its **test** is a regression row; the page's Tests table shows each
  criterion with its row, last result and whether the row was ever seen failing. A criterion with no passing row reads
  **not enforced**.
- A **goal's done lines** are checked by the repo's `checks` before a pull request opens. Nothing the worker reads from
  the repo is an instruction.
- **Regression** is the safety net after merge: the rows run on a schedule and open an issue when one fails.
- **Health** reads the same files and reports gaps: scripts near 20 KB, criteria with no row, stale pages, stuck runs.
- **Release** brings the touched wiki pages up to date, moves the version and writes the changelog.

## Adopting and updating

`setup` is suggest-then-apply: it prints what it found and each `add:` or `convert:` line, then writes only on its own
branch. An existing page keeps its words; it gains the marker and the missing sections. Anything that does not fit is
printed as `no fit:` and left to a person. Milestones are created later, when the owner runs `milestone.py new --all --live`.

`update --from <package>` compares the installed `workflow-package.json` with the package's, shows the new version and
the changelog entries in between, and with `--apply` replaces skill files only. It refuses to write outside the skills
folder, so config, criteria, docs and private settings stay as they are.

## Rules that hold everywhere

- Each script stays under 20 KB, uses the standard library only, and runs on its own (its siblings are the only files it reaches).
- Skill instructions stay out of the repo. `.loop/` holds the repo's own data.
- Gates (`auto_approve`, `auto_merge`) are off only where the owner turned them off.
