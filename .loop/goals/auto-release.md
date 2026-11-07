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

1. Run `bash dev/toy/test-release.sh`.
   Expect: it ends with ALL PASS, and the 4b section shows NEED patch/minor/leave/ask lines and only draft releases.

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

`release.py ask` stays the single entry the batch already reaches. When the goal is a batch goal not marked
`release: ask` and `release_auto` is true, it classifies the diff against the base: `.loop/` ignored; docs, tests and
markdown only means leave; a BREAKING or `!:` commit or a removed file means ask; a new non-doc file or `feat` commit
means minor; else patch. It records need and reason, then calls `cmd_cut` with an internal `auto` flag, so the draft,
verify-step, stale-page and checks refusals all still run. On any refusal it falls through to the normal wait. Risk: the
heuristic misreads a change; the draft and the owner's publish step contain that.

## Plan

1. Add auto_on/auto_need and the batch branch in cmd_ask; accept `auto` in cmd_cut (done lines 1-4).
2. Extend dev/toy/test-release.sh section 4b with a fake gh for every line (lines 1-5).
3. Update SKILL.md and docs/wiki/Release.md (line 5); confirm size under 20 KB.
4. Run goal.py check and judge (line 6).
