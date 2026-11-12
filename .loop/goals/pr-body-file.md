# Pass every long gh text (PR body, PR edit body, release notes) through --body-file or --notes-file instead of the command line, so goal.py pr and release work on native Windows (https://github.com/jcl2018/agent-workflow-template/issues/2879)

- Slug: pr-body-file
- Touches: skills/workflow-delivery/scripts, skills/workflow-release/scripts

## Done lines

Frozen. A wrong done line needs a new goal.

1. goal.py pr opens a PR with a body over 32,000 characters on native Windows, and no gh call in skills/ passes a body or notes text as an argument

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
