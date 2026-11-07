# Decisions

One line each, where the roadmap didn't say.

- Layout: `skills/workflow-<name>/` per skill, `skills/loop-files.md` as the shared file contract.
- Toy runs use a test double for `gh` (`dev/toy/fakegh`); only the real-repo check calls the real `gh`.
- A goal's run state lives in `<git common dir>/loop/`, so every worktree sees it and nothing extra is committed.
- `goal.py` counts a failed fresh-judge verdict as a try, the same as a failed check.
- The judge gets its evidence in an empty temporary folder, via standard input.
- `cut` refuses in a monitored batch unless `--user` is passed; the skill says to pass it only on the human's own words.
- `dev/package.sh` ships `skills/`, `listing.json` and `README.md` only.
- The version in a draft release comes from `VERSION`; with no file, the first release is 0.1.0.
- Starting goals moved from `monitor.py` to `watch.py`, so `monitor.py` only reads. `watch` replaces `start --wait`.
- `goal.py new` needs `--here`: a tool that can't run a background agent is the only reason to build in the governing session.
- A regression row never seen failing blocks `run`, and `red` proves it on a temporary copy of `HEAD`.
- The Actions workflow carries its own small runner, because skill scripts stay out of the repo.
- `mend` and `resume_on_limit` are off by default, since each spends the user's usage without asking.
- A level 2 design skill runs through `design.py`, detached, in an agent with tools. `goal.py` holds no skill code, and `judge --design` refuses while a skill can run, so the built-in review can't stand in for it.
