# Write the project wiki and bring the roadmap up to date

- Slug: project-wiki
- Level: standard
- Touches: docs/wiki, .loop/docs.tsv, README.md, docs/ROADMAP.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs/wiki has pages Home, Getting-started, Delivery, Monitoring, Documentation, Regression, Release and Files, each mapped in .loop/docs.tsv to the skill or files it describes
2. Home lists every feature with a link to its page and says what is proven and what is not, using only claims found in FINDINGS.md, DECISIONS.md, or the dev tests
3. Each feature page gives its real commands and flags, matching the feature's SKILL.md and script help, with one real example
4. Getting-started takes a new user from install to one finished goal, using dev/install-local.sh and the setup, go and watch commands
5. docs/ROADMAP.md marks the first and second batches as built, lists what is left, and no longer names commands that were removed
6. README.md links to the wiki and the release page and copies no page content beyond its command summary
7. Every page starts with the workflow-docs marker, and the private name scan finds nothing in docs or README
8. The repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
