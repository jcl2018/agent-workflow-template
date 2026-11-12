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
- 2026-11-12, regression time: the loop runs only the affected rows within `test_budget_minutes`; the full suite runs on the schedule, because a full suite in every goal outgrows the budget. Fixed `workflow-delivery` SKILL.md and its commands.md; REG-7 stands, DEL-6 reworded.
- 2026-11-12, one owner per artifact: MON-3 owns the live board (report, dashboard, artifact) and MON-4 holds its layout; MON-5 owns the check-in reply and never prints the board, because two layouts for one artifact drifted apart. Third layout removed: MON-3, MON-4, MON-5.
- 2026-11-12, GitHub writes need `--live`: a token alone never writes; the scheduled workflows pass `--live`, because the safer default is a preview. Reworded GRD-5, REG-5, AUT-5, HLT-4; defect #2614 filed for the code, which still writes on a token alone.
- 2026-11-12, Guardrails is an index: it points to the owning ids (DEL-8, REG-7, DEL-9, SET-8, MON-7, MON-8) and restates none of their text, because two copies of a rule disagree. Reworded GRD-1 and the overlapping bullets of GRD-2, GRD-3, GRD-4, GRD-8.
- 2026-11-12, unknown tokens: a goal with no token count records "unknown" and the board shows "tokens unread", never 0, because 0 reads as an unspent budget. Reworded GRD-2; defect #2615 filed for the code.
- 2026-11-12, review depth and release: condensed review happens only when `review_depth: condensed` (the default stays full); release merges and publishes with `auto_merge` on and makes a draft without it, because DEL-6 and DEL-5 promised what the settings don't do. Reworded DEL-5, DEL-6.
- 2026-11-12, generated sections and Usage: the generated Deployments, Runbook, Settings and Automation sections are allowed on their pages, the Regression metric uses REG-7's 15-minute floor, and Usage carries no module or refactor notes, because DOC-1, DOC-4, DOC-14 and DOC-15 contradicted each other and DOC-6 says Usage lists commands. Reworded DOC-1, DOC-4; Usage cleaned on Documentation, Regression and Monitoring.
- 2026-11-12, feature labels: `feature_labels` stays false by default, and the requirements say "when feature_labels is on", because the code tags a feature only then. Reworded HLT-4, AUT-2, AUT-3.
- 2026-11-12, one budget name: the setting is `test_budget_minutes` everywhere, because `test_budget_seconds` does not exist. Fixed workflow-health commands.md and the HLT-6 row descriptions; HLT-2 names no setting and stands.
- 2026-11-12, Monitoring non-goal: "does not merge" becomes "never merges unless auto_merge is on", because MON-7 and MON-15 let the post-merge step merge. Reworded the Monitoring Non-goals.
