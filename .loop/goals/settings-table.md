# Every adopted repo's wiki Home and its README show the loop's settings table: each setting's name, what it means, how to set it, its default, and this repo's value when it overrides the default; the README names and links the template repo the loop came from; adoption output points to both (owner, 2026-11-11: "in the home page, it will show the setup of all the local commit figs, like the actual name and what does it mean, how to set it, like at the default value or if there's overridden value. And so for the adoption, you should link mention somewhere, also mention in the maybe readme ... the readme will also link the original path, which repo, which is this template repo"; then: "so for the automation part, I want each tab, each repo, if I apply this template, we'll be able to have a session or tag in their README, also showing some of the required this deployment or automation needed. Currently, you should turn on the like health, showing if it's turned on or not ... if I arranged like the auto health check every 4 hours, you should see that at least the cadence ... I want to have this status thing in the migration as well. And also you should turn it on for all other repos")

- Slug: settings-table
- Touches: skills/workflow-docs, dev/toy, .loop/regression.tsv, docs/wiki/Home.md, docs/wiki/Documentation.md, docs/wiki/Tests.md, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. docs.py renders a Settings section on Home and in README from the settings reference and the repo's .loop/config.json: name, meaning, how to set, default, and the repo's value marked overridden only when it differs; a toy repo with one overridden setting shows exactly that one marked
2. README carries one line naming and linking the template repo (from a template_repo setting, defaulting to the repo the skills were installed from), never a local path
3. the Settings section goes stale (and docs.py check says so) when a setting or its value changes, and wiki publish refreshes it
4. setup's adoption output names the Home Settings section and the README line
5. Home and README also show an Automation section: each routine (health, regression, digest email, and any repo routine named in config) with on or off, its cadence in plain words (for example every 4 hours), where it runs (this Mac or GitHub Actions), and its last run time when known, plus any one-time deployment step still owed by the owner; built from config, the installed launch agent and the workflow files, and stale when any of them changes

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
