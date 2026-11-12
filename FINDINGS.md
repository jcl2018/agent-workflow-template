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
2026-11-12 (migration, lesson 1): Native Windows broke again and again: fcntl (#1395), os.getuid, os.O_NOFOLLOW, os.killpg and os.kill(pid, 0) sending Ctrl+C (#1396, fixed by PR 2616), tmp_for looping at the drive root, signal.SIGHUP, rows run through cmd.exe, bash toy tests. Main then reintroduced fcntl in goal.py, because nothing checks Windows on merge. Tracked: #2871, with #1397 and #1408.
2026-11-12 (migration, lesson 2): Workers belong in app sessions, not background processes. Without a session_command, operate.py send only writes an inbox, so a held worker looks silent or stuck. Tracked: #1404 (never fall back to a background worker) and #2872 (the board says a message waits in an inbox).
2026-11-12 (migration, lesson 3): Over Remote Control the app cannot start sessions, local or cloud. An idle session pool plus messaging works around it: the pool sessions are bound to goals by message. Tracked: #1404 names the case; the pool is shipped.
2026-11-12 (migration, lesson 4): A private repo cannot rely on GitHub Actions, so local lanes that post statuses are the default for it. Fixed and documented: v0.27.26 (a private repo's pr lane posts its real result under every required check) and the Automation page (AUT-1, PR 2152).
2026-11-12 (migration, lesson 5): Handing a goal to another machine loses its run state (the step records stay behind), and a branch the handover called pushed was not pushed. Tracked: #2851, with the handover issue #2849.
2026-11-12 (migration, lesson 6): The govern hook refused the operation session's own memory notes outside every repo (#2850), and setup with --reply-hook plus --govern-hook installed the hook twice. Tracked: #2850 and #2873.
2026-11-12 (migration, lesson 7): Un-reviewing a locked requirement needs the owner's own sentence; a relayed single letter was rightly refused, but the rule was learned from the refusal. Setup should say so up front. Tracked: #2874, related #133.
2026-11-12 (migration, lesson 8): A new row cannot be seen red on a platform that cannot run it (the Windows PC), and skipped-unproven rows burned tries. Fixed: REG-10 (such rows wait, no try). Tracked: #2865 (goal.py pr's lane gate reuses qa's run).
2026-11-12 (migration, lesson 9): With auto_merge on, the release merges before the operation session has seen the diff, and several merges needed a follow-up. A review hold needs a decision. Tracked: #2875.
2026-11-12 (migration, lesson 10): Two sessions ran the same scheduled routine at once on the Mac. A routine needs a lock per repo and name. Tracked: #2876.
2026-11-12 (migration, lesson 11): The Gmail connector was read-only until it was reconnected, and nothing noticed. The setup connector probe should test write scope where a PRD writes. Tracked: #1410 (comment added).
2026-11-12 (migration, lesson 12): A repo reads 'template version unknown' until update --apply, because adoption does not stamp it. Tracked: #2877, related #1409.
