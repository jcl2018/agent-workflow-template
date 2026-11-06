<!-- workflow-docs -->
# Delivery

Skill: `workflow-delivery`. Takes one sentence to a judged pull request. Script: `skills/workflow-delivery/scripts/goal.py`.

## Commands

- `poc "<question>"`: answers a question about the repo and writes nothing. It ends with a `go` line and a queue line.
- `go "<goal>" --done "<line>" ... [--level minimum|quick|standard|full]`: freezes the done lines and runs the goal. In an
  interactive session it hands off to [Monitoring](Monitoring), so the governing session never builds.

## Levels

| Level | Steps | Fresh judge |
|---|---|---|
| `minimum` (default) | Build, checks | No |
| `quick` | Written plan, build, checks | No |
| `standard` | Short design, plan, build, checks | One, at the end |
| `full` | Adds a design review before the build | One, plus the review |

Changes to CI, auth or data are `standard` at least.

## goal.py

```text
new SLUG --here --goal TEXT --done LINE [--level L] [--touches A,B]
queue SLUG --goal TEXT --done LINE [--level L] [--touches A,B]
step SLUG NAME [--note TEXT]      check SLUG      judge SLUG [--design]
verdict SLUG --file FILE [--design]      pr SLUG
wait SLUG --ask TEXT --words W [--words W]      answer SLUG
finding SLUG TEXT      show SLUG
```

A background agent runs `step`, `check`, `judge` and `pr` in order and fills in `## Verify by hand`. After 3 failed
tries it files a finding in `.loop/findings.md` and stops with exit code 3. `pr` pushes the branch and opens the pull
request, and refuses until the checks (and the judge, where the level needs one) hold on this commit.

## Example

```bash
python3 scripts/goal.py check add-median
python3 scripts/goal.py judge add-median
python3 scripts/goal.py pr add-median
```
