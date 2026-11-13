# The owner's words given to the operation session are recorded verbatim and accepted by workers for reviews; full auto applies routine recommendations

- Slug: owner-relay
- Touches: skills/workflow-docs, skills/workflow-monitoring, skills/workflow-delivery, docs/wiki, DECISIONS.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. criteria.py review --user --owner-record ID applies a recorded owner message for its ids only; a worker cannot write an owner-words record

## Verify by hand

1. In the operation session run `python3 skills/workflow-monitoring/scripts/sessions.py owner-words "Review DOC-1 now" --ids DOC-1`.
   Expect: `OWNER-WORDS o1 covers DOC-1`, and a line in `.git/loop/owner-words.tsv` with the text in quotes.
2. In a worker session run the same command with `LOOP_ROLE=worker`.
   Expect: `REFUSED: only the operation session records the owner's words`, and no new line in the file.
3. Run `python3 skills/workflow-docs/scripts/criteria.py review DOC-2 --user --owner-record o1 < /dev/null`.
   Expect: `REFUSED: record o1 does not cover DOC-2`, and the page unchanged.
4. Read DECISIONS.md under "Waiting on owner un-review".
   Expect: the drafted DOC-2 and MON-11 wording, waiting for your typed words.
