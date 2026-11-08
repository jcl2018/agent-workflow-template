# Replace the wiki criteria with the owner's final approved set of 6 features and 30 criteria from ~/projects/agent-workflow-template/.local/criteria-review.md (read it; it is outside the repo and must never be committed)

- Slug: final-criteria
- Touches: docs/wiki, .loop/docs.tsv, .loop/regression.tsv, skills/workflow-docs, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. The wiki has exactly the feature pages Delivery, Monitoring, Documentation, Regression, Health and Setup plus Home; the Release and Milestones pages are removed and their content folded as the file says
2. Each page carries the owner's 5 criteria word for word from the file, with ids DEL-1..5, MON-1..5, DOC-1..5, REG-1..5, HLT-1..5, SET-1..5, and each is marked Reviewed 2026-11-08 with criteria.py review --user, because the owner approved every one in chat that day
3. The criteria cap in the code is 5, and docs.py check passes
4. Every existing regression row is mapped to the one new criterion it proves, rows that fit none are listed in the goal's report, and a criterion with no passing test shows as not enforced in its Tests table
5. No criterion wording differs from the file, and the repo checks pass

## Verify by hand

<!-- One or more numbered steps a person can follow, each with an Expect: line. Every release needs this. -->
