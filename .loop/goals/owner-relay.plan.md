# Plan: owner-relay

Checked: criteria.py mark_all (reads LOOP_OWNER_WORDS, logs reviews.tsv), sessions.py (subcommand parser, 19,700 bytes),
the delivery and docs SKILL.md files and DECISIONS.md exist.

## Build steps

1. `skills/workflow-monitoring/scripts/ownerwords.py`: add(text, ids) writes one tab-separated line (id o1, o2, ...; UTC
   time; LOOP_OPERATION_SESSION or "operation"; JSON text; ids) to <git common dir>/loop/owner-words.tsv; refuses when
   LOOP_ROLE=worker, with empty text or no ids. `sessions.py owner-words TEXT --ids A,B` calls it.
2. criteria.py: `--owner-record ID` on review and unreview; read the record, check every id or page on the command line is in
   the record's ids, refuse a record already used for the same command, use the record's text as the words, log
   "record ID" in reviews.tsv. LOOP_OWNER_WORDS and the terminal stay.
3. delivery and docs SKILL.md: one rule each.
4. dev/toy/test-owner-words.sh: record written and decoded exactly (tabs, quotes); a worker refused; review applies for
   its ids; an uncovered id refused with nothing changed; a record reused for the same command refused; a missing record
   refused.
5. Rows: owner-record-applies, worker-cannot-write-owner-words, owner-record-ids-only, seen red.
6. DECISIONS.md: "Waiting on owner un-review" with the DOC-2 and MON-11 draft.

## Could break

sessions.py and criteria.py stay under 20,480 bytes. Reviewed pages are untouched (their locks).

## Out of scope

Applying the DOC-2 change; merging before the owner types the DOC-2 words.
