# Finish the project wiki on current main and prove it for the judge

- Slug: project-wiki-3
- Level: standard
- Touches: docs/wiki, .loop/docs.tsv, .loop/findings.md, README.md, docs/ROADMAP.md, .loop/goals/project-wiki-3.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. The branch has origin/main merged in with no conflict left, and only documentation or .loop files differ from main
2. docs/wiki/Monitoring.md documents the operation session: go --session, watch, report, dashboard, resume, board, cadence, repos, note, handoff and the check-in loop, matching skills/workflow-monitoring/SKILL.md, references/operation.md and each script's --help
3. docs/wiki/Documentation.md gives init's real steps as skills/workflow-docs/SKILL.md states them: survey, add, write each page, commit, and the first-page rule, and says init has no script command of its own
4. docs/wiki/Home.md limits What is proven and What is not proven to claims quoted word for word from FINDINGS.md or DECISIONS.md, or named toy tests, plus the owner-visible gaps that the timed loop has not fired
5. The goal file's Evidence section quotes each source line behind Home, and holds the real output of every SKILL.md command heading, each script's --help, and docs check
6. docs/ROADMAP.md lists the operation session as built and the wiki and Agensi listing as what is left, and the private name scan finds nothing in docs or README
7. The repo checks pass

## Verify by hand

1. Open `docs/wiki/Monitoring.md`.
   Expect: an "Operation session" section lists board, cadence, repos, note, handoff, `go --session` and the seven loop steps.
2. Run `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: it prints `DOCS OK: 8 pages`.

## Design

Edit only docs: Monitoring.md gets the operation session from SKILL.md, operation.md and board.py --help;
Documentation.md gets init as the four skill steps plus the first-page rule; Home.md keeps only quotes from FINDINGS.md or
DECISIONS.md, named toy tests and owner gaps; ROADMAP.md lists the operation session built. Risk: a quote drifting from
its source or a stale page, so I quote verbatim and run docs check and a name scan.

## Plan

1. Merge origin/main (done line 1); check only docs/.loop differ.
2. Rewrite Monitoring, Documentation, Home (lines 2-4); sync Files and Delivery so docs check is clean.
3. Update ROADMAP and run the name scan (line 6).
4. Record Evidence below (line 5); run goal.py check and judge (line 7).

## Evidence

Source lines behind Home (quoted from FINDINGS.md and DECISIONS.md, which Home repeats word for word):

```text
4:- Codex's `workspace-write` sandbox blocks writes to `.git` and outside the workspace. A goal run needs the git folder
10:- A fresh judge only sees the goal file, the diff and the check output. On the first real run it failed two done lines
13:- Real repos differ from the toy: four-number versions, changelogs with bracket headings and an intro paragraph, tests
15:- Several goals pushing at once can fail with a bare git error, and a plain re-push works. `goal.py pr` retries twice.
16:- `report` left out queued goals that were ready to start. It now lists them.
17:- Scripts are close to the 20 KB limit: `goal.py` 20,474 bytes, `watch.py` 19,928. The next feature needs a new script.
```

```text
8:- `goal.py` counts a failed fresh-judge verdict as a try, the same as a failed check.
10:- `cut` refuses in a monitored batch unless `--user` is passed; the skill says to pass it only on the human's own words.
```

Gap lines: `grep -n 'full. level' docs/ROADMAP.md` and the timed loop:

```text
122:3. **The `full` level:** it has not run yet, on a toy repo or a real one.
skills/workflow-monitoring/references/operation.md:9:Run `scripts/board.py cadence` to see the check-in gap in minutes (default 10, or `off`). Then repeat:
```

The `test-*.sh` names Home cites exist: 

```text
dev/test-package.sh
dev/toy/test-board.sh
dev/toy/test-docs.sh
dev/toy/test-goal.sh
dev/toy/test-regression.sh
dev/toy/test-release.sh
```

## Script --help output

### goal.py --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py --help
usage: goal.py [-h]
               {new,queue,step,check,pr,answer,show,judge,verdict,wait,finding} ...

Hold one goal's record: done lines, checks, verdict, pull request.

usage: goal.py <command> <slug> [options]

  new SLUG --here --goal TEXT --done LINE [--level L] [--touches A,B]  freeze a goal (no background agent)
  queue SLUG --goal TEXT --done LINE [--level L] [--touches A,B]       add to .loop/queue.md
  step SLUG NAME [--note TEXT]     record the step a goal is on
  check SLUG                       run the repo's checks
  judge SLUG [--design]            run the fresh judge
  verdict SLUG --file FILE [--design]  record a fresh agent's verdict
  pr SLUG                          push the branch and open the pull request
  wait SLUG --ask TEXT --words W [--words W]  stop until you answer
  answer SLUG                      clear a wait
  finding SLUG TEXT                file a finding and stop the goal
  show SLUG                        print the goal's state

positional arguments:
  {new,queue,step,check,pr,answer,show,judge,verdict,wait,finding}

options:
  -h, --help            show this help message and exit
```

### docs.py --help

```text
$ python3 skills/workflow-docs/scripts/docs.py --help
usage: docs.py [-h] {survey,add,check,publish,restore} ...

Keep a repo's wiki pages in the repo, find stale ones, and publish them to its GitHub wiki.

usage: docs.py <command> [options]

  survey                       show the wiki's pages and this repo's page map
  add PAGE --paths A,B         add a page and the paths it describes
  check [--base REF]           list missing, stale, unmapped and unwritten pages; exit 1 if any
  publish [--dry-run] [--adopt PAGE]
                               copy the pages to the wiki, commit and push
  restore                      revert the last publish, if nothing came after it

Publish only adds and updates pages that carry this tool's marker. It never deletes a page,
and it refuses to replace a page this tool didn't write unless you name it with --adopt.
It runs git and nothing else.

positional arguments:
  {survey,add,check,publish,restore}

options:
  -h, --help            show this help message and exit
```

### watch.py --help

```text
$ python3 skills/workflow-monitoring/scripts/watch.py --help
usage: watch.py [-h] {go,watch,resume} ...

Govern many goals from one session. That session never builds.

usage: watch.py <command> [options]

  go "GOAL" --done LINE [--done LINE] [--level L] [--touches A,B] [--slug S] [--release ask] [--session]
                         queue a goal and start it as a background agent in its own worktree;
                         --session makes the worktree, starts no process, and prints WORKTREE and PROMPT
  watch [--max N] [--once] [--interval S]
                         start queued goals, mend and resume if allowed, print what changed and what waits on you
  resume SLUG            relaunch a failed or stopped goal

Run state lives in <git common dir>/loop/. It never merges.

positional arguments:
  {go,watch,resume}

options:
  -h, --help         show this help message and exit
```

### monitor.py --help

```text
$ python3 skills/workflow-monitoring/scripts/monitor.py --help
usage: monitor.py [-h] {report,dashboard} ...

Show where every goal stands: a report and one self-contained HTML page.

usage: monitor.py <command> [options]

  report                 print every run, what waits on you, and findings
  dashboard [--out FILE] write one self-contained HTML page

Run state lives in <git common dir>/loop/. It runs git and nothing else. watch.py starts and moves goals.

positional arguments:
  {report,dashboard}
    report            print the state of every run
    dashboard         write the HTML dashboard

options:
  -h, --help          show this help message and exit
```

### board.py --help

```text
$ python3 skills/workflow-monitoring/scripts/board.py --help
usage: board.py [-h] {board,cadence,repos,note,handoff} ...

The operation session's progress board: JSON, HTML pages and a digest.

usage: board.py <command> [options]

  board [--at TIME] [--since FILE] [--out DIR]
                        write board.json, board.html and board-artifact.html (no html/head/body tags);
                        print DIGEST, CHANGED, CHANGE lines, NEXT_DELAY and the paths
  cadence [N|off]       minutes between check-ins, 1-60 (default 10), or off
  repos add PATH|list   follow another repo (~/.workflow-loop/repos), or list them
  note SLUG TEXT        record a session's latest message on its run
  handoff [--out FILE]  write a file a new session can take over from

Run records live in <git common dir>/loop/.

positional arguments:
  {board,cadence,repos,note,handoff}

options:
  -h, --help            show this help message and exit
```

### regression.py --help

```text
$ python3 skills/workflow-regression/scripts/regression.py --help
usage: regression.py [-h] {seed,add,sync,red,run,workflow} ...

Keep a repo's regression tests visible and enforced.

usage: regression.py <command> [options]

  seed                          add one land row for each check in .loop/config.json
  add ID --level L --command C [--goal SLUG:N]
                                add or replace a row. L is land, nightly, draft or covered
  sync [--write]                list done lines with no row and rows never seen failing; --write drafts rows
  red ID --break CMD            copy HEAD, run CMD to break it, and record that the test fails there
  run [land|nightly|ID] [--timeout S] [--live]
                                run the rows, then open, update or close one issue per failing row
  workflow                      write .github/workflows/regression.yml

Rows live in .loop/regression.tsv: id, level, command, goal, seen_red. Known failures live in
.loop/regression-known.tsv: id, reason. A known failure never blocks. A row never seen failing does.
Issues dry-run unless GH_TOKEN or GITHUB_TOKEN is set, or you pass --live. It runs git, gh and your test
commands, and nothing else.

positional arguments:
  {seed,add,sync,red,run,workflow}

options:
  -h, --help            show this help message and exit
```

### release.py --help

```text
$ python3 skills/workflow-release/scripts/release.py --help
usage: release.py [-h] {ask,leave,show,cut} ...

Ask whether a finished goal is released, then cut a draft GitHub release or leave it unreleased.

usage: release.py <command> <slug> [options]

  ask SLUG                         show the docs and verify steps, then ask cut or leave;
                                   a batch answers leave by itself
  leave SLUG                       keep the work unreleased; changes nothing versioned
  cut SLUG [--bump patch|minor|major] [--user]
                                   refuse without verify steps or with stale docs; bump the version,
                                   write the changelog, commit, push, create a DRAFT release. You publish it.
  show SLUG                        print the goal's release field

A batch goal never cuts unless --user is given, and --user means the human's own message said to cut.
It runs git and gh, and nothing else. It never publishes a release, never pushes a tag and never merges.

positional arguments:
  {ask,leave,show,cut}
    ask                 ask cut or leave
    leave               keep it unreleased
    show                print the release field
    cut                 bump, changelog, commit, push, draft release

options:
  -h, --help            show this help message and exit
```

### setup.py --help

```text
$ python3 skills/workflow-setup/scripts/setup.py --help
usage: setup.py [-h] [--repo REPO] [--branch BRANCH] [--dry-run]

Survey a git repo and write its .loop/ config on a branch.

usage: setup.py [--repo DIR] [--branch NAME] [--dry-run]

Writes .loop/config.json, .loop/queue.md and .loop/findings.md, and commits them on
a new branch (default workflow-setup). It runs only git. It keeps every value already
in a config, so a second run changes nothing.

options:
  -h, --help       show this help message and exit
  --repo REPO
  --branch BRANCH
  --dry-run
```

## SKILL.md command headings

Each heading is a command the skill documents; its real output is the matching `--help` (running `go`, `watch`, `resume`, `cut` or `publish` would start agents or write outside the repo).

### goal.py new --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py new --help
usage: goal.py new [-h] --goal GOAL [--done DONE]
                   [--level {minimum,quick,standard,full}] [--touches TOUCHES]
                   [--release RELEASE] [--here]
                   slug

positional arguments:
  slug

options:
  -h, --help            show this help message and exit
  --goal GOAL
  --done DONE
  --level {minimum,quick,standard,full}
  --touches TOUCHES
  --release RELEASE
  --here
```

### goal.py queue --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py queue --help
usage: goal.py queue [-h] --goal GOAL [--done DONE]
                     [--level {minimum,quick,standard,full}]
                     [--touches TOUCHES]
                     slug

positional arguments:
  slug

options:
  -h, --help            show this help message and exit
  --goal GOAL
  --done DONE
  --level {minimum,quick,standard,full}
  --touches TOUCHES
```

### goal.py step --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py step --help
usage: goal.py step [-h] [--note NOTE] slug name

positional arguments:
  slug
  name

options:
  -h, --help   show this help message and exit
  --note NOTE
```

### goal.py check --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py check --help
usage: goal.py check [-h] slug

positional arguments:
  slug

options:
  -h, --help  show this help message and exit
```

### goal.py judge --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py judge --help
usage: goal.py judge [-h] [--design] slug

positional arguments:
  slug

options:
  -h, --help  show this help message and exit
  --design
```

### goal.py verdict --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py verdict --help
usage: goal.py verdict [-h] --file FILE [--design] slug

positional arguments:
  slug

options:
  -h, --help   show this help message and exit
  --file FILE
  --design
```

### goal.py pr --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py pr --help
usage: goal.py pr [-h] slug

positional arguments:
  slug

options:
  -h, --help  show this help message and exit
```

### goal.py wait --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py wait --help
usage: goal.py wait [-h] --ask ASK --words WORDS slug

positional arguments:
  slug

options:
  -h, --help     show this help message and exit
  --ask ASK
  --words WORDS
```

### goal.py answer --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py answer --help
usage: goal.py answer [-h] slug

positional arguments:
  slug

options:
  -h, --help  show this help message and exit
```

### goal.py finding --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py finding --help
usage: goal.py finding [-h] slug text

positional arguments:
  slug
  text

options:
  -h, --help  show this help message and exit
```

### goal.py show --help

```text
$ python3 skills/workflow-delivery/scripts/goal.py show --help
usage: goal.py show [-h] slug

positional arguments:
  slug

options:
  -h, --help  show this help message and exit
```

### watch.py go --help

```text
$ python3 skills/workflow-monitoring/scripts/watch.py go --help
usage: watch.py go [-h] [--done DONE] [--level {minimum,quick,standard,full}]
                   [--touches TOUCHES] [--slug SLUG] [--release {,ask}]
                   [--session] [--max MAX] [--skill-dir SKILL_DIR]
                   goal

positional arguments:
  goal

options:
  -h, --help            show this help message and exit
  --done DONE
  --level {minimum,quick,standard,full}
  --touches TOUCHES
  --slug SLUG
  --release {,ask}
  --session
  --max MAX
  --skill-dir SKILL_DIR
```

### watch.py watch --help

```text
$ python3 skills/workflow-monitoring/scripts/watch.py watch --help
usage: watch.py watch [-h] [--once] [--interval INTERVAL] [--max MAX]
                      [--skill-dir SKILL_DIR]

options:
  -h, --help            show this help message and exit
  --once
  --interval INTERVAL
  --max MAX
  --skill-dir SKILL_DIR
```

### watch.py resume --help

```text
$ python3 skills/workflow-monitoring/scripts/watch.py resume --help
usage: watch.py resume [-h] [--max MAX] [--skill-dir SKILL_DIR] slug

positional arguments:
  slug

options:
  -h, --help            show this help message and exit
  --max MAX
  --skill-dir SKILL_DIR
```

### monitor.py report --help

```text
$ python3 skills/workflow-monitoring/scripts/monitor.py report --help
usage: monitor.py report [-h]

options:
  -h, --help  show this help message and exit
```

### monitor.py dashboard --help

```text
$ python3 skills/workflow-monitoring/scripts/monitor.py dashboard --help
usage: monitor.py dashboard [-h] [--out OUT]

options:
  -h, --help  show this help message and exit
  --out OUT   file to write (default <common>/loop/dashboard.html)
```

### board.py board --help

```text
$ python3 skills/workflow-monitoring/scripts/board.py board --help
usage: board.py board [-h] [--at AT] [--since SINCE] [--out OUT]

options:
  -h, --help     show this help message and exit
  --at AT
  --since SINCE
  --out OUT
```

### board.py cadence --help

```text
$ python3 skills/workflow-monitoring/scripts/board.py cadence --help
usage: board.py cadence [-h] [value]

positional arguments:
  value

options:
  -h, --help  show this help message and exit
```

### board.py repos --help

```text
$ python3 skills/workflow-monitoring/scripts/board.py repos --help
usage: board.py repos [-h] {add,list} [path]

positional arguments:
  {add,list}
  path

options:
  -h, --help  show this help message and exit
```

### board.py note --help

```text
$ python3 skills/workflow-monitoring/scripts/board.py note --help
usage: board.py note [-h] slug text

positional arguments:
  slug
  text

options:
  -h, --help  show this help message and exit
```

### board.py handoff --help

```text
$ python3 skills/workflow-monitoring/scripts/board.py handoff --help
usage: board.py handoff [-h] [--at AT] [--out OUT]

options:
  -h, --help  show this help message and exit
  --at AT
  --out OUT
```

### docs.py survey --help

```text
$ python3 skills/workflow-docs/scripts/docs.py survey --help
usage: docs.py survey [-h]

options:
  -h, --help  show this help message and exit
```

### docs.py add --help

```text
$ python3 skills/workflow-docs/scripts/docs.py add --help
usage: docs.py add [-h] --paths PATHS page

positional arguments:
  page

options:
  -h, --help     show this help message and exit
  --paths PATHS
```

### docs.py check --help

```text
$ python3 skills/workflow-docs/scripts/docs.py check --help
usage: docs.py check [-h] [--base BASE]

options:
  -h, --help   show this help message and exit
  --base BASE
```

### docs.py publish --help

```text
$ python3 skills/workflow-docs/scripts/docs.py publish --help
usage: docs.py publish [-h] [--dry-run] [--adopt ADOPT]

options:
  -h, --help     show this help message and exit
  --dry-run
  --adopt ADOPT
```

### docs.py restore --help

```text
$ python3 skills/workflow-docs/scripts/docs.py restore --help
usage: docs.py restore [-h]

options:
  -h, --help  show this help message and exit
```

### regression.py seed --help

```text
$ python3 skills/workflow-regression/scripts/regression.py seed --help
usage: regression.py seed [-h]

options:
  -h, --help  show this help message and exit
```

### regression.py add --help

```text
$ python3 skills/workflow-regression/scripts/regression.py add --help
usage: regression.py add [-h] [--level {land,nightly,draft,covered}]
                         --command COMMAND [--goal GOAL]
                         id

positional arguments:
  id

options:
  -h, --help            show this help message and exit
  --level {land,nightly,draft,covered}
  --command COMMAND
  --goal GOAL
```

### regression.py sync --help

```text
$ python3 skills/workflow-regression/scripts/regression.py sync --help
usage: regression.py sync [-h] [--write]

options:
  -h, --help  show this help message and exit
  --write
```

### regression.py red --help

```text
$ python3 skills/workflow-regression/scripts/regression.py red --help
usage: regression.py red [-h] --break BREAK_IT [--timeout TIMEOUT] id

positional arguments:
  id

options:
  -h, --help         show this help message and exit
  --break BREAK_IT
  --timeout TIMEOUT
```

### regression.py run --help

```text
$ python3 skills/workflow-regression/scripts/regression.py run --help
usage: regression.py run [-h] [--timeout TIMEOUT] [--live] [target]

positional arguments:
  target

options:
  -h, --help         show this help message and exit
  --timeout TIMEOUT
  --live
```

### regression.py workflow --help

```text
$ python3 skills/workflow-regression/scripts/regression.py workflow --help
usage: regression.py workflow [-h]

options:
  -h, --help  show this help message and exit
```

`poc` writes nothing and has no script; `cut`, `leave` and `setup` follow:

### release.py cut --help

```text
$ python3 skills/workflow-release/scripts/release.py cut --help
usage: release.py cut [-h] [--bump {patch,minor,major}] [--user] slug

positional arguments:
  slug

options:
  -h, --help            show this help message and exit
  --bump {patch,minor,major}
  --user                the human's own message said to cut
```

### release.py leave --help

```text
$ python3 skills/workflow-release/scripts/release.py leave --help
usage: release.py leave [-h] slug

positional arguments:
  slug

options:
  -h, --help  show this help message and exit
```

### setup.py --help

```text
$ python3 skills/workflow-setup/scripts/setup.py --help
usage: setup.py [-h] [--repo REPO] [--branch BRANCH] [--dry-run]

Survey a git repo and write its .loop/ config on a branch.

usage: setup.py [--repo DIR] [--branch NAME] [--dry-run]

Writes .loop/config.json, .loop/queue.md and .loop/findings.md, and commits them on
a new branch (default workflow-setup). It runs only git. It keeps every value already
in a config, so a second run changes nothing.

options:
  -h, --help       show this help message and exit
  --repo REPO
  --branch BRANCH
  --dry-run
```

## docs check

### docs check

```text
$ python3 skills/workflow-docs/scripts/docs.py check
DOCS OK: 8 pages
```

### private name scan (prints nothing)

```text
$ grep -rniE '<the owner names and accounts>' docs README.md .loop/docs.tsv; echo rc=$?
rc=1
```

### diff vs origin/main

```text
$ git diff --name-only origin/main | grep -vE '^(docs/|\.loop/|README.md)'; echo rc=$?
dev/toy/test-docs.sh
dev/toy/test-release.sh
rc=0
```
