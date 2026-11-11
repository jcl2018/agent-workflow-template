# Test lanes run safely side by side and never go stale after a merge (issues 150, 135, 152, 168, 151, 99)

- Slug: lane-control
- Touches: skills/workflow-regression, skills/workflow-delivery, dev/toy, .loop/regression.tsv, docs/wiki

Closes #150, closes #135, closes #152, closes #168, closes #151, closes #99, closes #128, closes #143, closes #172, closes #173, closes #178, closes #435.

Beyond the six issues, the owner approved the Regression PRD (tiered goal lanes, workflow tests, release Fixes lines and reopened issues, health timing, lane settings, ports and temp folders, FLAKY marks) and issues 128, 143, 172 (items 1 and 4), 173 and 178, and the urgent 435 (the sweep reaps only its own lane's markers). Follow-ups: 172 items 2-3, the recycled-pid check before killpg in flow.py and mend.py, and tests for the health.yml fetch step and the fixes_lines fallbacks.

## Done lines

Frozen. A wrong done line needs a new goal.

1. A machine-wide lane limit (a setting, default 2) makes an extra full lane wait its turn with a clear message instead of starting; flow.py and goal.py honor it (150)
2. Parallel red runs never race on .loop/regression.tsv (135)
3. A lane's latest result has one stable path, and a wait command blocks until it ends (152)
4. ship and pr rerun or refuse when HEAD moved since the lane they reuse (168)
5. Rerunning rows by id and merging main never leave the Tests tables stale for the next lane: the lane re-renders them first (151)
6. The operate-all test waits for the goal's report instead of a fixed sleep and passes 10 of 10 under load (99)
7. A toy test proves each, seen failing on the old code; the issues close when this merges

## Verify by hand

<!-- Numbered steps for a person, each with an Expect: line. A release needs this. -->

P is the package's skills folder (for example `P=~/.claude/skills` or this repo's `skills`).

1. In an empty git repo run `python3 $P/workflow-setup/scripts/setup.py --bare`, add three land rows that can fail
   (`python3 $P/workflow-regression/scripts/regression.py add r1 --level land --command "sleep 20; test ! -e broken"`,
   r2 and r3 likewise), commit them, prove each with `regression.py red rN --break "touch broken"`, then start three
   `LOOP_LANE_LIMIT=2 python3 $P/workflow-regression/scripts/regression.py run land` at once.
   Expect: one prints `LANE_WAIT: 2 of 2 lane slots busy` naming the other two, and all three exit 0.
2. While a goal's qa lane runs, run `python3 $P/workflow-delivery/scripts/role.py lane-wait SLUG qa`.
   Expect: it blocks, then exits 0 with the `LANE qa ...` line.
3. Rerun one row by id (`regression.py run r1`), then start the goal's lane with `role.py lane SLUG qa`.
   Expect: `LANE_PREP: re-rendered the Tests tables (commit ...)`, then a passing lane.
4. After a ship lane passes, make one commit and run `goal.py record SLUG ship --file F --in-session`.
   Expect: `REFUSED (no try used): HEAD moved since the ship lane passed ...`; after `role.py lane SLUG ship`
   passes, the same record goes through.
5. On a toy goal that adds a file no row's `# reads:` header names, start its qa lane, then its pr lane.
   Expect: qa prints `UNMAPPED <path>: no row declares it. Note: ...` and runs AFFECTED; pr prints
   `FULL (unmapped <path> at pr)`.
6. On a toy goal whose branch added a defect row linked to an issue and seen failing, run `release.py cut SLUG`.
   Expect: the CHANGELOG and the draft release notes list `Fixes #N: test <row>, seen failing <date>, passing`.
7. Write `abc\tfull\t1900\t2026-11-10` into `<git common dir>/loop/suite-times.tsv` of a toy repo and run
   `python3 $P/workflow-health/scripts/health.py check --family cost`.
   Expect: `WARN performance full-suite time: 31 min (limit 30, full_suite_minutes) ...`.
