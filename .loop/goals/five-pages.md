# Rewrite the wiki as five feature pages with draft criteria

- Slug: five-pages
- Level: standard
- Touches: docs/wiki, .loop/docs.tsv, .loop/regression.tsv, README.md, docs/ROADMAP.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs/wiki holds only Home, Delivery, Documentation, Monitoring, Regression and Release, and each feature page has Summary, Commands, Criteria and Enforced by
2. Each criterion is a plain sentence the owner can check without reading code, marked as a draft for the owner's approval, and describes behaviour that exists today
3. Getting started and the file reference move into README.md, and the wiki links back to it
4. Every criterion has a row in .loop/regression.tsv that points to a real test, seen failing once, or is listed under a clear Not enforced yet heading on its page
5. docs.py check passes, and the repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->

## Design

## Plan
