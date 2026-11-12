# The Automation page says where each routine runs: health (all rule groups plus the agent review) runs only on the owner's Mac every 4 hours for every repo and never in GitHub Actions; the full regression runs every 4 hours in GitHub Actions for a public repo and on the Mac for a private one; a push or pull request runs only the affected tests; no GitHub check ever blocks a private repo's merge; and both still file their issues and the digest (owner, 2026-11-11: "I still want the 4-hour regression and health check to in the GitHub action, because for public repo, because that's free ... in the private repo, I want it to be completely in the local machine, like in the Mac, so it will never block"; then "So in that case, we shouldn't even use the health in the GitHub action, because it can only run fully in the local. So change that behavior as well.")

- Slug: automation-local-prd
- Touches: docs/wiki/Automation.md, docs/wiki/Home.md, .loop/docs.tsv

## Done lines

Frozen. A wrong done line needs a new goal.

1. AUT-1 is unreviewed with the owner's words above (criteria.py unreview --user, LOOP_OWNER_WORDS = the second quote) and rewritten as "Routines run where they can run fully": health on the Mac for every repo, regression on GitHub Actions for public and on the Mac for private, each schedulable and startable by hand
2. AUT-2 and AUT-3 are rewritten to match (AUT-3: health never runs in GitHub Actions; the agent review always runs, using the owner's own login on the Mac, no API key secret; a missed run happens at next wake and the report says when it last ran) and stay Unreviewed for the owner
3. AUT-4/AUT-5 keep their wording unless a line names GitHub Actions as the only place, in which case that line is unreviewed with the same owner words and reworded minimally
4. docs.py check passes; no private name, path or email

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
