# Consolidate monitoring so the operation session never does work: it assigns goals in batches to worker sessions, each worker runs its own independent loop, and workers report results back to the operation session by prompt; remove the extra session-upgrade paths so this is the one way to run

- Slug: worker-loops
- Touches: skills, docs/wiki, README.md, listing.json, dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. The operation session's commands only assign, watch and report; any command that would build, plan or run a goal step from the operation session refuses with one line naming the worker command to use instead
2. A batch starts one worker per goal, each running its own loop to the end without the operation session, and each worker sends its result (merged, failed or waiting, with the pull request) back to the operation session as a prompt message that the board shows
3. The older ways to promote or upgrade a session into a worker are removed, and a grep finds no command, flag or wiki text for them
4. The Monitoring wiki page and references/operation.md describe this one workflow with a chart, and its criteria are marked Unreviewed
5. A toy test proves the assign, worker loop and report-back path with a stand-in agent, and every script stays under 20 KB
6. Each check-in prints one fixed-format status block, and updates the dashboard artifact with the same content, in this order: Needs you (every stuck or waiting worker, with the exact words to answer, always first and never hidden), Now (each running goal's current step and stage), Next (queued and waiting goals), Roadmap (a progress bar per milestone and overall), and Goals (each goal's done lines met so far)
7. For each step of each goal, the status block and dashboard show the estimated time and tokens, the actual time and tokens so far, and the estimate for the goal's remaining steps, taken from past runs, or marked as no estimate yet
8. When a worker gets stuck, waits on the owner or fails, its report-back puts it at the top of Needs you on the next check-in and on the dashboard, and it stays there until it is answered

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
