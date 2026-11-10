# Plan: deployments-format

Goal file: .loop/goals/deployments-format.md (done lines frozen). Design: .loop/goals/deployments-format.design.md.

## Implementation plan

### Context

The owner approved ("a", 2026-11-10) an optional Deployments section on feature pages, and widened it the same day to
deliveries people receive. The page contract today refuses any section outside Problem, Usage, Requirements, Non-goals,
Success metrics and Tests. The goal also fixes issue 495 (the govern hook refuses `git pull --ff-only`). Scripts stay
under 20 KB (pageformat.py ends near 19.9 KB, criteria.py 19.1 KB); no new file under skills/ (package cap 99, 97 used).

### Changes

1. skills/workflow-docs/references/template.md: rules keys `deployments_section: Deployments`, `deployments_page:
   Page, Link, Access, Shows, Live build`, `deployments_delivery: Delivery, Channel, Recipients, What's sent, Status`,
   `deployments_access: public, sign-in`; `deployments` added to `format`; the Layout paragraph places the optional
   section between Success metrics and Tests and lists DOC-14 with the format checks; a Deployments bullet gives each
   column's rule.
2. skills/workflow-docs/scripts/pageformat.py: `deployments(page, name, lines, page_cols, delivery_cols, access)` and
   `deployments` in CHECKS. The section holds at most one Page and one Delivery table (a header row inside a run of `|`
   lines starts a new table) and blank lines. Refusals (`FORMAT <Page>:<line>: Deployments: DOC-14 ...`): other lines,
   an empty section, an unknown header, a second table of a kind, a table with no row, a row with the wrong cell count,
   an empty cell, a Page Link not http(s), Access not public/sign-in, Live build not a 7-40 hex sha, an email address in
   Delivery Recipients (the address itself is never echoed).
3. skills/workflow-docs/scripts/criteria.py: rules() reads the new keys; contract() accepts the optional section after
   Success metrics (before Tests) and runs pf.deployments when `deployments` is in `format`. docs.py check reaches this
   through criteria.contract.
4. skills/workflow-docs/scripts/prd.py: review_text and convert_text leave out the optional Deployments section the way
   they leave out Usage. Fingerprints are unchanged (Deployments is not one of them).
5. docs/wiki/Documentation.md: DOC-14 under Functional, a title line and sub-bullets carrying both owner messages and
   the checkable behaviours (one sub-bullet says the live-link and promoted-build check runs in the deploying repo for
   now), stamped Reviewed with `LOOP_OWNER_WORDS="a" criteria.py review DOC-14 --user`, then the page review stamped
   the same way (the Requirements fingerprint changes). Tests re-rendered.
6. skills/workflow-monitoring/scripts/govern_hook.py: `safe_pull(args)`: a `pull` passes only with `--ff-only` and none
   of `-r`, `--rebase`, `--rebase=<mode>`, `--no-ff`, anywhere after `pull`, after the global git options the hook
   already skips.

### Tests

New toy suite dev/toy/test-deployments.sh (made-up repo, no network), one PASS line per check:
- a page without the section passes; a page with a good Page table, a good Delivery table, or both passes (criteria
  contract and docs.py check);
- each malformed form is refused naming table and column: prose, empty section, wrong header, two Page tables, no row,
  wrong cell count, empty cell, bad link, bad access, bad sha, an email in Recipients (and the address is not echoed);
- the section in the wrong place (before Success metrics) is refused as SECTIONS;
- a Deployments edit on a Reviewed page gives neither LOCKED nor CHANGED; `criteria.py review` works on such a page;
  `criteria.py render` keeps the section byte for byte;
- the repo's Documentation page carries DOC-14 Reviewed, and `docs.py check` passes on this repo.
govern hook cases join dev/toy/test-monitoring-prd.sh's mon7 (or a pull495 case): `git pull --ff-only` and
`git -C . pull origin main --ff-only` pass; plain pull, `-r`, `--rebase=merges`, `--no-ff`, `--ff-only --rebase` are
refused (negative controls).

Regression rows (each seen failing on origin/main, then passing):

| Row id | Category | Guards |
|---|---|---|
| deploy-section-optional | criterion | DOC-14 |
| deploy-table-refused | criterion | DOC-14 |
| deploy-not-locked | criterion | DOC-14 |
| deploy-doc14-reviewed | criterion | DOC-14 |
| pull-ff-only-passes | defect | #495 |
| pull-plain-blocked | defect | #495 (negative control) |

### Not in scope

- The live-link and promoted-build check (stays in the deploying repo's pilot; the template takes it later).
- Any change to the PRD fingerprints or to other sections.

## Review record

(written by the plan step's reviewers)

### the review runner run log (run plan review-run-20261110220754, session_kind unattended, status gate_pending)

Host: the review runner. Scope: UI no (2 matches); DX yes (1 term matches, developer tool). Phase order: ceo → dx → eng.
Deviation: plan review guard: not enforced by this host; publication order is unverified (GUARD_NOT_INSTALLED)

#### ceo: closed 2026-11-10T22:16:58.136Z; snapshot 7719b024ef9db0cf37cd44724d01578c9ab656e0e61d4acfeb2be7816d7066f3

- native completed (model claude-opus-5-5, provider host-subagent, 13 findings, sha256 36257b61120f)
- outside completed (model gpt-6-astra, provider host-subagent, 6 findings, sha256 4ae8e7da3b6b)

```
CEO DUAL VOICES — CONSENSUS TABLE:
  Severity        claude-opus-5-5(native)      gpt-6-astra(host-subagent)
  Critical        0                            0
  High            2                            2
  Medium          7                            4
  Low             3                            0
  Informational   1                            0
  Findings        13                           6
CONFIRMED 0 · SAME LOCATION, UNVERIFIED 4 · DISAGREE 0 · NEW (outside only) 2 · native only 9. Both completed.

Reconciliation (each outside finding against the native result):
| outside | native | disposition | resolution |
|---|---|---|---|
| plan review-run-20261110220754-ceo-outside-1 Deployment claims have no provenance or freshness contract | plan review-run-20261110220754-ceo-native-3 Bespoke Deployments code instead of a declared optional-table-section mechanism in the rules block; next section will cost another ~3 KB of script | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:225): Bespoke Deployments code instead of a declared optional-table-section mechanism in the rules block; next section will cost another ~3 KB of script |
| plan review-run-20261110220754-ceo-outside-2 Review exemption includes audience and content commitments | — | new | not raised by the native voice |
| plan review-run-20261110220754-ceo-outside-3 Unconditional optionality cannot enforce DOC-14 completeness | plan review-run-20261110220754-ceo-native-12 Deployments is placed before the last rules section (want[:-1]) rather than after Success metrics by name | unverified | same location, agreement unverified (skills/workflow-docs/scripts/criteria.py:214): Deployments is placed before the last rules section (want[:-1]) rather than after Success metrics by name |
| plan review-run-20261110220754-ceo-outside-4 Template schema freezes unvalidated pilot assumptions | plan review-run-20261110220754-ceo-native-2 Plan spends the last headroom: pageformat.py 19,881 B = 97.1% of the 20 KiB cap (health WARN >= 90%), criteria.py 93%, and no new files allowed | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:217): Plan spends the last headroom: pageformat.py 19,881 B = 97.1% of the 20 KiB cap (health WARN >= 90%), criteria.py 93%, and no new files allowed |
| plan review-run-20261110220754-ceo-outside-5 Package headroom does not support the promised follow-on work | — | new | not raised by the native voice |
| plan review-run-20261110220754-ceo-outside-6 Independent pull fix is coupled to deployment schema rollout | plan review-run-20261110220754-ceo-native-5 safe_pull passes forced ref updates: 'git pull --ff-only origin +side:main', '-f', and combined '-vr' all PASS; +refspec demonstrably rewrote a local branch on git 2.39.5 | unverified | same location, agreement unverified (skills/workflow-monitoring/scripts/govern_hook.py:56): safe_pull passes forced ref updates: 'git pull --ff-only origin +side:main', '-f', and combined '-vr' all PASS; +refspec demonstrably rewrote a local branch on git 2.39.5 |
| — | plan review-run-20261110220754-ceo-native-1 Live build and Status are hand-typed live data with only a format check; template text claims 'the sha in the page's build.txt' and DOC-14 reads as a guarantee nothing enforces | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-ceo-native-4 Private/sign-in Link cells may carry share tokens or signed URLs onto a possibly public wiki; email check covers only Delivery Recipients | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-ceo-native-6 Issue 495's own alternative (merge.py fast-forwards the local base, like other post-merge steps running git in-process) dismissed without analysis | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-ceo-native-7 Every Page row must have a hex Live build, but external or third-party pages (hosted SaaS, docs, newsletter archives) have no build.txt, inviting fake shas | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-ceo-native-8 prd.py convert_text on a page with Deployments but missing Non-goals/Success metrics inserts them before '## Tests', after Deployments, producing a page the contract refuses; plan claims convert works but has no test | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-ceo-native-9 Regression rows claimed 'each seen failing on origin/main', but pull-plain-blocked and deploy-section-optional already pass on origin/main (pull is in WRITES at govern_hook.py:30) | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-ceo-native-10 DOC-14's widened delivery clause and worker-written sub-bullets are stamped Reviewed with the owner's 'a', which predates the widening | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-ceo-native-11 operation.md and commands.md list blocked git verbs without pull; after the change they should say pull is blocked except --ff-only | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-ceo-native-13 Access (public vs sign-in) is outside the fingerprints, so flipping a row to public on a Reviewed page passes silently | native_only | not raised by the outside voice |
```

#### design: skipped (no UI scope detected)

#### dx: closed 2026-11-10T22:24:21.541Z; snapshot 7719b024ef9db0cf37cd44724d01578c9ab656e0e61d4acfeb2be7816d7066f3

- native completed (model claude-opus-5-5, provider host-subagent, 12 findings, sha256 a6d59f92da96)
- outside completed (model gpt-6-astra, provider host-subagent, 17 findings, sha256 413b624d8304)

```
DX DUAL VOICES — CONSENSUS TABLE:
  Severity        claude-opus-5-5(native)      gpt-6-astra(host-subagent)
  Critical        0                            5
  High            3                            7
  Medium          5                            5
  Low             3                            0
  Informational   1                            0
  Findings        12                           17
CONFIRMED 0 · SAME LOCATION, UNVERIFIED 5 · DISAGREE 0 · NEW (outside only) 12 · native only 7. Both completed.

Reconciliation (each outside finding against the native result):
| outside | native | disposition | resolution |
|---|---|---|---|
| plan review-run-20261110220754-dx-outside-1 CAP4:deployments-diagnostics:redaction Raw diagnostic values expose credentials and addresses | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-2 CAP4:govern-hook-check:channel BLOCK exits successfully | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-3 CAP4:govern-hook-denial:fix Refusal advertises bypassing governance without authorization | plan review-run-20261110220754-dx-native-2 CAP6:govern_hook pull deny:fix - refusal of a non-ff pull tells the agent to hand off to a worker instead of naming 'git pull --ff-only' | unverified | same location, agreement unverified (skills/workflow-monitoring/scripts/govern_hook.py:33): CAP6:govern_hook pull deny:fix - refusal of a non-ff pull tells the agent to hand off to a worker instead of naming 'git pull --ff-only' |
| plan review-run-20261110220754-dx-outside-4 CAP4:govern-hook-evaluation:channel Failed policy evaluation silently permits execution | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-5 CAP4:govern-hook-exception-log:redaction Raw exceptions can disclose secrets through logs and health output | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-6 CAP6:deployment-rules:fix Invalid configured columns crash without identifying a repair | plan review-run-20261110220754-dx-native-10 DOC-14 FORMAT lines carry no doc anchor; rules() REFUSED does not name the broken key | unverified | same location, agreement unverified (skills/workflow-docs/scripts/criteria.py:67): DOC-14 FORMAT lines carry no doc anchor; rules() REFUSED does not name the broken key |
| plan review-run-20261110220754-dx-outside-7 CAP6:govern-hook-evaluation:fix Evaluator failures provide no caller-visible remediation | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-8 CAP6:unexpected-failures:recovery Schema and hook failures omit side effects and bounded recovery | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-9 CAP6:unexpected-failures:context Runtime diagnostics omit active configuration and sanitized causes | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-10 CAP6:unexpected-failures:trace Unexpected failures lack a compact redacted trace contract | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-11 Conversion reports completion while placing Deployments in an invalid section order | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-12 Fast-forward pull exception accepts combined rebase options and forced refspecs | plan review-run-20261110220754-dx-native-1 safe_pull denylist passes 'git pull --ff-only --ff' (last ff flag wins: verified merge commit on git 2.39.5), plus -vr, -f, +refspec | unverified | same location, agreement unverified (skills/workflow-monitoring/scripts/govern_hook.py:56): safe_pull denylist passes 'git pull --ff-only --ff' (last ff flag wins: verified merge commit on git 2.39.5), plus -vr, -f, +refspec |
| plan review-run-20261110220754-dx-outside-13 Deployment failures use stdout and lack documented error targets | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-14 Plan and implementation disagree on HTTP links and SHA syntax | plan review-run-20261110220754-dx-native-5 Uppercase sha refused with 'not a 7 to 40 hex sha' although it is hex | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:220): Uppercase sha refused with 'not a 7 to 40 hex sha' although it is hex |
| plan review-run-20261110220754-dx-outside-15 Deployment onboarding lacks complete examples and pull exception documentation | — | new | not raised by the native voice |
| plan review-run-20261110220754-dx-outside-16 Validator accepts missing table separators and HTTPS strings without a host | plan review-run-20261110220754-dx-native-6 template.md requires the separator row but the checker accepts a table without one | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:225): template.md requires the separator row but the checker accepts a table without one |
| plan review-run-20261110220754-dx-outside-17 Toy assertions cannot detect broken exit statuses or failure streams | — | new | not raised by the native voice |
| — | plan review-run-20261110220754-dx-native-3 Deployments Link accepts embedded credentials/tokens and a non-https Link is echoed verbatim in the FORMAT refusal | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-dx-native-4 Plan item 2 and Tests are stale: say 'Link not http(s)' and a bare sha, but HEAD refuses http and requires backticks | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-dx-native-7 No copy-paste example table: headers are given only inline in prose | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-dx-native-8 Live build is mandatory with no escape value for pages that have no build.txt (external/SaaS) | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-dx-native-9 Email check misses dotless addresses (ops@corp, me@localhost) | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-dx-native-11 operation.md / commands.md not updated to say 'git pull --ff-only' now passes the govern hook | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-dx-native-12 With 'deployments' absent from format, section placement is accepted but contents go unchecked (undocumented) | native_only | not raised by the outside voice |
```

#### eng: closed 2026-11-10T22:28:50.176Z; snapshot 7719b024ef9db0cf37cd44724d01578c9ab656e0e61d4acfeb2be7816d7066f3

- native completed (model claude-opus-5-5, provider host-subagent, 12 findings, sha256 40587c3ae0df)
- outside completed (model gpt-6-astra, provider host-subagent, 11 findings, sha256 05ee12d5a0c3)

```
ENG DUAL VOICES — CONSENSUS TABLE:
  Severity        claude-opus-5-5(native)      gpt-6-astra(host-subagent)
  Critical        0                            0
  High            2                            2
  Medium          5                            9
  Low             4                            0
  Informational   1                            0
  Findings        12                           11
CONFIRMED 0 · SAME LOCATION, UNVERIFIED 6 · DISAGREE 0 · NEW (outside only) 5 · native only 6. Both completed.

Reconciliation (each outside finding against the native result):
| outside | native | disposition | resolution |
|---|---|---|---|
| plan review-run-20261110220754-eng-outside-1 Pull exception admits conflicting options and forced ref updates | plan review-run-20261110220754-eng-native-2 safe_pull is a denylist: 'git pull --ff-only --ff' (merge commit, verified on git 2.39.5), '+src:dst' forced refspecs, -f and combined short flags all pass | unverified | same location, agreement unverified (skills/workflow-monitoring/scripts/govern_hook.py:58): safe_pull is a denylist: 'git pull --ff-only --ff' (merge commit, verified on git 2.39.5), '+src:dst' forced refspecs, -f and combined short flags all pass |
| plan review-run-20261110220754-eng-outside-2 Deployment diagnostics disclose credentials and email addresses | plan review-run-20261110220754-eng-native-3 The DOC-14 privacy promise breaks: a prose-line refusal echoes an email address verbatim, and addresses in Channel, What's sent or Page cells are accepted without a refusal | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:237): The DOC-14 privacy promise breaks: a prose-line refusal echoes an email address verbatim, and addresses in Channel, What's sent or Page cells are accepted without a refusal |
| plan review-run-20261110220754-eng-outside-3 Conversion inserts missing sections after Deployments | — | new | not raised by the native voice |
| plan review-run-20261110220754-eng-outside-4 Unvalidated deployment schemas can crash or overwrite cells | — | new | not raised by the native voice |
| plan review-run-20261110220754-eng-outside-5 Table validation accepts missing and malformed separators | plan review-run-20261110220754-eng-native-9 A Deployments table without a separator row is accepted, although template.md requires one | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:227): A Deployments table without a separator row is accepted, although template.md requires one |
| plan review-run-20261110220754-eng-outside-6 URL validation accepts HTTPS strings without a host | plan review-run-20261110220754-eng-native-4 The Page Link check accepts credentials and tokens (https://user:pw@host/?token=...), which then go onto a possibly public wiki | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:220): The Page Link check accepts credentials and tokens (https://user:pw@host/?token=...), which then go onto a possibly public wiki |
| plan review-run-20261110220754-eng-outside-7 Recipient validation accepts dotless email addresses | plan review-run-20261110220754-eng-native-8 An uppercase hex sha is refused with the message 'not a 7 to 40 hex sha', which misleads | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:222): An uppercase hex sha is refused with the message 'not a 7 to 40 hex sha', which misleads |
| plan review-run-20261110220754-eng-outside-8 Unbounded recipient regex has superlinear failure cost | — | new | not raised by the native voice |
| plan review-run-20261110220754-eng-outside-9 Toy assertions discard command failures and exit-status regressions | — | new | not raised by the native voice |
| plan review-run-20261110220754-eng-outside-10 Pull negative control lacks the claimed baseline failure | — | new | not raised by the native voice |
| plan review-run-20261110220754-eng-outside-11 Plan and implementation disagree on URL and SHA acceptance | plan review-run-20261110220754-eng-native-12 Bespoke deployments() leaves pageformat.py at 19,868 of 20,480 B. A declared optional-table-section mechanism (Shape B) would avoid the next split and would have owned the optional-section list | unverified | same location, agreement unverified (skills/workflow-docs/scripts/pageformat.py:220): Bespoke deployments() leaves pageformat.py at 19,868 of 20,480 B. A declared optional-table-section mechanism (Shape B) would avoid the next split and would have owned the optional-section list |
| — | plan review-run-20261110220754-eng-native-1 render.py skips any page with a Deployments section, so its Tests table never re-renders, render --check says TABLES OK, and docs check's DOC-9 refusal names a fix that cannot work | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-eng-native-5 The test plan misses the failure paths that matter: render on a Deployments page with changed rows, pull negative controls for --ff and +refspec, convert with Deployments, format without deployments, exit codes | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-eng-native-6 Deployments is placed before the last configured section (want[:-1]), not after Success metrics by name. prd convert_text, given a page with Deployments and a missing Non-goals or Success metrics, inserts them after Deployments | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-eng-native-7 An empty Deployments section is reported at line 1 instead of the heading line | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-eng-native-10 The #495 pull cases are in the DOC-14 suite (test-deployments.sh), not in test-monitoring-prd.sh mon7 as the plan says, and operation.md still lists the blocked verbs without the pull exception | native_only | not raised by the outside voice |
| — | plan review-run-20261110220754-eng-native-11 Two independent changes ship in one lane: the DOC-14 schema and the #495 hook fix, so a docs-side defect (F1) blocks the hook fix | native_only | not raised by the outside voice |
```

Gate: gate_rev 1, 8 decisions (8 pending). Findings: 71. Tasks: 23.

### Worker's response to the findings (applied in build)

- Pull (all phases, both voices): `git pull` is an allowlist now: `--ff-only`, `-q`/`--quiet`, `-v`/`--verbose`, a remote and
  plain branch names; `--ff` after `--ff-only`, a `+src:dst` refspec, `-f`, `-vr`, `--rebase[=mode]`, `-r` and `--no-ff`
  are refused, with negative-control rows.
- render (Eng native): render and prd convert leave out Deployments like Usage, and convert inserts missing Non-goals or
  Success metrics before Deployments; a toy case proves render rewrites a stale Tests table on a page with Deployments.
- Secrets (DX, Eng): a Link with a user, password or token-like query key is refused and never echoed; an email address
  anywhere in a Delivery row is refused and never echoed.
- Pilot shape (operation session, 2026-11-10): Link a full https URL, Live build the sha in backticks.
- Kept the owner's direction (gate defaults a): Deployments-specific rules rather than a generic optional-section
  mechanism (uc1), one goal for the schema and #495 (d5, d6), the hook's documented fail-open (DX outside F4) and the
  shape-only check with the live check in the deploying repo (d3, CEO native).
- Size (CEO native d4): pageformat.py ends at 20,131 of 20,480 bytes; the next optional section needs a split first.
