# Plan: regression-summary

Goal: `.loop/goals/regression-summary.md` (7 frozen done lines). Design: `.loop/goals/regression-summary.design.md` (Approach B).

## Implementation plan

### 1. Issue 92 at the root (done line 2)
- `skills/workflow-regression/scripts/actions.py`: `ROW_ENV` also drops `GITHUB_STEP_SUMMARY`, so no row (and no toy test it starts) can write into the real run summary. Regenerate `.github/workflows/regression.yml` with `regression.py workflow`.
- `regression.py run` (the local and loop runner) gets the same rule for its row environment, so the one command stays the same everywhere (REG-3).
- New defect row `summary-only-real-rows` (category defect, link https://github.com/jcl2018/agent-workflow-template/issues/92, goal REG-2, level land) in `dev/toy/test-regression.sh`: a row that appends `FIXTURE-LEAK` to `$GITHUB_STEP_SUMMARY`; after the runner ends, the summary file holds the real rows and no `FIXTURE-LEAK`. Seen failing with `regression.py red summary-only-real-rows --break` that removes the strip.
- PR body says "Closes #92".

### 2. One renderer: `skills/workflow-regression/scripts/tests.py` (done lines 3, 4, 6)
Stdlib only, under 20 KB, no imports from other skills, so the workflow can embed it.
- Inputs: wiki pages (folder from `.loop/config.json` `wiki_dir`, default `docs/wiki`): page title = feature, requirement IDs and words under `## Requirements` (or `## Criteria`), outside code fences; `.loop/regression.tsv`; `.loop/regression-runs.tsv` (id, status, date); `.loop/regression-issues.tsv` (link, state, date).
- Grouping: a row joins the feature whose page holds the requirement in its goal (or its id); defect rows the same; anything else joins "Other". Features in page order, then Other; rows in file order. Draft rows are left out.
- Fields, in order, the one fixed format: Test, Kind (requirement | defect), Guards (`REG-2: <words>` or `[#92](url) open`), Checks (description), Runs (both | nightly | by a person), Result (`PASS 2026-11-09` or `not run`), Seen failing (date or no).
- Commands:
  - `tests.py list [--markdown]`: the grouped list from the recorded runs; plain lines (one per test, fields joined by " | ", a `== Feature` line per group) or Markdown (one `### Feature` table per group).
  - `tests.py summary --results FILE --took SECONDS`: the GitHub run summary: one header `## Regression: N passed, N failed, N skipped of N, in Xm Ys`, then one table per feature with Test, Kind, Guards, Checks, Result, from that run's results file (id<TAB>state lines).
  - `tests.py issues [--write]`: read each defect link's issue state with `gh issue view` and print it, or write `.loop/regression-issues.tsv`; a finding link is "finding", an unreadable issue is "unknown".
- Words in table cells escape `|` and newlines.

### 3. The workflow uses it (done line 3)
- `actions.py`: the run step writes each row's result (id, state) to a results file as the row ends and prints it to the job log; after the loop it runs `tests.py summary` once. A job cut off before that loses the summary, which the job budget prevents (a row that doesn't fit is skipped, not started).
- `regression.py workflow` embeds `tests.py`'s source into the workflow as a heredoc written to a temp file, so a consumer repo needs only its own checkout. The step also refreshes issue states with `tests.py issues` before rendering (the job has the token; rows do not).
- The existing test that the committed workflow equals the generated one covers the embedding.

### 4. The wiki and the health report use the same fields (done line 4)
- `skills/workflow-docs/scripts/criteria.py` (outside the declared touches; the PR says so): `scenario()` takes its fields from `tests.py` (imported from the sibling skill folder; if missing, the line stays as today). Each line becomes: `<Given/When/Then words> — [id](link), <kind>, guards <REG-2 | [#92](url) open>, <runs>, <result date>, seen failing <date|no>`. Headings stay `#### ID` + words (the grouping by feature is the page itself), and **not enforced** stays. Keep the edit small: criteria.py is at 19,117 bytes.
- Update the rows that pin today's line shape (`tests-table-columns`, `tests-row-shape`) to the new fields.
- `skills/workflow-health/scripts/health.py`: after the report, print `TESTS` and the plain grouped list from the sibling `tests.py list`; health stays read-only and its verdict is unchanged.
- Re-render the wiki with `criteria.py render`.

### 5. Descriptions (done line 5)
- Already true on main: `sync` prints no `NODESC`, issue 91 is closed. Add to `every-row-described` a check that no description is longer than one line or empty after trimming; record its result in the run.

### 6. Toy proof of the format (done line 6)
- `dev/toy/test-summary.sh` (new): a made-up repo with two wiki pages (features Alpha and Beta), requirement rows and defect rows (one issue link, one finding), a runs file and an issues file; checks `tests.py list --markdown` and `tests.py summary` output: one header with totals and time, one table per feature in page order, each row's kind, guards (ID and words, or issue link and state), checks and result; and a row guarding nothing lands in Other. Row `summary-format` (goal REG-2), seen failing by breaking the grouping.

### 7. REG-2 and the PRD scenarios (done lines 1, 7)
- `criteria.py unreview REG-2 --user`, replace the REG-2 line with the owner's wording word for word, `criteria.py review REG-2 --user --date 2026-11-08`.
- Each done line gets one or more Given/When/Then rows under the requirement it serves (REG-2 for 1, 3, 4, 5, 6; the defect section for 2; DOC-3's own page links stay), each with a row id, so `criteria.py render` lists it with its last result.

### 8. Checks before review
- Land lane passes (operation's "go" is needed for full lanes), docs check OK, health green, every script under 20 KB, package check passes.

### Review changes taken into the build (autoplan, 2026-11-09; recommended answers, direction kept)
Autoplan ran CEO, DX and Eng on the native voice; the outside voice (Codex) was unavailable: its policy model is not supported with this Codex login. 38 findings, 1 Critical, 12 High. The gate stays pending (unattended runs never approve); the three user challenges keep the stated direction (recommended). The fixes below change no direction and are build obligations:
- Order: the issue 92 fix lands as its own commit first, before any renderer work (ordering only).
- Runner environment: rows lose every runner file-command variable (GITHUB_STEP_SUMMARY, GITHUB_ENV, GITHUB_OUTPUT, GITHUB_PATH, GITHUB_STATE) plus the tokens. One shared name list lives in actions.py; regression.py run and red use it. lanes.py stays untouched (narrow-rows owns it). regression.py has about 144 bytes of headroom, so its edit must be a net shrink or a one-line import. Behavior change: local runs now strip the tokens and those variables from rows too.
- Summary resilience: each row appends id<TAB>state to a results file under $RUNNER_TEMP (a path no row's environment names) as it ends; a separate step with `if: always()` renders `tests.py summary`, and if that render fails it writes the flat id/state table plus one error line. The row step's exit code is unchanged by the summary. Known failures show as KNOWN and are counted in the header.
- Embedding: actions.py gets one render function used by both `regression.py workflow` and the equality test; the embedded copy is indented to the block under a unique quoted delimiter, and the writer refuses when tests.py contains `${{`, the delimiter line or `@CRON@`. The test also checks that the embedded copy equals tests.py.
- The defect row for issue 92 regenerates the workflow from actions.py in its toy repo (as the ci-block harness does), so `red --break` (a sed on the drop list) really turns it red.
- tests.py issues: one `gh auth status` probe; on failure it says so on stderr, exits non-zero and writes nothing; `/pull/` links read through `gh pr view` (open, merged, closed); an unreadable link keeps its last recorded state. `regression.py run` (live) refreshes the issues file so it has an owner outside CI; the state shows its date.
- tests.py summary refuses a missing or malformed results file, an unknown state word or a non-number --took with `REFUSED: ... Fix: ...` and exit 2. States: PASS, FAIL, SKIPPED, KNOWN.
- Mappings: category criterion -> requirement, defect -> defect, anything else shown as written; level land -> both, nightly -> nightly, covered -> by a person (covered rows show "not run" in a run summary). Goal `-` or `slug:N` -> Other; a requirement ID on two pages belongs to the first page in page order.
- Escaping: `|` escaped, whitespace runs (newlines included) collapsed, in Markdown and plain output; a toy case has a description with `|`, a backtick and a newline. `list --tsv` gives agents one machine form. `--root` overrides the repo root.
- criteria.py: no silent fallback. It loads tests.py from the sibling skill; if it's missing it prints a NOTE naming the path and keeps today's line shape, and the docs rows pin the new shape so a missing tests.py shows as STALE, not a quiet change. (It keeps its own requirement parser this goal; a shared parser is a follow-up.)
- health.py: the TESTS block prints before the HEALTH verdict, so the verdict stays the last line; a missing or failing tests.py leaves the verdict unchanged and prints one NOTE.
- Docs: workflow-regression skill text, commands reference and the Regression wiki page describe tests.py and the new line shape; the PR body lists the behavior changes (criteria.py line shape, health TESTS block, local row env) and that the touches grew to skills/workflow-docs/scripts/criteria.py because done line 4 needs it (there is no command to widen touches: issue 157).

## Review record

Autoplan run: gate pending, artifact valid. Phase coverage: ceo native 10 findings, dx native 12, eng native 16; outside voice unavailable in all three. Gate items: d1/d2/d3 keep direction (recommended), p1 approve as-is (recommended, pending: unattended).
