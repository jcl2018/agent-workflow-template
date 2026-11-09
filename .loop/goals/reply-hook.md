# Enforce the operation session's reply format with a hook instead of a prompt rule

- Slug: reply-hook
- Touches: skills/workflow-monitoring, skills/workflow-setup, docs/wiki/Monitoring.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A Stop hook that setup can install checks the operation session's last reply ends with the full live board (and one decisions line above it); when it doesn't, the hook blocks the stop and says what is missing, so the session fixes the reply
2. The hook only acts in the operation session, never in worker sessions or other repos' sessions, and turning it off is one setting
3. MON-5 on the Monitoring PRD gains the rule as proposed wording marked Unreviewed, for the owner to review in their own words
4. A toy test proves a reply without the board is blocked, a reply with it passes, and a worker session is never checked
5. Per DOC-3, each done line above is recorded on its PRD page as one or more Given/When/Then scenarios under the requirement it serves, each linked to its regression row with its last result

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
