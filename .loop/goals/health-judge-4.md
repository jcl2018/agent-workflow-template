# Rebuild the Health suggestions step as a judge of criteria quality, test quality and performance and tokens, and add a Cost rule, with the owner's new HLT-2 and HLT-5 wording approved in chat on 2026-11-08

- Slug: health-judge-4
- Touches: skills/workflow-health, docs/wiki, dev/toy, .loop/config.json

## Done lines

Frozen. A wrong done line needs a new goal.

1. HLT-2 and HLT-5 are unreviewed and rewritten word for word as follows, then marked Reviewed 2026-11-08 with criteria.py review --user, since the owner approved this wording in chat: HLT-2 "The rules. Health checks exactly these rules: Size (every script stays under 20 KB, with a warning from 90%); Criteria (every criterion has a test seen failing once and passing now; done lines with no test are a warning); Docs (every required doc matches the template and the code; a stale page is a warning, any other gap fails); Hygiene (no more than 5 open findings, no goal waiting on me over 24 hours, no leftover merged branches); Cost (a goal over its time or token budget is a warning, naming the slowest or costliest steps); Mine (any rules I add of my own, named in a private setting). Adding a rule means retiring one or raising the cap on purpose. A rule may run an existing command to get its data." HLT-5 "Judge and next steps. After the rules, a separate judge section, marked as suggestions and never part of the verdict, reviews three things: criteria quality (whether each criterion is clear, testable and high-level enough, whether any conflict or overlap, and whether a feature is missing one, suggesting better wording that only I can apply); test quality (whether each criterion's tests and each defect's test really prove what they claim, or are weak, miss cases or test the wrong thing, suggesting stronger or missing tests for both categories); and performance and tokens (where the framework's skill steps, prompts, scripts, waits and retries could cut delivery time or token use, ranked by the savings). It ends with ranked next steps from the judgments, the warnings and the failures."
2. The Cost rule reads each goal's time and tokens per step from its run record, compares them with time and token budgets in .loop/config.json, warns on a goal over either, names its slowest or costliest steps, and prints UNREAD when no tokens were recorded
3. The health command runs the judge after the rules; the rule part and its verdict stay model-free and give the same answer twice, and the judge's output never changes the verdict
4. The judge reads every criterion, every criteria and defect test row with its command, and the skill files, prompts and recent goals' step times and tokens; it prints its three reviews in the health template's judge section, puts suggested criterion wording under Needs you, and lists weak tests and performance or token savings as candidate goals ranked by savings
5. A toy test with a stand-in judge proves the Cost rule, the judge section's format, that the verdict is unchanged by it, and that criterion suggestions land under Needs you; the repo checks pass and every script stays under 20 KB

## Verify by hand

1. Run `python3 skills/workflow-health/scripts/health.py check --family cost`.
   Expect: a `cost` group; each goal over `time_budget_minutes` or `token_budget` is a WARN naming its slowest or costliest steps, and `UNREAD cost tokens` prints if no recent goal recorded tokens.
2. Run `python3 skills/workflow-health/scripts/health.py judge`.
   Expect: the normal report and `HEALTH:` line, then `JUDGE (suggestions, never part of the verdict)` with criteria quality, test quality, performance and tokens, `Needs you`, candidate goals and next steps (or `JUDGE UNAVAILABLE: ...` if the judge fails), with the same exit code as `check`.

