# Add a board page ready to publish as an Artifact, honoring a manual theme

- Slug: board-artifact-page
- Level: standard
- Touches: skills/workflow-monitoring/scripts/board.py, skills/workflow-monitoring/references/operation.md, dev/toy/test-board.sh

## Done lines

Frozen. A wrong done line needs a new goal.

1. board.py also writes board-artifact.html without doctype, html, head or body tags, starting with the title and style
2. Both pages use theme tokens that follow prefers-color-scheme and a manual data-theme setting of dark or light
3. references/operation.md says to publish board-artifact.html, and dev/toy/test-board.sh proves the page's tags and theme rules
4. The repo checks pass

## Verify by hand

1. Run `python3 skills/workflow-monitoring/scripts/board.py board --out /tmp/b` and open `/tmp/b/board-artifact.html`.
   Expect: it starts with `<title>`, has no doctype, html, head or body tags, and still renders as a board.
2. Add `data-theme="dark"` to the root of `/tmp/b/board.html`, then `light`, and open it each time.
   Expect: the page is dark, then light, whatever the system setting is.

## Design

`page(doc, bare)` builds both pages from one body. The bare page starts with `<title>` and `<style>` and drops the doctype, html, head and body tags, so the Artifact tool needs no hand edit. The CSS defines light tokens on `:root`, dark tokens under `prefers-color-scheme:dark` guarded by `:root:not([data-theme=light])`, and again under `:root[data-theme=dark]`. A manual setting therefore wins over the system one. Risk: the 20 KB cap on board.py, met by trimming the docstring and repeated code. The branch starts from loop/board-truth.

## Plan

1. board.py: `page(doc, bare)`, the shared CSS tokens, and the new `ARTIFACT` path (done lines 1, 2).
2. operation.md says to publish board-artifact.html (done line 3).
3. test-board.sh checks the tags and the theme rules on both pages (done lines 2, 3).
4. `goal.py check` proves the repo checks and the 20 KB cap (done line 4).
