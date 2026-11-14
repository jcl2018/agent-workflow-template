# Design: owner-relay

## Problem

The owner wants to answer only in the operation session. A worker rightly refuses the owner's words when another session
relays them (DOC-2: only the owner), so every review or un-review needed the owner to type in the worker's own chat.

## Approaches

1. A worker accepts any text passed in LOOP_OWNER_WORDS (today's rule) from the operation session. No audit, no scope.
2. The operation session writes the owner's message verbatim to a record only the operation role can write
   (`<git common dir>/loop/owner-words.tsv`); `criteria.py review|unreview --user --owner-record ID` reads the words from
   the record, checks the record covers every id on the command line, and uses each record once per command.

**Chosen: 2.** Same trust as today (an agent could already set LOOP_OWNER_WORDS), but the words are recorded, scoped to
ids, single-use and visible in reviews.tsv. LOOP_OWNER_WORDS and the terminal prompt stay as they are.

## Changes

- `ownerwords.py` (workflow-monitoring): `sessions.py owner-words "TEXT" --ids A,B` appends id, time, the operation
  session's id, the text (JSON-encoded, so tabs and newlines survive) and the ids; refused when LOOP_ROLE=worker.
- `criteria.py` (workflow-docs): `--owner-record ID` for review and unreview; refuses a missing record, an id the record
  does not cover, a record already used for this command; logs the record id with the words in reviews.tsv.
- delivery and docs SKILL.md: a record in owner-words.tsv, written only by the operation role, is the owner's words.
- DECISIONS.md "Waiting on owner un-review": draft DOC-2 and MON-11 wording. Reviewed requirements are not edited.
- Held before merge.py: the SKILL.md rule makes workers accept relayed words, which DOC-2 forbids until the owner
  types the new DOC-2 wording.

## Done line

`criteria.py review --user --owner-record ID` applies a recorded owner message for its ids only; a worker cannot write
an owner-words record. Tested by a toy (dev/toy/test-owner-words.sh) with rows seen red.

## Open questions

None; the DOC-2 wording needs the owner's typed words and waits in DECISIONS.md.
