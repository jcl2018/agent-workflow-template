# The built-in flow

A step mapped to `built-in` in the flow file runs the routine below instead of a skill from your own suite, so the
package works with no suite at all. `flow.py` puts the step's section into the step's prompt. Setup fills an empty
suite with `built-in` for idea, plan, review, qa and ship; build, pr and release are run by delivery itself, as always.
Name your own skill for any step in the flow file, and it replaces that step's routine.

Every routine runs unattended: take the recommended answer at every question, approve nothing, merge nothing and push
nothing. A built-in step needs no probe: delivery's own build and pr steps already run under the same command and
prompt rules, and the command's allowed tools set the real limit.

## idea
Read `.loop/goals/<slug>.md`: its done lines are frozen. Read the code and pages the goal touches. Write
`.loop/goals/<slug>.design.md`: the problem in two or three sentences, two approaches with their cost and risk, the one
you chose and why, what each done line needs, and the open questions. Commit it.

## plan
Read the design. Check each claim against the code: name the files and functions to change and confirm they exist.
Write `.loop/goals/<slug>.plan.md`: the ordered build steps, the test for each done line (a regression row seen
failing before the change and passing after), what could break, and what is out of scope. Commit it. List anything only
the owner can decide as a PENDING line.

## review
Read `git diff <base>...HEAD`. For each change, check it does what the plan says, handles errors and empty input,
keeps every script under 20 KB, adds no private value, name or machine path, and has a test. Fix what is clearly wrong
and commit; list the rest as findings, one line each, in your reply.

## qa
The regression lane has already run on this commit. Run the repo's check commands from `.loop/config.json` and try
each done line the way a person would, from the goal's Verify by hand steps. If a step needs a browser or a tool this
machine doesn't have, end with STEP: skipped and say what was missing.

## ship
Check the branch is ready for a pull request: the version and changelog follow the repo's habit, the docs that
describe the changed paths are updated, and the tree is clean. Commit what is missing. Don't push and don't open the
pull request: delivery does that. File what you found and did not fix, one line each, in your reply:
`FILE defect <Feature>: text` for a break of a Reviewed requirement outside this goal's touches, `FILE backlog <Feature>: text` for an
improvement, idea or saving (`Other` when no feature fits). A break inside the touches is fixed, not filed. Record files them once.
