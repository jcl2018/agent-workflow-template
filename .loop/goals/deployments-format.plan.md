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
