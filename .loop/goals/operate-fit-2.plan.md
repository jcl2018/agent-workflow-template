# Plan: operate-fit-2

Goal: `.loop/goals/operate-fit-2.md` (done lines and Verify by hand are frozen and belong to delivery; not restated or reopened here).
Design: `.loop/goals/operate-fit-2.design.md`. Reviewed by /autoplan (unattended; no UI or developer-tool scope). Every question took the recommended answer.

## Implementation plan

Order: `board_runs.py checkin`, then `board_status.py` (wiki error, github_state, closed, Goals filter), then `operate.py` call, then fake gh, then toy test, then docs.

1. **Check-in marker (done line 3).** `board_runs.py` gains `checkin`: atomic write (temp file, `os.replace`, like `write`) of `loop/checkin.json` `{"at": <now>}` under the git common dir. It takes no slug and touches no run record.
2. **Stale wiki errors (done line 1).** In `board_status.error_open`, before the merged test, return closed when the run's log has a `wiki published` entry after its last `wiki not published` entry (same `last(...)` scan; only for the wiki marker, so `release failed` is untouched). The merged rule is unchanged, including old records with no markers.
3. **Closed pull requests (done line 2).** Replace `github_merged` with `github_state(url, cwd)` returning `MERGED|CLOSED|OPEN|""` (same `gh pr view --json state`, same timeout, any doubt `""`). Call it once per done run with a PR and reuse the answer for `merged_now` and a new `closed_now` (done, record not merged, state CLOSED). Closed goals are dropped from `live`, add one Roadmap line after the merged line `closed without merging: #71, #72`, and never get the `waiting to merge` block. Open or unknown keeps `[awaiting merge]`. Dependents of a closed goal stay blocked (they keep the dependency in `depends`).
4. **Goals filter (done line 3).** `goals` = `goal_lines` only for runs that are running, waiting (ASKING), queued (queued goals read their goal file) or merged since the check-in. Merge time is the stamp on the run's `merged` log entry, else `updated`; after `checkin.json["at"]`. No check-in file: every merged goal counts as new once. Closed and other merged goals are absent from Goals.
5. **`operate.py`.** After a full block is printed (the `else` branch of `one_pass`, not the one-line "nothing changed" answer) call `board_runs.py checkin`. A failure to write the marker prints nothing fatal.
6. **Fake gh.** `dev/toy/fakegh/gh` `pr view` reads `FAKE_GH_PR_STATE_<n>` (n from the URL's trailing number) before `FAKE_GH_PR_STATE`. No other change to the fake.
7. **Toy test (done line 4).** Extend `dev/toy/test-operate-fit.sh`, keeping `rec`, `gh`, `late`, `fresh`: a goal with `wiki not published` then `wiki published` and a leftover `wiki_error` (unmerged); a CLOSED-PR goal and an OPEN-PR goal; two old merged goals and one merged after a seeded `checkin.json`; plus running, waiting and queued goals. Assertions: cleared error absent from Needs you; closed reads closed, not awaiting merge, open still awaiting merge; Goals holds done lines only for running, waiting, queued and the newly merged goal, old merged slugs only in the merged line; `operate.py` writes `checkin.json` after a full block and not after a quiet pass. `test-operate.sh` and `test-wiki.sh` stay green.
8. **Docs.** `references/operation.md` and `docs/wiki/Monitoring.md` mention the new Goals rule, the closed line and `board_runs.py checkin`; `docs.py check` passes; scripts stay under 20 KB (`board_status.py` ~12 KB now, `operate.py` ~5 KB).

## Failure modes

| Step | Failure | Handling |
|---|---|---|
| 2 | A publish that logged later than a real new failure hides it | compare log order only, so a later `wiki not published` reopens it |
| 3 | `gh` missing or slow | `""` keeps awaiting merge; one call per run, 20 s cap |
| 3 | Dependent of a closed goal renders a `? not a goal here` node | accepted: stays blocked; `status_graph.py` is outside Touches |
| 4 | Unparseable log stamp | fall back to `updated`; if none, count as old |
| 5 | Marker write fails | ignored; next block lists the merged goals again (harmless) |
| 7 | fakegh change breaks other toy tests | env vars are additive; run all toy tests that use the fake |

## Review record

<!-- autoplan-accepted:ceo -->
- Keep the fix on the read side: `wiki.py` and `status_graph.py` stay unchanged; old records are fixed by how they are read.
<!-- /autoplan-accepted:ceo -->
<!-- autoplan-accepted:eng -->
- `github_state` is called once per done run and reused; the fake gh change is limited to per-PR state variables.
- The toy test asserts each of the four done lines and the check-in write rule.
<!-- /autoplan-accepted:eng -->
