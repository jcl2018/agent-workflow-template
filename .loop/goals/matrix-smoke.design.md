# Design: matrix-smoke

Problem: "many agents, many machines" is promised but nothing proves it per cell. Approach chosen: one Python smoke script (dev/toy/matrix-smoke.py, no new files under skills/) that runs the same seven steps everywhere and appends a dated line to .loop/matrix-runs.tsv; a health Adoption rule `matrix` (in report.py, which has room under the 20 KB limit) reads it; a matrix-smoke job in the generated regression workflow covers Linux. Rejected: a `regression.py smoke` subcommand (regression.py and actions.py are near the 20 KB limit) and a bot that commits CI records to main (a guardrail change for the owner).

Done line: smoke writes a dated matrix record (matrix-smoke-record row); health warns on an unproven cell and fails on an unproven V1 cell (matrix-health-rule row). Both rows seen failing.

Open for the owner: the SET-17 wording (DECISIONS.md, waiting on owner un-review).
