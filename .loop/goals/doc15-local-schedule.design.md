# doc15-local-schedule: design

## Problem
Main's Documentation page is STALE: 081de7bf and d861e9c6 changed what the Automation table says about health, and no page text describes it. That fails review-findings-skill-lines and settings-render-fresh in every pr lane (#3875, closed as not a bug).

## Approaches
1. Add a Tests-intro line or other hand text: refused, Tests is generated (DOC-9) and no other place takes text.
2. The owner un-reviews the page and DOC-15; a DOC-15 sub-bullet states the local schedule; the owner reviews again. Chosen: it is the one path that records the change in a page the owner owns.

## Chosen
2. Done 2026-11-13 on the owner's two sentences typed in this session. Home's Documentation row also names the local schedule so Home reads current.

## Done lines
Met: docs.py check reports DOCS OK, and DOC-15 carries the sub-bullet. The publish dry-run on the merged head is for the release.

## Open questions
None.
