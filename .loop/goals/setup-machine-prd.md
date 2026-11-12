# Add the lessons from adopting the template on a second machine (Windows, 5 repos) to the Setup PRD as new Unreviewed requirements, so setup guides an owner straight to a working multi-repo operation session

- Slug: setup-machine-prd
- Touches: docs/wiki/Setup.md, docs/wiki/Home.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs/wiki/Setup.md holds new Unreviewed requirements SET-11 to SET-15 covering: machine prerequisites with fixes, multi-repo adoption, worker sessions and the pool, MCP connector checks, and the private-name list
2. workflow-docs check prints DOCS OK and the page stays within criteria_max

## Verify by hand

1. Open `docs/wiki/Setup.md` and read SET-11 to SET-15.
   Expect: five requirements marked **Unreviewed**, each ending with the issue it comes from (#1408, #1409, #1404, #1410, #1411), and SET-1 to SET-10 unchanged.
2. Open `dev/toy/adoption-golden.tsv`.
   Expect: eight steps in order, prerequisites to the first check-in, each with a check, golden result and fix, and no path, account or private repo name.
3. Run `bash dev/toy/test-adoption-golden.sh`.
   Expect: four PASS lines and `ALL PASS`.
