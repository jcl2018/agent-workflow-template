# Let a goal release itself as a draft when its change needs one

- Slug: auto-release
- Level: standard
- Touches: skills/workflow-release, dev/toy/test-release.sh, docs/wiki/Release.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. With release_auto true in .loop/config.json, release.py ask reads the goal's diff and records a release need and reason: leave for only docs, tests or .loop changes; patch for a fix; minor for a new feature or command; ask for a breaking change
2. In that mode a batch goal with checks passing and a judge pass cuts a draft release with no --user flag, and a goal marked release: ask still waits for the owner
3. A breaking change always waits for the owner and docs-only work always leaves, and repos without release_auto behave exactly as today, including batch cut refusing without --user
4. The release is always a draft: nothing merges, publishes or pushes a tag, and every existing refusal for missing verify steps or stale pages still applies
5. skills/workflow-release/SKILL.md and docs/wiki/Release.md describe this, dev/toy/test-release.sh proves every line above with a fake gh, and release.py stays under 20 KB
6. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
