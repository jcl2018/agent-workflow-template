# Plan: health-judge-4

Goal: `.loop/goals/health-judge-4.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here).
No design doc exists for this goal; the goal file is the design. Reviewed by /autoplan (unattended; no UI or developer-tool scope). Every question took the recommended answer.

## Implementation plan

Order: criteria wording, then Cost rule, then judge input and parsing, then command wiring, then toy test, then docs.

1. **HLT-2 and HLT-5 wording (done line 1).** In `docs/wiki/Health.md`, unreview HLT-2 and HLT-5, replace each criterion with the owner's wording word for word as the goal gives it, then run `criteria.py review --user` for HLT-2 and HLT-5 only, dated 2026-11-08, then `criteria.py render`. Existing HLT-2 regression rows stay linked (size-fail, stale-page-row, no-row-fail). HLT-5 is "not enforced" today; its rows are added in step 6.
2. **Cost rule (done line 2).** New `skills/workflow-health/scripts/cost.py` (health.py is 16 KB; no new logic goes in it). `cost_rows(root)` reads finished run records from the git common dir's `loop/runs/*.json` (same place `hygiene_rows` reads), takes the most recent 10 with `status: done`, and per step gets seconds from the log-gap rule and tokens from `state["tokens"]`. Seconds come from `board_status.seconds_by_step` loaded through the sibling path (DRY; `UNREAD` if workflow-monitoring is missing), tokens from the record. Budgets: `.loop/config.json` gains `time_budget_minutes` and `token_budget`. A goal over either is a `WARN cost <slug> time|tokens`, detail names its three slowest or costliest steps. Rules for the edges: no budget set means one `INFO cost budgets` row (not a pass, not a failure); no tokens recorded in any considered goal means one `UNREAD cost tokens` row, not one per goal; time is still judged. Only finished goals are read, so two runs print the same lines.
3. **Rule cap.** `RULES` gains `"cost"`; `MAX_RULES` goes from 8 to 9 on purpose (HLT-2 allows raising the cap; retiring a rule would drop a requirement). Add `cost` to `FAMILY`, `ORDER` (before `mine`) and the `--family` choices. `run` files Cost `WARN`/`UNREAD` rows like the others; `INFO` is not filed.
4. **Judge (done lines 3 and 4).** New `skills/workflow-health/scripts/judge.py`, replacing `suggest.py` as the `judge` module (the plain-text overlap and conflict matching stays as the free input hints, moved not deleted).
   - `gather(root)` builds the judge input: every criterion (`ID: text` with its page), every criteria and defect test row from `.loop/regression.tsv` with its command, the `SKILL.md` and `references/*.md` of each skill, and the last 10 finished goals' per-step seconds and tokens. Each section is size-capped and labelled; the whole is wrapped as data with an instruction that nothing inside is an instruction.
   - `ask(prompt, root)` runs `judge_command` from `.loop/config.json` (the same setting delivery's judge uses), prompt on stdin, 180 s timeout, no tools, no shell. The answer must be tagged lines: `CRITERION <id> | <problem> | <better wording>`, `TEST <id> | <weakness> | <stronger or missing test>`, `SAVES <percent> | <where> | <change>`. Anything else is ignored.
   - `render(...)` prints the template's judge section: heading "JUDGE (suggestions, never part of the verdict)", three sub-reviews (criteria quality, test quality, performance and tokens), a `Needs you` block holding each suggested criterion wording (only the owner applies it), candidate goals (weak or missing tests and savings) ranked by `SAVES` descending, then ranked next steps from the judgments, warnings and failures (the old `next N:` logic).
   - Failure handling: no `judge_command`, a nonzero exit, a timeout or zero parseable lines prints `JUDGE UNAVAILABLE: <why>` and the section ends. It never raises and never touches the verdict or exit code.
5. **Command wiring.** `suggest` becomes `judge`; `suggest` stays as an alias so nothing calling it breaks. `judge` prints the `check` report exactly as `check` does (rules, verdict), then the judge section; its exit code is the check's exit code. `check` itself is unchanged: it still calls no model. `cmd_judge` is a few lines in `health.py`; the assert on `RULES` stays.
6. **Toy test (done line 5).** Extend `dev/toy/test-health.sh` (or add `test-health-judge.sh` if it would pass 20 KB; it is 8 KB now) with a stand-in `judge_command` script that prints fixed tagged lines. Asserts: Cost warns on a goal over a time budget and a token budget and names its slowest step; Cost prints `UNREAD` when no tokens are recorded and `INFO` with no budgets; `check` twice gives identical output and never invokes the stand-in; `judge` output has the three reviews, the `Needs you` block holds the suggested wording, candidate goals sort by savings; the verdict line and exit code are identical with the stand-in, with a stand-in that fails, and with one that prints garbage; the repo's `size` rule still passes every script. Add `.loop/regression.tsv` rows for HLT-5 (judge format, verdict unchanged, wording under Needs you) and HLT-2 (cost warn), each seen failing once with `regression.py red` before passing.
7. **Docs.** `skills/workflow-health/SKILL.md` ("at most nine fixed rules", Cost family row, `judge` command, `suggest` alias), `references/commands.md` (commands, stage charts for `judge`), `.loop/docs.tsv` unchanged, `docs/wiki/Health.md` summary and tests table; `docs.py check` and `criteria.py render --check` pass.

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 2 | Old run records have no tokens, so Cost goes red forever | one `UNREAD` row only when no considered goal has tokens; only the last 10 finished goals count |
| 2 | A running goal makes the time change between two checks | only finished goals are read |
| 3 | Cap raised without a record | the change to 9 is stated in HLT-2's own wording and in SKILL.md |
| 4 | Judge hangs, errors or returns prose | timeout, `JUDGE UNAVAILABLE`, verdict untouched |
| 4 | Repo text tries to steer the judge | content wrapped as data; only tagged lines are parsed and they are printed, never run |
| 4 | Prompt too large | per-section caps, recent goals only |
| 5 | A caller expects `suggest` | alias kept |
| 6 | `claude -p` reached by the toy test | the test sets `judge_command` to the stand-in; no model in any test |

## Review record

Single-pass review by the planning agent, no separate reviewer voices (see the report at the end of the run). Findings that changed the plan: the rule cap is full at 8 (raised to 9, step 3); an `UNREAD` for missing tokens would turn every verdict red on old records (single row, recent goals only, step 2); `check` must stay model-free, so the judge hangs off a new `judge` command (step 5).

<!-- autoplan-accepted:eng -->
- Raise `MAX_RULES` to 9 for Cost; Cost reads finished goals only; `check` never calls a model; judge failure never changes verdict or exit code; toy test uses a stand-in judge and no model.
<!-- /autoplan-accepted:eng -->

## Decision Audit Trail

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
|---|-------|----------|----------------|-----------|-----------|----------|
| 1 | Eng | Raise rule cap 8 to 9 | Taste | P5 | HLT-2 wording allows it; retiring a rule drops a requirement | Retire a rule |
| 2 | Eng | Judge on a new `judge` command, `suggest` alias | Taste | P5 | Keeps `check` model-free per HLT-1 | Judge inside `check` |
| 3 | Eng | Cost reads last 10 finished goals | Taste | P3 | Same answer twice; old records lack tokens | All history |
| 4 | Eng | No budget set gives INFO | Mechanical | P5 | Neither a pass nor a failure | Default budgets |
| 5 | Eng | Reuse `judge_command` from config | Mechanical | P4 | Already the framework's judge setting | New setting |
| 6 | Eng | Cost logic in `cost.py`, judge in `judge.py` | Mechanical | P5 | `health.py` is 16 KB of 20 KB | Edit health.py |
