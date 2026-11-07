# Fix the wiki's two errors and record proof for the judge

- Slug: project-wiki-2
- Level: standard
- Touches: docs/wiki, .loop/goals/project-wiki-2.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs/wiki/Documentation.md names the init command and what it does, matching skills/workflow-docs/SKILL.md
2. docs/wiki/Home.md says dev/toy/test-monitoring.sh exists but was not re-run after the commands changed, and that dev/toy/test-goal.sh covers monitoring logic
3. The goal file's Evidence section holds the real output of: every SKILL.md command heading, each script's --help, ls dev dev/toy, and the FINDINGS.md or DECISIONS.md line behind each Home claim
4. Each command and flag on the feature pages appears in that evidence, and any that does not is removed from the page
5. dev/toy/test-goal.sh and dev/toy/test-release.sh pass with LOOP_BATCH=1 set in the environment
6. The repo checks pass

## Verify by hand

1. Open docs/wiki/Documentation.md.
   Expect: an Init section names `init` and says it runs `survey` then `add`.
2. Open docs/wiki/Home.md.
   Expect: it says test-monitoring.sh was not re-run and test-goal.sh covers monitoring logic.

## Design

Edit two wiki pages, record evidence; test-release.sh must unset inherited LOOP_BATCH. Risk: stale claims.

## Plan

1. Edit pages (done lines 1,2,4). 2. Evidence (3). 3. Run toy tests with LOOP_BATCH=1 (5). 4. goal.py check (6).

## Evidence

### SKILL.md command headings (grep -n '^## `' skills/*/SKILL.md)
```
skills/workflow-delivery/SKILL.md:11:## `poc "<question>"`
skills/workflow-delivery/SKILL.md:27:## `go "<goal>" --done "<line>" ... [--level minimum|quick|standard|full]`
skills/workflow-monitoring/SKILL.md:21:## `go "<goal>" --done "<line>" ... [--level L] [--touches A,B] [--slug S] [--release ask]`
skills/workflow-monitoring/SKILL.md:30:## `watch [--max N] [--once] [--interval S]`
skills/workflow-monitoring/SKILL.md:65:## `report`
skills/workflow-monitoring/SKILL.md:82:## `dashboard [--out FILE]`
skills/workflow-monitoring/SKILL.md:95:## `resume SLUG`
skills/workflow-regression/SKILL.md:20:## `seed`
skills/workflow-regression/SKILL.md:28:## `add <id> --level <level> --command "<command>" [--goal <slug>:<n>]`
skills/workflow-regression/SKILL.md:33:## `sync [--write]`
skills/workflow-regression/SKILL.md:43:## `red <id> --break "<command>"`
skills/workflow-regression/SKILL.md:55:## `run [land|nightly|<id>] [--timeout S] [--live]`
skills/workflow-regression/SKILL.md:77:## `workflow`
skills/workflow-docs/SKILL.md:15:## `init`
skills/workflow-docs/SKILL.md:37:## `check`
skills/workflow-docs/SKILL.md:52:## `publish`
skills/workflow-docs/SKILL.md:68:## `restore`
```
### Each script's --help

#### python3 skills/workflow-delivery/scripts/goal.py --help
```
usage: goal.py [-h]
               {new,queue,step,check,pr,answer,show,judge,verdict,wait,finding} ...

Hold one goal's record: its frozen done lines, checks, judge verdict and pull request.

usage: goal.py <command> <slug> [options]

  new SLUG --here --goal TEXT --done LINE [--level L] [--touches A,B]  only when no background agent can run it
  queue SLUG --goal TEXT --done LINE [--level L] [--touches A,B]       add a line to .loop/queue.md
  step SLUG NAME [--note TEXT]     record the step a goal is on
  check SLUG                       run the repo's checks and record the result
  judge SLUG [--design]            pack the evidence and run the fresh judge
  verdict SLUG --file FILE [--design]  record a verdict a fresh agent wrote
  pr SLUG                          push the branch and open the pull request
  wait SLUG --ask TEXT --words W [--words W]  stop until you answer
  answer SLUG                      clear a wait
  finding SLUG TEXT                file a finding and stop the goal
  show SLUG                        print the goal's state

It runs only git, gh, and your check and judge commands.

positional arguments:
  {new,queue,step,check,pr,answer,show,judge,verdict,wait,finding}

options:
  -h, --help            show this help message and exit
```

#### python3 skills/workflow-docs/scripts/docs.py --help
```
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

#### python3 skills/workflow-monitoring/scripts/monitor.py --help
```
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

#### python3 skills/workflow-monitoring/scripts/watch.py --help
```
usage: watch.py [-h] {go,watch,resume} ...

Govern many goals from one session. That session never builds.

usage: watch.py <command> [options]

  go "GOAL" --done LINE [--done LINE] [--level L] [--touches A,B] [--slug S] [--release ask]
                         queue a goal and start it as a background agent in its own worktree
  watch [--max N] [--once] [--interval S]
                         start queued goals, mend and resume if the config says so, print what changed
                         and what waits on you, and end when nothing is left
  resume SLUG            relaunch a failed or stopped goal

Run state lives in <git common dir>/loop/. It runs git and your agent_command, and nothing else. It never
changes your permission settings and never merges.

positional arguments:
  {go,watch,resume}

options:
  -h, --help         show this help message and exit
```

#### python3 skills/workflow-regression/scripts/regression.py --help
```
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

#### python3 skills/workflow-release/scripts/release.py --help
```
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

#### python3 skills/workflow-setup/scripts/setup.py --help
```
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

### ls dev dev/toy
```
dev:
install-local.sh
package.py
package.sh
test-package.sh
toy

dev/toy:
fakegh
make.sh
repo
run-goal.sh
test-docs.sh
test-goal.sh
test-govern.sh
test-monitoring.sh
test-regression.sh
test-release.sh
```

### Home claims
```
FINDINGS.md:3:- Codex with this ChatGPT account rejects `gpt-5.4`, its configured default, and the mini models; `gpt-5.6-luna` works.
FINDINGS.md:4:- Codex's `workspace-write` sandbox blocks writes to `.git` and outside the workspace. A goal run needs the git folder
FINDINGS.md:6:- Codex runs a login shell that resets `PATH`, so a test double of `gh` has to be named in the prompt.
FINDINGS.md:10:- A fresh judge only sees the goal file, the diff and the check output. On the first real run it failed two done lines
FINDINGS.md:13:- Real repos differ from the toy: four-number versions, changelogs with bracket headings and an intro paragraph, tests
FINDINGS.md:15:- Several goals pushing at once can fail with a bare git error, and a plain re-push works. `goal.py pr` retries twice.
FINDINGS.md:17:- Scripts are close to the 20 KB limit: `goal.py` 20,474 bytes, `watch.py` 19,928. The next feature needs a new script.
DECISIONS.md:8:- `goal.py` counts a failed fresh-judge verdict as a try, the same as a failed check.
DECISIONS.md:10:- `cut` refuses in a monitored batch unless `--user` is passed; the skill says to pass it only on the human's own words.
2:# Test levels, the queue command, version bumps and the governing watch with a fake agent. No model is called.
9:W="python3 $here/skills/workflow-monitoring/scripts/watch.py"
10:M="python3 $here/skills/workflow-monitoring/scripts/monitor.py"
# WARNING: this calls the REAL claude CLI (model haiku by default, set MODEL=...) for about six short goals, which costs
# money and takes several minutes. gh is faked by dev/toy/fakegh; the real gh is never called. Dev only; never packaged.
```

### Toy tests with LOOP_BATCH=1
```
test-goal.sh: ALL PASS (rc 0)
test-release.sh: ALL PASS (rc 0)
```

Every command and flag on the feature pages (Delivery, Monitoring, Regression, Release, Documentation, Getting-started) appears in the help text above; none were removed.

### Getting-started and Regression examples (grep output)
```
30:   `["claude", "-p", "--allowedTools=Bash,Read,Write,Edit"]`. They choose the list. You don't.
11:  "agent_command": [
12-    "claude",
13-    "-p",
14-    "--model=sonnet",
15-    "--allowedTools=Bash,Read,Write,Edit,Skill"
16-  ],
48:python3 scripts/regression.py red check-1 --break "sed -i.bak 's/return a + b/return a - b/' calc.py"
skills/workflow-setup/SKILL.md:17:python3 scripts/setup.py --dry-run
skills/workflow-setup/scripts/setup.py:4:usage: setup.py [--repo DIR] [--branch NAME] [--dry-run]
skills/workflow-setup/scripts/setup.py:120:    parser.add_argument("--dry-run", action="store_true")
5:here=$(cd "$(dirname "$0")/.." && pwd); to=${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}
10:  ln -sfn "$skill" "$to/$name"; echo "LINKED $name"
```

Correction: the flags `-p` and `--allowedTools` (Getting-started) and the `sed -i.bak` break command (Regression) are backed by the lines above, so they stay.
