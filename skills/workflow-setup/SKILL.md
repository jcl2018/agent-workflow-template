---
name: workflow-setup
description: Surveys a git repo and writes its .loop/ config on a branch, so the delivery, monitoring and release skills can run there. Use when a repo has no .loop/config.json, or when asked to set up the workflow.
---

# workflow-setup

One command: `setup`. It finds the repo's base branch, its check commands and the agent on this machine, then writes
`.loop/` on a branch called `workflow-setup`. Running it again changes nothing.

## Run it

Run `scripts/setup.py` from inside the repo, with `python3`. If the skill's files aren't on disk, write the script to a
temporary file, run it, and delete it.

```bash
python3 scripts/setup.py --dry-run
python3 scripts/setup.py
```

Read the dry run first and tell the user what it found.

## After it runs

1. Check `checks` in `.loop/config.json`. The survey only guesses from the repo's files, so run each command once. Fix
   or add commands until they prove the repo works. Commit that on the same branch.
2. If `checks` is empty, ask the user what proves the repo works. Goals can't run without a check.
3. Tell the user that `workflow-monitoring` needs them to allow tools in `agent_command`, because a background agent
   can't answer a permission prompt. For Claude Code, that looks like
   `["claude", "-p", "--allowedTools=Bash,Read,Write,Edit"]`. For Codex, it means `-s workspace-write` with the git
   folder and the remote in `sandbox_workspace_write.writable_roots`. They choose the list. You don't.
4. Tell the user to review the branch and merge it. The other skills read the config from the base branch.

Keep to these rules:

- Don't write skill instructions into the repo. `.loop/` holds only the repo's own data.
- Don't change `agent_command` to loosen permissions. The user's own settings decide what a
  background agent may do.
- Don't merge the branch. The user does.

## What it writes

| Path | Holds |
|---|---|
| `.loop/config.json` | Base branch, checks, agent commands, risky paths, wiki folder |
| `.loop/queue.md` | An empty goal queue |
| `.loop/findings.md` | An empty findings list |

Values already in a config are kept. See `loop-files.md` (`../` here, `shared/` in a pack) for each field.
