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
- Scripts run alone, so a feature that won't fit needs a new script the agent runs: `goal.py` 19,461 bytes, `watch.py` 20,466.
- A skill pasted into the toolless judge doesn't run: the first level 2 review took 18 seconds and did none of its phases.
- A real design skill needs tools, the repo and minutes: one full unattended pass on a toy goal took 9 minutes and $2.74.
- In a goal run the same skill gave no verdict on the first try and stopped at its own phase guard on the second, so a pull request says `full` or `condensed`.
- Codex ran a level 0 toy goal from design to pull request with no failed try, using `gpt-5.6-luna` and a test double of `gh`.
- Every regression row passes with an empty home folder, no git identity and a token set, on a Mac. A real run on GitHub is still unproven.
- A monitored Codex goal needs `-s workspace-write` with the git folder and remote as writable roots, and `setup`'s default `codex exec` has neither.
- In a pack, a file outside every skill folder reaches no skill unless it's under `shared/`, so the ZIP moves `loop-files.md` there.
- The first regression workflow run on GitHub failed 2 rows: one needed an agent on the machine, and one looked for a renamed test line.
- `cut` lists commits not yet on the base branch, so a pull request merged just before it gives an empty changelog that says "No code changes".
- The first real flow run ran the idea step unattended in about 75 seconds and stopped with three owner items, among them the design approval its unattended mode never gives. So every goal waits on the owner at least once before it builds.
