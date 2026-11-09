#!/bin/bash
# Run every step of a goal's skill flow through flow.py and goal.py record, with the stand-in flow make.sh writes.
# flow.py is called until it prints NEXT: the qa and ship steps first run the regression lane in the background.
# usage: flow-done.sh SLUG   (from the goal's worktree, with LOOP_FLOW set)
export LOOP_ROLE=worker
here=$(cd "$(dirname "$0")/../.." && pwd); slug=${1:?usage: flow-done.sh SLUG}
runs="$(cd "$(git rev-parse --git-common-dir)" && pwd)/loop/runs"
for step in idea plan review qa ship; do
  for _ in $(seq 20); do
    out=$(python3 "$here/skills/workflow-delivery/scripts/flow.py" "$slug" $step --wait 10) || exit 1
    grep -q "^NEXT:" <<<"$out" && break
  done
  python3 "$here/skills/workflow-delivery/scripts/goal.py" record "$slug" $step --file "$runs/$slug.$step.txt" >/dev/null || exit 1
done
