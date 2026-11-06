# Findings

- Codex with this ChatGPT account rejects `gpt-5.4`, its configured default, and the mini models; `gpt-5.6-luna` works.
- Codex's `workspace-write` sandbox blocks writes to `.git` and outside the workspace. A goal run needs the git folder
  and the remote added as writable roots (see `dev/toy/run-goal.sh`).
- Codex runs a login shell that resets `PATH`, so a test double of `gh` has to be named in the prompt.
- `claude -p` flags such as `--allowedTools` and `--add-dir` take many values and swallow a trailing prompt. Use the
  `--flag=value` form, or send the prompt on standard input.
- `.loop/goals/<slug>.md` is committed on the goal's branch, so each pull request carries its goal file.
- A fresh judge only sees the goal file, the diff and the check output. On the first real run it failed two done lines
  for missing evidence, correctly. Goals now record such proof under `## Evidence`.
- A done line that depends on something after the pull request can't be judged. Done lines must be provable before it.
- Real repos differ from the toy: four-number versions, changelogs with bracket headings and an intro paragraph, tests
  outside `tests/`, a wiki with pages from another tool, and a pre-push hook that takes minutes.
- Several goals pushing at once can fail with a bare git error, and a plain re-push works. `goal.py pr` retries twice.
- `report` left out queued goals that were ready to start. It now lists them.
- Scripts are close to the 20 KB limit: `goal.py` 20,474 bytes, `watch.py` 19,928. The next feature needs a new script.
