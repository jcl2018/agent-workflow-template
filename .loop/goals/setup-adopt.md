# Make Setup adopt any repo and ship as an updatable package, as SET-1 to SET-5 say

- Slug: setup-adopt
- Touches: skills/workflow-setup, dev, listing.json, VERSION, README.md, skills/loop-files.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. One setup command, run in a new or existing repo, prints what it found and what it would add or convert, then writes on a branch the loop config, feature pages with criteria and tests, milestones, the regression workflow and the health rules, adapting existing files instead of overwriting them
2. The package is built with its version number and every skill, works by copying into any SKILL.md agent, and keeps every script under 20 KB
3. An update command in an installed repo shows the newer version and what changed, and updates the skills without touching the repo's config, criteria, docs or private settings
4. A design guide in the package explains how the loop, operation and workers, criteria and tests, regression and health fit together
5. A toy test proves adopting a fresh toy repo and updating it, and the repo checks pass

## Verify by hand

1. Run `bash dev/toy/test-adopt.sh`.
   Expect: it prints `PASS SET-1 SET-2`, `PASS SET-3`, `PASS SET-4 SET-5` and `ALL PASS`.
2. In a scratch git repo with a code folder and an unmarked `docs/wiki/Home.md`, run `python3 skills/workflow-setup/scripts/setup.py --dry-run`.
   Expect: a `FOUND:` line, then `add:` and `convert:` lines, and `DRY RUN: nothing written`.
3. Run `bash dev/package.sh --out /tmp/pk.zip`, then `python3 skills/workflow-setup/scripts/update.py --from /tmp/pk.zip --skills <a copy of skills/>`.
   Expect: `PASS: ... version 0.3.0`, then `INSTALLED:`, `AVAILABLE: 0.3.0` and a preview that writes nothing.
