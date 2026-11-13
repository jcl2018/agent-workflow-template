# pr lanes run one at a time per repo, and a try lost to main moving doesn't use up max_tries (#3877)

- Slug: pr-queue
- Touches: skills/workflow-delivery, skills/workflow-release, skills/workflow-monitoring, dev/toy, .loop/regression.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. Two goals at pr in one repo run their lanes in order without either failing on BASE_MOVED, and a main-moved retry leaves max_tries unchanged

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
