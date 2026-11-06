# Roadmap

## Feature 1: the goal loop

One goal, from a sentence to a judged pull request. This is the smallest version that's useful, so everything else waits.

| Part | What it does | Why it can't wait |
|---|---|---|
| Goal file | `.loop/goals/<slug>.md` holds the done lines, plan, log and verdict | Everything else reads it |
| Sizes | S: plan, build, checks. M: adds a short design and a fresh judge | This is where the speed comes from |
| Checks | `.loop/check.sh` runs the repo's tests plus one command per done line | The judge needs evidence, not claims |
| Fresh judge | A new agent sees only the diff, the goal file and the check results | The one rule that catches bad work |
| Findings | Failed work goes in `.loop/findings.md` after 3 tries, and the run stops | Keeps a run from looping forever |
| Install | Copies `.loop/` in and adds a short `AGENTS.md` block | Without it, the loop can't reach another repo |

The pull request is the human gate. You set the goal, you review the PR, and the loop never merges.

### Done means

1. On a toy repo, an S goal and an M goal each end in a PR.
2. The judge fails a planted bug, and the loop fixes it or files a finding.
3. Install runs twice on a repo with no changes the second time.
4. One real S goal works on a real repo.
5. The skill stays at 5 files and 300 lines at most.

## Later, in order

1. **Regression:** nightly and fast levels, a GitHub Actions template, an issue per failing check.
2. **Documentation:** wiki pages kept in the repo, stale page check, draft releases.
3. **Operation:** a queue of goals, a status report, unattended runs.
4. **Other agents:** Kimi, Qwen and OpenCode support.
5. **Marketplace:** the Agensi package.
