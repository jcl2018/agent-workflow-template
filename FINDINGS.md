# Findings

- Codex with this ChatGPT account rejects `gpt-5.4`, its configured default, and the mini models; `gpt-5.6-luna` works.
- Codex's `workspace-write` sandbox blocks writes to `.git` and outside the workspace. A goal run needs the git folder
  and the remote added as writable roots (see `dev/toy/run-goal.sh`).
- Codex runs a login shell that resets `PATH`, so a test double of `gh` has to be named in the prompt.
- `claude -p` flags such as `--allowedTools` and `--add-dir` take many values and swallow a trailing prompt. Use the
  `--flag=value` form, or send the prompt on standard input.
- `.loop/goals/<slug>.md` is committed on the goal's branch, so each pull request carries its goal file.
