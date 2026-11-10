# Design: docs-format

Status: idea for the plan step. It meets the frozen done lines in `.loop/goals/docs-format.md` and changes none of them.

## The owner's problem

The owner talks to the agent in plain sentences, reads the wiki to decide what to review, and wants one place to see
every test. Today:

- Home is a long essay.
- The README has no per-feature "how to use" in the owner's own phrasing.
- Usage lines mix prose with commands.
- Requirements are long single paragraphs.
- Problem sections describe code (scripts, config keys, file paths).
- Tests are long Given/When/Then bullet lists with no run report.
- No rule says that every issue belongs to a milestone.

None of these shapes is checked, so pages drift back as soon as a goal edits them. The owner's words are in
`.local/docs-format-draft.md` (condensed in the goal). The owner later added this about the cap: "for the
documentation, I want you to make that cap as like a config as well, and probably do that as 10 as default."

## Premises

1. **Every new rule is a `docs.py check` rule.** A shape that isn't checked won't last.
   - Each refusal names the page, the section and the rule: `FORMAT Page: Section: DOC-n <what is wrong>. Fix: <how>`.
2. **Reviewed wording stays locked (DOC-2).**
   - Requirement lines the owner stamped keep their words.
   - The new shape adds structure around them, such as sub-bullets, instead of rewording them.
   - Only DOC-4..DOC-6 on the Documentation page are reworded. The operation session relayed the owner's mapping for
     these, and they go back to Unreviewed.
3. **Meaning is kept.** Wherever a page's meaning changes, the PR's review list names it.
4. **Size.**
   - `criteria.py` is at 20356 of 20480 bytes, so no new code goes into it.
   - New checks go into a new module, `skills/workflow-docs/scripts/pageformat.py`, which `docs.py` imports the way
     it imports `counting`.
   - The Tests rendering moves out of `criteria.py` into that module, which frees room.
5. **Health stays a fixed-rule check.**
   - The new issue rule reads GitHub through `gh`.
   - When `gh` can't answer, the row reads UNREAD, the way the cost rule does with no tokens. It never guesses.

## The Documentation requirements (the mapping the operation session relayed)

| ID | Rule | Was |
|---|---|---|
| DOC-1..3 | unchanged, Reviewed | unchanged |
| DOC-4 | Home is one table | One command enforces it (Reviewed) |
| DOC-5 | The front door is natural language | Required docs and milestones (Reviewed) |
| DOC-6 | Usage is an API reference | Usage as asks (Reviewed) |
| DOC-7 | Requirements are bullets | new |
| DOC-8 | Problem is the user's problem | new |
| DOC-9 | Tests are a table with links | new |
| DOC-10 | One full Tests page, and every open issue on a feature milestone or Backlog | new (draft DOC-10 + DOC-11) |

- **The cap:** `criteria_max` stays a config setting, and its default becomes 10. This changes setup's default in
  `settings.py` and `references/settings.md`, `criteria.py`'s fallback (one constant), and this repo's
  `.loop/config.json`.
- **Rows that guarded the old DOC-4..6 move:**
  - Old DOC-4 rows (14: stale pages, audit, publish, counts) guard DOC-1. That is the template the one command
    enforces, so DOC-1's text doesn't change.
  - Old DOC-5 rows (4: milestones, release note) guard DOC-10.
  - Old DOC-6 rows (2) guard the new DOC-6. `usage-agent-requests` is replaced by a row for the API shape.
- **Meaning change for the owner:** "the release step runs the one command, it never deletes a page, publish can be
  undone" and "a release note for every release" are no longer requirement text. Their tests stay, under DOC-1 and
  DOC-10.

## Approach

Each rule below is enforced in `pageformat.py`, called from `docs.py check` (via `contract`).

1. **DOC-4, Home.**
   - Home holds the `<!-- workflow-docs -->` marker, `# title`, `## Features` and one table, and nothing else.
   - The header is exactly `| Feature | Description | Page | How to use | Milestone |`.
   - Each row has a wiki link to an existing feature page, a link to `README#how-to-use-<feature>`, and a milestone URL.
   - Every feature page in `docs.tsv` has a row.
   - Home's current essay (the no-gates warning, how to read the charts, what is and isn't proven, gaps) moves to the
     README. That move is listed in the PR.
2. **DOC-5, README front door.**
   - The README gets `## How to use` with one `### <Feature>` per feature page.
   - Each entry is a bullet: `- "<phrase the owner says>" — <what happens next>`.
   - The check fails a How-to-use section that has no phrase bullet, a backtick command, or a line starting with `/`,
     `python` or `bash`.
   - The README's command reference elsewhere stays.
3. **DOC-6, Usage as API.**
   - Usage is a list of `### `/skill verb`` entries, and each entry has `- Syntax:`, `- Prints:` and `- Refuses:` bullets.
   - `Arguments:` is optional when there are none. `Refuses:` gives the exit code and message, or `nothing`.
   - No other lines are allowed except blank ones.
   - The existing rules stay: no `.py`/`.sh` names, and each `/skill verb` must be in the Command map.
4. **DOC-7, Requirements.**
   - Each `- ID: ...` line has at least one nested `  - ` bullet, and each bullet is one sentence of at most 30 words.
   - An Unreviewed requirement line is at most 20 words, a title.
   - A Reviewed line keeps its locked wording, and its bullets break it down underneath.
   - Fingerprints and requirement hashes are unchanged: they cover the line, and sub-bullets are part of the PRD `R=`
     fingerprint only. The plan step must confirm this against `criteria.py`/`prd.py`.
5. **DOC-8, Problem.**
   - The Problem has no backtick code, no file path or extension, and no word from a `problem_banned` list in the
     template sheet's `rules` block: script, function, flag, regex, json, tsv, config, routine.
   - It is at most `problem_lines` lines. The `Skill:` lines leave the Problem; the skill name goes into the Usage
     entries.
6. **DOC-9, Tests table.**
   - `criteria.py render` (moved into `pageformat.render`) writes one table per page:
     `| Test | Kind | Guards | Checks | Last result | Report |`.
   - Checks is the row's one-line Given/When/Then. Report links to `Tests#t-<row>`.
   - A requirement with no row gets a `not enforced` row, and every defect row appears.
   - The check fails a Tests section that isn't exactly the rendered table (the existing staleness test) or is missing
     a requirement.
7. **DOC-10, the full Tests page and issue milestones.**
   - `render` also writes the generated page `docs/wiki/Tests.md`: a `## <Feature>` section per feature, then a table
     `| Test | Kind | Guards | Result | Date | Run | Seen failing |`, whose first cell carries `<a id="t-<row>"></a>`.
   - The check reports Tests.md STALE when it differs from a fresh render.
   - **Run link:** `regression.py run` adds a fourth column `run` to `regression-runs.tsv`. In CI it holds
     `$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID`; elsewhere it is empty, shown as `local`.
     Old 3-column files still read.
   - **Health:** a new `issue-milestones` rule FAILs each open issue with no milestone (`gh issue list --state open
     --json number,milestone`). It reads UNREAD when `gh` fails. MAX_RULES goes 12 → 13 on purpose, with a negative
     control in `controls.py`.
   - The feature page's Milestone line stays required.
8. **Rewrites.** Home, README How-to-use, and the six feature pages (Problem, Usage, Requirements bullets, Tests via
   render) are rewritten, keeping each requirement's meaning.
   - Other goals edit `docs/wiki` (loop-guards, lane-control, board-estimates, automation), so: merge main before the
     rewrite, and again before review and before pr.
9. **Tests.**
   - `dev/toy/test-docs-format.sh`: for each of DOC-4..DOC-9 a bad page fails naming the page, section and rule, and a
     good page passes. Also: Tests.md stale and fresh, the 4-column runs file, and the health issue rule with fakegh
     (an issue with and without a milestone, and gh failing → UNREAD).
   - One regression row per check, each made red with `regression.py red --break`.
   - Plus `docs.py check` and `health.py check` green on this repo.

## Alternatives considered

- **B: put the rules only in the template sheet's prose and leave the audit to list them.** Rejected: the done line
  needs `docs.py check` to enforce them.
- **C: rewrite reviewed requirement lines into short titles and unreview all ~34 stamps.** Rejected for now: DOC-2 says
  only the owner un-reviews, and the owner asked for DOC-4..6 only. The sub-bullets give the bullet shape without
  touching locked words. The owner can shorten titles in the final review.

## Risks

- **Concurrent docs edits** cause merge conflicts on the wiki pages. Mitigation: merge often, re-render Tests after
  each merge, never hand-edit Tests.
- **The size of `criteria.py`/`regression.py`/`health.py`** (all near 20 KB). Mitigation: move code out of them, and
  keep the health `size` rule green.
- **A Home and README rewrite drops content the owner relies on.** Mitigation: move it, don't delete it, and list each
  move in the PR.
- **GitHub wiki anchors** (`#t-row`) depend on the wiki keeping `id` attributes. The fallback is the feature heading
  anchor. Mitigation: check this by hand after publish, as a Verify-by-hand step.

## Proof (done lines → evidence)

1. Documentation page: DOC-4..DOC-10 per the mapping, Unreviewed (`git diff`, docs check).
2. The toy test names the page, section and rule for each of DOC-4..9; the regression rows were seen red.
3. `docs/wiki/Tests.md` is generated, each feature's Tests table links into it, and the check reports it stale when
   behind.
4. The health issue rule passes its toy test with fakegh, and each page has its Milestone line.
5. Rewritten pages pass `docs.py check`, and the PR lists meaning changes.
6. `dev/toy/test-docs-format.sh` passes; docs check and health are green.
7. The PR body's review list covers each page and what changed, plus the DOC mapping.

STEP: done
