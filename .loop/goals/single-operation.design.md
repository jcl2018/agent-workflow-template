# Design: single-operation

Goal done lines (frozen) are in `.loop/goals/single-operation.md`. This design meets them as written.

## Facts verified in the tree

- `operate.py` (8.5 KB): `cmd_claim` refuses workers, writes `<git common dir>/loop/operation.id` (last claim wins, per repo). `cmd_run` calls `cmd_claim` when `CLAUDE_SESSION_ID` is set. No pod concept exists.
- `board.py`: `repo_file()` is `~/.workflow-loop/repos`; `followed()` returns `(name, main_path, common_dir)` for the current repo plus every listed repo, de-duplicated by git common dir. The repo name is `basename(main)`. This is the pod. Reuse it, do not re-implement it.
- `checkin.render(root)` loads one repo (`lb.load`, `graph.classify`, `bs.queued`, `graph.ready`), then draws Dependencies with `board_lines.render(items)`. `render` drops any `depends` not in the same item set, so a cross-repo dependency is silently lost today. The "All sessions" table already has a repo column but only ever holds the one repo.
- `board_lines.py` is 16.8 KB and `board.py` 17.7 KB, so new code goes into `checkin.py` (8.6 KB) and `operate.py`, not those two.

## Approach

### A. Pod record and refusal (done line 2)

- Pod record: `~/.workflow-loop/operation.json` = `{"session": <id>, "repo": <name>}`. Written by `operate.py claim`; `operate.py run` reaches it through `cmd_claim` as today. The per-repo `operation.id` file is still written (the govern hook, MON-7, reads it) so no hook change.
- New helper `governed(common)` in `operate.py`: reads the record; the record governs a repo when that repo is the recorded one or any entry from `board.followed()` (the repos file). Compare by git common dir, not by name or path string.
- Refusal in `cmd_claim` (and so `run`): if a record exists, its session differs from this session id, and the current repo is governed by it, `sys.exit("REFUSED: operation session <id> already governs <repo-name> (pod). Fix: work from that session, or claim with --replace to take over.")`. The line names the existing session and the repo by name, never by path. Same session id re-claiming is a no-op success. `--replace` overwrites both the pod record and `operation.id`, and prints `(replaced <old>)`.
- A worker is still refused first, with the existing line (the worker check stays before the pod check).
- A repo outside the pod (not recorded, not in the repos file) claims normally, and the pod record is then rewritten to that session and repo. One pod, one operation.
- Corrupt or unreadable `operation.json` is treated as no record (a refusal on garbage would lock the owner out); a missing `~/.workflow-loop` is created.
- `HOME` is read through `os.path.expanduser`, so tests redirect it with `HOME=<tmp>`.

### B. Per-repo dependency blocks in the check-in (done line 3)

- Refactor `checkin.render` so the per-repo gathering (`runs`, `states`, `live`, `queue`) is a small function `gather(root, at)` that returns the items for one repo. `render` calls it for every `board.followed()` entry (own repo first, then the repos file order), skipping a repo whose `.loop` can't be read with a one-line note under Needs you (never a crash).
- The "All sessions" table lists the live sessions of every repo, with the repo name in the existing repo column. Counts in the first line cover the pod.
- New `grouped(blocks)` in `checkin.py` returns the Dependencies lines. For each repo, in order: a header line `== <repo name> ==` then `board_lines.render(items)` output without its trailing legend. The `LEGEND` is printed once at the end. Header and bands stay within 60 columns: a name longer than 54 characters is cut with `...`.
- Cross-repo dependency syntax: a dependency written `repo/slug` points at slug in repo `repo` (a plain `slug` stays same-repo). Inside the owning block the node shows `slug <- repo/slug` using the existing `<-` line (the `board_lines.render` filter keeps only same-repo ones for banding, so the cross-repo ones are re-attached in `grouped` by appending ` <- repo/slug` to that node's line, wrapped by `lb.fit`). After all blocks, a `Between repos` section lists each edge as `a-repo/x <- b-repo/y` with the mark of the target, so the edge is visible between blocks. An edge to a repo not in the pod or to a missing slug is shown with `(unknown)`, never dropped. No edges: the section is omitted.
- A repo with nothing live and nothing queued still gets its header and `- (none)`, so every pod repo is visible.
- `graph.ready` / `queued` already take dependency slugs; a `repo/slug` dependency is treated as unmet until that goal's state is merged in its repo (look it up in the gathered states). This keeps ready-ness correct without a graph change: `gather` rewrites resolved cross-repo deps before calling `graph.ready`.

### C. Docs, rows, tests

- `docs/wiki/Monitoring.md`: add MON-13 and MON-14 (text from the done line) as `Unreviewed`, then mark them Reviewed with `criteria.py` (user mode) using `LOOP_OWNER_WORDS` set to the owner's quote from the goal file. This is a step for the implementation to run; `criteria.py` seals the text hash, so the wording must be final before marking. Also add rows to the Tests table (`mon13-one-operation`, `mon14-repo-blocks`) and entries in `docs/wiki/Tests.md`.
- `dev/toy`: a fixture script builds three invented repos (`alpha-app`, `beta-svc`, `gamma-lib`; never real private names) with runs and queued goals, one cross-repo edge (`beta-svc/api` waits on `alpha-app/core`), and a temp `HOME` with a repos file.
- Regression: `.loop/regression.tsv` gets two rows (operation refusal; repo blocks). The refusal row must fail on the pre-change `operate.py` (second claim succeeds there) and pass after; record the before/after in the goal's test notes by running the row against `git stash`-free means: run it with the base commit's script (`git show main:...` into a temp dir) to see it fail, then with the new one.

## Alternatives considered

1. Pod record in the git common dir only (extend `operation.id`). Rejected: it is per repo, so two repos can each have an operation session, which is the exact problem.
2. Use the repos file alone as the pod, no record. Rejected: it can't say which session governs, so the refusal line can't name it.
3. Lock file with a PID or heartbeat so a dead session releases the pod. Rejected for now: session ids carry no liveness here and `--replace` covers a dead session. Listed as a risk.
4. Put the grouped renderer in `board_lines.py` or `board_page`. Rejected: `board_lines.py` is 16.8 KB, 18 KB is the cap. `checkin.py` has 9 KB of room.
5. Draw cross-repo edges as arrows inside one merged graph with repo prefixes. Rejected: it is the current "not clean" view the owner complained about. Blocks plus a Between repos list is what the done line asks for.
6. A new skill file or `pod.py`. Rejected: the 99-file cap and no new files; the code is small.

## Risks

- Size: `checkin.py` grows by roughly 2 KB and `operate.py` by about 1 KB; both stay far below 18 KB. Check with `wc -c` at the end; also confirm the package file count with `git ls-files | wc -l`-style check used by the existing size test.
- Stale pod record after the operation session dies: the owner gets a refusal and must pass `--replace`. The message says so. Accepted.
- Repos file entries that moved or aren't git repos: `followed()` already skips them; `gather` must tolerate a repo with no `.loop` (note, not crash).
- A slow or broken follower repo must not break the check-in of the others: wrap each `gather` in try/except and report in Needs you.
- Slug collisions across repos: handled because blocks are per repo and cross edges are always `repo/slug`.
- `lb.fit(out, 100)` wraps lines at 100 for the whole check-in, while the Dependencies lines must be at most 60; keep each line produced by `grouped` at most 60 (test asserts it, including a long repo name and long slugs).
- Existing tests that assert the single-repo Dependencies format must be updated for the header line; single-repo pods still show one block with the header (consistent, simplest).
- Reviewed-line sealing: any later edit to MON-13/14 wording relocks; finalize wording before marking.

## Test plan

1. `operate` refusal (regression row, also a unit test): temp `HOME`, two repos `alpha-app` and `beta-svc`, repos file lists `beta-svc`. Session `s1` claims in `alpha-app` and succeeds. Session `s2` claims in `beta-svc`: exit non-zero, message contains `s1` and `beta-svc` (or `alpha-app`), contains no path separators of the temp dir. `s1` again: success. `s2 --replace`: success and record shows `s2`. Worker env (`LOOP_ROLE=worker`) still refused with the old text. An unrelated third repo not in the pod claims and becomes the new record. Corrupt `operation.json` does not refuse. Run once against the pre-change script to see the failure (second claim succeeded), then post-change.
2. `cmd_run` path: with `CLAUDE_SESSION_ID=s2` run `--once` in a governed repo is refused with the same line.
3. Check-in grouping (done line 3): three-repo fixture (`alpha-app`, `beta-svc`, `gamma-lib`), goals including one cross-repo edge and one dependency to an unknown repo. Assert: each repo name appears as a `== name ==` header exactly once, in order; each repo's goals appear after their own header and before the next; the cross edge appears in the `Between repos` list and on the dependent node; the legend appears once; every Dependencies line has at most 60 characters; an empty repo shows `- (none)`; a single-repo pod shows one block.
4. Table and counts: the "All sessions" table carries each repo's name in the repo column; first-line counts sum the pod.
5. Sizes: assert each script under 18 KB and package at most 99 files (existing size check; run it).
6. Docs: `criteria.py` check passes (MON-13, MON-14 Reviewed, seals valid); wiki test table rows reference existing tests; the `Tests.md` anchors resolve.
7. Full suite via the repo's normal test lane, plus a manual look at a real check-in print with the repos file empty (single block) as the by-hand step.

## Verify by hand (for the goal file)

1. In two registered repos, claim from one session, then try to claim from a second. Expect: a REFUSED line naming the first session and the repo's name.
2. Run the check-in with two followed repos. Expect: one block per repo headed by its name, no line over 60 characters, and a cross-repo dependency listed between the blocks.
