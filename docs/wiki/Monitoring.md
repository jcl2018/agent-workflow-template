<!-- workflow-docs -->
# Monitoring

Skill: `workflow-monitoring`. One session governs and the others build. Scripts: `watch.py` (`go`, `watch`, `resume`) and
`monitor.py` (`report`, `dashboard`). Run them from the main checkout, on the base branch.

## Commands

```text
go "GOAL" --done LINE [--done LINE] [--level L] [--touches A,B] [--slug S] [--release ask]
watch [--max N] [--once] [--interval S]
report
dashboard [--out FILE]
resume SLUG
```

- `go` adds the goal to `.loop/queue.md` and starts it if a slot is free.
- `watch` starts queued goals (3 at a time by default), each on branch `loop/<slug>` in its own worktree, and ends when
  nothing is left. `--once` makes one pass.
- `report` lists each run, what waits on you with the exact words to type, findings, and queued goals.
- `dashboard` writes one self-contained HTML page under the git folder's `loop/`.
- `resume` relaunches a `failed` or `stopped` goal, and refuses anything else.

Goals whose `touches` overlap never run together. A failed goal never stops the others. A batch goal answers the release
question with `leave` by itself, never `cut`; `--release ask` makes it wait for you.

## Config

`mend` (one fresh agent for a failed goal) and `resume_on_limit` (continue after a usage limit) are off by default,
since each spends your usage. Background agents run `agent_command` with your own permissions.

## Example

```text
python3 scripts/watch.py go "Add median()" --done "Even lists average the two middle values" --level standard --touches calc.py
python3 scripts/watch.py watch
python3 scripts/monitor.py report
```
