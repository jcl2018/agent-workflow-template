# Cut v0.28.0 V1 format: record the owner's re-review of Delivery, Documentation, Setup and Health, refresh the Tests page, and release the Phase 1 pieces as a minor version

- Slug: v1-format
- Touches: docs/wiki

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs.py check on this branch prints DOCS OK with no CHANGED, STALE or Unreviewed line, the release is a minor bump to 0.28.0, and its notes list review-findings, spec-decisions, v1-roadmap, migration-check, health-docs-size, settings-render-windows and review-sitting

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

1. Open the v0.28.0 release page.
   Expect: the release is published and lists review-findings, spec-decisions, v1-roadmap, migration-check, health-docs-size, settings-render-windows and review-sitting.
2. Run `python3 skills/workflow-docs/scripts/docs.py check` on a fresh checkout of main.
   Expect: it prints DOCS OK and no CHANGED, STALE or Unreviewed line.
