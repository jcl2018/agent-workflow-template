# Design: setup-machine-prd

## Problem

Adopting the template on a second machine (native Windows, five repos followed from one operation session) took a
long run of trial and error: missing or signed-out tools, Windows crashes, repos found one at a time, workers that
fell back to background agents, connectors nobody checked, and a private-name list that blocked a private repo's own
pushes. The Setup PRD promises none of this, so `/workflow-setup` can't guide the next owner past it.

## Approaches

1. **Five new Unreviewed requirements on the Setup page (chosen).** SET-11 to SET-15, each written as owner-facing
   outcomes in the page's existing shape, each naming the issue it comes from. Cost: one page edit; the page reaches
   15 requirements, exactly `criteria_max`. Risk: the page is full, so a later requirement needs merging or a new page.
2. **A new "Machine" PRD page.** Keeps Setup under its cap, but splits one owner journey (adopt a machine) across two
   pages and needs a new milestone and path map. The done lines name Setup.md, so this doesn't meet them.

## What each done line needs

1. SET-11 machine prerequisites with fixes (#1395, #1396, #1397, plus a new enhancement issue for the checklist);
   SET-12 multi-repo adoption (new issue); SET-13 worker sessions and the pool (#1404, hook idempotency folded in);
   SET-14 MCP connector checks (new issue); SET-15 the private-name list (new issue). All **Unreviewed**; reviewed
   requirements are untouched.
2. `docs.py check` prints DOCS OK; render adds the untested rows to Tests; 15 requirements = criteria_max.

## Open questions

None for the owner: no private names (repo names, accounts, paths) go on the page or in the issues; examples stay generic.
