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
