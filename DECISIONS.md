# Decisions

One line each, where the roadmap didn't say.

- Layout: `skills/workflow-<name>/` per skill, `skills/loop-files.md` as the shared file contract.
- Toy runs use a test double for `gh` (`dev/toy/fakegh`); only the real-repo check calls the real `gh`.
- A goal's run state lives in `<git common dir>/loop/`, so every worktree sees it and nothing extra is committed.
- `dev/package.sh` ships `skills/`, `listing.json` and `README.md` only.
- Starting goals moved from `monitor.py` to `watch.py`, so `monitor.py` only reads. `watch` replaces `start --wait`.
- `goal.py new` needs `--here`: a tool that can't run a background agent is the only reason to build in the governing session.
- A regression row never seen failing blocks `run`, and `red` proves it on a temporary copy of `HEAD`.
- The Actions workflow carries its own small runner, because skill scripts stay out of the repo.
- `mend` and `resume_on_limit` are off by default, since each spends the user's usage without asking.
- Delivery is a wrapper around the owner's own skill suite: one flow, no levels, no judge of its own. A private flow file names the skills, and a probe must prove their unattended mode before any step runs, so a ship skill never runs by a person's rules.
- Nothing a skill leaves for the owner is approved by an agent. It waits under Waiting on you, and `pr` waits for it.
- POCs are deleted: the suite's idea skill covers trying an idea. `workflow-release` stays, as the owner's place for routines before a release.
