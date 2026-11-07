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

1. Run `ls docs/wiki` and `python3 skills/workflow-docs/scripts/docs.py check`.
   Expect: six files (Home, Delivery, Documentation, Monitoring, Regression, Release), and `DOCS OK: 6 pages`.
2. Open `docs/wiki/Release.md` and read the Criteria section.
   Expect: three one-line criteria marked `(draft)`, each with a matching line under Enforced by.
3. Run `python3 skills/workflow-regression/scripts/regression.py sync`.
   Expect: no GAP, DRAFT or UNPROVEN lines for DEL, DOC, MON, REG or REL rows.
4. Open README.md and read the Getting started and File reference sections.
   Expect: install steps and a file table, and Home.md links to the README.

## Design

Keep five feature pages with the fixed sections Summary, Commands, Criteria and Enforced by; extra detail from the old pages
becomes `###` subsections under them. Home stays free-form and links to the README. Getting started and Files move into
README.md and their pages leave `.loop/docs.tsv`. Each page gets three draft criteria, each backed by a row whose command
looks for one named PASS line of an existing toy test, so the criteria describe behaviour that exists today. Each row was
proven with `regression.py red`, using a break that changes behaviour. Risk: criteria turn on `"criteria": true` in the config.

## Plan

1. Rewrite the pages, README and docs.tsv; set `criteria` in the config. Proof: `docs.py check` prints DOCS OK.
2. Add 15 rows and run `red` on each. Proof: every row has a seen_red date, and `regression.py sync` is clean.
3. Run `goal.py check`. Proof: all repo checks pass.

## Evidence

Output of `ls docs/wiki` and `python3 skills/workflow-docs/scripts/docs.py check`, run on this branch:

```text
Delivery.md
Documentation.md
Home.md
Monitoring.md
Regression.md
Release.md
DOCS OK: 6 pages
```

Output of `python3 skills/workflow-regression/scripts/regression.py criteria`, which runs the row of every wiki criterion (DEL-1 to REL-3) and prints one UNMET line for each that is missing, a draft or failing. It printed nothing and exited 0, so all 15 rows pass on this commit. The three DEL rows grep these lines of `bash dev/toy/test-goal.sh`:

```text
PASS: go needs a done line
PASS: default level 0, starts at design
PASS: raised at the start
criteria exit=0
```
