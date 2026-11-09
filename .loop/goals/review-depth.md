# Make how deeply the plan and review steps run a setting, full by default

- Slug: review-depth
- Touches: skills/workflow-delivery, skills/workflow-setup, skills/loop-files.md, .loop/config.json, docs/wiki/Delivery.md, dev/toy

## Done lines

Frozen. A wrong done line needs a new goal.

1. A repo setting review_depth (full or condensed, default full) decides whether the plan and review steps run the mapped skill's full pipeline or a condensed version; with full, a worker never condenses on its own
2. Every step's recorded result says which depth ran, and the board and the pull request body show it
3. Setup writes review_depth with its default and a one-line explanation, and the settings reference lists it
4. A toy test proves full is the default, condensed runs only when set, and the recorded result names the depth

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->
