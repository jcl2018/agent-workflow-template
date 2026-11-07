# Make the package fit Agensi's published rules and be ready for a draft release

- Slug: agensi-fit
- Level: 1
- Touches: dev/package.py, dev/test-package.sh, listing.json, README.md

## Done lines

Frozen. A wrong done line needs a new goal.

1. The ZIP dev/package.py builds holds shared/loop-files.md and no skills/loop-files.md, and dev/test-package.sh proves it
2. dev/package.py refuses the dangerous commands and phrases Agensi's scan fails, and a README with no title, and notes shell=True
3. listing.json says seven skills, lists each command once, and states what it requires and its limitations

## Verify by hand

1. Run `python3 dev/package.py --out dist/agent-workflow-template.zip`, then `unzip -l dist/agent-workflow-template.zip | grep -c SKILL.md`.
   Expect: it prints PASS with a NOTE about `shell=True`, then 7.
2. Run `unzip -l dist/agent-workflow-template.zip | grep loop-files`.
   Expect: one line, `shared/loop-files.md`.
3. Open the repo's Actions tab, pick regression, and choose Run workflow on `main`.
   Expect: the run ends green, and every row prints PASS in its log.
4. Install the ZIP's seven `skills/` folders in an agent, and start one level 0 goal on a test repo.
   Expect: it ends at a pull request.

## Design

Keep the repo layout, and map `loop-files.md` to `shared/` only in the ZIP. Keep `shell=True`: check commands are the
repo's own strings, so changing how they're spelled would only hide them from the scan. The listing says so instead.
What could go wrong: an agent on Agensi can't reach a sibling script, so those features must say so and skip.

## Plan

1. Map the file in `dev/package.py`, proved by `dev/test-package.sh`.
2. Add the scan's rules to `dev/package.py`, proved by its planted faults.
3. Update `listing.json`, proved by the diff.

## Evidence

`python3 -c` on listing.json: 48 commands, 48 distinct. The full list, each once:
setup poc go report dashboard resume cut leave ask show new step check judge verdict pr wait answer finding survey add criteria publish restore init watch queue run sync seed red workflow board cadence repos note session retire handoff start status promote save take review attach features move
