# Design: health-repo-rules

## Problem

Health's twelve groups are fixed, and the only extension is Mine, the owner's private rules in `~/.workflow-loop/health.json`.
A repo cannot commit its own rules, tune a default number (the script size cap, the SKILL.md line cap) or turn a default
rule off with a recorded reason.

## Approaches

1. A committed `.loop/health-rules.json` read by the code health already has. Rules run like Mine's (same command runner),
   their rows are placed in their own group, thresholds are repo settings in `.loop/config.json` (so Setup's settings table
   and `fill-repo` document and default them), and an `off` map carries reasons. Cost: edits to existing scripts only
   (enforce.py, health.py, controls.py, report.py, rules.py, issues.py, settings.py), each kept under 20,480 bytes. Risk:
   the same scripts are being changed by health-v1 and backlog-milestones, so this merges after them.
2. A new `repo.py` module. Rejected: the package is at its 99-file cap, and a new file under skills/ is not allowed.

## Chosen

Approach 1.
- Rules: `{"name", "group", "feature", "command", "fix", "break"}`; `group` is one of the twelve or `repo` (a thirteenth
  reporting heading like Mine, before it). `command` is a word list (or one shell string); exit 0 PASS, 2 WARN, 1 FAIL,
  anything else, a timeout or a missing command UNREAD, never a pass. A rule with no `break`, a repeated name or a name of
  a default rule makes health refuse (exit 2) like a built-in rule with no control.
- Controls: the Controls group copies the repo's tracked files to a private temp folder, runs `break` there, then the rule's
  command there; the control fires when the command then exits 1 or 2, is UNREAD if `break` or the copy fails, and FAIL
  ("cannot fire") if the rule still passes.
- Thresholds: `health_script_bytes` (default 20480) and `health_skill_lines` (150) in `.loop/config.json`, in Setup's TABLE.
- Off: `"off": {"<default rule>": "<reason>"}`; the rule does not run, its group prints `INFO <rule>: turned off: <reason>`;
  an empty reason or an unknown rule is UNREAD and the rule stays on.
- Filing: a repo rule's row carries its `feature`; `issues.feature_of` returns it, so filing treats FAIL as a defect and
  WARN as backlog on that feature exactly as it does for default rules (those classes arrive with health-v1 and
  backlog-milestones, which this merges after).
- Setup: `settings.fill_repo` (adoption and update both call it) writes an empty commented `.loop/health-rules.json`
  when absent.

## What the done line needs

A rule in the file runs in the report with its group and feature (toy: a passing, a warning, a failing and an unreadable
rule); its break makes the Controls group see it fail (toy: a rule whose break works fires, one whose break does nothing is
reported as unable to fire); a default turned off shows its reason in the report (toy).

## Open questions

- Repo rules execute committed commands on whoever runs `health.py check`, the same trust as the repo's regression rows;
  Health's usage says so.
