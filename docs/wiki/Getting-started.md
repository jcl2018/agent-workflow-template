<!-- workflow-docs -->
# Getting started

From install to one finished goal.

## 1. Install

```bash
dev/install-local.sh
```

It links each `skills/workflow-*` folder into `~/.claude/skills` (or `$CLAUDE_SKILLS_DIR`) and prints
`LINKED <name>`. It skips a name that is already a real folder. For another agent, copy the `skills/` folders into its
skills folder.

## 2. Set up your repo

```text
/workflow-setup
```

It writes `.loop/config.json`, `.loop/queue.md` and `.loop/findings.md` on a branch called `workflow-setup`. Preview
with `python3 scripts/setup.py --dry-run`, using the path to the skill's folder. Then:

1. Run each command in `checks` once, and fix or add commands until they prove the repo works.
2. Allow the tools a background agent needs in `agent_command`, for example
   `["claude", "-p", "--allowedTools=Bash,Read,Write,Edit"]`. You choose the list.
3. Review the branch and merge it yourself. The other skills read the config from the base branch.

## 3. Start a goal

From the main checkout, on the base branch:

```text
/workflow-monitoring go "add result caching" --done "repeat searches are served from the cache"
```

Done lines are frozen once the goal starts, so make each one provable before the pull request, from the diff, the goal
file and the check results (see [Delivery](Delivery)). The level is `minimum` unless you add `--level`, and only
`standard` and `full` get a fresh judge. To try an idea first, use `/workflow-delivery poc "<question>"`, which writes
nothing.

## 4. Watch it

```text
/workflow-monitoring watch
```

It starts queued goals in their own worktrees, prints what changed, and ends with what waits on you. Use `report` for a
snapshot.

## 5. Review

The goal ends at a pull request. A monitored goal answers `leave` by itself, unless you started it with
`--release ask`. Then it waits for `cut <slug>` or `leave <slug>` (see [Release](Release)). Answer before you merge,
because `cut` commits on the goal's branch. Review and merge the pull request yourself; nothing here merges.
