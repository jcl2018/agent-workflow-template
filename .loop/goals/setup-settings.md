# Put every setting in one place with defaults and explanations, with the owner's new SET-1 and SET-2 wording approved in chat on 2026-11-08

- Slug: setup-settings
- Touches: skills/workflow-setup, skills/workflow-monitoring, skills/loop-files.md, .loop/config.json, docs/wiki, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. SET-1 and SET-2 are unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: SET-1 "One command adopts a repo. One command sets up a new or existing repo in this template's format, everything at once: the loop config, the feature pages with criteria and tests, a milestone per feature plus Backlog, the nightly regression in GitHub Actions and the health rules. It first shows what it found, what it would add or convert and what doesn't fit, then applies it on a branch through the usual loop. In an existing repo it adapts what is there instead of overwriting." SET-2 "Every setting in one place. Every setting lives in one of two places: repo settings in the repo's config, committed and shared, and private settings outside the repo, never committed. Setup writes each with a default and a one-line explanation, I can change any of them at any time, and the framework reads them every run. Parallel workers default to unlimited."
2. parallel 0 means unlimited and is the default, and this repo's committed config sets it to 0
3. A settings reference lists every repo setting (parallel, cadence, auto_approve, auto_merge, version and release-note switches, routines, regression schedule, time and token budgets, mend, max tries, resume_on_limit, base, wiki_dir, version_file, risky_paths) and every private setting (flow file with a default suite and per-step overrides, agent command, allowed tools and model per step, own health rules, followed repos), each with its default and a one-line explanation, and Setup writes both halves into a repo
4. Every script reads settings fresh on each run, a toy test changes a setting and sees the effect, and every script stays under 20 KB

## Verify by hand


1. Run `python3 skills/workflow-setup/scripts/settings.py reference`.
   Expect: a table of every repo and private setting, each with its default and a one-line explanation; `parallel` shows 0, unlimited.
2. Run `grep parallel .loop/config.json`.
   Expect: it prints `"parallel": 0`.
3. Run `bash dev/toy/test-settings.sh`.
   Expect: it ends with ALL PASS, after showing parallel 2 start two goals and parallel 0 start all four.

