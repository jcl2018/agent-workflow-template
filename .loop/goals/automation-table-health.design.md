# automation-table-health design

Problem (#3857): the generated Automation table (counting.py BUILT_IN) lists health and the digest email as run by GitHub Actions (health.yml), so it showed "not deployed" with .github/workflows/health.yml owed. AUT-3: health never runs in Actions; it runs on the Mac's local schedule.

Chosen: health and the digest email get runs "local:schedule"; the table reads "this Mac's local schedule", state on/off from the cron or digest_mail, nothing owed; docs.py automation says so too instead of querying gh. Regression keeps github:regression.yml. A leftover health.yml never changes the row. Old toy assertions (settings-table, docs-split golden) updated to the new truth; row automation-missing-workflow reworded. New Python toy test-automation-table-health.py, row automation-table-health (defect, #3857), seen red with the sed break.

Open questions: none. #3854 is already fixed by 536fd6b6 (v0.27.37); closed with that commit.
