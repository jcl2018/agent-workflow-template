<!-- workflow-docs -->
# Delivery

Skill: `workflow-delivery`. Takes one sentence to a pull request, judged by a fresh agent at `standard` and `full`.
Script: `skills/workflow-delivery/scripts/goal.py`.

## Commands

- `poc "<question>"`: answers a question about the repo and writes nothing. It ends with a `go` line and a queue line.
- `go "<goal>" --done "<line>" ... [--level minimum|quick|standard|full] [--touches "<file,file>"]`: freezes the done
  lines and runs the goal. In an interactive session it hands off to [Monitoring](Monitoring), so the governing session
  never builds.

## Levels

| Level | Steps | Fresh judge |
|---|---|---|
| `minimum` (default) | Build, checks | No |
| `quick` | Written plan, build, checks | No |
| `standard` | Short design, plan, build, checks | One, at the end |
| `full` | Adds a design review before the build | One, plus the review |

Changes to CI, auth or data are `standard` at least. The script raises `minimum` or `quick` to `standard` when
`--touches` or the diff hits a path in `risky_paths`.

## Done lines

Done lines are frozen when the goal starts. A wrong one needs a new goal. The judge reads the diff, the goal file and
the check results, and no other file in the repo, so write each line for those:

- Say what the change does, so the diff shows it or a named check passes on it.
- To compare with a file outside the diff, name a check that compares them, or one short quote for `## Evidence`.
- Keep the proof small. A documentation goal proves what the page says from the diff, plus a passing docs check, and
  doesn't ask for output of every command.

## goal.py

```text
new SLUG --here --goal TEXT --done LINE [--level L] [--touches A,B] [--release R]
queue SLUG --goal TEXT --done LINE [--level L] [--touches A,B]
step SLUG NAME [--note TEXT]      check SLUG      judge SLUG [--design]
verdict SLUG --file FILE [--design]      pr SLUG
wait SLUG --ask TEXT --words W [--words W]      answer SLUG
finding SLUG TEXT      show SLUG
```

A background agent runs `step`, `check`, `judge` (where the level needs it) and `pr` in order, and fills in
`## Verify by hand`. Failed checks, a failed or missing verdict and a failed design review each cost a try, even when
only the proof was missing. After 3 failed tries it files a finding in `.loop/findings.md` and stops with exit code 3.

`pr` pushes the branch, retrying twice, and opens the pull request. It refuses until the checks (and the judge, where
the level needs one) hold on this commit, and at `full` until the design review has passed. With `pr_bumps_version` on,
it first moves the last number of the version file once.

The fresh judge is given only the diff, the goal file and the check results, in an empty folder. The design review at
`full` is given only the goal file. Proof the checks don't print goes under `## Evidence` in the goal file. Commit it
and run `check` again, because `judge` refuses a commit the checks haven't passed.

## Example

From the goal's worktree, with `scripts/` in the skill's folder:

```bash
python3 scripts/goal.py check add-median
python3 scripts/goal.py judge add-median
python3 scripts/goal.py pr add-median
```
